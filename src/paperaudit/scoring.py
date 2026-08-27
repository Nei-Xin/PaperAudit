from __future__ import annotations

from statistics import fmean

from .models import (
    AuditSummary,
    AutoLabel,
    ClaimAudit,
    ClaimCategory,
    ClaimErrorType,
    DimensionScores,
    Severity,
    TrustGrade,
)


_LABEL_SCORE = {
    AutoLabel.SUPPORTED: 1.0,
    AutoLabel.PARTIALLY_SUPPORTED: 0.5,
    AutoLabel.CONTRADICTED: 0.0,
    AutoLabel.NO_SUPPORT_FOUND: 0.0,
}


def _percentage(values: list[float]) -> float | None:
    return round(fmean(values) * 100, 1) if values else None


def _label_scores(audits: list[ClaimAudit]) -> list[float]:
    return [
        _LABEL_SCORE[audit.judgment.label]
        for audit in audits
        if audit.judgment.label in _LABEL_SCORE
    ]


def build_summary(audits: list[ClaimAudit], scope: list[ClaimCategory]) -> AuditSummary:
    total_claims = len(audits)
    decided = [audit for audit in audits if audit.judgment.label != AutoLabel.ABSTAIN]
    coverage = len(decided) / total_claims if total_claims else 0.0

    evidence_found = [audit for audit in audits if audit.judgment.evidence_ids]
    evidence_discovery_rate = len(evidence_found) / total_claims if total_claims else 0.0

    non_numeric = [
        audit
        for audit in audits
        if not audit.claim.numbers and not audit.claim.metric
    ]
    numeric = [audit for audit in audits if audit.claim.numbers or audit.claim.metric]

    claims_with_anchor = [audit for audit in audits if audit.claim.provided_evidence]
    evidence_correctness = None
    if claims_with_anchor:
        evidence_correctness = _percentage(
            [
                1.0
                if audit.judgment.evidence_error_type is None
                and audit.judgment.label in {AutoLabel.SUPPORTED, AutoLabel.PARTIALLY_SUPPORTED}
                else 0.0
                for audit in claims_with_anchor
            ]
        )

    key_claims = [audit for audit in audits if audit.claim.key_claim]
    evidence_completeness = None
    if key_claims and claims_with_anchor:
        evidence_completeness = _percentage(
            [1.0 if audit.claim.provided_evidence else 0.0 for audit in key_claims]
        )

    effective_scope = [category for category in scope if category != ClaimCategory.OTHER]
    present_categories = {audit.claim.category for audit in audits}
    content_coverage = _percentage(
        [1.0 if category in present_categories else 0.0 for category in effective_scope]
    )

    boundary_audits = [
        audit
        for audit in decided
        if audit.claim.category
        in {
            ClaimCategory.CONTRIBUTION,
            ClaimCategory.METHOD,
            ClaimCategory.RESULTS,
            ClaimCategory.LIMITATIONS,
        }
    ]
    conclusion_boundary = _percentage(
        [
            0.0
            if audit.judgment.claim_error_type
            in {ClaimErrorType.MISSING_CONDITION, ClaimErrorType.OVERGENERALIZATION}
            else 1.0
            for audit in boundary_audits
        ]
    )

    dimensions = DimensionScores(
        factual_support=_percentage(_label_scores(non_numeric)),
        evidence_correctness=evidence_correctness,
        evidence_completeness=evidence_completeness,
        numeric_consistency=_percentage(_label_scores(numeric)),
        content_coverage=content_coverage,
        conclusion_boundary=conclusion_boundary,
    )
    dimension_values = [value for value in dimensions.model_dump().values() if value is not None]
    total_score = round(fmean(dimension_values), 1) if dimension_values else None

    critical_count = sum(audit.judgment.severity == Severity.CRITICAL for audit in audits)
    high_count = sum(audit.judgment.severity == Severity.HIGH for audit in audits)
    medium_count = sum(audit.judgment.severity == Severity.MEDIUM for audit in audits)
    review_count = sum(audit.judgment.label == AutoLabel.ABSTAIN for audit in audits)

    if critical_count:
        grade = TrustGrade.UNTRUSTED
    elif coverage < 0.6:
        grade = TrustGrade.UNRATED
    elif total_score is None or total_score < 60:
        grade = TrustGrade.UNTRUSTED
    elif coverage < 0.8 or total_score < 80 or high_count or medium_count:
        grade = TrustGrade.REVIEW
    else:
        grade = TrustGrade.TRUSTED

    return AuditSummary(
        grade=grade,
        total_score=total_score,
        audit_coverage=round(coverage * 100, 1),
        evidence_discovery_rate=round(evidence_discovery_rate * 100, 1),
        dimensions=dimensions,
        critical_count=critical_count,
        high_count=high_count,
        medium_count=medium_count,
        review_count=review_count,
    )

