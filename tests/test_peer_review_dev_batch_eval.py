from __future__ import annotations

from eval.evaluate_peer_review_dev_batch import _paper_key


def test_paper_key_normalizes_arxiv_versions() -> None:
    assert _paper_key({"arxiv_url": "https://arxiv.org/abs/2306.07915"}) == "2306.07915"
