"""Single-worker Luna evaluation with durable per-request recovery."""
from dataclasses import asdict
from datetime import datetime,timezone
from pathlib import Path
import argparse
import time
from eval import run_luna_experiment as previous
from eval import analyze_final_hy3 as analysis
from eval.durable_requests import DurableRequests,TransportPaused,write
from eval.reference_annotation_v2 import read
from paperaudit.hy3_client import Hy3Client
from paperaudit.models import ParsedPaper,ClaimCategory
from paperaudit.service import AuditService

ROOT=previous.ROOT
OUT=ROOT/'eval/luna_reliable_20260907'

def prepare():
    previous.OUT=OUT
    if (OUT/'protocol.json').exists(): return
    previous.prepare()
    p=read(OUT/'protocol.json')
    p.update(workers=1,retry_policy='Each request up to 3 attempts per invocation, 6 lifetime; wait 5/15 seconds. Cache ordered successful responses per run. Stop on exhausted retries or auth/billing. No output-driven rerun.',
        organizer_policy='User confirms organizer accepts other models.',
        pilot_gate='Independent historical DeepFM high/medium/low reports; require 3 completed application audits before formal run. No score-based tuning.',
        interpretation='Same-model Luna reference agreement; pre-existing reports and labels reused after prior exploratory results. Not a new unseen holdout.')
    p['source_sha256'].update({str(path.relative_to(ROOT)):previous.base.sha(path) for path in [Path(__file__).resolve(),ROOT/'eval/durable_requests.py']})
    write(OUT/'protocol.json',p)
    (OUT/'README.md').write_text('# Luna 正式恢复实验\n\n单并发、240秒超时、有限网络重试、逐请求断点恢复。原实验均保留。主办方接受其他模型（用户确认）。\n\n'
        '36份报告保持不变，包括6份Hy3生成的自然报告。Luna参考标注属于同模型参考；这批数据已用于前期探索，不再宣称全新未见测试集。\n\n'
        '先运行历史DeepFM三档开发检查，仅以能否完成为门槛，不按得分调整方法。96次正式运行分别保存请求检查点，不跨重复运行共享结果。\n',encoding='utf-8')

def status(stage,**kwargs):
    write(OUT/'workflow_status.json',dict(stage=stage,updated_at=datetime.now(timezone.utc).isoformat(),**kwargs))

def run_one(paper,text,scope,path,mode,rid,repeat,transport_factory=DurableRequests):
    if path.exists(): return read(path)
    config=previous.settings();client=Hy3Client(config);client._client.max_retries=0
    client._client.chat.completions.create=transport_factory(client._client.chat.completions.create,path.parent/(path.stem+'_checkpoints'))
    start=time.monotonic()
    try:
        run=AuditService(config,client=client).audit(paper,text,scope,mode=mode)
        result=dict(status='ok',report_id=rid,repeat=repeat,audit=run.model_dump(mode='json'))
    except TransportPaused:
        raise
    except Exception as exc:
        result=dict(status='error',report_id=rid,repeat=repeat,error_type=type(exc).__name__)
    finally:
        client._client.close()
    requests=[]
    for checkpoint in sorted((path.parent/(path.stem+'_checkpoints')).glob('*.json')):
        data=read(checkpoint)
        requests.extend(data['attempts'])
    result.update(seconds=time.monotonic()-start,seconds_note='This invocation only; total network attempts recorded separately',requests=requests,raw_outputs=client.raw_outputs)
    write(path,result)
    write(path.with_name(path.stem+'_requests.json'),requests)
    return result

def pilot():
    source=ROOT/'eval/hy3_pilot_20260907'
    paper=ParsedPaper.model_validate(read(source/'paper_evidence.json'))
    for r in read(source/'blind_inputs.json'):
        status('pilot',report=r['report_id'])
        result=run_one(paper,r['report_text'],list(ClaimCategory),OUT/'pilot'/(r['report_id']+'.json'),'luna_reliable_pilot',r['report_id'],1)
        if result['status']!='ok': raise RuntimeError('Pilot audit failed; do not launch formal run')

def audit():
    p=read(OUT/'protocol.json');runtime=asdict(previous.settings());runtime.pop('api_key')
    assert runtime==p['runtime']
    for name,h in p['source_sha256'].items(): assert previous.base.sha(ROOT/name)==h,name
    for name,h in p['input_sha256'].items(): assert previous.base.sha(OUT/name)==h,name
    for name,h in read(OUT/'reference_freeze.json')['sha256'].items(): assert previous.base.sha(OUT/name)==h,name
    papers={r['paper_id']:ParsedPaper.model_validate(read(OUT/r['evidence_path'])) for r in read(OUT/'inputs/papers.json')}
    for i in (1,2,3):
        for r in p['reports']:
            if i>r['repeats']: continue
            status('auditing',report=r['report_id'],repeat=i)
            result=run_one(papers[r['paper_id']],(OUT/r['report_path']).read_text(encoding='utf-8'),
                [ClaimCategory(c) for c in p['scope']],OUT/f'run_{i}'/(r['report_id']+'.json'),'luna_reliable_formal',r['report_id'],i)
            print(r['report_id']+'/'+str(i)+' '+result['status'],flush=True)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['prepare','pilot','all']);args=parser.parse_args()
    prepare()
    if args.phase=='prepare': return
    try:
        pilot()
        if args.phase=='pilot': status('pilot_complete');return
        audit()
        status('audits_complete_analysis_pending')
    except Exception as exc:
        status('paused_error',error_type=type(exc).__name__,detail=str(exc)[:250])
        raise

if __name__=='__main__': main()
