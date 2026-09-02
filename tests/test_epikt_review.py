from __future__ import annotations

from pathlib import Path

from eval.check_epikt_review import check


def test_epikt_fixture_preserves_core_findings() -> None:
    fixture = Path("D:/downloads/paperaudit-peer-review.md")
    if not fixture.exists():
        return
    result = check(fixture)
    assert result["passed"] is True
