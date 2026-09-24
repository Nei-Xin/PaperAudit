from paperaudit.config import Settings
from paperaudit.hy3_client import Hy3ResponseError
from paperaudit.models import (
    AtomicClaim,
    AutoLabel,
    ClaimCategory,
    ClaimErrorType,
    ClaimExtraction,
    ClaimJudgment,
    CitationReview,
    EvidenceCandidate,
    JudgmentBatch,
    PaperChunk,
    ParsedPaper,
    Severity,
)
from paperaudit.service import AuditService, MAX_AUDIT_REPORT_CHARS
from eval.run_eval import _validated_judgment


class FakeHy3Client:
    def review_citation_coverage(self, claim, candidates, judgment):
        return CitationReview(
            claim_id=claim.claim_id, complete=True, evidence_ids=judgment.evidence_ids,
            aspects=[{"aspect": "测试论断", "reasoning": "测试客户端返回完整原文。",
                      "citations": [{"evidence_id": c.evidence_id, "quote": c.text}
                                    for c in candidates if c.evidence_id in judgment.evidence_ids]}],
            missing_aspects=[], explanation="测试引用复核。",
        )

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


class InvalidEvidenceThenValidClient(FakeHy3Client):
    def judge_claims(self, claims: list[tuple], page_count: int) -> JudgmentBatch:
        claim, _ = claims[0]
        return JudgmentBatch(
            judgments=[
                ClaimJudgment(
                    claim_id=claim.claim_id,
                    label=AutoLabel.SUPPORTED,
                    evidence_ids=["not-a-candidate"],
                    explanation="证据编号错误。",
                    severity=Severity.NONE,
                )
            ]
        )

    def adjudicate_claim(self, claim, candidates, page_count: int) -> JudgmentBatch:
        return JudgmentBatch(
            judgments=[
                ClaimJudgment(
                    claim_id=claim.claim_id,
                    label=AutoLabel.SUPPORTED,
                    evidence_ids=[candidates[0].evidence_id],
                    explanation="自动重试后证据编号有效。",
                    severity=Severity.NONE,
                )
            ]
        )


class LabelCalibrationRequiresEvidenceClient(FakeHy3Client):
    def judge_claims(self, claims: list[tuple], page_count: int) -> JudgmentBatch:
        claim, _ = claims[0]
        return JudgmentBatch(
            judgments=[
                ClaimJudgment(
                    claim_id=claim.claim_id,
                    label=AutoLabel.NO_SUPPORT_FOUND,
                    evidence_ids=[],
                    explanation="错误归属。",
                    claim_error_type="wrong_attribution",
                    severity=Severity.HIGH,
                )
            ]
        )

    def adjudicate_claim(self, claim, candidates, page_count: int) -> JudgmentBatch:
        return self.judge_claims([(claim, candidates)], page_count)


