"""Offline regression of plain and cited-page candidates on frozen sample sets."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

from paperaudit.pdf_parser import parse_pdf
from paperaudit.retrieval import EvidenceRetriever, retrieve_claim_evidence
from eval.run_eval import _claim

# run_regression also supports direct script execution and imports run_eval locally.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_regression import DATASETS

EVAL_DIR = Path(__file__).resolve().parent


def compare() -> dict:
    output, cache = [], {}
    hashes = {}
    for dataset in DATASETS:
        samples_path = EVAL_DIR / dataset['samples']
        papers_path = EVAL_DIR / dataset['papers']
        for path in (samples_path, papers_path):
            hashes[str(path.relative_to(EVAL_DIR))] = hashlib.sha256(path.read_bytes()).hexdigest()
        samples = [json.loads(line) for line in samples_path.read_text().splitlines() if line.strip()]
        manifests = {paper['paper_id']: paper for paper in json.loads(papers_path.read_text())}
        results = []
        for pid in sorted({s['paper_id'] for s in samples}):
            manifest = manifests[pid]
            key = manifest['sha256']
            if key not in cache:
                pdf = EVAL_DIR / manifest['local_pdf'].replace('\\', '/')
                data = pdf.read_bytes()
                if hashlib.sha256(data).hexdigest() != key:
                    raise ValueError('PDF hash mismatch: ' + pid)
                cache[key] = parse_pdf(data)
            paper = cache[key]
            with EvidenceRetriever(paper.chunks) as retriever:
                for sample in samples:
                    if sample['paper_id'] != pid or not sample.get('gold_evidence_chunk_ids'):
                        continue
                    claim = _claim(sample)
                    candidates = {a: retrieve_claim_evidence(retriever, claim, paper.chunks, strategy=a)
                                  for a in ('plain', 'cited')}
                    for pool in candidates.values():
                        assert len(pool) <= 10 and sum(len(c.text) for c in pool) <= 18_000
                    gold = set(sample['gold_evidence_chunk_ids'])
                    results.append({'sample_id': sample['sample_id'], **{
                        a: bool(gold & {c.chunk_id for c in pool}) for a, pool in candidates.items()}})
        hits = {a: sum(row[a] for row in results) for a in ('plain', 'cited')}
        rates = {a: hits[a] / len(results) for a in hits}
        output.append({'dataset': dataset['name'], 'sample_count': len(samples),
                       'evidence_sample_count': len(results), 'hits': hits, 'rates': rates,
                       'minimum_recall': dataset['min_recall'],
                       'passed': all(rate >= dataset['min_recall'] for rate in rates.values()),
                       'gained': [r['sample_id'] for r in results if r['cited'] and not r['plain']],
                       'lost': [r['sample_id'] for r in results if r['plain'] and not r['cited']]})
    return {'max_candidates': 10, 'max_chars': 18_000, 'datasets': output,
            'passed': all(d['passed'] for d in output), 'input_sha256': hashes,
            'note': 'Offline gold chunk hit, not judgment accuracy; final_holdout is reporting only.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Use a new output file')
    result = compare()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    for row in result['datasets']:
        print(row['dataset'], row['hits'], row['evidence_sample_count'], 'lost', len(row['lost']))
    if not result['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
