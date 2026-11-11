"""Paired development evaluation of evidence verification on identical findings.

Freeze protocol before calls; never overwrite or resume a paid run. First check
nine warmup fixtures, then investigate 39 development questions three times and
review each exact answer once. Reference labels are used only by the scorer.
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
from paperaudit.agents.finding_verifier import verify_answer
from paperaudit.code_parser import parse_code_zip
from paperaudit.config import Settings
from paperaudit.hy3_client import Hy3Client
from paperaudit.models import CodeCitation, EvidenceAnchor, JointAnswer, PaperCodeFinding
from paperaudit.pdf_parser import parse_pdf
from paperaudit.request_budget import RequestBudget, use_request_budget
from .run import build_archive
from .score import predict

HERE = Path(__file__).resolve().parent


def prediction(answer, item):
    if answer is None:
        return "ERROR"
    # Keep the existing score function unchanged for the original verdict.
    row = {"mode": "agent", "status": answer.status.value,
           "findings": [{"verdict": f.verdict.value, "text": f.text} for f in answer.findings]}
    return predict(row, item)


def summarize(rows):
    eligible = [r for r in rows if r['before'] in {'CONSISTENT','INCONSISTENT','PARTIAL'}]
    wrong = [r for r in eligible if r['before'] != r['expected']]
    correct = [r for r in eligible if r['before'] == r['expected']]
    return {'observations':len(rows),
        'before_matches_reference':sum(r['before']==r['expected'] for r in rows),
        'after_matches_reference':sum(r['after']==r['expected'] for r in rows),
        'wrong_conclusive':len(wrong), 'wrong_conclusive_withheld':sum(r['pending'] for r in wrong),
        'reference_matching_conclusive':len(correct), 'reference_matching_withheld':sum(r['pending'] for r in correct),
        'semantic_rejections':sum(r['rejected_findings'] for r in rows),
        'unreviewed_required':sum(r['unreviewed_findings'] for r in rows),
        'baseline_requests':sum(r['baseline_requests'] for r in rows),
        'verification_requests':sum(r['verification_requests'] for r in rows),
        'baseline_tokens':sum(r['baseline_tokens'] for r in rows),
        'verification_tokens':sum(r['verification_tokens'] for r in rows),
        'limitations':'Withholding a reference-matching answer is a false-positive proxy, not an independently '
                      'adjudicated finding-level error. Unsupported details may justify withholding. '
                      'Paired runs share the exact investigation, not two independently generated answers.'}


def warmup_fixture(parsed, code_value, verdict):
    paper, code = parsed[('mae', 'mae_warmup' if code_value == 20 else None)]
    chunk = next(c for c in paper.chunks if 'warmup epochs [20] 40' in ' '.join(c.content.split()))
    file = next(f for f in code.files if f.path == 'main_pretrain.py')
    lines = file.content.splitlines()
    index = next(i for i, line in enumerate(lines) if "add_argument('--warmup_epochs'" in line)
    assert f'default={code_value}' in lines[index]
    assertion = (f'论文默认 warmup 与代码默认值均为 {code_value}，一致。' if verdict == 'CONSISTENT'
                 else f'论文 warmup 为 40，代码默认 {code_value}，不一致。')
    return JointAnswer(question='预训练默认 warmup 是否一致？', answer=assertion, scope='joint',status='ANSWERED',
        findings=[PaperCodeFinding(text=assertion,verdict=verdict,
            paper_citations=[EvidenceAnchor(chunk_id=chunk.chunk_id,page=chunk.page,text=chunk.content,
                                           quote='warmup epochs [20] 40')],
            code_citations=[CodeCitation(chunk_id=f'{file.path}:L{index+1}',path=file.path,
                start_line=index+1,end_line=min(index+2,len(lines)),text='\n'.join(lines[index:index+2]))])])


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--data',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--run',action='store_true')
    args=ap.parse_args()
    cases=json.loads((HERE/'cases.json').read_text())
    settings=Settings.from_env()
    parsed={}; inputs={}
    for name,spec in cases['papers'].items():
        pdf=(args.data/name/'paper.pdf').read_bytes(); raw=(args.data/name/'repo.zip').read_bytes()
        assert sha256(pdf).hexdigest()==spec['pdf_sha256']
        assert sha256(raw).hexdigest()==spec['zip_sha256']
        paper=parse_pdf(pdf)
        variants={None}|{i['mutation'] for i in cases['items'] if i['paper']==name}
        for mutation in variants:
            archive=build_archive(raw,spec['include'],cases['mutations'][mutation] if mutation else [])
            parsed[name,mutation]=(paper,parse_code_zip(archive,f'{name}.zip'))
            inputs[f'{name}:{mutation or "original"}']={'pdf_sha256':sha256(pdf).hexdigest(),
                'archive_sha256':sha256(archive).hexdigest()}
    root=HERE.parents[1]
    sources=[*root.joinpath('src/paperaudit').rglob('*.py'),Path(__file__),HERE/'score.py',HERE/'run.py']
    protocol={'split':'development','model':settings.model,'temperature':settings.temperature,
        'reasoning_effort':settings.reasoning_effort,'cases_sha256':sha256((HERE/'cases.json').read_bytes()).hexdigest(),
        'inputs':inputs,'sources':{str(p.relative_to(root)):sha256(p.read_bytes()).hexdigest() for p in sources},
        'items':[i['id'] for i in cases['items']],'repeats':3,'workers':3,
        'baseline':'Tool investigator only, no single-retrieval fallback. 11 requests, 180 seconds.',
        'intervention':'One review of exact same findings, no investigation history, shared 180s deadline, '
                       'total ceiling 12 requests. No retries. All failures stay in denominator.',
        'score':'Original score.predict before verification; any pending finding makes after=PENDING_REVIEW. '
                'Full original verdicts and evidence remain saved. No reclassification to another verdict.',
        'primary_metrics':['wrong conclusive answers withheld','reference-matching conclusive answers withheld',
                           'before/after matches reference','extra requests and tokens','review failures'],
        'acceptance':'Three repeats of wrong CONSISTENT with code warmup=20, correct INCONSISTENT with 20, '
                     'correct CONSISTENT with 40. All three wrong findings must be semantically rejected '
                     'before dispatching the development comparison. Correct controls are reported regardless.',
        'maximum_requests':9+len(cases['items'])*3*12,
        'limits':['Known development data, no holdout or independent annotation.',
                  'Same model reviews itself; batch peers visible but history and other investigations excluded.',
                  'Label agreement is not proof that every statement has adequate evidence.']}
    args.output.mkdir(parents=True,exist_ok=False)
    (args.output/'protocol.json').write_text(json.dumps(protocol,ensure_ascii=False,indent=2)+'\n')
    if not args.run:
        print('Inputs verified; protocol frozen. Use a new directory with --run for paid calls.')
        return
    lock=Lock()
    def record(file,row):
        with lock,(args.output/file).open('a') as h:h.write(json.dumps(row,ensure_ascii=False)+'\n')
    acceptance=[]
    for repeat in range(3):
        for name,value,verdict,expected in [('wrong-consistent',20,'CONSISTENT','failed'),
            ('correct-inconsistent',20,'INCONSISTENT','passed'),('correct-consistent',40,'CONSISTENT','passed')]:
            before=warmup_fixture(parsed,value,verdict)
            record('dispatch.jsonl',{'fixture':name,'repeat':repeat})
            budget=RequestBudget(max_requests=1,max_seconds=180)
            with use_request_budget(budget):after=verify_answer(Hy3Client(settings),before)
            row={'fixture':name,'repeat':repeat,'expected_status':expected,
                 'before':before.model_dump(mode='json'),'after':after.model_dump(mode='json'),
                 'requests':budget.requests,'tokens':budget.tokens}
            acceptance.append(row);record('acceptance.jsonl',row)
            print(json.dumps({'fixture':name,'repeat':repeat,'status':after.findings[0].verification.status}),flush=True)
    if not all(r['after']['findings'][0]['verification']['status']=='failed'
               for r in acceptance if r['fixture']=='wrong-consistent'):
        print('ACCEPTANCE_FAILED: preserved observations; development comparison not dispatched.',flush=True)
        return
    def work(item,repeat):
        key=f"{item['id']}-{repeat}"
        record('dispatch.jsonl',{'item':item['id'],'repeat':repeat})
        paper,code=parsed[item['paper'],item['mutation']]
        client=Hy3Client(settings); budget=RequestBudget(max_requests=11,max_seconds=180)
        start=monotonic(); error=None
        try:
            before,trace=CodeInvestigator(client,paper,code,settings.model,budget=budget).run(item['question'],'joint')
        except Exception as exc:
            before=None;error=type(exc).__name__
        base_requests,base_tokens=budget.requests,budget.tokens
        baseline_seconds=monotonic()-start
        budget.max_requests=12
        try:
            with use_request_budget(budget):
                after=verify_answer(client,before) if before and before.status=='ANSWERED' else before
        except Exception as exc:
            # Preserve the pre-review answer and count a reviewer error, never drop the observation.
            after=None;error=type(exc).__name__
        findings=after.findings if after else []
        pending=any(f.needs_review for f in findings)
        row={'item':item['id'],'repeat':repeat,'expected':item['expected'],
             'before':prediction(before,item),'after':'PENDING_REVIEW' if pending else prediction(after,item),
             'pending':pending,'rejected_findings':sum(f.verification.status=='failed' for f in findings),
             'unreviewed_findings':sum(f.verification.required and f.verification.status=='not_reviewed' for f in findings),
             'baseline_requests':base_requests,'baseline_tokens':base_tokens,'baseline_seconds':round(baseline_seconds,2),
             'verification_requests':budget.requests-base_requests,'verification_tokens':budget.tokens-base_tokens,
             'verification_seconds':round(monotonic()-start-baseline_seconds,2),'error':error}
        (args.output/f'{key}.json').write_text(json.dumps({'observation':row,
            'before':before.model_dump(mode='json') if before else None,
            'after':after.model_dump(mode='json') if after else None},ensure_ascii=False,indent=2)+'\n')
        record('observations.jsonl',row)
        return row
    rows=[]
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures=[pool.submit(work,item,repeat) for repeat in range(3) for item in cases['items']]
        for future in as_completed(futures):
            row=future.result();rows.append(row)
            print(json.dumps({'completed':len(rows),'item':row['item'],'repeat':row['repeat'],
                              'before':row['before'],'after':row['after']}),flush=True)
    summary=summarize(rows)
    summary['acceptance_requests']=sum(r['requests'] for r in acceptance)
    summary['acceptance_tokens']=sum(r['tokens'] for r in acceptance)
    (args.output/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(summary),flush=True)


if __name__=='__main__':
    main()
