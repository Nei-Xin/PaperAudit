"""运行错误类型 v2 的四数据集统一回归。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from run_eval import run as run_eval


EVAL_DIR = Path(__file__).resolve().parent
DATA_DIR = EVAL_DIR / "error_type_v2"
DEFAULT_OUTPUT = EVAL_DIR / "results_error_type_v2_regression_actual"

DATASETS: tuple[dict[str, Any], ...] = (
    {"name": "holdout", "min_recall": 1.0},
    {"name": "broad", "min_recall": 0.85},
    {"name": "body", "min_recall": 0.90},
    {"name": "cross_v2", "min_recall": 0.90},
)


def run(output_dir: Path, *, dry_run: bool, top_k: int) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for dataset in DATASETS:
        name = dataset["name"]
        result = run_eval(
            DATA_DIR / f"{name}_resolved_samples.jsonl",
            output_dir / name,
            dry_run=dry_run,
            retrieval_top_k=top_k,
            papers_path=DATA_DIR / f"{name}_papers.json",
        )
        metrics = result["metrics"]
        passed = (
            metrics.get("retrieval_hit_rate") is not None
            and metrics["retrieval_hit_rate"] >= dataset["min_recall"]
        )
        rows.append(
            {
                "name": name,
                "min_recall": dataset["min_recall"],
                "passed": passed,
                "metrics": metrics,
                "output_dir": result["output_dir"],
            }
        )
    summary = {
        "version": "error-taxonomy-v2",
        "config": {"dry_run": dry_run, "retrieval_top_k": top_k},
        "regression_passed": all(row["passed"] for row in rows),
        "datasets": rows,
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="运行错误类型 v2 四数据集回归。")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.top_k < 1:
        raise SystemExit("--top-k 必须大于 0。")
    summary = run(args.output_dir, dry_run=args.dry_run, top_k=args.top_k)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if not summary["regression_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
