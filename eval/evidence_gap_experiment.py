"""Frozen development probe for overlooked candidate evidence, not an end-to-end audit.

Baseline: one initial judgment plus the production citation coverage gate.
Candidate: replay that frozen outcome through the proposed bounded recheck.
Extraction, majority voting and supplementary retrieval are outside this probe.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import getpass
import hashlib
import json
from pathlib import Path
from threading import Event
import time

from eval.retrieval_strategy_experiment import digest, save
from paperaudit.audit_rules import calibrate_judgment, validate_judgment_references
from paperaudit.citation_review import review_supported_citations
from paperaudit.config import Settings
from paperaudit.hy3_client import Hy3Client
from paperaudit.models import AtomicClaim, ClaimJudgment, EvidenceCandidate
from paperaudit.pdf_parser import parse_pdf
from paperaudit.retrieval import EvidenceRetriever, retrieve_claim_evidence


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def prepare(output: Path):
    if (output / 'protocol.json').exists():
        raise ValueError('Protocol already exists')
    samples_path = Path('eval/evidence_gap_dev_samples_20260924.json')
    papers_path = Path('eval/evidence_gap_dev_papers_20260924.json')
    papers = json.loads(papers_path.read_text())
    samples = json.loads(samples_path.read_text())
    # Check paper identity, not just claim IDs, against every existing audit manifest.
    old = [p for p in Path('eval').glob('*papers*.json') if p != papers_path]
    old.append(Path('eval/hy3_reliable_20260907/inputs/papers.json'))
    overlap = [str(p) for p in old if any(row['arxiv_id'] in p.read_text() for row in papers)]
    if overlap:
        raise ValueError('New papers overlap existing manifests: ' + str(overlap))
    inputs = {str(p): sha(p) for p in [samples_path, papers_path, *old]}
    cases = []
    for manifest in papers:
        pdf = Path(manifest['local_pdf'])
        if sha(pdf) != manifest['sha256']:
            raise ValueError('PDF hash mismatch')
        inputs[str(pdf)] = sha(pdf)
        paper = parse_pdf(pdf.read_bytes())
        chunks = {c.chunk_id: c for c in paper.chunks}
        with EvidenceRetriever(paper.chunks) as retriever:
            for sample in samples:
                if sample['paper_id'] != manifest['paper_id']:
                    continue
                claim = AtomicClaim.model_validate(sample['claim'])
                for ref in sample['reference_evidence']:
                    if ref['quote'] not in chunks[ref['chunk_id']].content:
                        raise ValueError('Invalid reference quote')
                if sample['control_chunks']:
                    candidates = [EvidenceCandidate(evidence_id=f'{claim.claim_id}_e{i}', chunk_id=cid,
                                                    page=chunks[cid].page, text=chunks[cid].content, score=0)
                                  for i, cid in enumerate(sample['control_chunks'], 1)]
                else:
                    candidates = retrieve_claim_evidence(retriever, claim, paper.chunks, strategy='cited')
                assert len(candidates) <= 10 and sum(len(c.text) for c in candidates) <= 18_000
                gold = {r['chunk_id'] for r in sample['reference_evidence']}
                cases.append({**sample, 'page_count': paper.page_count,
                              'candidates': [c.model_dump(mode='json') for c in candidates],
                              'reference_chunks_retrieved': sorted(gold & {c.chunk_id for c in candidates}),
                              'all_reference_chunks_retrieved': gold.issubset({c.chunk_id for c in candidates})})
    save(output / 'protocol.json', dict(cases=cases, input_sha256=inputs,
         isolation=dict(existing_manifests_checked=len(old), overlapping_papers=[], final_holdout_used=False),
         method=__doc__, selection='20 cases fixed before model calls: 14 production-retrieval cases (8 supported, 4 numeric/configuration errors, 2 overgeneralizations), 2 evidence-removal controls, 4 complete-evidence probes. Probe variants are dependent on original facts. References checked on rendered PDFs; no independent human annotation.'))
    return dict(cases=len(cases), complete_reference_sets=sum(c['all_reference_chunks_retrieved'] for c in cases if not c['control_chunks']))


def summarize(output: Path, stage: str):
    protocol = json.loads((output / 'protocol.json').read_text())
    rows = []
    for case in protocol['cases']:
        path = output / stage / 'results' / (case['case_id'] + '.json')
        if path.exists():
            rows.append(json.loads(path.read_text()))
    good = [r for r in rows if r['status'] == 'ok']
    natural = [r for r in good if not r['control']]
    requests = [q for r in rows for q in r['requests']]
    summary = dict(stage=stage, planned=len(protocol['cases']), completed=len(rows), failures=len(rows)-len(good),
                   natural_cases=len(natural), reference_agreement=sum(r['after']['label'] == r['reference_label'] for r in natural),
                   supported_reference_count=sum(r['reference_label'] == 'SUPPORTED' for r in natural),
                   missed_support=sum(r['reference_label'] == 'SUPPORTED' and r['after']['label'] != 'SUPPORTED' for r in natural),
                   false_support=sum(r['reference_label'] != 'SUPPORTED' and r['after']['label'] == 'SUPPORTED' for r in good),
                   abstain=sum(r['after']['label'] == 'ABSTAIN' for r in natural),
                   rechecks=sum(r.get('recheck') is not None for r in good),
                   recovered_support=sum(r['before']['label'] != 'SUPPORTED' and r['after']['label'] == 'SUPPORTED' for r in good),
                   controls=[dict(case_id=r['case_id'],label=r['after']['label']) for r in good if r['control']],
                   api_requests=len(requests), total_tokens=sum((q.get('usage') or {}).get('total_tokens',0) for q in requests),
                   mean_case_seconds=sum(r['seconds'] for r in rows)/len(rows) if rows else 0)
    save(output / stage / 'summary.json', summary)
    return summary


def run(output: Path, stage: str, api_base: str, model: str, api_key: str):
    protocol = json.loads((output / 'protocol.json').read_text())
    for path, expected in protocol['input_sha256'].items():
        if sha(path) != expected:
            raise ValueError('Frozen input changed: ' + path)
    root = output / stage
    root.mkdir(exist_ok=True)
    sources = [Path(__file__), *Path('src/paperaudit').glob('*.py')]
    runtime = dict(model=model,api_base=api_base,temperature=.2,top_p=1.0,timeout_seconds=120,
                   max_completion_tokens=6000,sdk_retries=0,concurrency=2,
                   protocol_sha256=digest(protocol),source_sha256={str(p):sha(p) for p in sources})
    runtime_path = root / 'runtime.json'
    if runtime_path.exists() and json.loads(runtime_path.read_text()) != runtime:
        raise ValueError('Stage runtime or source changed; choose a new output')
    save(runtime_path, runtime)
    snapshots = root / 'source_snapshot'
    snapshots.mkdir(exist_ok=True)
    for path in sources:
        (snapshots / path.name).write_bytes(path.read_bytes())
    results = root / 'results'
    results.mkdir(exist_ok=True)
    jobs = []
    for case in protocol['cases']:
        path = results / (case['case_id'] + '.json')
        if path.exists():
            saved = json.loads(path.read_text())
            if saved['case_sha256'] != digest(case) or saved['runtime_sha256'] != digest(runtime):
                raise ValueError('Saved result mismatch')
            if saved['status'] != 'ok':
                raise ValueError('Previous failed request requires explicit recovery')
        elif path.with_suffix('.requests.json').exists():
            raise ValueError('Interrupted request requires explicit recovery')
        else:
            jobs.append(case)
    stop = Event()

    def job(case):
        if stop.is_set():
            return
        path = results / (case['case_id'] + '.json')
        client = Hy3Client(Settings(api_base=api_base,api_key=api_key,model=model,reasoning_effort=''))
        client._client.max_retries = 0
        original = client._client.chat.completions.create
        requests = []
        phase = 'initial_judgment'

        def tracked(**kwargs):
            if stop.is_set():
                raise RuntimeError('Dispatch stopped')
            kwargs.pop('extra_body',None)
            kwargs['max_completion_tokens'] = 6000
            record = dict(status='started',phase=phase)
            requests.append(record)
            save(path.with_suffix('.requests.json'),requests)
            started = time.monotonic()
            try:
                response = original(**kwargs)
                record.update(status='ok',response_id=response.id,model=response.model,
                              usage=response.usage.model_dump() if response.usage else None)
                return response
            except Exception as exc:
                stop.set()
                record.update(status='error',error_type=type(exc).__name__,http_status=getattr(exc,'status_code',None))
                raise
            finally:
                record['seconds'] = time.monotonic()-started
                save(path.with_suffix('.requests.json'),requests)

        client._client.chat.completions.create = tracked
        claim = AtomicClaim.model_validate(case['claim'])
        candidates = [EvidenceCandidate.model_validate(c) for c in case['candidates']]
        row = dict(case_id=case['case_id'],case_sha256=digest(case),runtime_sha256=digest(runtime),
                   reference_label=case['reference_label'],control=bool(case['control_chunks']))
        started = time.monotonic()
        print(stage + ' ' + case['case_id'],flush=True)
        try:
            recheck = None
            if stage == 'baseline':
                batch = client.judge_claims([(claim,candidates)],case['page_count'])
                if len(batch.judgments)!=1 or batch.judgments[0].claim_id != claim.claim_id:
                    raise ValueError('Unexpected claim ID')
                raw = batch.judgments[0]
                before = validate_judgment_references(calibrate_judgment(raw),candidates)
                phase = 'citation_coverage'
                after,review,repair = review_supported_citations(client,claim,candidates,before)
                row['raw_judgment'] = raw.model_dump(mode='json')
            else:
                from paperaudit.evidence_gap import recheck_candidate_gap
                baseline_path = output/'baseline'/'results'/(case['case_id']+'.json')
                baseline = json.loads(baseline_path.read_text())
                if baseline['status']!='ok' or baseline['case_sha256']!=digest(case):
                    raise ValueError('Baseline does not match case')
                row['baseline_sha256'] = sha(baseline_path)
                # Recheck the initial judgment before citation coverage; this
                # isolates candidate-gap behavior from quote transcription.
                before = ClaimJudgment.model_validate(baseline['before'])
                phase = 'candidate_recheck'
                proposed,recheck = recheck_candidate_gap(client,claim,candidates,before,case['page_count'])
                if proposed != before:
                    phase = 'citation_coverage'
                    after,review,repair = review_supported_citations(client,claim,candidates,proposed)
                else:
                    after,review,repair = before,None,None
            row.update(status='ok',before=before.model_dump(mode='json'),after=after.model_dump(mode='json'),
                       recheck=recheck.model_dump(mode='json') if recheck else None,
                       citation_review=review.model_dump(mode='json') if review else None,
                       citation_review_before_repair=repair.model_dump(mode='json') if repair else None)
        except Exception as exc:
            stop.set()
            row.update(status='error',error_type=type(exc).__name__,http_status=getattr(exc,'status_code',None))
        finally:
            row.update(seconds=time.monotonic()-started,requests=requests,raw_outputs=client.raw_outputs)
            save(path,row)
            client._client.close()
        print('Done '+case['case_id']+' '+row['status'],flush=True)

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(job,jobs))
    return summarize(output,stage)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase',choices=['prepare','baseline','candidate','summarize'])
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--api-base')
    parser.add_argument('--model')
    args=parser.parse_args()
    if args.phase=='prepare':
        result=prepare(args.output)
    elif args.phase=='summarize':
        result={stage:summarize(args.output,stage) for stage in ['baseline','candidate'] if (args.output/stage).exists()}
    else:
        if not args.api_base or not args.model:
            parser.error('--api-base and --model required')
        result=run(args.output,args.phase,args.api_base,args.model,getpass.getpass('API key (not saved): '))
    print(json.dumps(result,ensure_ascii=False,indent=2))