class BatchFailureFallbackClient(FakeHy3Client):
    def judge_claims(self, claims: list[tuple], page_count: int) -> JudgmentBatch:
        raise Hy3ResponseError("invalid batch JSON")

    def adjudicate_claim(self, claim, candidates, page_count: int) -> JudgmentBatch:
        return JudgmentBatch(
            judgments=[
                ClaimJudgment(
                    claim_id=claim.claim_id,
                    label=AutoLabel.SUPPORTED,
                    evidence_ids=[candidates[0].evidence_id],
                    explanation="单条回退成功。",
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


def test_service_retries_invalid_evidence_ids_automatically() -> None:
    settings = Settings(api_base="https://example.invalid/v1", api_key="test", model="hy3")
    paper = ParsedPaper(
        title="Test Paper",
        page_count=1,
        chunks=[
            PaperChunk(
                chunk_id="p1_b1",
                page=1,
                content="On Dataset A, the method improves F1 by 3.2 points.",
            )
        ],
    )
    service = AuditService(settings, client=InvalidEvidenceThenValidClient())  # type: ignore[arg-type]

    run = service.audit(paper, "该方法在 Dataset A 上将 F1 提升了 3.2 个点。", [ClaimCategory.RESULTS])

    assert run.audits[0].judgment.label == AutoLabel.SUPPORTED
    assert run.audits[0].judgment.evidence_ids == ["C001_e1"]


def test_service_validates_evidence_after_label_calibration() -> None:
    settings = Settings(api_base="https://example.invalid/v1", api_key="test", model="hy3")
    paper = ParsedPaper(
        title="Test Paper",
        page_count=1,
        chunks=[
            PaperChunk(
                chunk_id="p1_b1",
                page=1,
                content="On Dataset A, the method improves F1 by 3.2 points.",
            )
        ],
    )
    service = AuditService(  # type: ignore[arg-type]
        settings,
        client=LabelCalibrationRequiresEvidenceClient(),
    )

    run = service.audit(
        paper,
        "该结果被归属于另一团队。",
        [ClaimCategory.RESULTS],
    )

    assert run.audits[0].judgment.label == AutoLabel.ABSTAIN
    assert run.audits[0].judgment.evidence_ids == []


def test_service_falls_back_to_single_claim_when_batch_response_is_invalid() -> None:
    settings = Settings(api_base="https://example.invalid/v1", api_key="test", model="hy3")
    paper = ParsedPaper(
        title="Test Paper",
        page_count=1,
        chunks=[
            PaperChunk(
                chunk_id="p1_b1",
                page=1,
                content="On Dataset A, the method improves F1 by 3.2 points.",
            )
        ],
    )
    service = AuditService(settings, client=BatchFailureFallbackClient())  # type: ignore[arg-type]

    run = service.audit(paper, "测试论断。", [ClaimCategory.RESULTS])

    assert run.audits[0].judgment.label == AutoLabel.SUPPORTED
    assert run.audits[0].judgment.evidence_ids == ["C001_e1"]


def test_service_rejects_oversized_report_before_model_call() -> None:
    settings = Settings(api_base="https://example.invalid/v1", api_key="test", model="hy3")
    paper = ParsedPaper(
        title="Test Paper",
        page_count=1,
        chunks=[PaperChunk(chunk_id="p1_b1", page=1, content="Evidence")],
    )
    service = AuditService(settings, client=FakeHy3Client())  # type: ignore[arg-type]

    try:
        service.audit(
            paper,
            "x" * (MAX_AUDIT_REPORT_CHARS + 1),
            [ClaimCategory.RESULTS],
        )
    except ValueError as exc:
        assert "100,000" in str(exc)
    else:
        raise AssertionError("oversized report was accepted")


def test_evaluation_validates_evidence_after_label_calibration() -> None:
    judgment = ClaimJudgment(
        claim_id="C001",
        label=AutoLabel.NO_SUPPORT_FOUND,
        evidence_ids=[],
        explanation="错误归属。",
        claim_error_type=ClaimErrorType.WRONG_ATTRIBUTION,
        severity=Severity.HIGH,
    )
    candidates = [
        EvidenceCandidate(
            evidence_id="C001_e1",
            chunk_id="p1_b1",
            page=1,
            text="Evidence",
            score=1.0,
        )
    ]

    validated = _validated_judgment(judgment, candidates)

    assert validated.label == AutoLabel.ABSTAIN
    assert validated.evidence_ids == []


def test_audit_sends_ranked_extension_with_verified_ids_and_original_text():
    class ContextClient(FakeHy3Client):
        def judge_claims(self, batch, page_count):
            claim, candidates = batch[0]
            assert len(candidates) == 6
            assert {c.chunk_id for c in candidates} == {f'result{i}' for i in range(6)}
            assert [c.evidence_id for c in candidates] == [f'C001_e{i}' for i in range(1, 7)]
            return super().judge_claims(batch, page_count)

    paper = ParsedPaper(title='Context', page_count=2, chunks=[
        *[PaperChunk(chunk_id=f'result{i}', page=2, content=f'Dataset A improves F1 by 3.2 points. Study {i}.')
          for i in range(6)],
        PaperChunk(chunk_id='formula', page=2, content='L = ∑ (y - x)²'),
    ])
    service = AuditService(Settings(api_base='https://example.invalid', api_key='test',
                                    model='fake', retrieval_top_k=1), ContextClient())
    run = service.audit(paper, '结果提升3.2。', [ClaimCategory.RESULTS])
    source = {c.chunk_id: c for c in paper.chunks}
    assert all(c.text == source[c.chunk_id].content for c in run.audits[0].candidates)


def test_first_judgment_receives_cited_page_evidence_as_a_search_hint():
    class CitedClient(FakeHy3Client):
        def extract_claims(self, *args):
            extraction = super().extract_claims(*args)
            extraction.claims[0] = extraction.claims[0].model_copy(update={'provided_evidence': '第3页'})
            return extraction

        def judge_claims(self, batch, page_count):
            claim, candidates = batch[0]
            assert len(candidates) == 10
            assert all(c.page == 2 for c in candidates[:5])
            assert any(c.chunk_id == 'cited_result' and c.page == 3 for c in candidates)
            return super().judge_claims(batch, page_count)

    paper = ParsedPaper(title='Cited paper', page_count=3, chunks=[
        *[PaperChunk(chunk_id=f'global{i}', page=2, content=f'Dataset A improves F1 by 3.2 points. Result {i}.')
          for i in range(11)],
        PaperChunk(chunk_id='cited_result', page=3, content='Dataset A\nF1\n3.2'),
    ])
    service = AuditService(Settings(api_base='https://example.invalid', api_key='test', model='fake'), CitedClient())
    run = service.audit(paper, '结果提升3.2。', [ClaimCategory.RESULTS])
    assert run.audits[0].claim.provided_evidence == '第3页'
