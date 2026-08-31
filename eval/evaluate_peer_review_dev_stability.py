"""Aggregate repeated real-model dev runs and produce a review queue.

This is intentionally paper-level: it checks recommendation/score drift and
the safety of P0/P1 concerns, without inventing issue-level gold alignment.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


_ORDER = {"STRONG_REJECT": 0, "WEAK_REJECT": 1, "BORDERLINE": 2, "WEAK_ACCEPT": 3, "STRONG_ACCEPT": 4}


def evaluate(run_dirs: list[Path], manifest: Path, review_path: Path | None = None) -> dict[str, object]:
    if len(run_dirs) < 2:
        raise ValueError("至少需要两次 dev 真实评审运行")
    keys = [str(item["paper_key"]) for item in json.loads(manifest.read_text(encoding="utf-8"))["papers"]]
    finalized_reviews: dict[str, dict[str, object]] = {}
    if review_path and review_path.is_file():
        review_payload = json.loads(review_path.read_text(encoding="utf-8"))
        for item in review_payload.get("items", []):
            if item.get("status") != "finalized" or item.get("needs_human_confirmation", True):
                continue
            finalized_reviews[str(item["paper_key"])] = item
    papers: list[dict[str, object]] = []
    review_queue: list[dict[str, object]] = []
    resolved_reviews: list[dict[str, object]] = []
    for key in keys:
        artifacts = []
        for run_dir in run_dirs:
            path = run_dir / f"{key}.json"
            if not path.is_file():
                raise FileNotFoundError(path)
            artifacts.append(json.loads(path.read_text(encoding="utf-8")))
        reports = [item["report"] for item in artifacts]
        decisions = [str(item.get("decision", "")) for item in reports]
        scores = [float(item.get("overall_score", 0)) for item in reports]
        high = []
        high_titles_by_run: list[set[str]] = []
        for run_index, report in enumerate(reports, 1):
            concerns = [*report.get("major_concerns", []), *report.get("minor_concerns", [])]
            high_count = 0
            high_titles: set[str] = set()
            for concern in concerns:
                level = str(concern.get("severity_level", ""))
                if level not in {"P0", "P1"}:
                    continue
                high_count += 1
                title = str(concern.get("title", ""))
                high_titles.add(title)
                if not concern.get("evidence"):
                    review_queue.append({
                        "paper_key": key,
                        "run": run_index,
                        "severity_level": level,
                        "title": title,
                        "reason": "高严重度问题缺少可定位引文",
                    })
            high.append(high_count)
            high_titles_by_run.append(high_titles)
        # Exact titles are not stable enough for comparison (the model may
        # paraphrase the same concern).  Use the number of high-risk concerns
        # as the drift signal, and expose all run-local titles only when that
        # count changes for manual review.
        drift_review = finalized_reviews.get(key) if len(set(high)) > 1 else None
        if drift_review:
            retained = str(drift_review.get("decision", "")).startswith("retain_p1")
            resolved_reviews.append({
                "paper_key": key,
                "decision": drift_review.get("decision"),
                "recommended_severity": drift_review.get("recommended_severity"),
                "adjudicated_high_risk_count": 1 if retained else 0,
                "evidence_chunks": drift_review.get("evidence_chunks", []),
            })
        elif len(set(high)) > 1:
            for run_index, titles in enumerate(high_titles_by_run, 1):
                for title in sorted(titles):
                    review_queue.append({
                        "paper_key": key,
                        "run": run_index,
                        "severity_level": "P0/P1",
                        "title": title,
                        "reason": "高风险问题数量在重复运行中变化，需人工确认是否保留",
                    })
        decision_values = [_ORDER.get(value, -1) for value in decisions]
        decision_span = max(decision_values) - min(decision_values)
        score_span = max(scores) - min(scores)
        papers.append({
            "paper_key": key,
            "decisions": decisions,
            "scores": scores,
            "decision_span_bands": decision_span,
            "score_span": score_span,
            "high_risk_counts": high,
            "stable_high_risk_title_count": min(high) if high else 0,
            "unstable_high_risk_title_count": max(high) - min(high) if high else 0,
            "adjudication": ({
                "decision": drift_review.get("decision"),
                "recommended_severity": drift_review.get("recommended_severity"),
            } if drift_review else None),
            "passed": decision_span <= 1 and score_span <= 1.5 and not any(
                item["paper_key"] == key for item in review_queue
            ),
        })
    result = {
        "evaluation_version": "peer-review-stage9-dev-stability-v1",
        "run_dirs": [str(path) for path in run_dirs],
        "paper_count": len(papers),
        "repeat_count": len(run_dirs),
        "passed": all(bool(item["passed"]) for item in papers),
        "policy": "同一论文重复运行允许最多一档建议漂移、评分最多 1.5 分；任何无证据 P0/P1 都必须人工复核后才能进入 holdout。",
        "papers": papers,
        "high_risk_review_queue": review_queue,
        "resolved_high_risk_reviews": resolved_reviews,
        "review_file": str(review_path) if review_path else None,
    }
    return result


def main() -> int:
    root = Path(__file__).parent
    parser = argparse.ArgumentParser(description="汇总 dev 集真实评审稳定性并生成高风险复核队列")
    parser.add_argument("--run-dir", action="append", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=root / "peer_review_dev_papers.json")
    parser.add_argument("--review", type=Path, default=root / "peer_review_stage9_dev_high_risk_review.json")
    parser.add_argument("--output", type=Path, default=root / "peer_review_stage9_dev_stability.json")
    args = parser.parse_args()
    result = evaluate(args.run_dir, args.manifest, args.review)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
