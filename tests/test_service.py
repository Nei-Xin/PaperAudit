from paperaudit.config import Settings
from paperaudit.models import (
    AtomicClaim,
    AutoLabel,
    ClaimCategory,
    ClaimExtraction,
    ClaimJudgment,
    JudgmentBatch,
    PaperChunk,
    ParsedPaper,
    Severity,
)
from paperaudit.service import AuditService


class FakeHy3Client:
    def extract_claims(self, report_text: str, scope: list[str]) -> ClaimExtraction:
        return ClaimExtraction(
            claims=[
                AtomicClaim(
                    claim_id="model-id",
                    text="该方法在 Dataset A 上将 F1 提升了 3.2 个点。",
                    category=ClaimCategory.RESULTS,
                    key_claim=True,
                    query_en="Dataset A improves F1 3.2 points",
                    entities=["Dataset A"],
                    numbers=["3.2"],
                    metric="F1",
                    dataset="Dataset A",
                )
            ]
        )

    def judge_claims(self, claims: list[tuple], page_count: int) -> JudgmentBatch:
        claim, candidates = claims[0]
        return JudgmentBatch(
            judgments=[
                ClaimJudgment(
                    claim_id=claim.claim_id,
                    label=AutoLabel.SUPPORTED,
                    evidence_ids=[candidates[0].evidence_id],
                    explanation="原文数字与论断一致。",
                    severity=Severity.NONE,
                )
            ]
        )


def test_service_runs_claim_to_evidence_flow() -> None:
    settings = Settings(
        api_base="https://example.invalid/v1",
        api_key="test",
        model="hy3",
    )
    paper = ParsedPaper(
        title="Test Paper",
        page_count=2,
        chunks=[
            PaperChunk(
                chunk_id="p2_b1",
                page=2,
                content="On Dataset A, the method improves F1 by 3.2 points.",
            )
        ],
    )
    service = AuditService(settings, client=FakeHy3Client())  # type: ignore[arg-type]

    run = service.audit(
        paper,
        "该方法在 Dataset A 上将 F1 提升了 3.2 个点。",
        [ClaimCategory.RESULTS],
    )

    assert len(run.audits) == 1
    assert run.audits[0].judgment.label == AutoLabel.SUPPORTED
    assert run.audits[0].judgment.evidence_ids == ["C001_e1"]
    assert run.summary.audit_coverage == 100.0

