from paperaudit.models import (
    AtomicClaim,
    AutoLabel,
    ClaimAudit,
    ClaimCategory,
    ClaimErrorType,
    ClaimJudgment,
    Severity,
    TrustGrade,
)
from paperaudit.scoring import build_summary


def make_audit(
    claim_id: str,
    category: ClaimCategory,
    label: AutoLabel,
    severity: Severity = Severity.NONE,
    error: ClaimErrorType | None = None,
    provided_evidence: str | None = "P1",
) -> ClaimAudit:
    return ClaimAudit(
        claim=AtomicClaim(
            claim_id=claim_id,
            text=f"Claim {claim_id}",
            category=category,
            key_claim=True,
            query_en="test claim",
            provided_evidence=provided_evidence,
        ),
        candidates=[],
        judgment=ClaimJudgment(
            claim_id=claim_id,
            label=label,
            explanation="test",
            severity=severity,
            claim_error_type=error,
        ),
    )


def test_summary_requires_review_for_medium_risk() -> None:
    audits = [
        make_audit("C001", ClaimCategory.CONTRIBUTION, AutoLabel.SUPPORTED),
        make_audit(
            "C002",
            ClaimCategory.RESULTS,
            AutoLabel.PARTIALLY_SUPPORTED,
            Severity.MEDIUM,
            ClaimErrorType.OVERGENERALIZATION,
        ),
    ]

    summary = build_summary(audits, [ClaimCategory.CONTRIBUTION, ClaimCategory.RESULTS])

    assert summary.audit_coverage == 100.0
    assert summary.medium_count == 1
    assert summary.grade == TrustGrade.REVIEW


def test_summary_is_unrated_when_most_claims_abstain() -> None:
    audits = [
        make_audit("C001", ClaimCategory.METHOD, AutoLabel.SUPPORTED),
        make_audit("C002", ClaimCategory.RESULTS, AutoLabel.ABSTAIN),
        make_audit("C003", ClaimCategory.LIMITATIONS, AutoLabel.ABSTAIN),
    ]

    summary = build_summary(audits, [ClaimCategory.METHOD, ClaimCategory.RESULTS])

    assert summary.audit_coverage == 33.3
    assert summary.grade == TrustGrade.UNRATED


def test_summary_scores_missing_key_claim_evidence_as_zero() -> None:
    audit = make_audit(
        "C001",
        ClaimCategory.CONTRIBUTION,
        AutoLabel.SUPPORTED,
        provided_evidence=None,
    )

    summary = build_summary([audit], [ClaimCategory.CONTRIBUTION])

    assert summary.dimensions.evidence_completeness == 0.0
    assert summary.total_score == 75.0
    assert summary.grade == TrustGrade.REVIEW
