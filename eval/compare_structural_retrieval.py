"""Replay natural-report retrieval only; keep frozen extraction and alignment.

No API calls or label predictions. Compare baseline top-k, plain top-(k+5),
and top-k plus up to five structural neighbors against validated references.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from eval.diagnose_report_failures import Inputs, diagnose, evidence_overlap
from paperaudit import pdf_parser, retrieval
from paperaudit.models import AtomicClaim, ParsedPaper


def compare(root: Path, top_k: int = 5) -> tuple[dict, list[dict]]:
    if top_k < 1:
        raise ValueError('top_k must be positive')
    diagnostic, facts, hashes = diagnose(root)
    source = Inputs(root)
    cache = {}
    counts = {name: Counter() for name in ('baseline', 'plain_expanded', 'structural')}
    details = []
    candidate_counts = []
    for pid in sorted({row['paper_id'] for row in facts if row['kind'] == 'natural'}):
        paper = ParsedPaper.model_validate(source.read(f'inputs/{pid}_paper.json'))
        chunks = {chunk.chunk_id: chunk.model_dump() for chunk in paper.chunks}
        with retrieval.EvidenceRetriever(paper.chunks) as retriever:
            for row in facts:
                if (row['kind'] != 'natural' or row['paper_id'] != pid
                        or row['reference_status'] != 'resolved' or row['coverage'] != 'full'):
                    continue
                pools = {name: [] for name in counts}
                for selected in row['claims']:
                    key = (row['report_id'], row['repeat'], selected['claim']['claim_id'])
                    if key not in cache:
                        claim = AtomicClaim.model_validate(selected['claim'])
                        baseline = retriever.search(retrieval.build_claim_query(claim), claim.claim_id, top_k)
                        plain = retriever.search(retrieval.build_claim_query(claim), claim.claim_id, top_k + 5)
                        expanded = retrieval.expand_claim_evidence(claim, paper.chunks, baseline)
                        assert expanded[:len(baseline)] == baseline
                        cache[key] = {name: [c.model_dump() for c in candidates] for name, candidates in (
                            ('baseline', baseline), ('plain_expanded', plain), ('structural', expanded))}
                        candidate_counts.append({name: len(candidates) for name, candidates in cache[key].items()})
                    for name in pools:
                        pools[name].append({'candidates': cache[key][name]})
                reference = {'evidence': row['reference_evidence']}
                overlaps = {name: evidence_overlap(reference, selected, chunks) for name, selected in pools.items()}
                if any(value['status'] == 'invalid_reference_quote' for value in overlaps.values()):
                    raise ValueError(f"Invalid frozen reference: {row['report_id']} {row['fact_id']}")
                for name, value in overlaps.items():
                    counts[name][value['status']] += 1
                details.append({'report_id': row['report_id'], 'fact_id': row['fact_id'],
                                'repeat': row['repeat'], 'overlap': overlaps})
    summary = {
        'experiment': root.name, 'top_k': top_k, 'max_additions': 5,
        'fact_observations': len(details), 'unique_claims': len(cache),
        'overlap': {name: dict(values) for name, values in counts.items()},
        'mean_candidate_count': {name: sum(c[name] for c in candidate_counts) / max(len(cache), 1) for name in counts},
        'input_sha256': {**hashes, **source.hashes},
        'implementation_sha256': {Path(module.__file__).name: hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()
                                  for module in (retrieval, pdf_parser)},
        'frozen_integrity': diagnostic['integrity'],
        'limitations': [
            '只比较自然报告中已完整抽取且参考已决的事实；失败及缺失抽取不在检索分母内。',
            '沿用冻结参考、抽取和对齐，仅重放本地检索；不是端到端准确率或弃权率评测。',
            '结构扩展最多增加5块，plain_expanded为同上限的普通Top-K对照；实际候选数不同。',
            '未调用模型API；命中参考不等于判定正确，同一claim可能对应多个fact。',
        ],
    }
    return summary, details


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--experiment', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.resolve().is_relative_to(args.experiment.resolve()):
        raise ValueError('Output must be outside the frozen experiment')
    summary, details = compare(args.experiment)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    (args.output_dir / 'facts.jsonl').write_text(''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in details))
    print(json.dumps({k: summary[k] for k in ('fact_observations', 'unique_claims', 'overlap', 'mean_candidate_count')}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
