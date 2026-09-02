"""运行 PaperAudit 固定评测集回归并生成验收摘要。

默认只运行本地解析/检索（--dry-run），因此可在无 API 的环境中稳定检查召回
是否回归。传入 --actual 才会调用 Hy3；两种模式都使用同一批固定样本和 PDF。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from run_eval import run as run_eval


EVAL_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT = EVAL_DIR / "results_regression_latest"

# 这些是当前冻结基线的最低证据召回门槛，不是论文或样本专属规则。
DATASETS: tuple[dict[str, Any], ...] = (
    {"name": "dev", "samples": "resolved_samples.jsonl", "papers": "papers.json", "min_recall": 1.0},
    {"name": "holdout", "samples": "holdout_resolved_samples.jsonl", "papers": "holdout_papers.json", "min_recall": 1.0},
    {"name": "extended", "samples": "extended_resolved_samples.jsonl", "papers": "extended_papers.json", "min_recall": 0.95},
    {"name": "broad", "samples": "broad_resolved_samples.jsonl", "papers": "broad_papers.json", "min_recall": 0.85},
    {"name": "body", "samples": "body_resolved_samples.jsonl", "papers": "broad_papers.json", "min_recall": 0.90},
    {"name": "concept", "samples": "concept_resolved_samples.jsonl", "papers": "concept_papers.json", "min_recall": 0.55},
    {"name": "cross_v2", "samples": "cross_resolved_samples_v2.jsonl", "papers": "cross_papers_v2.json", "min_recall": 0.90},
    {"name": "external_v1", "samples": "external_resolved_samples_v1.jsonl", "papers": "external_papers_v1.json", "min_recall": 0.75},
    {"name": "external_v2", "samples": "external_resolved_samples_v2.jsonl", "papers": "external_papers_v2.json", "min_recall": 0.90},
    # 完全按论文隔离的最终留出集；冻结规则后只用于最终泛化验收。
    {"name": "final_holdout", "samples": "final_holdout_resolved_samples.jsonl", "papers": "final_holdout_papers.json", "min_recall": 0.85, "independent_final": True},
)


def _markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# PaperAudit 统一回归结果",
        "",
        f"模式：`{'actual' if not summary['config']['dry_run'] else 'dry-run'}`；Top-K：`{summary['config']['retrieval_top_k']}`。",
        "",
        "| 数据集 | 样本数 | Top-5 召回 | 最低门槛 | 结果 |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for row in summary["datasets"]:
        metrics = row["metrics"]
        recall = metrics.get("retrieval_hit_rate")
        recall_text = "—" if recall is None else f"{recall:.2%}"
        lines.append(
            f"| {row['name']} | {metrics['sample_count']} | {recall_text} | "
            f"{row['min_recall']:.2%} | {'PASS' if row['passed'] else 'FAIL'} |"
        )
    lines.extend(
        [
            "",
            f"总体结果：**{'PASS' if summary['regression_passed'] else 'FAIL'}**。",
            "",
            "分层指标保留在各数据集目录的 `metrics.json`，仅用于诊断，不参与规则分支。",
        ]
    )
    return "\n".join(lines) + "\n"


def run_regression(
    output_dir: Path = DEFAULT_OUTPUT,
    *,
    dry_run: bool = True,
    retrieval_top_k: int = 5,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for dataset in DATASETS:
        dataset_output = output_dir / dataset["name"]
        result = run_eval(
            EVAL_DIR / dataset["samples"],
            dataset_output,
            dry_run=dry_run,
            retrieval_top_k=retrieval_top_k,
            papers_path=EVAL_DIR / dataset["papers"],
        )
        metrics = result["metrics"]
        recall = metrics.get("retrieval_hit_rate")
        passed = recall is not None and recall >= dataset["min_recall"]
        rows.append(
            {
                "name": dataset["name"],
                "samples": dataset["samples"],
                "papers": dataset["papers"],
                "min_recall": dataset["min_recall"],
                "independent_final": bool(dataset.get("independent_final", False)),
                "passed": passed,
                "metrics": metrics,
                "output_dir": str(dataset_output),
            }
        )
    summary = {
        "config": {"dry_run": dry_run, "retrieval_top_k": retrieval_top_k},
        "regression_passed": all(row["passed"] for row in rows),
        "final_holdout_is_independent": True,
        "final_holdout_policy": "论文级隔离；不用于规则调优，仅用于最终泛化验收",
        "datasets": rows,
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output_dir / "summary.md").write_text(_markdown(summary), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="运行 PaperAudit 固定评测集统一回归。")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--actual", action="store_true", help="调用真实 Hy3 API；默认只跑离线检索。")
    args = parser.parse_args()
    if args.top_k < 1:
        raise SystemExit("--top-k 必须大于 0。")
    summary = run_regression(args.output_dir, dry_run=not args.actual, retrieval_top_k=args.top_k)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if not summary["regression_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
