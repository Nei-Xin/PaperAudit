"""Replay frozen judgments through citation review, without rerunning retrieval.

The extra prose-only control removes MobileNet's configuration table deliberately.
This diagnostic sample does not measure general accuracy or the full audit pipeline.
"""
from __future__ import annotations

import argparse
import getpass
import hashlib
import json
from pathlib import Path
import time

from eval.retrieval_strategy_experiment import digest, save
from paperaudit.citation_review import review_supported_citations
from paperaudit.config import Settings
from paperaudit.hy3_client import Hy3Client
from paperaudit.models import AtomicClaim, CitationReview, ClaimJudgment, EvidenceCandidate


def prepare(baseline: Path, output: Path, review_baseline: Path | None = None):
    if output.exists():
        raise ValueError('Choose a new output directory')
    protocol_path = baseline / 'protocol.json'
    previous = json.loads(protocol_path.read_text())
    hashes = {str(protocol_path): hashlib.sha256(protocol_path.read_bytes()).hexdigest()}
    cases = []
    for source in previous['cases']:
        path = baseline / 'results' / (source['case_id'] + '_cited.json')
        result = json.loads(path.read_text())
        if result['status'] != 'ok' or result['case_sha256'] != digest(source):
            raise ValueError('Baseline result does not match frozen case')
        hashes[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
        cases.append(dict(case_id=source['case_id'], claim=source['claim'],
                          candidates=source['candidates']['cited'], judgment=result['judgment'],
                          reference_label=source['reference_label'], control=False))
    mobile = next(c for c in cases if c['case_id'] == 'P04_natural_1_C023')
    cases.append({**mobile, 'case_id': mobile['case_id'] + '_prose_only',
                  'candidates': [c for c in mobile['candidates'] if c['evidence_id'] == 'C023_e1'],
                  'reference_label': 'ABSTAIN', 'control': True})
    if review_baseline is not None:
        for case in cases:
            path = review_baseline / 'results' / (case['case_id'] + '.json')
            previous_review = json.loads(path.read_text())
            if previous_review['status'] != 'ok' or previous_review['case_sha256'] != digest(case):
                raise ValueError('Review baseline does not match case')
            hashes[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
            case['frozen_review'] = previous_review['review']
    sources = [Path(__file__), Path('src/paperaudit/hy3_client.py'),
               Path('src/paperaudit/models.py'), Path('src/paperaudit/audit_rules.py'),
               Path('src/paperaudit/citation_review.py'), Path('eval/retrieval_strategy_experiment.py')]
    hashes.update({str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources})
    output.mkdir(parents=True)
    save(output / 'protocol.json', {'cases': cases, 'sha256': hashes,
         'method': 'Production citation review with at most one repair of invalid quotes/IDs. Two negative labels bypass review. One prose-only control. If frozen_review is present, reuse it without calling the provider again; only repair locally rejected complete reviews. No retries for evidence gaps.'})
    return {'cases': len(cases), 'reusing_initial_reviews': review_baseline is not None}


def run(output: Path, api_base: str, model: str, api_key: str):
    protocol = json.loads((output / 'protocol.json').read_text())
    for path, expected in protocol['sha256'].items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest() != expected:
            raise ValueError('Frozen input/source changed: ' + path)
    runtime = dict(api_base=api_base, model=model, temperature=.2, top_p=1.0,
                   timeout_seconds=120, max_completion_tokens=6000, sdk_retries=0,
                   protocol_sha256=digest(protocol))
    runtime_path = output / 'runtime.json'
    if runtime_path.exists() and json.loads(runtime_path.read_text()) != runtime:
        raise ValueError('Runtime changed')
    save(runtime_path, runtime)
    results = output / 'results'
    results.mkdir(exist_ok=True)
    rows = []
    for case in protocol['cases']:
        path = results / (case['case_id'] + '.json')
        journal = path.with_suffix('.requests.json')
        if path.exists():
            saved = json.loads(path.read_text())
            if saved['case_sha256'] != digest(case) or saved['runtime_sha256'] != digest(runtime):
                raise ValueError('Saved result changed')
            rows.append(saved)
            continue
        if journal.exists():
            raise ValueError('Interrupted request requires explicit recovery')
        judgment = ClaimJudgment.model_validate(case['judgment'])
        candidates = [EvidenceCandidate.model_validate(c) for c in case['candidates']]
        row = dict(case_id=case['case_id'], case_sha256=digest(case), runtime_sha256=digest(runtime),
                   control=case['control'], before=case['judgment'], reference_label=case['reference_label'])
        requests = []
        client = Hy3Client(Settings(api_base=api_base, api_key=api_key, model=model, reasoning_effort=''))
        client._client.max_retries = 0
        create = client._client.chat.completions.create

        def tracked(**kwargs):
            kwargs.pop('extra_body', None)
            kwargs['max_completion_tokens'] = 6000
            request = {'status': 'started'}
            requests.append(request)
            save(journal, requests)
            started = time.monotonic()
            try:
                response = create(**kwargs)
                request.update(status='ok', model=response.model, response_id=response.id,
                               usage=response.usage.model_dump() if response.usage else None)
                return response
            except Exception as exc:
                request.update(status='error', error_type=type(exc).__name__,
                               http_status=getattr(exc, 'status_code', None))
                raise
            finally:
                request['seconds'] = time.monotonic() - started
                save(journal, requests)

        client._client.chat.completions.create = tracked
        if case.get('frozen_review') is not None:
            frozen = CitationReview.model_validate(case['frozen_review'])
            client.review_citation_coverage = lambda *args: frozen
        print('Review ' + case['case_id'], flush=True)
        try:
            final, review, before_repair = review_supported_citations(
                client, AtomicClaim.model_validate(case['claim']), candidates, judgment,
            )
            row.update(status='ok', review=review.model_dump(mode='json') if review else None,
                       review_before_repair=before_repair.model_dump(mode='json') if before_repair else None,
                       after=final.model_dump(mode='json'),
                       added_ids=sorted(set(final.evidence_ids) - set(judgment.evidence_ids)))
        except Exception as exc:
            row.update(status='error', error_type=type(exc).__name__, http_status=getattr(exc, 'status_code', None))
        finally:
            row.update(requests=requests, raw_outputs=client.raw_outputs)
            save(path, row)
            client._client.close()
        rows.append(row)
        if row['status'] == 'error':
            break  # No automatic dispatch after any provider or structure failure.
    natural = [r for r in rows if not r['control'] and r['status'] == 'ok']
    summary = dict(completed=len(rows), planned=len(protocol['cases']),
                   natural_cases=len(natural),
                   before_reference_agreement=sum(r['before']['label'] == r['reference_label'] for r in natural),
                   after_reference_agreement=sum(r['after']['label'] == r['reference_label'] for r in natural),
                   abstain=sum(r['after']['label'] == 'ABSTAIN' for r in natural),
                   invalid_complete_reviews=sum(bool(r['review'] and r['review']['complete'] and r['after']['label'] == 'ABSTAIN') for r in natural),
                   requests=sum(len(r['requests']) for r in rows),
                   tokens=sum((q.get('usage') or {}).get('total_tokens', 0) for r in rows for q in r['requests']),
                   controls=[{'case_id': r['case_id'], 'status': r['status'], 'after': r.get('after')} for r in rows if r['control']])
    save(output / 'summary.json', summary)
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=['prepare', 'run'])
    parser.add_argument('--baseline', type=Path)
    parser.add_argument('--review-baseline', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--api-base')
    parser.add_argument('--model')
    args = parser.parse_args()
    if args.phase == 'prepare':
        if not args.baseline:
            parser.error('--baseline is required')
        result = prepare(args.baseline, args.output, args.review_baseline)
    else:
        if not args.api_base or not args.model:
            parser.error('--api-base and --model are required')
        result = run(args.output, args.api_base, args.model, getpass.getpass('API key (not saved): '))
    print(json.dumps(result, ensure_ascii=False, indent=2))
