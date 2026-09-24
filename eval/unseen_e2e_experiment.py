"""Freeze unseen paper/report inputs, then exercise the real production audit pipeline.

Reference labels never enter model prompts. Missing/split sources stay in the
denominator. Credentials enter via getpass only; request logs omit exception text.
"""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
import functools
import getpass
import hashlib
import json
import math
from pathlib import Path
import time

from paperaudit.audit_rules import apply_citation_review
from paperaudit.claim_extraction import split_report_sources
from paperaudit.config import Settings
from paperaudit.hy3_client import Hy3Client
from paperaudit.models import AutoLabel, ClaimCategory
from paperaudit.pdf_parser import parse_pdf
from paperaudit.reporting import render_markdown
from paperaudit.service import AuditService
from eval.durable_requests import DurableRequests, write


DEFAULT_ROOT = Path('tmp/experiments/unseen-e2e-20260924')
SAMPLES = Path('eval/unseen_e2e_samples_20260924.json')
PHASES = ('extract_claims', 'judge_claims', 'adjudicate_claim', 'review_missing_support',
          'review_candidate_gap', 'review_citation_coverage', 'repair_citation_coverage')


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(root: Path) -> dict:
    if (root / 'protocol.json').exists():
        raise ValueError('Protocol already exists; never overwrite a frozen run')
    fixture = json.loads(SAMPLES.read_text())
    historical = [p for p in Path('eval').rglob('*.json')
                  if any(word in p.name for word in ('papers', 'protocol', 'manifest'))]
    inputs = {str(SAMPLES): sha(SAMPLES)}
    for report in fixture['reports']:
        aid = report['arxiv_version'].split('v')[0]
        overlaps = [str(p) for p in historical if aid in p.read_text(errors='replace')]
        if overlaps:
            raise ValueError('Historical paper overlap: ' + ', '.join(overlaps))
        pdf, report_path = Path(report['pdf_path']), Path(report['report_path'])
        if sha(pdf) != report['pdf_sha256']:
            raise ValueError('PDF hash mismatch')
        paper = parse_pdf(pdf.read_bytes())
        chunks = {c.chunk_id: c for c in paper.chunks}
        sources = split_report_sources(report_path.read_text())
        if [(s.source_id, s.text) for s in sources] != [(f['source_id'], f['text']) for f in report['facts']]:
            raise ValueError('Report source boundaries differ from reference units')
        for fact in report['facts']:
            for ref in fact['reference_evidence']:
                chunk = chunks[ref['chunk_id']]
                if ref['page'] != chunk.page or ref['quote'] not in chunk.content:
                    raise ValueError('Reference passage does not match parsed PDF')
        inputs.update({str(pdf): sha(pdf), str(report_path): sha(report_path)})
    runtime = asdict(Settings(api_base='https://sub2api.zzii.de/v1', api_key='',
                              model='gpt-6-luna', reasoning_effort=''))
    runtime.pop('api_key')
    sources = [Path(__file__), Path('eval/durable_requests.py'), *Path('src/paperaudit').glob('*.py')]
    protocol = dict(**fixture, runtime=runtime, input_sha256=inputs,
                    source_sha256={str(p): sha(p) for p in sources},
                    isolation=dict(historical_manifests=len(historical), overlapping_papers=[],
                                   final_holdout_used=False), concurrency=2,
                    retry_policy='DurableRequests: at most 3 transport attempts per request in this invocation; SDK retries disabled; no label-driven reruns.',
                    scoring='Per frozen source: all extracted claims must match the reference. Missing sources count as failures. NO_SUPPORT_FOUND and ABSTAIN reported separately; safe withholding also reported.',
                    max_logical_requests_per_report=60)
    write(root / 'protocol.json', protocol)
    for p in sources:
        target = root / 'source_snapshot' / p.name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(p.read_bytes())
    return dict(reports=len(fixture['reports']), facts=sum(len(r['facts']) for r in fixture['reports']),
                protocol_sha256=sha(root / 'protocol.json'))


def verify(root: Path) -> dict:
    protocol = json.loads((root / 'protocol.json').read_text())
    for key in ('input_sha256', 'source_sha256'):
        for path, expected in protocol[key].items():
            if sha(Path(path)) != expected:
                raise ValueError('Frozen input/source changed: ' + path)
    return protocol


