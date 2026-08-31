"""Evaluate real dev reviews without leaking issue labels into model output.

The public regression set intentionally stores compact issue labels, not full
review prose. Therefore this evaluator reports paper-level decision/score
agreement and risk coverage, while explicitly avoiding fake issue-to-concern
semantic matches.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean
from urllib.parse import parse_qs, urlparse


_DECISION_ORDER = {"STRONG_REJECT": 0, "WEAK_REJECT": 1, "BORDERLINE": 2, "WEAK_ACCEPT": 3, "STRONG_ACCEPT": 4}


def _rows(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _paper_key(row: dict[str, object]) -> str:
    explicit = str(row.get("paper_key", "")).strip()
    if explicit:
        return explicit
    arxiv = str(row.get("arxiv_url", "")).strip()
    if arxiv:
        value = arxiv.rsplit("/", 1)[-1]
        return value.removesuffix(".html").replace("v1", "").replace("v2", "").replace("v3", "").replace("v5", "")
    forum = str(row.get("openreview_url", "")).strip()
    forum_id = parse_qs(urlparse(forum).query).get("id", [""])[0]
    if forum_id:
        return str(forum_id)
    value = str(row.get("paper_version_url") or "").rsplit("/", 1)[-1]
    return value.removesuffix(".html").replace("v1", "").replace("v2", "").replace("v3", "").replace("v5", "")


def evaluate(dev_path: Path, output_dir: Path) -> dict[str, object]:
    rows = _rows(dev_path)
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[_paper_key(row)].append(row)
    details: list[dict[str, object]] = []
    for key, gold_rows in sorted(grouped.items()):
        path = output_dir / f"{key}.json"
        if not path.is_file():
            raise FileNotFoundError(f"缺少真实 dev 评审：{path}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        report = payload["report"]
        concerns = [*report.get("major_concerns", []), *report.get("minor_concerns", [])]
        gold_decision = str(gold_rows[0].get("gold_decision", "BORDERLINE"))
        gold_score = float(gold_rows[0].get("gold_score", 5.0))
        generated_decision = str(report.get("decision", "BORDERLINE"))
        gold_categories = {str(row.get("category")) for row in gold_rows}
        generated_categories = {str(item.get("category")) for item in concerns}
        has_gold_p1 = any(str(row.get("severity")) == "P1" for row in gold_rows)
        has_generated_high = any(str(item.get("severity_level")) in {"P0", "P1"} for item in concerns)
        details.append({
            "paper_key": key,
            "gold_decision": gold_decision,
            "generated_decision": generated_decision,
            "decision_match": generated_decision == gold_decision,
            "gold_score": gold_score,
            "generated_score": float(report.get("overall_score", 0)),
            "score_abs_error": abs(float(report.get("overall_score", 0)) - gold_score),
            "gold_p1": has_gold_p1,
            "generated_high_risk": has_generated_high,
            "p1_risk_covered": not has_gold_p1 or has_generated_high,
            "gold_categories": sorted(gold_categories),
            "generated_categories": sorted(generated_categories),
            "category_coverage": len(gold_categories & generated_categories) / len(gold_categories) if gold_categories else 1.0,
            "concern_count": len(concerns),
            "evidence_rate": sum(bool(item.get("evidence")) for item in concerns) / len(concerns) if concerns else 1.0,
            "actionability_rate": sum(bool(item.get("suggestion")) for item in concerns) / len(concerns) if concerns else 1.0,
            "unsupported_high_risk_count": sum(str(item.get("severity_level")) in {"P0", "P1"} and not item.get("evidence") for item in concerns),
            "warning_count": len(report.get("parse_warnings", [])),
        })
    result = {
        "evaluation_version": "peer-review-stage9-dev-paper-v1",
        "gold_policy": "paper_level_only; no fabricated issue semantic alignment",
        "paper_count": len(details),
        "decision_accuracy": mean(bool(item["decision_match"]) for item in details) if details else 0.0,
        "mean_abs_score_error": mean(float(item["score_abs_error"]) for item in details) if details else 0.0,
        "p1_paper_recall": mean(bool(item["p1_risk_covered"]) for item in details) if details else 0.0,
        "category_coverage": mean(float(item["category_coverage"]) for item in details) if details else 0.0,
        "evidence_rate": mean(float(item["evidence_rate"]) for item in details) if details else 0.0,
        "actionability_rate": mean(float(item["actionability_rate"]) for item in details) if details else 0.0,
        "unsupported_high_risk_count": sum(int(item["unsupported_high_risk_count"]) for item in details),
        "mean_warning_count": mean(int(item["warning_count"]) for item in details) if details else 0.0,
        "details": details,
        "limitations": ["当前回归集未保存 reviewer 原文，因此不计算伪造的逐条 issue 语义匹配 Macro-F1。"],
    }
    return result


def main() -> int:
    root = Path(__file__).parent
    parser = argparse.ArgumentParser(description="评估 dev 集真实模型投稿评审")
    parser.add_argument("--dev", type=Path, default=root / "peer_review_regression_dev.jsonl")
    parser.add_argument("--output-dir", type=Path, default=root / "stage9_dev_real")
    parser.add_argument("--output", type=Path, default=root / "peer_review_stage9_dev_report.json")
    args = parser.parse_args()
    result = evaluate(args.dev, args.output_dir)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
