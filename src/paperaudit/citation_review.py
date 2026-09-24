"""Bounded review of citations behind support and contradiction judgments."""
from __future__ import annotations

from .audit_rules import apply_citation_review
from .hy3_client import Hy3Client, Hy3ResponseError
from .models import AtomicClaim, AutoLabel, CitationReview, ClaimJudgment, EvidenceCandidate


def review_citations(
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
    if judgment.label not in {AutoLabel.SUPPORTED, AutoLabel.CONTRADICTED}:
        return judgment, None, None
    review = None
    before_repair = None
    try:
        review = client.review_citation_coverage(claim, candidates, judgment)
    except Hy3ResponseError:
        pass
    final = apply_citation_review(judgment, candidates, review)
    # A suggestion gap (including missing verification) is semantic, even when
    # complete=True for the verdict or a quotation also has formatting errors.
    if (review is not None and review.complete and not review.missing_aspects
            and review.aspects and review.claim_id == claim.claim_id == judgment.claim_id
            and review.reviewed_label == judgment.label.value
            and (not judgment.suggestion or (
                review.suggestion_verified is True
                and not review.suggestion_missing_aspects
            ))
            and final.label == AutoLabel.ABSTAIN):
        before_repair, review = review, None
        try:
            review = client.repair_citation_coverage(
                claim, candidates, before_repair, judgment,
            )
        except Hy3ResponseError:
            pass
        final = apply_citation_review(judgment, candidates, review)
    return final, review, before_repair


def review_supported_citations(client, claim, candidates, judgment):
    """Keep historical support-only experiment entry points unchanged."""
    if judgment.label != AutoLabel.SUPPORTED:
        return judgment, None, None
    return review_citations(client, claim, candidates, judgment)