def score_sources(report: dict, audits: list[dict]) -> list[dict]:
    rows = []
    for fact in report['facts']:
        matches = [a for a in audits if a['claim'].get('source_id') == fact['source_id']]
        labels = [a['judgment']['label'] for a in matches]
        gold = fact['reference_label']
        pool = {c['chunk_id'] for a in matches for c in a['candidates']}
        refs = {r['chunk_id'] for r in fact['reference_evidence']}
        rows.append(dict(case_id=fact['case_id'], reference_label=gold, labels=labels,
                         claim_count=len(matches), extracted=bool(matches),
                         exact_agreement=bool(matches) and all(label == gold for label in labels),
                         missed_support=gold == 'SUPPORTED' and (not labels or any(x != 'SUPPORTED' for x in labels)),
                         false_support=gold != 'SUPPORTED' and 'SUPPORTED' in labels,
                         safe_withholding=bool(labels) and all(x in {'NO_SUPPORT_FOUND', 'ABSTAIN'} for x in labels),
                         all_reference_chunks_retrieved=refs.issubset(pool) if refs else None,
                         missing_reference_chunks=sorted(refs - pool)))
    return rows


def run_one(root: Path, protocol: dict, report: dict, api_key: str) -> dict:
    pid = report['paper_id']
    directory = root / 'runs' / pid
    if directory.exists():
        raise ValueError('Run directory exists; preserve its first-run result')
    directory.mkdir(parents=True)
    settings = Settings(**protocol['runtime'], api_key=api_key)
    client = Hy3Client(settings)
    client._client.max_retries = 0
    transport = DurableRequests(client._client.chat.completions.create, directory / 'requests')
    journal, calls = [], []
    phase = 'unknown'

    def tracked(**kwargs):
        if len(journal) >= protocol['max_logical_requests_per_report']:
            raise RuntimeError('Logical request budget exhausted')
        record = dict(index=len(journal) + 1, phase=phase, status='started')
        journal.append(record)
        write(directory / 'journal.json', journal)
        start = time.monotonic()
        try:
            response = transport(**kwargs)
            record.update(status='ok', model=response.model,
                          usage=response.usage.model_dump() if response.usage else None)
            return response
        except Exception as exc:
            record.update(status='error', error_type=type(exc).__name__)
            raise
        finally:
            record['seconds'] = time.monotonic() - start
            write(directory / 'journal.json', journal)
            print(pid, phase, record['status'], round(record['seconds'], 1), flush=True)

    client._client.chat.completions.create = tracked

    def wrap(name, original):
        @functools.wraps(original)
        def invoke(*args, **kwargs):
            nonlocal phase
            previous, phase = phase, name
            start_index = len(journal)
            try:
                result = original(*args, **kwargs)
                call = dict(phase=name, request_indices=list(range(start_index + 1, len(journal) + 1)),
                            response=result.model_dump(mode='json'))
                if name == 'judge_claims':
                    call['initial_candidates'] = {c.claim_id: [e.model_dump(mode='json') for e in es]
                                                  for c, es in args[0]}
                calls.append(call)
                write(directory / 'calls.json', calls)
                return result
            finally:
                phase = previous
        return invoke

    for name in PHASES:
        setattr(client, name, wrap(name, getattr(client, name)))
    started = time.monotonic()
    result = dict(paper_id=pid, protocol_sha256=sha(root / 'protocol.json'))
    try:
        paper = parse_pdf(Path(report['pdf_path']).read_bytes())
        audit = AuditService(settings, client=client).audit(
            paper, Path(report['report_path']).read_text(), list(ClaimCategory), mode='unseen_e2e',
        )
        audit_data = audit.model_dump(mode='json')
        # This is local quotation/ID validation, not an independent semantic judge.
        supported = [a for a in audit.audits if a.judgment.label == AutoLabel.SUPPORTED]
        valid = sum(apply_citation_review(a.judgment, a.candidates, a.citation_review).label
                    == AutoLabel.SUPPORTED for a in supported)
        result.update(status='ok', audit=audit_data,
                      sources=score_sources(report, audit_data['audits']),
                      supported_claims=len(supported), supported_locally_valid_citations=valid)
        (directory / 'audit.md').write_text(render_markdown(audit))
    except Exception as exc:
        result.update(status='error', error_type=type(exc).__name__)
    finally:
        result['seconds'] = time.monotonic() - started
        result['requests'] = journal
        write(directory / 'result.json', result)
        client._client.close()
    return result


