"""Verify that the v2 diagnostic papers are isolated from v1 data and production runs."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


EVAL_DIR = Path(__file__).resolve().parent


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def check(papers_path: Path, samples_path: Path) -> dict[str, object]:
    diagnostic = _json(papers_path)
    diagnostic_ids = {str(row["paper_id"]) for row in diagnostic}
    diagnostic_hashes = {str(row["sha256"]) for row in diagnostic}

    fixed_ids: set[str] = set()
    fixed_hashes: set[str] = set()
    for path in EVAL_DIR.glob("*_papers.json"):
        if path.resolve() == papers_path.resolve():
            continue
        for row in _json(path):
            fixed_ids.add(str(row["paper_id"]))
            fixed_hashes.add(str(row.get("sha256", "")))

    production_hashes: set[str] = set()
    for path in (EVAL_DIR / "production_observations_v1").glob("runtime*/audits.jsonl"):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line:
                row = json.loads(line)
                production_hashes.add(str(row.get("paper_hash", "")))

    sample_ids: set[str] = set()
    sample_papers: set[str] = set()
    if samples_path.exists():
        for line in samples_path.read_text(encoding="utf-8").splitlines():
            if line:
                row = json.loads(line)
                sample_ids.add(str(row["sample_id"]))
                sample_papers.add(str(row["paper_id"]))

    local_hashes = {
        hashlib.sha256((EVAL_DIR / str(row["local_pdf"])).read_bytes()).hexdigest()
        for row in diagnostic
    }
    result = {
        "diagnostic_paper_count": len(diagnostic),
        "diagnostic_sample_count": len(sample_ids),
        "sample_paper_count": len(sample_papers),
        "fixed_paper_id_overlap": sorted(diagnostic_ids & fixed_ids),
        "fixed_pdf_hash_overlap": sorted(diagnostic_hashes & fixed_hashes),
        "production_pdf_hash_overlap": sorted(local_hashes & production_hashes),
        "all_samples_reference_diagnostic_papers": sample_papers == diagnostic_ids,
        "samples_file": str(samples_path),
        "isolated": (
            len(diagnostic) == 8
            and len(sample_ids) >= 32
            and sample_papers == diagnostic_ids
            and not (diagnostic_ids & fixed_ids)
            and not (diagnostic_hashes & fixed_hashes)
            and not (local_hashes & production_hashes)
        ),
        "policy": "v2 诊断开发集；不加入 v1 固定集、最终留出集或生产观测，不直接用于发布门禁",
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="检查 v2 missing_condition 诊断集隔离性。")
    parser.add_argument(
        "--papers",
        type=Path,
        default=EVAL_DIR / "v2_diagnostics/missing_condition_papers.json",
    )
    parser.add_argument(
        "--samples",
        type=Path,
        default=EVAL_DIR / "v2_diagnostics/missing_condition_resolved_samples_v2.jsonl",
    )
    args = parser.parse_args()
    result = check(args.papers, args.samples)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["isolated"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
