"""Bounded review of the citations behind a supported audit judgment."""
from __future__ import annotations

from .audit_rules import apply_citation_review
from .hy3_client import Hy3Client, Hy3ResponseError
from .models import AtomicClaim, AutoLabel, CitationReview, ClaimJudgment, EvidenceCandidate


def review_supported_citations(
    client: Hy3Client,
    claim: AtomicClaim,
    candidates: list[EvidenceCandidate],
    judgment: ClaimJudgment,
) -> tuple[ClaimJudgment, CitationReview | None, CitationReview | None]:
    """Review once; repair locally invalid quotations/IDs once, never a gap.

    Return the accepted-or-abstained judgment, final review, and pre-repair
    review. Provider errors propagate as in the rest of the audit pipeline;
    malformed structured responses fail closed without an extra semantic retry.
    """
    if judgment.label != AutoLabel.SUPPORTED:
        return judgment, None, None
    review = None
    before_repair = None
    try:
        review = client.review_citation_coverage(claim, candidates, judgment)
    except Hy3ResponseError:
        pass
    final = apply_citation_review(judgment, candidates, review)
    if (review is not None and review.complete and not review.missing_aspects
            and review.aspects and review.claim_id == claim.claim_id == judgment.claim_id
            and final.label == AutoLabel.ABSTAIN):
        before_repair, review = review, None
        try:
            review = client.repair_citation_coverage(claim, candidates, before_repair)
        except Hy3ResponseError:
            pass
        final = apply_citation_review(judgment, candidates, review)
    return final, review, before_repair
