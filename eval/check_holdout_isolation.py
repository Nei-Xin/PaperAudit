"""Verify that final holdout papers do not occur in any tuning/evaluation split."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


EVAL_DIR = Path(__file__).resolve().parent
DEFAULT_SPLITS = (
    "papers.json", "holdout_papers.json", "extended_papers.json", "broad_papers.json",
    "concept_papers.json", "cross_papers_v2.json", "external_papers_v1.json", "external_papers_v2.json",
)


def check(final_path: Path, split_paths: list[Path]) -> dict[str, object]:
    final = json.loads(final_path.read_text(encoding="utf-8"))
    final_ids = {str(row["paper_id"]) for row in final}
    overlaps: dict[str, list[str]] = {}
    for path in split_paths:
        rows = json.loads(path.read_text(encoding="utf-8"))
        overlap = sorted(final_ids & {str(row["paper_id"]) for row in rows})
        if overlap:
            overlaps[path.name] = overlap
    return {
        "final_paper_count": len(final_ids),
        "final_paper_ids": sorted(final_ids),
        "checked_split_count": len(split_paths),
        "overlaps": overlaps,
        "isolated": not overlaps,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--final", type=Path, default=EVAL_DIR / "final_holdout_papers.json")
    parser.add_argument("--splits", nargs="*", type=Path, default=[EVAL_DIR / name for name in DEFAULT_SPLITS])
    args = parser.parse_args()
    result = check(args.final, args.splits)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["isolated"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
