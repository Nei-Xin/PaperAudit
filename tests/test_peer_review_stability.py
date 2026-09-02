from __future__ import annotations

import json
from pathlib import Path

from eval.check_peer_review_stability import check


def _write(path: Path, decision: str, score: float) -> None:
    path.write_text(json.dumps({"report": {"decision": decision, "overall_score": score}}), encoding="utf-8")


def test_stability_allows_one_band_drift(tmp_path: Path) -> None:
    first, second = tmp_path / "a.json", tmp_path / "b.json"
    _write(first, "BORDERLINE", 6.0)
    _write(second, "WEAK_ACCEPT", 7.0)
    assert check([first, second])["passed"] is True


def test_stability_rejects_large_drift(tmp_path: Path) -> None:
    first, second = tmp_path / "a.json", tmp_path / "b.json"
    _write(first, "STRONG_REJECT", 2.0)
    _write(second, "STRONG_ACCEPT", 9.0)
    assert check([first, second])["passed"] is False
