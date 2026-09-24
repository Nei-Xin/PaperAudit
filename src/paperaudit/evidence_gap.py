"""Bounded recheck for negative judgments when candidates contain structured evidence."""
from __future__ import annotations

import re

from .audit_rules import calibrate_judgment, validate_judgment_references
from .hy3_client import Hy3Client, Hy3ResponseError
from .models import AtomicClaim, AutoLabel, CandidateGapReview, ClaimJudgment, EvidenceCandidate


def candidate_gap_trigger(claim: AtomicClaim, candidates: list[EvidenceCandidate]) -> bool:
    """Select only likely table/configuration cases for the extra call."""
    if not candidates or not claim.numbers:
        return False
    for candidate in candidates:
        text = candidate.text.casefold()
        if "table" in text or "表" in text:
            return True
        numeric_lines = sum(
            len(re.findall(r"\d+(?:\.\d+)?%?", line)) >= 2
            for line in candidate.text.splitlines()
        )
        if numeric_lines >= 2:
            return True
    return False


def recheck_candidate_gap(
    client: Hy3Client,
    claim: AtomicClaim,
    candidates: list[EvidenceCandidate],
    judgment: ClaimJudgment,
    page_count: int,
) -> tuple[ClaimJudgment, CandidateGapReview | None]:
    """Recheck one negative judgment once; fail closed on API/schema errors."""
    if judgment.label == AutoLabel.SUPPORTED or not candidate_gap_trigger(claim, candidates):
        return judgment, None
    try:
        review = client.review_candidate_gap(claim, candidates, judgment, page_count)
    except Hy3ResponseError:
        return judgment, None
    if review.claim_id != claim.claim_id or not review.evidence_relevant:
        return judgment, review
    # The recheck is allowed to recover a missed full-support result. A second
    # negative/partial interpretation must not rewrite the original judgment:
    # calibration can turn a numeric mismatch into CONTRADICTED, which would
    # overstate a mere evidence gap.
    if review.judgment.label != AutoLabel.SUPPORTED:
        return judgment, review
    proposed = validate_judgment_references(calibrate_judgment(review.judgment), candidates)
    if proposed.label != AutoLabel.SUPPORTED:
        return judgment, review
    return proposed, review
