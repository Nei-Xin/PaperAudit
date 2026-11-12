"""Frozen full development comparison of investigation with/without reusable repo maps.

Generate one map per exact code variant, then alternate both arms for all 39
questions, three repeats each. Generation cost is separate and also amortized.
No fallback, verifier, resuming, overwriting, or paid retries.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from hashlib import sha256
import json
from pathlib import Path
from threading import Lock
from time import monotonic

from paperaudit.agents.code_investigator import CodeInvestigator
from paperaudit.agents.repo_mapper import build_repo_map
from paperaudit.code_parser import parse_code_zip
from paperaudit.config import Settings
from paperaudit.consistency_inputs import index_hash
from paperaudit.hy3_client import Hy3Client
from paperaudit.pdf_parser import parse_pdf
from paperaudit.request_budget import RequestBudget
from .run import build_archive
from .score import predict

HERE=Path(__file__).resolve().parent

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--data',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--run',action='store_true');args=ap.parse_args()
    cases=json.loads((HERE/'cases.json').read_text());items=cases['items'];settings=Settings.from_env()
    variants=sorted({(i['paper'],i['mutation'] or '') for i in items})
    parsed={};inputs={}
    for name,mutation in variants:
        spec=cases['papers'][name];pdf=(args.data/name/'paper.pdf').read_bytes();raw=(args.data/name/'repo.zip').read_bytes()
        assert sha256(pdf).hexdigest()==spec['pdf_sha256'] and sha256(raw).hexdigest()==spec['zip_sha256']
        archive=build_archive(raw,spec['include'],cases['mutations'][mutation] if mutation else [])
        paper=parse_pdf(pdf);codebase=parse_code_zip(archive,f'{name}.zip');key=name+':'+(mutation or 'original')
        parsed[key]=(paper,codebase);inputs[key]={'pdf_sha256':sha256(pdf).hexdigest(),'archive_sha256':sha256(archive).hexdigest(),'code_hash':index_hash(codebase)}
    root=HERE.parents[1];sources=[*root.joinpath('src/paperaudit').rglob('*.py'),Path(__file__),HERE/'run.py',HERE/'score.py',HERE/'cases.json',root/'uv.lock']
    protocol={'split':'previously seen development set; no independent holdout',
        'model':settings.model,'temperature':settings.temperature,'reasoning_effort':settings.reasoning_effort,
        'items':[i['id'] for i in items],'repeats':3,'arms':['baseline','map'],'workers':3,
        'inputs':inputs,'sources':{str(p.relative_to(root)):sha256(p.read_bytes()).hexdigest() for p in sources},
        'max_requests':len(items)*3*2*11+len(variants)*4,
        'investigation':{'requests':11,'seconds':180,'verifier':False,'fallback':False},
        'maps':{'one_per_exact_code_variant':True,'variant_count':len(variants),'requests_each':4,'seconds_each':120,
                'question_or_labels_visible':False,'persisted_before_investigations':True},
        'scoring':'Unchanged score.predict. Errors, missing answers, abstentions stay in all denominators. No independent finding-level annotation.',
        'decision':'Enable by default only if map arm matches at least baseline reference accuracy and reduces total requests INCLUDING map generation by >=5%. Otherwise retain opt-in.',
        'limits':['One generated map per code variant, reused across repeats: map-generation variance not measured.',
                  'Equal investigation budgets; cold-start and warm-cache costs reported separately.',
                  'This isolates navigation in unverified investigations; not a test of planning or semantic review.',
                  'Per-item repeats are correlated; no statistical-significance or generalization claim.']}
    args.output.mkdir(parents=True,exist_ok=False)
    (args.output/'protocol.json').write_text(json.dumps(protocol,ensure_ascii=False,indent=2)+'\n')
    if not args.run:print(json.dumps({'items':len(items),'variants':len(variants),'max_requests':protocol['max_requests']}));return
    lock=Lock()
    def record(file,row):
        with lock,(args.output/file).open('a') as h:h.write(json.dumps(row,ensure_ascii=False)+'\n')
    def generate(key):
        record('dispatch.jsonl',{'kind':'map','variant':key})
        budget=RequestBudget(max_requests=4,max_seconds=120)
        memory=build_repo_map(Hy3Client(settings),parsed[key][1],settings.model,budget=budget)
        record('maps.jsonl',{'variant':key,'map':memory.model_dump(mode='json')})
        print(json.dumps({'map':key,'entries':len(memory.entries),'requests':memory.requests,'stop':memory.stop_reason}),flush=True)
        return key,memory
    with ThreadPoolExecutor(max_workers=3) as pool:maps=dict(pool.map(generate,parsed))
    def investigate(item,arm,repeat):
        key=item['paper']+':'+(item['mutation'] or 'original');paper,codebase=parsed[key]
        record('dispatch.jsonl',{'kind':'investigation','item':item['id'],'arm':arm,'repeat':repeat})
        budget=RequestBudget(max_requests=11,max_seconds=180);start=monotonic()
        row={'item':item['id'],'arm':arm,'repeat':repeat,'variant':key,'mode':'agent'}
        try:
            answer,trace=CodeInvestigator(Hy3Client(settings),paper,codebase,settings.model,budget=budget,
                repo_map=maps[key] if arm=='map' else None).run(item['question'],'joint')
            row.update(status=answer.status.value if answer else 'INSUFFICIENT_EVIDENCE',
                findings=[f.model_dump(mode='json') for f in answer.findings] if answer else [],
                trace=trace.model_dump(mode='json'))
            if answer is None:row['error']='NoAnswer:'+trace.stop_reason
        except Exception as exc:row['error']=type(exc).__name__
        row.update(requests=budget.requests,tokens=budget.tokens,seconds=round(monotonic()-start,2))
        row['predicted']=predict(row,item);row['expected']=item['expected'];row['correct']=row['predicted']==row['expected']
        record('observations.jsonl',row);return row
    jobs=[]
    for repeat in range(3):
        for n,item in enumerate(items):
            for arm in (['baseline','map'] if (n+repeat)%2==0 else ['map','baseline']):jobs.append((item,arm,repeat))
    rows=[]
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures=[pool.submit(investigate,*job) for job in jobs]
        for future in as_completed(futures):
            row=future.result();rows.append(row)
            print(json.dumps({'completed':len(rows),'item':row['item'],'arm':row['arm'],'requests':row['requests'],'correct':row['correct']}),flush=True)
    summary={}
    for arm in ['baseline','map']:
        group=[r for r in rows if r['arm']==arm]
        summary[arm]={'n':len(group),'correct':sum(r['correct'] for r in group),
            'requests':sum(r['requests'] for r in group),'tokens':sum(r['tokens'] for r in group),
            'seconds_sum':round(sum(r['seconds'] for r in group),2),'errors':sum('error' in r for r in group),
            'map_used':sum((r.get('trace') or {}).get('repo_map_used',False) for r in group),
            'list_dir_calls':sum(s['tool']=='list_dir' for r in group for s in (r.get('trace') or {}).get('steps',[])),
            'citation_repair_investigations':sum(bool((r.get('trace') or {}).get('first_rejections')) for r in group)}
    summary['generation']={'maps':len(maps),'usable':sum(bool(m.entries) for m in maps.values()),
        'requests':sum(m.requests for m in maps.values()),'tokens':sum(m.tokens for m in maps.values()),
        'seconds_sum':round(sum(m.elapsed_seconds for m in maps.values()),2)}
    summary['map_including_generation']={k:summary['map'][k]+summary['generation'][k] for k in ['requests','tokens','seconds_sum']}
    summary['enable_by_rule']=(summary['map']['correct']>=summary['baseline']['correct'] and
        summary['map_including_generation']['requests']<=.95*summary['baseline']['requests'])
    (args.output/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(summary),flush=True)

if __name__=='__main__':main()
