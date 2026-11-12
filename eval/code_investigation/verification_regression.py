"""Frozen development regression: old review, captions only, scope only, both.

All arms review the exact same fixed findings. Context is rebuilt from hash-
checked PDFs using the production layout linker and workspace observation path.
No paid run resumes, overwrites, or tunes itself after results are available.
"""
from __future__ import annotations

import argparse
import copy
from concurrent.futures import ThreadPoolExecutor, as_completed
from hashlib import sha256
import json
from pathlib import Path
from threading import Lock
from time import monotonic

from paperaudit.agents.code_tools import CodeWorkspace
from paperaudit.agents.finding_verifier import verify_answer
from paperaudit.config import Settings
from paperaudit.hy3_client import Hy3Client
from paperaudit.models import JointAnswer, PaperCodeFinding, ParsedCodebase
from paperaudit.pdf_parser import parse_pdf
from paperaudit.request_budget import RequestBudget, use_request_budget

HERE = Path(__file__).resolve().parent
ARMS = ('v1', 'captions_only', 'scope_only', 'v2')
SCOPED_PROMPT = (HERE/'verification_scope_v2_prompt.txt').read_text()


def fixtures(data):
    previous = HERE/'results/verification-dev-20261112'
    stored = {(r['item'], r['repeat']): r for line in (previous/'reviewed-findings.jsonl').read_text().splitlines()
              if (r := json.loads(line))}
    acceptance = [json.loads(line) for line in (previous/'acceptance.jsonl').read_text().splitlines()]
    items = []
    def add(name, paper, f, expected, provenance, reason):
        finding = PaperCodeFinding.model_validate({k:f[k] for k in ('text','verdict','paper_citations','code_citations')})
        items.append({'id':name,'paper':paper,'finding':finding,'expected':expected,'provenance':provenance,'reason':reason})
    def old(name, item, repeat, n, expected, reason):
        add(name,item.split('-')[0],stored[item,repeat]['findings'][n],expected,
            f'reviewed-findings.jsonl:{item}:{repeat}:finding{n}',reason)
    old('wrong_experiment','mae-warmupx',2,0,False,'Table belongs to supervised training from scratch, not pretraining.')
    for name, source, expected in [('reference_marker_error','wrong-consistent',False),
                                  ('correct_pretrain_difference','correct-inconsistent',True),
                                  ('correct_pretrain_match','correct-consistent',True)]:
        row=next(r for r in acceptance if r['fixture']==source and r['repeat']==1)
        add(name,'mae',row['before']['findings'][0],expected,f'acceptance.jsonl:{source}:1',
            'Pretraining table value is 40; [20] is a reference marker, not the value.')
    old('b_init_neighbor_difference','lora-b-init',1,0,True,'Only B zero-initialization is asserted; A is out of scope.')
    original=items[-1]['finding'].model_dump(mode='json')
    altered=copy.deepcopy(original)
    changed=0
    for c in altered['code_citations']:
        changed += c['text'].count('nn.init.zeros_(self.lora_B)')
        c['text']=c['text'].replace('nn.init.zeros_(self.lora_B)','nn.init.ones_(self.lora_B)')
    assert changed==1
    add('b_init_actual_difference','lora',altered,False,
        'Controlled evidence mutation of b_init_neighbor_difference: zeros_(B) -> ones_(B), exactly once.',
        'The target B now differs; scope restriction must not accept this wrong consistency claim.')
    old('scaling_same_roles','lora-scaling',0,0,True,'Both paper and code define rank-normalized alpha scaling.')
    old('scaling_real_difference','lora-scalingx',0,0,True,'The controlled scaling change supports the original INCONSISTENT verdict.')
    old('default_mask_difference','mae-maskx',0,0,True,'Explicit Table 1 default 75% differs from code default 0.6.')
    old('missing_code_default','gcn-dropoutx',2,0,False,'Only FLAGS.dropout use is cited; its value is not defined.')
    old('missing_normalization_formula','gcn-renorm',2,0,False,'Paper excerpt stops before the symmetric normalization formula.')
    old('missing_optimizer_recipe','mae-linprobe',2,0,False,'The cited prose refers to a recipe but does not identify the optimizer.')
    cases=json.loads((HERE/'cases.json').read_text())
    inputs={}; parsed={}
    for name in sorted({i['paper'] for i in items}):
        pdf=(data/name/'paper.pdf').read_bytes()
        digest=sha256(pdf).hexdigest()
        assert digest==cases['papers'][name]['pdf_sha256']
        parsed[name]=parse_pdf(pdf);inputs[name]=digest
    for item in items:
        paper=parsed[item['paper']]
        f=item.pop('finding')
        anchors=[]
        with CodeWorkspace(paper,ParsedCodebase(name='no_code_reads',files=[],chunks=[])) as workspace:
            for a in f.paper_citations:
                chunk=workspace.paper_chunks[a.chunk_id]
                assert chunk.content==a.text, (item['id'],a.chunk_id,'parsed evidence changed')
                rendered=workspace._paper_blocks([chunk])
                assert a.chunk_id in workspace.observed_chunks and rendered
                anchors.append(a.model_copy(update={'source_context':workspace.observed_context.get(a.chunk_id,[])}))
        f=f.model_copy(update={'paper_citations':anchors})
        item['answer']=JointAnswer(question='Frozen finding review',answer='Not sent to reviewer',scope='joint',
                                  status='ANSWERED',findings=[f]).model_dump(mode='json')
    return items, inputs


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--data',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--run',action='store_true')
    args=ap.parse_args()
    items,inputs=fixtures(args.data)
    settings=Settings.from_env()
    old_prompt=(HERE/'verification_v1_prompt.txt').read_text()
    root=HERE.parents[1]
    sources=[*root.joinpath('src/paperaudit').rglob('*.py'),Path(__file__),HERE/'verification_v1_prompt.txt',HERE/'verification_scope_v2_prompt.txt']
    protocol={'split':'development regression, previously seen cases; no holdout claim',
        'model':settings.model,'temperature':settings.temperature,'reasoning_effort':settings.reasoning_effort,
        'inputs':inputs,'arms':ARMS,'repeats':3,'workers':3,'max_requests':len(items)*len(ARMS)*3,
        'per_review':{'requests':1,'seconds':180,'no_retries':True},
        'assessor':'Expected support labels defined by implementation assistant before running; no independent annotation.',
        'scoring':'Expected supported: only passed is correct. Expected unsupported: only failed is correct. '
                  'Errors or not_reviewed are unsuccessful in both groups and remain in denominators.',
        'sources':{str(p.relative_to(root)):sha256(p.read_bytes()).hexdigest() for p in sources},
        'prompts':{'v1':old_prompt,'v2':SCOPED_PROMPT},
        'selection':'Twelve fixed cases: eight prior development findings, three original warmup fixtures, '
                    'and one controlled B initialization mutation. All previously known topics.',
        'mechanisms':{'captions_only':'v1 prompt with new source_context',
                      'scope_only':'v2 prompt without source_context',
                      'v2':'v2 prompt with source_context','v1':'v1 prompt, exact old payload shape'},
        'limits':['Fixed evidence, not full end-to-end investigation accuracy.',
                  'Captions linked by layout are hints, not guaranteed table understanding.',
                  'No adaptation or paid rerun after inspecting this batch.']}
    args.output.mkdir(parents=True,exist_ok=False)
    frozen=json.dumps(items,ensure_ascii=False,indent=2)+'\n'
    protocol['fixtures_sha256']=sha256(frozen.encode()).hexdigest()
    (args.output/'fixtures.json').write_text(frozen)
    (args.output/'protocol.json').write_text(json.dumps(protocol,ensure_ascii=False,indent=2)+'\n')
    if not args.run:
        print(json.dumps({'fixtures':len(items),'maximum_requests':protocol['max_requests'],'context':{
            i['id']:[c['chunk_id'] for a in i['answer']['findings'][0]['paper_citations'] for c in a['source_context']]
            for i in items}},ensure_ascii=False))
        return
    lock=Lock()
    def record(name,row):
        with lock,(args.output/name).open('a') as h:h.write(json.dumps(row,ensure_ascii=False)+'\n')
    class ArmClient(Hy3Client):
        def __init__(self,arm):super().__init__(settings);self.arm=arm
        def verify_findings(self,payload):
            if self.arm in {'v1','scope_only'}:
                payload=copy.deepcopy(payload)
                for f in payload:
                    for a in f['paper']:
                        a.pop('source_context',None);a.pop('chunk_id',None)
            return super().verify_findings(payload,system_prompt=old_prompt if self.arm in {'v1','captions_only'} else SCOPED_PROMPT)
    def work(item,arm,repeat):
        record('dispatch.jsonl',{'case':item['id'],'arm':arm,'repeat':repeat})
        budget=RequestBudget(max_requests=1,max_seconds=180);start=monotonic()
        try:
            with use_request_budget(budget):
                after=verify_answer(ArmClient(arm),JointAnswer.model_validate(item['answer']))
            review=after.findings[0].verification.model_dump(mode='json');error=None
        except Exception as exc:review={'status':'not_reviewed'};error=type(exc).__name__
        row={'case':item['id'],'arm':arm,'repeat':repeat,'expected_supported':item['expected'],
             'verification':review,'correct':review['status']==('passed' if item['expected'] else 'failed'),
             'requests':budget.requests,'tokens':budget.tokens,'seconds':round(monotonic()-start,2),'error':error}
        record('observations.jsonl',row);return row
    rows=[]
    with ThreadPoolExecutor(max_workers=3) as pool:
        # Rotate arm order per repeat/case to avoid all old/new calls in separate time blocks.
        jobs=[]
        for repeat in range(3):
            for n,item in enumerate(items):
                offset=(repeat+n)%len(ARMS)
                jobs += [(item,a,repeat) for a in ARMS[offset:]+ARMS[:offset]]
        futures=[pool.submit(work,*job) for job in jobs]
        for future in as_completed(futures):
            row=future.result();rows.append(row)
            print(json.dumps({'completed':len(rows),'case':row['case'],'arm':row['arm'],
                              'repeat':row['repeat'],'status':row['verification']['status'],'correct':row['correct']}),flush=True)
    summary={}
    for arm in ARMS:
        group=[r for r in rows if r['arm']==arm];supported=[r for r in group if r['expected_supported']]
        unsupported=[r for r in group if not r['expected_supported']]
        summary[arm]={'correct':sum(r['correct'] for r in group),'n':len(group),
            'unsupported_rejected':sum(r['verification']['status']=='failed' for r in unsupported),
            'unsupported_n':len(unsupported),'supported_passed':sum(r['verification']['status']=='passed' for r in supported),
            'supported_n':len(supported),'false_rejections':sum(r['verification']['status']=='failed' for r in supported),
            'missed_errors':sum(r['verification']['status']=='passed' for r in unsupported),
            'unreviewed':sum(r['verification']['status']=='not_reviewed' for r in group),
            'requests':sum(r['requests'] for r in group),'tokens':sum(r['tokens'] for r in group)}
    (args.output/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(summary),flush=True)


if __name__=='__main__':main()
