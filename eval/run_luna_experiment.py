"""Fresh Luna rerun on the identical frozen 36 reports; never rewrite Hy3 data."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, replace
from datetime import datetime, timezone
from pathlib import Path
import argparse
import json
import shutil
import time
from threading import Event
from eval import final_hy3_experiment as base
from eval import analyze_final_hy3 as analysis
from eval.reference_annotation_v2 import read, save
from paperaudit.config import Settings
from paperaudit.hy3_client import Hy3Client
from paperaudit.models import ClaimCategory, ParsedPaper
from paperaudit.service import AuditService

ROOT=base.ROOT
SOURCE=ROOT/'eval/hy3_final_20260907'
OUT=ROOT/'eval/luna_final_20260907'

def settings():
    value=Settings.from_env()
    assert value.model=='gpt-5.6-luna'
    return replace(value,timeout_seconds=240)

def prepare():
    if (OUT/'protocol.json').exists():
        return
    old=read(SOURCE/'protocol.json')
    for name,h in old['input_sha256'].items():
        assert base.sha(SOURCE/name)==h,name
    for name,h in read(SOURCE/'reference_freeze.json')['sha256'].items():
        assert base.sha(SOURCE/name)==h,name
    OUT.mkdir(parents=True,exist_ok=True)
    for folder in ('inputs','reports','reference','reference_recovery'):
        shutil.copytree(SOURCE/folder,OUT/folder,dirs_exist_ok=True)
    for name in ('reference_selection.json','reference_freeze.json'):
        shutil.copy2(SOURCE/name,OUT/name)
    runtime=asdict(settings());runtime.pop('api_key')
    inputs=[p for folder in ('inputs','reports') for p in (OUT/folder).rglob('*') if p.is_file()]
    sources=list((ROOT/'src/paperaudit').rglob('*.py'))+[Path(__file__).resolve(),ROOT/'eval/analyze_final_hy3.py',ROOT/'eval/final_hy3_experiment.py']
    save(OUT/'protocol.json',dict(created_at=datetime.now(timezone.utc).isoformat(),model='gpt-5.6-luna',runtime=runtime,
        reports=old['reports'],scope=old['scope'],thresholds=old['thresholds'],workers=2,expected_audits=96,
        input_sha256={str(p.relative_to(OUT)):base.sha(p) for p in inputs},
        source_sha256={str(p.relative_to(ROOT)):base.sha(p) for p in sources},
        source_protocol_sha256=base.sha(SOURCE/'protocol.json'),
        changes=['Judge changed from Hy3 to Luna','Timeout 120 to 240 seconds','Concurrency 4 to 2'],
        annotation='Reuse existing frozen Luna model-assisted reference. Same-model agreement; no independent-model or human validation claim.',
        natural_reports='Unchanged original Hy3-generated reports, now audited by Luna; not Luna-generated.',
        reasoning='Application sends chat_template_kwargs.reasoning_effort=high; provider handling not independently verified.',
        retry_policy='SDK retries disabled; existing application internal retries unchanged. Preserve failed attempts; stop new requests on 401/402/403.'))
    (OUT/'README.md').write_text('# Luna 同数据重跑实验\n\n使用相同36份报告，重新执行96次完整审计。保留原Hy3数据，不复用Hy3判断。\n\n'
        '参考标注仍来自Luna，因此结果为同模型参考一致性。自然报告仍由Hy3生成，不改称Luna生成。\n\n'
        '本轮并发2、超时240秒；不直接将差异全归因于模型。应用其余参数及评分规则保持一致。失败不静默重跑。\n\n'
        'Luna实验不满足原任务要求使用Hy3的模型限制，应作为替代模型实验材料。\n',encoding='utf-8')

def audit():
    p=read(OUT/'protocol.json'); config=settings(); runtime=asdict(config);runtime.pop('api_key')
    assert runtime==p['runtime']
    for name,h in p['source_sha256'].items():
        assert base.sha(ROOT/name)==h,name
    for name,h in p['input_sha256'].items():
        assert base.sha(OUT/name)==h,name
    for name,h in read(OUT/'reference_freeze.json')['sha256'].items():
        assert base.sha(OUT/name)==h,name
    papers={r['paper_id']:ParsedPaper.model_validate(read(OUT/r['evidence_path'])) for r in read(OUT/'inputs/papers.json')}
    stop=Event()
    jobs=[(r,i) for i in (1,2,3) for r in p['reports'] if i<=r['repeats']]
    def job(pair):
        r,i=pair; rid=r['report_id']; path=OUT/f'run_{i}'/(rid+'.json')
        if path.exists() or stop.is_set():
            return
        if path.with_name(rid+'_requests.json').exists():
            raise RuntimeError('Interrupted audit has request log; explicit recovery required: '+rid)
        client=Hy3Client(config);client._client.max_retries=0; original=client._client.chat.completions.create; requests=[]
        def tracked(**kwargs):
            if stop.is_set():
                raise RuntimeError('Stopped after authentication/billing rejection')
            start=time.monotonic()
            try:
                response=original(**kwargs)
                requests.append(dict(status='ok',seconds=time.monotonic()-start,model=response.model,response_id=response.id,
                    usage=response.usage.model_dump() if response.usage else None))
                return response
            except Exception as exc:
                code=getattr(exc,'status_code',None)
                if code in (401,402,403):
                    stop.set()
                requests.append(dict(status='error',seconds=time.monotonic()-start,error_type=type(exc).__name__,http_status=code))
                raise
            finally:
                save(path.with_name(rid+'_requests.json'),requests)
        client._client.chat.completions.create=tracked
        start=time.monotonic();result=dict(report_id=rid,repeat=i,model=config.model)
        print('Start '+rid+'/'+str(i),flush=True)
        try:
            run=AuditService(config,client=client).audit(papers[r['paper_id']],(OUT/r['report_path']).read_text(encoding='utf-8'),
                [ClaimCategory(c) for c in p['scope']],mode='luna_frozen_rerun')
            result.update(status='ok',audit=run.model_dump(mode='json'))
        except Exception as exc:
            result.update(status='error',error_type=type(exc).__name__,http_status=getattr(exc,'status_code',None))
        finally:
            result.update(seconds=time.monotonic()-start,requests=requests,raw_outputs=client.raw_outputs)
            save(path,result);client._client.close()
        print('Finished '+rid+'/'+str(i)+' '+result['status'],flush=True)
    with ThreadPoolExecutor(max_workers=p['workers']) as pool:
        list(pool.map(job,jobs))
    if stop.is_set():
        raise RuntimeError('Billing/authentication rejected; pipeline stopped')

def report():
    s=read(OUT/'analysis/summary.json')
    text='# Luna 同数据重跑实验报告\n\n'
    text+=f'计划96次，记录{s["attempted_audits"]}次，成功{s["successful_audits"]}次。此轮使用gpt-5.6-luna。\n\n'
    text+='沿用6篇论文、18份控制报告、6份原Hy3生成的自然报告、12份对抗报告。参考标注来自Luna，与被测模型相同；模型间独立性不成立，不能称为人工准确率。超时改为240秒，并发改为2，因此与Hy3的差异不能仅归因于模型。\n\n'
    text+='## 分组端到端结果\n\n| 组别 | 参考观测数 | 标签一致率（含失败） | 已判定一致率 | 语义召回 |\n| --- | --- | --- | --- | --- |\n'
    def pct(v):
        return 'N/A' if v is None else f'{100*v:.2f}%'
    for k,g in s['groups'].items():
        text+=f'| {k} | {g["resolved_reference_observations"]} | {pct(g["end_to_end_label_accuracy"])} | {pct(g["decided_label_accuracy"])} | {pct(g["semantic_fact_recall"])} |\n'
    eligible=[r for r in s['rankings'] if all(r[k] is not None for k in ('high','medium','low'))]
    text+=f'\n具备完整三档各三次结果的论文：{len(eligible)}/6。原计划排序交付通过率：{pct(s["ranking_rate"])}；缺失不算通过，不等于实际排序错误。整体分数标准差均值：{s["controlled_mean_score_std"]}。\n\n'
    text+='完整明细见analysis目录。任务失败、语义漏抽取与弃权不计正确；无有效分母时显示N/A。结果受参考模型偏差、6篇论文的小样本和重复观测相关性限制。本轮不宣称满足Hy3指定模型要求。\n'
    (OUT/'submission_report.md').write_text(text,encoding='utf-8')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['prepare','audit','all']);args=parser.parse_args()
    if args.phase=='prepare':
        prepare();return
    if args.phase=='audit':
        audit();return
    try:
        prepare()
        analysis.OUT=OUT
        for stage,fn in [('auditing',audit),('aligning',analysis.align),('summarizing',analysis.summarize),('writing_report',report)]:
            save(OUT/'workflow_status.json',dict(stage=stage,updated_at=datetime.now(timezone.utc).isoformat()))
            fn()
        save(OUT/'workflow_status.json',dict(stage='data_and_markdown_complete',updated_at=datetime.now(timezone.utc).isoformat()))
    except Exception as exc:
        save(OUT/'workflow_status.json',dict(stage='failed',error_type=type(exc).__name__,updated_at=datetime.now(timezone.utc).isoformat()))
        raise

if __name__=='__main__':
    main()
