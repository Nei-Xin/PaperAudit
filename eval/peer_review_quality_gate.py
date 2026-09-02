"""Quality gate for the structured peer-review regression set.

The gate is deliberately offline: it validates provenance/split hygiene and
checks a supplied prediction file against the frozen gold annotations.  It does
not download reviews or call a model.  Use ``--strict`` in CI/release jobs.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:  # Works both as ``python eval/...py`` and as an importable test module.
    from peer_review_quality import _load_jsonl, evaluate
except ModuleNotFoundError:  # pragma: no cover - exercised when imported as eval.*
    from .peer_review_quality import _load_jsonl, evaluate


def _portable_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return str(path)


def _dataset_checks(rows: list[dict[str, Any]], *, min_samples: int, min_papers: int) -> dict[str, Any]:
    papers = {str(row["openreview_url"]) for row in rows}
    fatal_without_evidence = [
        str(row["sample_id"])
        for row in rows
        if str(row.get("severity")) == "P0" and not bool(row.get("evidence_valid"))
    ]
    missing_split = [str(row["sample_id"]) for row in rows if str(row.get("split", "")).lower() not in {"dev", "holdout"}]
    # The combined regression file is intentionally allowed to omit split labels;
    # the dedicated dev/holdout files carry them and are checked separately.
    has_any_split = any(str(row.get("split", "")).strip() for row in rows)
    checks = {
        "min_samples": len(rows) >= min_samples,
        "min_papers": len(papers) >= min_papers,
        "fatal_severity_has_evidence": not fatal_without_evidence,
        "split_field_consistent": not has_any_split or not missing_split,
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "sample_count": len(rows),
        "paper_count": len(papers),
        "fatal_severity_without_evidence": fatal_without_evidence,
        "missing_split": missing_split if has_any_split else [],
    }


def _split_checks(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_split: dict[str, set[str]] = {"dev": set(), "holdout": set()}
    for row in rows:
        split = str(row.get("split", ""))
        if split in by_split:
            by_split[split].add(str(row["openreview_url"]))
    overlap = sorted(by_split["dev"] & by_split["holdout"])
    return {"passed": not overlap, "dev_papers": len(by_split["dev"]), "holdout_papers": len(by_split["holdout"]), "paper_overlap": overlap}


def _metric_checks(metrics: dict[str, Any], *, max_p1_miss: float) -> dict[str, Any]:
    checks = {
        "category_accuracy": float(metrics.get("category_accuracy", 0)) >= 0.85,
        "severity_macro_f1": float(metrics.get("severity_macro_f1", 0)) >= 0.85,
        "evidence_valid_accuracy": float(metrics.get("evidence_valid_accuracy", 0)) >= 0.95,
        "p0_false_positive_rate": float(metrics.get("p0_false_positive_rate", 1)) == 0.0,
        "p1_miss_rate_evidence_backed": float(
            metrics.get("p1_miss_rate_evidence_backed", metrics.get("p1_miss_rate", 1))
        ) <= max_p1_miss,
        "decision_severity_mismatch_rate": float(metrics.get("decision_severity_mismatch_rate", 1)) <= 0.10,
    }
    return {"passed": all(checks.values()), "checks": checks}


def run_gate(
    gold_path: Path,
    predictions_path: Path | None = None,
    *,
    min_samples: int = 30,
    min_papers: int = 10,
    max_p1_miss: float = 0.20,
) -> dict[str, Any]:
    gold = _load_jsonl(gold_path, validate_schema=True)
    dataset = _dataset_checks(gold, min_samples=min_samples, min_papers=min_papers)
    split = _split_checks(gold)
    result: dict[str, Any] = {
        "gate_version": "peer-review-quality-gate-v1",
        "gold": _portable_path(gold_path),
        "dataset": dataset,
        "split": split,
        "thresholds": {
            "min_samples": min_samples,
            "min_papers": min_papers,
            "max_p1_miss_rate": max_p1_miss,
        },
    }
    if predictions_path is None:
        result["metrics"] = {"status": "not_run", "reason": "未提供 predictions，仅检查数据集"}
        result["passed"] = bool(dataset["passed"] and split["passed"])
        return result
    predictions = _load_jsonl(predictions_path)
    metrics = evaluate(gold, predictions)
    result["metrics"] = metrics
    metric_gate = _metric_checks(metrics, max_p1_miss=max_p1_miss)
    result["metric_gate"] = metric_gate
    result["passed"] = bool(dataset["passed"] and split["passed"] and metric_gate["passed"])
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="运行 PaperAudit 投稿评审质量门禁")
    parser.add_argument("--gold", type=Path, default=Path(__file__).with_name("peer_review_regression.jsonl"))
    parser.add_argument("--predictions", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--min-samples", type=int, default=30)
    parser.add_argument("--min-papers", type=int, default=10)
    parser.add_argument("--max-p1-miss", type=float, default=0.20)
    parser.add_argument("--strict", action="store_true", help="门禁失败时返回非零退出码")
    args = parser.parse_args()
    result = run_gate(
        args.gold,
        args.predictions,
        min_samples=args.min_samples,
        min_papers=args.min_papers,
        max_p1_miss=args.max_p1_miss,
    )
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if result["passed"] or not args.strict else 1


if __name__ == "__main__":
    raise SystemExit(main())
