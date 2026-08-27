from __future__ import annotations

from paperaudit.models import (
    AtomicClaim,
    AuditRun,
    AuditSummary,
    AutoLabel,
    ClaimAudit,
    ClaimCategory,
    ClaimJudgment,
    DimensionScores,
    EvidenceCandidate,
    Severity,
    TrustGrade,
)


def get_demo_audit_run() -> AuditRun:
    labels = [
        AutoLabel.SUPPORTED,
        AutoLabel.PARTIALLY_SUPPORTED,
        AutoLabel.CONTRADICTED,
        AutoLabel.NO_SUPPORT_FOUND,
        AutoLabel.ABSTAIN,
        AutoLabel.SUPPORTED,
    ]
    severities = [
        Severity.NONE,
        Severity.MEDIUM,
        Severity.CRITICAL,
        Severity.HIGH,
        Severity.NONE,
        Severity.LOW,
    ]
    audits: list[ClaimAudit] = []
    for index, (label, severity) in enumerate(zip(labels, severities, strict=True), start=1):
        claim_id = f"C{index:03d}"
        candidate = EvidenceCandidate(
            evidence_id=f"{claim_id}-E1",
            chunk_id=f"p{index}_b1",
            page=index,
            text=f"Demo source evidence for claim {index}.",
            score=1.0,
        )
        evidence_ids = [candidate.evidence_id] if label in {
            AutoLabel.SUPPORTED,
            AutoLabel.PARTIALLY_SUPPORTED,
            AutoLabel.CONTRADICTED,
        } else []
        audits.append(
            ClaimAudit(
                claim=AtomicClaim(
                    claim_id=claim_id,
                    text=f"示例论断 {index}",
                    category=ClaimCategory.CONTRIBUTION,
                    key_claim=index <= 3,
                    query_en=f"demo claim {index}",
                ),
                candidates=[candidate],
                judgment=ClaimJudgment(
                    claim_id=claim_id,
                    label=label,
                    evidence_ids=evidence_ids,
                    explanation="示例判断说明。",
                    severity=severity,
                ),
            )
        )
    return AuditRun(
        paper_title="Demo Paper",
        page_count=6,
        mode="audit_existing",
        scope=[ClaimCategory.CONTRIBUTION],
        report_text="示例报告。",
        audits=audits,
        summary=AuditSummary(
            grade=TrustGrade.UNTRUSTED,
            total_score=58.0,
            audit_coverage=83.3,
            evidence_discovery_rate=66.7,
            dimensions=DimensionScores(
                factual_support=58.0,
                evidence_correctness=60.0,
                evidence_completeness=70.0,
                numeric_consistency=55.0,
                content_coverage=80.0,
                conclusion_boundary=62.0,
            ),
            critical_count=1,
            high_count=1,
            medium_count=1,
            review_count=2,
        ),
    )
