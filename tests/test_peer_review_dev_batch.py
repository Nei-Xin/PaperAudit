from __future__ import annotations

from paperaudit.models import PeerReviewVenue
from eval.run_peer_review_dev_batch import _VENUES


def test_dev_batch_uses_supported_venue_mapping() -> None:
    assert _VENUES["NeurIPS"] == PeerReviewVenue.NEURIPS
    assert _VENUES["ICLR"] == PeerReviewVenue.ICLR
    assert "ICML" not in _VENUES