def summarize(root: Path) -> dict:
    protocol = json.loads((root / 'protocol.json').read_text())
    results = [json.loads(p.read_text()) for p in sorted((root / 'runs').glob('*/result.json'))]
    rows = [s for r in results for s in r.get('sources', [])]
    requests = [q for r in results for q in r['requests']]
    audits = [a for r in results for a in r.get('audit', {}).get('audits', [])]
    by_phase = {}
    for phase in PHASES:
        qs = [q for q in requests if q['phase'] == phase]
        by_phase[phase] = dict(requests=len(qs), seconds=sum(q['seconds'] for q in qs),
                               tokens=sum((q.get('usage') or {}).get('total_tokens', 0) for q in qs))
    times = sorted(r['seconds'] for r in results if r['status'] == 'ok')
    summary = dict(planned_reports=len(protocol['reports']), completed_reports=len(results),
                   successful_reports=sum(r['status'] == 'ok' for r in results),
                   planned_sources=sum(len(r['facts']) for r in protocol['reports']),
                   evaluated_sources=len(rows), extracted_sources=sum(r['extracted'] for r in rows),
                   extracted_claims=len(audits), exact_agreement=sum(r['exact_agreement'] for r in rows),
                   supported_reference_count=sum(r['reference_label'] == 'SUPPORTED' for r in rows),
                   missed_support=sum(r['missed_support'] for r in rows),
                   false_support=sum(r['false_support'] for r in rows),
                   unsupported_safely_withheld=sum(r['reference_label'] == 'NO_SUPPORT_FOUND' and r['safe_withholding'] for r in rows),
                   labels=dict(Counter(a['judgment']['label'] for a in audits)),
                   supported_claims=sum(r.get('supported_claims', 0) for r in results),
                   supported_locally_valid_citations=sum(r.get('supported_locally_valid_citations', 0) for r in results),
                   candidate_rechecks=sum(a.get('candidate_gap_review') is not None for a in audits),
                   citation_repairs=sum(a.get('citation_review_before_repair') is not None for a in audits),
                   logical_requests=len(requests), by_phase=by_phase,
                   usage_missing_requests=sum(q['status'] == 'ok' and not q.get('usage') for q in requests),
                   prompt_tokens=sum((q.get('usage') or {}).get('prompt_tokens', 0) for q in requests),
                   completion_tokens=sum((q.get('usage') or {}).get('completion_tokens', 0) for q in requests),
                   total_tokens=sum((q.get('usage') or {}).get('total_tokens', 0) for q in requests),
                   mean_report_seconds=sum(times)/len(times) if times else None,
                   p95_report_seconds=times[math.ceil(.95 * len(times))-1] if times else None,
                   latency_note='Concurrent reports; nearest-rank P95 on only three reports is descriptive, not an SLA.',
                   sources=rows)
    attempts = [a for p in (root / 'runs').glob('*/requests/*.json')
                for a in json.loads(p.read_text())['attempts']]
    summary['network_attempts'] = len(attempts)
    summary['transport_errors'] = sum(a['status'] != 'ok' for a in attempts)
    write(root / 'summary.json', summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=['prepare', 'run', 'summary'])
    parser.add_argument('--output', type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args()
    if args.phase == 'prepare':
        result = prepare(args.output)
    elif args.phase == 'run':
        protocol = verify(args.output)
        if (args.output / 'runs').exists():
            raise ValueError('Existing run; inspect it instead of repeating')
        api_key = getpass.getpass('API key (hidden, memory only): ')
        with ThreadPoolExecutor(max_workers=protocol['concurrency']) as pool:
            futures = [pool.submit(run_one, args.output, protocol, report, api_key)
                       for report in protocol['reports']]
            for future in futures:
                future.result()
        result = summarize(args.output)
    else:
        result = summarize(args.output)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
