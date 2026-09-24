"""Replay seen reports and frozen prior contradiction pools without changing inputs.

The gate controls isolate quote verification from retrieval changes: four prior
well-evidenced contradictions should remain; two caption-only verdicts should abstain.
This is development regression, not a new independent evaluation.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import getpass
import json
from pathlib import Path
import time

from eval.durable_requests import DurableRequests, write
from eval.unseen_e2e_experiment import prepare as prepare_e2e, run_one, sha, summarize, verify
from paperaudit.citation_review import review_citations
from paperaudit.config import Settings
from paperaudit.hy3_client import Hy3Client
from paperaudit.models import ClaimAudit

BASELINE = Path('tmp/experiments/unseen-e2e-20260924')
ROOT = Path('tmp/experiments/contradiction-gate-20260924')


def prepare(root):
    prepare_e2e(root)
    protocol = json.loads((root / 'protocol.json').read_text())
    protocol.update(experiment_kind='seen_case_development_regression',
                    annotation='Reuses the 18 already-seen report sentences and pre-existing labels. No independent-generalization claim.',
                    baseline_protocol_sha256=sha(BASELINE / 'protocol.json'))
    controls = []
    for pid, prefix in [('resnext', 'RX'), ('layernorm', 'LN'), ('senet', 'SE')]:
        path = BASELINE / 'runs' / pid / 'result.json'
        previous = json.loads(path.read_text())
        protocol['input_sha256'][str(path)] = sha(path)
        for a in previous['audit']['audits']:
            if a['judgment']['label'] != 'CONTRADICTED':
                continue
            cid = prefix + a['claim']['source_id'][-2:]
            controls.append(dict(case_id=cid, expected='ABSTAIN' if cid in {'SE04', 'SE05'} else 'CONTRADICTED', audit=a))
    protocol['gate_controls'] = controls
    protocol['source_sha256'][str(Path(__file__))] = sha(Path(__file__))
    write(root / 'protocol.json', protocol)
    (root / 'source_snapshot' / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    return {'reports': len(protocol['reports']), 'controls': len(controls), 'protocol_sha256': sha(root / 'protocol.json')}


def control(root, protocol, case, api_key):
    directory = root / 'gate_controls' / case['case_id']
    directory.mkdir(parents=True, exist_ok=False)
    client = Hy3Client(Settings(**protocol['runtime'], api_key=api_key))
    client._client.max_retries = 0
    client._client.chat.completions.create = DurableRequests(
        client._client.chat.completions.create, directory / 'requests')
    audit = ClaimAudit.model_validate(case['audit'])
    result = dict(case_id=case['case_id'], expected=case['expected'])
    started = time.monotonic()
    try:
        final, review, repair = review_citations(client, audit.claim, audit.candidates, audit.judgment)
        result.update(status='ok', passed=final.label.value == case['expected'],
                      final=final.model_dump(mode='json'),
                      review=review.model_dump(mode='json') if review else None,
                      before_repair=repair.model_dump(mode='json') if repair else None)
    except Exception as exc:
        result.update(status='error', error_type=type(exc).__name__, passed=False)
    finally:
        result['seconds'] = time.monotonic() - started
        write(directory / 'result.json', result)
        client._client.close()
    print('gate_control', case['case_id'], result['status'], result['passed'], flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=['prepare', 'run'])
    parser.add_argument('--output', type=Path, default=ROOT)
    args = parser.parse_args()
    if args.phase == 'prepare':
        print(json.dumps(prepare(args.output), indent=2))
        return
    protocol = verify(args.output)
    if (args.output / 'runs').exists() or (args.output / 'gate_controls').exists():
        raise ValueError('Existing run; preserve original results')
    api_key = getpass.getpass('API key (hidden, memory only): ')
    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs = [pool.submit(run_one, args.output, protocol, r, api_key) for r in protocol['reports']]
        jobs += [pool.submit(control, args.output, protocol, c, api_key) for c in protocol['gate_controls']]
        for future in jobs:
            future.result()
    summary = summarize(args.output)
    results = [json.loads(p.read_text()) for p in sorted((args.output / 'gate_controls').glob('*/result.json'))]
    write(args.output / 'gate_summary.json', dict(controls=len(results), passed=sum(r['passed'] for r in results), results=results))
    print(json.dumps(dict(exact_agreement=summary['exact_agreement'], missed_support=summary['missed_support'],
                          false_support=summary['false_support'], controls_passed=sum(r['passed'] for r in results)), indent=2))


if __name__ == '__main__':
    main()
