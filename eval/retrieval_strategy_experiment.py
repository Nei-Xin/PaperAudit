"""Budget-matched offline retrieval comparison and optional paired API pilot.

Prepare freezes candidates, references, sample selection and source hashes before
any calls. Run sends only claims/candidates; API credentials stay in memory.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
import getpass
import hashlib
import json
from pathlib import Path
import time
from threading import Event

from eval.diagnose_report_failures import Inputs, diagnose, evidence_overlap
from paperaudit.audit_rules import calibrate_judgment, validate_judgment_references
from paperaudit.config import Settings
from paperaudit.hy3_client import Hy3Client
from paperaudit.models import AtomicClaim, EvidenceCandidate, ParsedPaper
from paperaudit.pdf_parser import _classify_block
from paperaudit.retrieval import EvidenceRetriever, retrieve_claim_evidence

ARMS = ('plain', 'structural', 'hybrid')


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def save(path: Path, value) -> None:
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(path)


def tags_for(row: dict, chunks: dict) -> list[str]:
    evidence = [chunks[item['chunk_id']] for item in row['reference_evidence'] if item['chunk_id'] in chunks]
    tags = {_classify_block(chunk['content']) for chunk in evidence} & {'formula', 'table'}
    if len({chunk['page'] for chunk in evidence}) > 1:
        tags.add('cross_page')
    return sorted(tags) or ['prose']


def prepare(root: Path, output: Path) -> dict:
    if output.resolve().is_relative_to(root.resolve()):
        raise ValueError('Output must be outside the frozen experiment')
    if (output / 'protocol.json').exists():
        raise ValueError('Protocol already exists; choose a new output directory')
    diagnostic, facts, hashes = diagnose(root)
    source = Inputs(root)
    records, cache, mapped = [], {}, defaultdict(list)
    counts = {arm: Counter() for arm in ARMS}
    groups = {arm: defaultdict(Counter) for arm in ARMS}
    natural = [r for r in facts if r['kind'] == 'natural']
    for row in natural:
        for cid in row['claim_ids']:
            mapped[(row['report_id'], row['repeat'], cid)].append(row)
    for pid in sorted({row['paper_id'] for row in natural}):
        paper = ParsedPaper.model_validate(source.read(f'inputs/{pid}_paper.json'))
        chunks = {c.chunk_id: c.model_dump() for c in paper.chunks}
        with EvidenceRetriever(paper.chunks) as retriever:
            for row in natural:
                if row['paper_id'] != pid or row['coverage'] != 'full' or row['reference_status'] != 'resolved':
                    continue
                pools = {arm: [] for arm in ARMS}
                for selected in row['claims']:
                    key = (row['report_id'], row['repeat'], selected['claim']['claim_id'])
                    if key not in cache:
                        claim = AtomicClaim.model_validate(selected['claim'])
                        candidates = {arm: [c.model_dump(mode='json') for c in retrieve_claim_evidence(
                            retriever, claim, paper.chunks, strategy=arm)] for arm in ARMS}
                        linked = mapped[key]
                        labels = {r['reference_label'] for r in linked}
                        eligible = (len(labels) == 1 and all(r['coverage'] == 'full'
                                    and r['reference_status'] == 'resolved'
                                    and len(r['claim_ids']) == 1 for r in linked))
                        cache[key] = {
                            'case_id': '_'.join(map(str, key)), 'paper_id': pid,
                            'page_count': paper.page_count, 'claim': claim.model_dump(mode='json'),
                            'candidates': candidates, 'eligible_for_pilot': eligible,
                            'reference_label': next(iter(labels)) if eligible else None,
                            'fact_ids': [r['fact_id'] for r in linked],
                            'tags': sorted({t for r in linked for t in tags_for(r, chunks)}),
                            'previous_error': any(r['outcome'] in {'abstain', 'label_disagreement'} for r in linked),
                        }
                    for arm in ARMS:
                        pools[arm].append({'candidates': cache[key]['candidates'][arm]})
                tags = tags_for(row, chunks)
                overlap = {arm: evidence_overlap({'evidence': row['reference_evidence']}, pools[arm], chunks) for arm in ARMS}
                for arm in ARMS:
                    status = overlap[arm]['status']
                    if status == 'invalid_reference_quote':
                        raise ValueError('Invalid frozen reference quote')
                    counts[arm][status] += 1
                    for tag in tags:
                        groups[arm][tag][status] += 1
                records.append({'report_id': row['report_id'], 'repeat': row['repeat'], 'fact_id': row['fact_id'],
                                'tags': tags, 'overlap': overlap})
    costs = {}
    for arm in ARMS:
        pools = [case['candidates'][arm] for case in cache.values()]
        lengths = [sum(len(c['text']) for c in candidates) for candidates in pools]
        costs[arm] = {'mean_candidates': sum(map(len, pools)) / len(pools),
                      'mean_text_chars': sum(lengths) / len(lengths), 'max_text_chars': max(lengths)}
    # Diagnostic sampling is fixed before responses: one historical error,
    # one structured case and one remaining control per represented paper.
    pilot = []
    for pid in sorted({c['paper_id'] for c in cache.values()}):
        remaining = sorted([c for c in cache.values() if c['paper_id'] == pid and c['eligible_for_pilot']],
                           key=lambda c: digest(c['case_id']))
        for bucket in ('previous_error', 'structured', 'control'):
            options = [c for c in remaining if (c['previous_error'] if bucket == 'previous_error' else
                       bool(set(c['tags']) & {'formula', 'table', 'cross_page'}) if bucket == 'structured' else True)]
            if options:
                case = options[0]
                pilot.append({**case, 'selection_bucket': bucket})
                remaining.remove(case)
    sources = [Path(__file__), Path('src/paperaudit/retrieval.py'), Path('src/paperaudit/pdf_parser.py'),
               Path('src/paperaudit/hy3_client.py'), Path('src/paperaudit/audit_rules.py')]
    protocol = {
        'schema_version': 1, 'arms': ARMS, 'seed_limit': 5, 'max_candidates': 10, 'max_text_chars': 18_000,
        'cases': pilot, 'input_sha256': {**hashes, **source.hashes},
        'source_sha256': {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
        'selection': 'Deterministic SHA256 order, at most one historical error, one structured case and one remaining control per paper; only single-claim, resolved, homogeneous references.',
        'api_protocol': 'One judge_claims call per case/arm, identical prompt, no adjudication/voting; application JSON repair allowed; SDK retries disabled; concurrency 2; rotated arm order; fatal auth/billing/rate-limit errors stop dispatch.',
        'limitations': ['Diagnostic sample, not representative accuracy.', 'Frozen model-assisted references are not human gold.',
                        'Repeated facts mapped to the same claim are dependent.', 'Actual counts/text lengths can differ within the same caps.',
                        'Structure tags are heuristic and overlap; cross_page requires references on multiple pages.'],
    }
    summary = {'fact_observations': len(records), 'unique_claims': len(cache),
               'overlap': {arm: dict(counts[arm]) for arm in ARMS},
               'by_structure': {arm: {tag: dict(value) for tag, value in groups[arm].items()} for arm in ARMS},
               'cost': costs, 'pilot_cases': len(pilot), 'planned_judgments': len(pilot) * len(ARMS),
               'frozen_integrity': diagnostic['integrity']}
    output.mkdir(parents=True, exist_ok=True)
    save(output / 'protocol.json', protocol)
    save(output / 'offline.json', summary)
    save(output / 'offline_facts.json', records)
    return summary


def summarize(output: Path) -> dict:
    protocol = json.loads((output / 'protocol.json').read_text())
    values = {arm: [] for arm in ARMS}
    for case in protocol['cases']:
        for arm in ARMS:
            path = output / 'results' / f"{case['case_id']}_{arm}.json"
            if path.exists():
                values[arm].append(json.loads(path.read_text()))
    summary = {'planned_per_arm': len(protocol['cases']), 'arms': {}}
    for arm, rows in values.items():
        good = [r for r in rows if r['status'] == 'ok']
        summary['arms'][arm] = {
            'completed': len(rows), 'succeeded': len(good), 'failed': len(rows) - len(good),
            'reference_agreement': sum(r['judgment']['label'] == r['reference_label'] for r in good),
            'abstain': sum(r['judgment']['label'] == 'ABSTAIN' for r in good),
            'invalid_references': sum(r['invalid_references'] for r in good),
            'api_requests': sum(len(r['requests']) for r in rows),
            'total_tokens': sum((q.get('usage') or {}).get('total_tokens', 0) for r in rows for q in r['requests']),
            'mean_seconds': sum(r['seconds'] for r in rows) / len(rows) if rows else None,
        }
    save(output / 'live_summary.json', summary)
    return summary


def run(output: Path, *, api_base: str, model: str, api_key: str, limit: int | None) -> dict:
    protocol = json.loads((output / 'protocol.json').read_text())
    for name, expected in protocol['source_sha256'].items():
        if hashlib.sha256(Path(name).read_bytes()).hexdigest() != expected:
            raise ValueError('Source changed since preparation: ' + name)
    runtime = {'model': model, 'api_base': api_base, 'temperature': .2, 'top_p': 1.0,
               'timeout_seconds': 120, 'max_completion_tokens': 4096,
               'provider_options': 'Standard chat completion only; no Hy3 chat_template_kwargs',
               'protocol_sha256': digest(protocol)}
    runtime_path = output / 'runtime.json'
    if runtime_path.exists() and json.loads(runtime_path.read_text()) != runtime:
        raise ValueError('Runtime differs from saved experiment')
    save(runtime_path, runtime)
    results = output / 'results'
    results.mkdir(exist_ok=True)
    stop = Event()
    jobs = []
    for index, case in enumerate(protocol['cases']):
        order = ARMS[index % len(ARMS):] + ARMS[:index % len(ARMS)]
        for arm in order:
            path = results / f"{case['case_id']}_{arm}.json"
            if not path.exists():
                jobs.append((case, arm, path))
    if limit is not None:
        jobs = jobs[:limit]

    def job(item):
        if stop.is_set():
            return
        case, arm, path = item
        client = Hy3Client(Settings(api_base=api_base, api_key=api_key, model=model, reasoning_effort='', timeout_seconds=120))
        client._client.max_retries = 0
        original = client._client.chat.completions.create
        requests = []

        def tracked(**kwargs):
            if stop.is_set():
                raise RuntimeError('Stopped after provider rejection')
            kwargs.pop('extra_body', None)
            kwargs['max_completion_tokens'] = 4096
            started = time.monotonic()
            try:
                response = original(**kwargs)
                requests.append({'status': 'ok', 'seconds': time.monotonic() - started,
                                 'model': response.model, 'response_id': response.id,
                                 'usage': response.usage.model_dump() if response.usage else None})
                return response
            except Exception as exc:
                code = getattr(exc, 'status_code', None)
                if code in (400, 401, 402, 403, 404, 429):
                    stop.set()
                requests.append({'status': 'error', 'error_type': type(exc).__name__, 'http_status': code,
                                 'seconds': time.monotonic() - started})
                raise
            finally:
                save(path.with_suffix('.requests.json'), requests)

        client._client.chat.completions.create = tracked
        claim = AtomicClaim.model_validate(case['claim'])
        candidates = [EvidenceCandidate.model_validate(c) for c in case['candidates'][arm]]
        started = time.monotonic()
        result = {'case_id': case['case_id'], 'arm': arm, 'reference_label': case['reference_label'],
                  'case_sha256': digest(case), 'runtime_sha256': digest(runtime)}
        print('Start ' + case['case_id'] + ' ' + arm, flush=True)
        try:
            batch = client.judge_claims([(claim, candidates)], case['page_count'])
            if len(batch.judgments) != 1 or batch.judgments[0].claim_id != claim.claim_id:
                raise ValueError('Unexpected claim IDs')
            raw = batch.judgments[0]
            calibrated = calibrate_judgment(raw)
            judgment = validate_judgment_references(calibrated, candidates)
            result.update(status='ok', raw_judgment=raw.model_dump(mode='json'),
                          judgment=judgment.model_dump(mode='json'), invalid_references=judgment != calibrated)
        except Exception as exc:
            result.update(status='error', error_type=type(exc).__name__, http_status=getattr(exc, 'status_code', None))
        finally:
            result.update(seconds=time.monotonic() - started, requests=requests, raw_outputs=client.raw_outputs)
            save(path, result)
            client._client.close()
        print('Done ' + case['case_id'] + ' ' + arm + ' ' + result['status'], flush=True)

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(job, jobs))
    summary = summarize(output)
    if stop.is_set():
        print('Provider rejected request; dispatch stopped. See sanitized request metadata.', flush=True)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=['prepare', 'run', 'summarize'])
    parser.add_argument('--experiment', type=Path, default=Path('eval/hy3_reliable_20260907'))
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--api-base')
    parser.add_argument('--model')
    parser.add_argument('--limit', type=int)
    args = parser.parse_args()
    if args.phase == 'prepare':
        summary = prepare(args.experiment, args.output_dir)
    elif args.phase == 'summarize':
        summary = summarize(args.output_dir)
    else:
        if not args.api_base or not args.model:
            parser.error('--api-base and --model are required for run')
        key = getpass.getpass('API key (not saved): ')
        summary = run(args.output_dir, api_base=args.api_base, model=args.model, api_key=key, limit=args.limit)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
