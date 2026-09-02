from __future__ import annotations

import json
from pathlib import Path

from eval.evaluate_peer_review_dev_stability import evaluate


def _write_run(path: Path, *, score: float, concerns: list[dict[str, object]]) -> None:
    path.mkdir()
    (path / "paper.json").write_text(json.dumps({
        "report": {
            "decision": "WEAK_ACCEPT",
            "overall_score": score,
            "major_concerns": concerns,
            "minor_concerns": [],
        }
    }), encoding="utf-8")


def _manifest(path: Path) -> Path:
    target = path / "manifest.json"
    target.write_text(json.dumps({"papers": [{"paper_key": "paper"}]}), encoding="utf-8")
    return target


def test_finalized_review_resolves_high_risk_count_drift(tmp_path: Path) -> None:
    run1, run2 = tmp_path / "run1", tmp_path / "run2"
    _write_run(run1, score=7, concerns=[{
        "severity_level": "P1", "title": "中心风险", "evidence": [{"chunk_id": "p1"}]
    }])
    _write_run(run2, score=8, concerns=[])
    review = tmp_path / "review.json"
    review.write_text(json.dumps({"items": [{
        "paper_key": "paper",
        "status": "finalized",
        "needs_human_confirmation": False,
        "decision": "retain_p1_candidate",
        "recommended_severity": "P1",
        "evidence_chunks": ["p1"],
    }]}), encoding="utf-8")

    result = evaluate([run1, run2], _manifest(tmp_path), review)

    assert result["passed"] is True
    assert result["high_risk_review_queue"] == []
    assert result["resolved_high_risk_reviews"][0]["adjudicated_high_risk_count"] == 1


def test_review_cannot_exempt_unsupported_high_risk(tmp_path: Path) -> None:
    run1, run2 = tmp_path / "run1", tmp_path / "run2"
    concern = {"severity_level": "P1", "title": "无证据风险", "evidence": []}
    _write_run(run1, score=7, concerns=[concern])
    _write_run(run2, score=7, concerns=[concern])
    review = tmp_path / "review.json"
    review.write_text(json.dumps({"items": [{
        "paper_key": "paper",
        "status": "finalized",
        "needs_human_confirmation": False,
        "decision": "retain_p1_candidate",
        "recommended_severity": "P1",
    }]}), encoding="utf-8")

    result = evaluate([run1, run2], _manifest(tmp_path), review)

    assert result["passed"] is False
    assert any(item["reason"] == "高严重度问题缺少可定位引文" for item in result["high_risk_review_queue"])
