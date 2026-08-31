"""Offline quality metrics for structured PaperAudit peer-review outputs.

The script intentionally reads only compact, manually reviewed records. It never
downloads review pages or sends paper content to a model.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


_CATEGORIES = {
    "correctness", "evidence", "evaluation", "novelty",
    "reproducibility", "ethics", "clarity", "other",
}
_SEVERITIES = {"P0", "P1", "P2", "P3"}
_REQUIRED_PROVENANCE = {"paper_title", "openreview_url", "meeting", "year"}
_PAPER_VERSION_FIELDS = ("arxiv_url", "paper_version_url")


def _load_jsonl(path: Path, *, validate_schema: bool = False) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_no} 不是有效 JSON") from exc
        if not isinstance(row, dict) or not row.get("sample_id"):
            raise ValueError(f"{path}:{line_no} 缺少 sample_id")
        rows.append(row)
    if validate_schema:
        _validate_gold_rows(rows, path)
    return rows


def _validate_gold_rows(rows: list[dict[str, Any]], path: Path) -> None:
    """Fail early on malformed or untraceable regression annotations."""
    seen: set[str] = set()
    for index, row in enumerate(rows, 1):
        sample_id = str(row["sample_id"])
        if sample_id in seen:
            raise ValueError(f"{path}:{index} 重复 sample_id：{sample_id}")
        seen.add(sample_id)
        missing = [name for name in _REQUIRED_PROVENANCE if not str(row.get(name, "")).strip()]
        if missing:
            raise ValueError(f"{path}:{index} 缺少来源字段：{', '.join(sorted(missing))}")
        has_direct_note = bool(str(row.get("source_note_id", "")).strip()) and bool(
            str(row.get("source_note_url", "")).strip()
        )
        has_archive_record = all(
            str(row.get(field, "")).strip()
            for field in ("source_archive_url", "source_record_id", "source_archive_commit", "source_license")
        )
        if not has_direct_note and not has_archive_record:
            raise ValueError(
                f"{path}:{index} 缺少可复核评审来源：需要 OpenReview note 或版本化公开归档记录"
            )
        if not any(str(row.get(field, "")).startswith("https://") for field in _PAPER_VERSION_FIELDS):
            raise ValueError(f"{path}:{index} 缺少固定论文版本 URL（arxiv_url 或 paper_version_url）")
        for field in (
            "arxiv_url",
            "paper_version_url",
            "openreview_url",
            "source_note_url",
            "source_archive_url",
        ):
            if field in row and str(row[field]).strip() and not str(row[field]).startswith("https://"):
                raise ValueError(f"{path}:{index} {field} 必须是 HTTPS URL")
        if has_direct_note and "noteId=" not in str(row["source_note_url"]):
            raise ValueError(f"{path}:{index} source_note_url 缺少 noteId")
        if has_archive_record and str(row["source_license"]).strip().upper() != "CC-BY-4.0":
            raise ValueError(f"{path}:{index} source_license 必须明确为 CC-BY-4.0")
        if str(row.get("category", "")) not in _CATEGORIES:
            raise ValueError(f"{path}:{index} category 无效")
        if str(row.get("severity", "")) not in _SEVERITIES:
            raise ValueError(f"{path}:{index} severity 无效")
        confidence = row.get("confidence")
        if not isinstance(confidence, int) or not 1 <= confidence <= 5:
            raise ValueError(f"{path}:{index} confidence 必须为 1–5 整数")
        if "actionability" not in row and "actionable" in row:
            row["actionability"] = bool(row["actionable"])
        if "actionability" not in row:
            raise ValueError(f"{path}:{index} 缺少 actionability")
    if not rows:
        raise ValueError(f"{path} 为空，至少需要一条标注记录")


def _macro_f1(gold: list[str], pred: list[str]) -> float:
    labels = sorted(set(gold) | set(pred))
    if not labels:
        return 0.0
    scores: list[float] = []
    for label in labels:
        tp = sum(g == label and p == label for g, p in zip(gold, pred))
        fp = sum(g != label and p == label for g, p in zip(gold, pred))
        fn = sum(g == label and p != label for g, p in zip(gold, pred))
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        scores.append(2 * precision * recall / (precision + recall) if precision + recall else 0.0)
    return sum(scores) / len(scores)


def _align(gold_rows: list[dict[str, Any]], pred_rows: list[dict[str, Any]]) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    predicted = {str(row["sample_id"]): row for row in pred_rows}
    missing = [str(row["sample_id"]) for row in gold_rows if str(row["sample_id"]) not in predicted]
    if missing:
        raise ValueError("预测缺少样本：" + ", ".join(missing[:8]))
    return [(row, predicted[str(row["sample_id"])]) for row in gold_rows]


def evaluate(gold_rows: list[dict[str, Any]], pred_rows: list[dict[str, Any]]) -> dict[str, Any]:
    pairs = _align(gold_rows, pred_rows)
    category_gold = [str(g.get("category", "other")) for g, _ in pairs]
    category_pred = [str(p.get("category", "other")) for _, p in pairs]
    severity_gold = [str(g.get("severity", "P2")) for g, _ in pairs]
    severity_pred = [str(p.get("severity", "P2")) for _, p in pairs]
    evidence_hits = [bool(p.get("evidence_valid")) == bool(g.get("evidence_valid")) for g, p in pairs]
    p0_fp = sum(p == "P0" and g != "P0" for g, p in zip(severity_gold, severity_pred))
    p0_pred = sum(p == "P0" for p in severity_pred)
    p1_fn = sum(g == "P1" and p != "P1" for g, p in zip(severity_gold, severity_pred))
    p1_gold = sum(g == "P1" for g in severity_gold)
    # A conservative downgrade is expected when the gold issue itself has no
    # verifiable paper evidence.  Track the evidence-backed subset separately
    # so the recall gate measures missed, actionable high-risk findings.
    # Rebuild directly from aligned rows for deterministic per-record accounting.
    p1_evidence_gold = 0
    p1_evidence_fn = 0
    for gold_row, pred_row in pairs:
        if str(gold_row.get("severity")) == "P1" and bool(gold_row.get("evidence_valid")):
            p1_evidence_gold += 1
            if str(pred_row.get("severity", "P2")) != "P1":
                p1_evidence_fn += 1
    calibration = []
    for gold, pred in pairs:
        confidence = max(1, min(5, int(pred.get("confidence", 3))))
        target = 1.0 if bool(gold.get("evidence_valid")) else 0.0
        calibration.append(abs(confidence / 5 - target))
    decision_mismatch = 0
    for gold, pred in pairs:
        decision = str(pred.get("decision", gold.get("gold_decision", "BORDERLINE")))
        max_severity = min((severity_pred[i] for i, (g, _) in enumerate(pairs) if g["sample_id"] == gold["sample_id"]), default="P2")
        if decision in {"STRONG_ACCEPT", "WEAK_ACCEPT"} and max_severity == "P0":
            decision_mismatch += 1
        if decision == "STRONG_REJECT" and max_severity not in {"P0", "P1"}:
            decision_mismatch += 1
    return {
        "sample_count": len(pairs),
        "paper_count": len({str(g["openreview_url"]) for g, _ in pairs}),
        "category_accuracy": sum(g == p for g, p in zip(category_gold, category_pred)) / len(pairs),
        "severity_macro_f1": _macro_f1(severity_gold, severity_pred),
        "evidence_valid_accuracy": sum(evidence_hits) / len(evidence_hits),
        "confidence_calibration_mae": sum(calibration) / len(calibration),
        "p0_false_positive_rate": p0_fp / p0_pred if p0_pred else 0.0,
        "p1_miss_rate": p1_fn / p1_gold if p1_gold else 0.0,
        "p1_miss_rate_evidence_backed": p1_evidence_fn / p1_evidence_gold if p1_evidence_gold else 0.0,
        "p1_evidence_backed_count": p1_evidence_gold,
        "decision_severity_mismatch_rate": decision_mismatch / len(pairs),
        "gold_category_distribution": dict(Counter(category_gold)),
        "gold_severity_distribution": dict(Counter(severity_gold)),
    }


def _oracle_predictions(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "sample_id": row["sample_id"],
            "category": row.get("category", "other"),
            "severity": row.get("severity", "P2"),
            "confidence": row.get("confidence", 3),
            "evidence_valid": row.get("evidence_valid", False),
            "decision": row.get("gold_decision", "BORDERLINE"),
        }
        for row in rows
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="评审问题抽取离线质量评估")
    parser.add_argument("--gold", type=Path, default=Path(__file__).with_name("peer_review_regression.jsonl"))
    parser.add_argument("--predictions", type=Path, help="模型输出 JSONL；不提供则运行结构校验 oracle dry-run")
    parser.add_argument("--compare", type=Path, help="可选的第二份预测，用于比较版本")
    parser.add_argument("--output", type=Path, help="写入 JSON 报告")
    parser.add_argument("--markdown", type=Path, help="写入 Markdown 报告")
    args = parser.parse_args()
    gold = _load_jsonl(args.gold, validate_schema=True)
    pred = _load_jsonl(args.predictions) if args.predictions else _oracle_predictions(gold)
    result: dict[str, Any] = {"metrics": evaluate(gold, pred), "gold": str(args.gold), "predictions": str(args.predictions) if args.predictions else "oracle-dry-run"}
    if args.compare:
        result["compare_metrics"] = evaluate(gold, _load_jsonl(args.compare))
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    if args.markdown:
        metrics = result["metrics"]
        lines = ["# Peer-review quality evaluation", "", f"样本数：{metrics['sample_count']}", f"论文数：{metrics['paper_count']}", "", "| 指标 | 数值 |", "|---|---:|"]
        for key, value in metrics.items():
            if isinstance(value, (int, float)):
                lines.append(f"| {key} | {value:.4f} |" if isinstance(value, float) else f"| {key} | {value} |")
        args.markdown.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
