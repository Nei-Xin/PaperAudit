"""Offline, paired BM25 versus current retrieval comparison; no model calls.

Both arms share the production FTS index, PDF chunks, query builder and tokenizer.
The baseline takes BM25's first five hits. The current arm additionally performs
candidate supplementation and rule reranking, so this is NOT reranker-only ablation.
Gold evidence is used only for scoring after both arms have retrieved their results.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pymupdf

from check_holdout_isolation import DEFAULT_SPLITS, check
from run_eval import _claim, _load_jsonl
from paperaudit.pdf_parser import parse_pdf
from paperaudit.retrieval import EvidenceRetriever, _query_terms, build_claim_query

ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "eval"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bm25_ids(retriever: EvidenceRetriever, query: str) -> list[str]:
    terms = _query_terms([query])
    if not terms:
        return []
    expression = " OR ".join(f'"{term.replace(chr(34), chr(34) * 2)}"' for term in terms)
    # Same SQL order and index as production's first-stage retrieval.
    return [str(row[0]) for row in retriever._connection.execute(
        "SELECT chunk_id FROM chunks WHERE chunks MATCH ? ORDER BY bm25(chunks) LIMIT 5",
        (expression,),
    ).fetchall()]


def summarize(rows: list[dict]) -> dict:
    eligible = [row for row in rows if row["gold_chunk_ids"]]
    baseline = sum(row["bm25_hit"] for row in eligible)
    current = sum(row["current_hit"] for row in eligible)
    count = len(eligible)
    return {
        "samples": len(rows), "gold_evidence_samples": count,
        "bm25_hits": baseline, "current_hits": current,
        "bm25_hit_rate_at_5": baseline / count if count else None,
        "current_hit_rate_at_5": current / count if count else None,
        "delta_percentage_points": 100 * (current - baseline) / count if count else None,
        "wins": sum(row["current_hit"] and not row["bm25_hit"] for row in eligible),
        "losses": sum(row["bm25_hit"] and not row["current_hit"] for row in eligible),
        "both_hit": sum(row["bm25_hit"] and row["current_hit"] for row in eligible),
        "both_miss": sum(not row["bm25_hit"] and not row["current_hit"] for row in eligible),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        raise SystemExit("Choose a new output directory to preserve previous results.")
    samples_path = EVAL / "final_holdout_resolved_samples.jsonl"
    papers_path = EVAL / "final_holdout_papers.json"
    isolation = check(papers_path, [EVAL / name for name in DEFAULT_SPLITS])
    if not isolation["isolated"]:
        raise ValueError("Holdout overlaps an existing split")
    samples = _load_jsonl(samples_path)
    papers = json.loads(papers_path.read_text(encoding="utf-8"))
    assert len({sample["sample_id"] for sample in samples}) == len(samples)
    assert {s["paper_id"] for s in samples} == {p["paper_id"] for p in papers}
    provenance_paths = [Path(__file__), EVAL / "run_eval.py", EVAL / "check_holdout_isolation.py",
                        ROOT / "src/paperaudit/retrieval.py", ROOT / "src/paperaudit/pdf_parser.py",
                        ROOT / "src/paperaudit/models.py", samples_path, papers_path, ROOT / "uv.lock"]
    hashes = {str(path.relative_to(ROOT)): digest(path) for path in provenance_paths}
    rows = []
    for paper in papers:
        pdf_path = EVAL / paper["local_pdf"]
        pdf_hash = digest(pdf_path)
        if pdf_hash != paper["sha256"]:
            raise ValueError(f"PDF hash mismatch: {paper['paper_id']}")
        hashes[str(pdf_path.relative_to(ROOT))] = pdf_hash
        parsed = parse_pdf(pdf_path.read_bytes())
        chunk_ids = {chunk.chunk_id for chunk in parsed.chunks}
        with EvidenceRetriever(parsed.chunks) as retriever:
            for sample in [s for s in samples if s["paper_id"] == paper["paper_id"]]:
                claim = _claim(sample)
                query = build_claim_query(claim)
                baseline_ids = bm25_ids(retriever, query)
                current_ids = [c.chunk_id for c in retriever.search(query, claim.claim_id, 5)]
                gold = set(sample["gold_evidence_chunk_ids"])
                if not gold.issubset(chunk_ids):
                    raise ValueError(f"Gold chunk missing: {claim.claim_id}")
                assert len(baseline_ids) <= 5 and len(current_ids) <= 5
                assert len(set(baseline_ids)) == len(baseline_ids)
                assert len(set(current_ids)) == len(current_ids)
                rows.append({
                    "sample_id": claim.claim_id, "paper_id": paper["paper_id"],
                    "query": query, "gold_chunk_ids": sorted(gold),
                    "bm25_chunk_ids": baseline_ids, "current_chunk_ids": current_ids,
                    "bm25_hit": bool(gold.intersection(baseline_ids)),
                    "current_hit": bool(gold.intersection(current_ids)),
                })
    for path in provenance_paths:
        assert digest(path) == hashes[str(path.relative_to(ROOT))], "Source changed during evaluation"
    summary = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "python": platform.python_version(), "pymupdf": pymupdf.VersionBind,
        "sqlite": sqlite3.sqlite_version, "top_k": 5, "api_calls": 0,
        "metric": "Fraction of samples with at least one gold chunk in top five (hit rate, not all-evidence recall)",
        "baseline": "Production FTS5 index and query, ranked only by BM25",
        "current": "Current production retrieval including candidate supplementation and rule reranking",
        "limitations": "Fixed query_en from existing samples; no claim extraction or judgment evaluation; no tuning on holdout; six-paper sample, no broad generalization claim.",
        "isolation": isolation, "sha256": hashes, "overall": summarize(rows),
        "by_paper": {p["paper_id"]: summarize([r for r in rows if r["paper_id"] == p["paper_id"]]) for p in papers},
    }
    args.output_dir.mkdir(parents=True)
    (args.output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.output_dir / "predictions.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    print(json.dumps(summary["overall"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
