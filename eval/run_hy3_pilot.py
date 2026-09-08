"""Development-only DeepFM pilot, with immutable inputs and per-request usage.

python -m eval.run_hy3_pilot prepare
python -m eval.run_hy3_pilot audit
python -m eval.run_hy3_pilot summarize
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
from itertools import combinations
import json
from pathlib import Path
from statistics import fmean, pstdev
import time

from paperaudit.claim_extraction import split_report_sources
from paperaudit.config import Settings
from paperaudit.hy3_client import Hy3Client
from paperaudit.models import ClaimCategory
from paperaudit.pdf_parser import parse_pdf
from paperaudit.service import AuditService

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'eval/direction_one_report_test'
OUT = ROOT / 'eval/hy3_pilot_20260907'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def prepare():
    if (OUT / 'protocol.json').exists():
        raise ValueError('Pilot already prepared; refusing to overwrite.')
    settings = Settings.from_env()
    if settings.model != 'hy3':
        raise ValueError('Expected hy3 application model.')
    reports = [json.loads(line) for line in (DATA / 'report_index.jsonl').read_text(encoding='utf-8').splitlines()]
    reports = [r for r in reports if r['paper_id'] == 'guo2017_deepfm']
    paper = next(p for p in read(DATA / 'papers.json') if p['paper_id'] == 'guo2017_deepfm')
    pdf_path = ROOT / 'eval' / paper['local_pdf']
    if digest(pdf_path) != paper['sha256']:
        raise ValueError('PDF hash mismatch.')
    chunks = parse_pdf(pdf_path.read_bytes())
    save(OUT / 'paper_evidence.json', chunks.model_dump(mode='json'))
    blind = []
    claims = [json.loads(line) for line in (DATA / 'blind_claims.jsonl').read_text(encoding='utf-8').splitlines()]
    for report in reports:
        path = DATA / report['report_path']
        if digest(path) != report['report_sha256']:
            raise ValueError('Report hash mismatch.')
        text = path.read_text(encoding='utf-8')
        target = OUT / report['report_path']
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding='utf-8')
        # Record the actual snapshot bytes, including newline normalization.
        report['snapshot_sha256'] = digest(target)
        sources = split_report_sources(text)
        facts = []
        used_sources = set()
        for c in claims:
            if c['report_id'] != report['report_id']:
                continue
            matches = [s for s in sources if c['claim_text'] in s.text and s.source_id not in used_sources]
            if not matches:
                raise ValueError('Ambiguous blind fact source.')
            # Blind facts preserve report order; repeated sentences have distinct occurrences.
            used_sources.add(matches[0].source_id)
            facts.append({'fact_id': f"F{c['claim_no']:02d}", 'text': c['claim_text'],
                          'source_id': matches[0].source_id, 'report_location': matches[0].report_location})
        blind.append({'report_id': report['report_id'], 'report_text': text, 'facts': facts})
    save(OUT / 'blind_inputs.json', blind)
    config = asdict(settings)
    config.pop('api_key')
    save(OUT / 'protocol.json', {
        'created_at': datetime.now(timezone.utc).isoformat(),
        'purpose': 'Development pilot only; historical reports, not independent final evaluation.',
        'reference_method': 'Independent model, two blind requests, disagreement adjudication; pending credentials.',
        'reference_model_proposed': 'gpt-5.6-luna',
        'reports': reports, 'paper': paper, 'runtime': config,
        'source_sha256': {str(p.relative_to(ROOT)): digest(p) for p in sorted((ROOT/'src/paperaudit').rglob('*.py'))},
        'runner_sha256': digest(Path(__file__)),
        'blind_inputs_sha256': digest(OUT/'blind_inputs.json'),
        'paper_evidence_sha256': digest(OUT/'paper_evidence.json'),
        'run_order': ['R016','R002','R012','R012','R016','R002','R002','R012','R016'],
        'repeats': 3,
        'retry_policy': 'SDK retries disabled in pilot; application semantic retries unchanged. Failed audit recorded, not silently rerun.',
        'metrics': {
            'score_std': 'Population standard deviation across 3 completed runs; unavailable if any run fails.',
            'source_presence': 'At least one extraction at expected source; proxy only, not semantic fact recall.',
            'source_label_agreement': 'Nonempty non-abstaining source label multisets identical across run pairs; missing/abstaining sources are not agreement.',
            'reference_accuracy': 'Not calculated until independently frozen reference labels are available.',
        },
    })
    print('Prepared 1 historical paper, 3 reports, 30 fact instances; no reference labels exposed.', flush=True)


def check_inputs(config, settings):
    current = asdict(settings)
    current.pop('api_key')
    if current != config['runtime']:
        raise ValueError('Runtime differs from protocol.')
    for name, expected in config['source_sha256'].items():
        if digest(ROOT/name) != expected:
            raise ValueError('Application source changed: '+name)
    for report in config['reports']:
        if digest(OUT/report['report_path']) != report['snapshot_sha256']:
            raise ValueError('Report snapshot changed.')
    for name in ('blind_inputs', 'paper_evidence'):
        if digest(OUT/(name+'.json')) != config[name+'_sha256']:
            raise ValueError('Pilot input changed: '+name)
    if digest(ROOT/'eval'/config['paper']['local_pdf']) != config['paper']['sha256']:
        raise ValueError('PDF changed.')


def audit():
    config = read(OUT/'protocol.json')
    settings = Settings.from_env()
    check_inputs(config, settings)
    paper = parse_pdf((ROOT/'eval'/config['paper']['local_pdf']).read_bytes())
    reports = {r['report_id']: r for r in config['reports']}
    counts = {}
    for rid in config['run_order']:
        counts[rid] = counts.get(rid, 0)+1
        repeat = counts[rid]
        path = OUT / f'run_{repeat}' / (rid+'.json')
        if path.exists():
            print('Preserving existing attempt: '+str(path.name), flush=True)
            continue
        client = Hy3Client(settings)
        client._client.max_retries = 0
        original = client._client.chat.completions.create
        requests = []
        def tracked(**kwargs):
            start = time.monotonic()
            try:
                response = original(**kwargs)
                requests.append({'seconds': time.monotonic()-start, 'model': response.model,
                                 'response_id': response.id,
                                 'usage': response.usage.model_dump() if response.usage else None,
                                 'status': 'ok'})
                save(OUT/f'run_{repeat}'/(rid+'_requests.json'), requests)
                return response
            except Exception as exc:
                requests.append({'seconds': time.monotonic()-start, 'status': 'error',
                                 'error_type': type(exc).__name__, 'http_status': getattr(exc,'status_code',None)})
                save(OUT/f'run_{repeat}'/(rid+'_requests.json'), requests)
                raise
        client._client.chat.completions.create = tracked
        start = time.monotonic()
        result = {'report_id': rid, 'tier': reports[rid]['tier'], 'repeat': repeat}
        print(f'Start {rid} repeat {repeat}', flush=True)
        try:
            run = AuditService(settings, client=client).audit(
                paper, (OUT/reports[rid]['report_path']).read_text(encoding='utf-8'),
                [ClaimCategory(c) for c in config['paper']['scope']], mode='hy3_development_pilot',
                progress=lambda msg, value: print(f'{rid}/{repeat}: {msg}', flush=True))
            result.update(status='ok', audit=run.model_dump(mode='json'))
        except Exception as exc:
            result.update(status='error', error_type=type(exc).__name__,
                          error=str(exc).replace(settings.api_key,'[REDACTED]')[:1200])
        result.update(seconds=time.monotonic()-start, requests=requests, raw_outputs=client.raw_outputs)
        save(path, result)
        print(f"Finished {rid}/{repeat}: {result['status']}", flush=True)
    summarize()


def summarize():
    config = read(OUT/'protocol.json')
    blind = {b['report_id']: b for b in read(OUT/'blind_inputs.json')}
    rows, all_runs = [], []
    for report in config['reports']:
        rid = report['report_id']
        runs = [read(p) for i in range(1,4) if (p:=OUT/f'run_{i}'/(rid+'.json')).exists()]
        all_runs.extend(runs)
        good = [r for r in runs if r['status']=='ok']
        row = {'report_id': rid, 'tier': report['tier'], 'attempts':len(runs), 'completed':len(good)}
        scores = [r['audit']['summary']['total_score'] for r in good]
        row.update(scores=scores, mean_score=fmean(scores) if len(scores)==3 and None not in scores else None,
                   score_std=pstdev(scores) if len(scores)==3 and None not in scores else None)
        observations = []
        if len(good)==3:
            for fact in blind[rid]['facts']:
                matches = [[a for a in r['audit']['audits'] if a['claim']['source_id']==fact['source_id']] for r in good]
                labels = [sorted(a['judgment']['label'] for a in group) for group in matches]
                observations.append({'fact_id':fact['fact_id'], 'source_id':fact['source_id'],
                    'counts':list(map(len,matches)), 'labels':labels,
                    'agreement': fmean(bool(a and b) and 'ABSTAIN' not in a+b and a==b for a,b in combinations(labels,2))})
            row.update(source_presence=fmean(n>0 for o in observations for n in o['counts']),
                       source_label_agreement=fmean(o['agreement'] for o in observations), sources=observations)
        rows.append(row)
    requests = [q for r in all_runs for q in r['requests']]
    tokens = sum(q['usage'].get('total_tokens',0) for q in requests if q.get('usage'))
    tier_scores = {r['tier']:r['mean_score'] for r in rows}
    complete = len(all_runs)==9 and all(r['status']=='ok' for r in all_runs)
    save(OUT/'summary.json', {'complete':complete, 'reports':rows,
        'strict_tier_order': tier_scores['high']>tier_scores['medium']>tier_scores['low'] if complete and all(v is not None for v in tier_scores.values()) else None,
        'request_count':len(requests), 'reported_total_tokens':tokens,
        'requests_without_usage':sum(not q.get('usage') for q in requests),
        'audit_wall_seconds':sum(r['seconds'] for r in all_runs),
        'projected_96_audit_tokens':round(tokens/9*96) if complete else None,
        'cost_currency':None, 'cost_note':'No verified billing rate; token projection excludes generation/reference annotation and differs with report length.',
        'reference_status':'pending_independent_model_configuration',
        'limitations':['Historical controlled data, 1 paper only.', 'Source presence does not establish semantic completeness.', 'No reference accuracy or false-positive claims until labels are frozen.']})
    print(json.dumps({'complete':complete,'attempts':len(all_runs),'tokens':tokens},ensure_ascii=False),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('phase',choices=['prepare','audit','summarize'])
    args=parser.parse_args()
    globals()[args.phase]()
