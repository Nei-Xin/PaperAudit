"""Verify the second v2 boundary validation set is isolated from all prior data."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


EVAL_DIR = Path(__file__).resolve().parent


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def check(papers_path: Path, samples_path: Path) -> dict[str, object]:
    papers = _json(papers_path)
    ids = {str(row["paper_id"]) for row in papers}
    hashes = {str(row["sha256"]) for row in papers}
    local_hashes = {hashlib.sha256((EVAL_DIR / str(row["local_pdf"])).read_bytes()).hexdigest() for row in papers}
    prior_ids: set[str] = set()
    prior_hashes: set[str] = set()
    for path in EVAL_DIR.glob("*_papers.json"):
        if path.resolve() != papers_path.resolve():
            for row in _json(path):
                prior_ids.add(str(row["paper_id"]))
                prior_hashes.add(str(row.get("sha256", "")))
    for path in (EVAL_DIR / "v2_diagnostics/missing_condition_papers.json", EVAL_DIR / "v2_diagnostics/holdout_papers.json"):
        for row in _json(path):
            prior_ids.add(str(row["paper_id"]))
            prior_hashes.add(str(row.get("sha256", "")))
    production_hashes = {
        str(json.loads(line).get("paper_hash", ""))
        for path in (EVAL_DIR / "production_observations_v1").glob("runtime*/audits.jsonl")
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    }
    samples = [json.loads(line) for line in samples_path.read_text(encoding="utf-8").splitlines() if line]
    sample_papers = {str(row["paper_id"]) for row in samples}
    result = {
        "validation_paper_count": len(papers),
        "validation_sample_count": len(samples),
        "sample_paper_count": len(sample_papers),
        "paper_id_overlap": sorted(ids & prior_ids),
        "declared_sha256_overlap": sorted(hashes & prior_hashes),
        "production_pdf_hash_overlap": sorted(local_hashes & production_hashes),
        "all_samples_reference_validation_papers": sample_papers == ids,
        "isolated": len(papers) == 4 and len(samples) == 16 and sample_papers == ids and not (ids & prior_ids) and not (hashes & prior_hashes) and not (local_hashes & production_hashes),
        "policy": "v2 第二批独立边界验证集；只验证标签规范稳定性，不用于调参",
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="检查 v2 第二批边界验证集隔离性。")
    parser.add_argument("--papers", type=Path, default=EVAL_DIR / "v2_diagnostics/validation_papers.json")
    parser.add_argument("--samples", type=Path, default=EVAL_DIR / "v2_diagnostics/validation_resolved_samples.jsonl")
    args = parser.parse_args()
    result = check(args.papers, args.samples)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["isolated"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
