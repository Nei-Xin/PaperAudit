from __future__ import annotations

from pathlib import Path

from eval.check_peer_review_dev_pdfs import check


def test_dev_pdf_manifest_is_intact() -> None:
    root = Path("eval")
    result = check(root / "peer_review_dev_papers.json", root / "peer_review_regression_dev.jsonl")
    assert result["passed"] is True
