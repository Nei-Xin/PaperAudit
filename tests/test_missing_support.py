import pytest

from paperaudit.config import Settings
from paperaudit.hy3_client import Hy3ResponseError
from paperaudit.models import (
    AtomicClaim, AutoLabel, ClaimCategory, ClaimErrorType, ClaimExtraction,
    ClaimJudgment, EvidenceCandidate, EvidenceErrorType, EvidenceReview,
    JudgmentBatch, PaperChunk, ParsedPaper, Severity,
)
from paperaudit.retrieval import report_evidence_pages, supplement_claim_evidence
from paperaudit.service import AuditService


def _claim(anchor="（证据：论文第2页）"):
    return AtomicClaim(claim_id="C001", text="在单个退化图像上拟合生成器。", category=ClaimCategory.METHOD,
                       query_en="fit generator single degraded image", provided_evidence=anchor)


def _paper():
    return ParsedPaper(title="Paper", page_count=2, chunks=[
        PaperChunk(chunk_id="p1_b1", page=1, content="Abstract: Image restoration uses a generator network."),
        PaperChunk(chunk_id="p2_b3", page=2, content="We fit a generator network to a single degraded image."),
    ])


def test_supplement_prefers_cited_page_and_preserves_evidence_ids():
    original = [EvidenceCandidate(evidence_id="C001_e1", chunk_id="p1_b1", page=1, text=_paper().chunks[0].content, score=1)]
    result = supplement_claim_evidence(_claim(), _paper().chunks, original)
    assert result[0] == original[0]
    assert result[1].chunk_id == "p2_b3"
    assert result[1].evidence_id == "C001_e2"
    assert len({c.evidence_id for c in result}) == len(result)
    assert report_evidence_pages("第2页；page 999；p. 3；表99") == {2, 3, 999}


class MissingClient:
    def __init__(self, *, outcome="supported", anchor="（证据：论文第2页）"):
        self.outcome, self.anchor, self.reviews = outcome, anchor, 0

    def extract_claims(self, *args):
        return ClaimExtraction(claims=[_claim(self.anchor)])

    def judge_claims(self, batch, page_count):
        claim, candidates = batch[0]
        return JudgmentBatch(judgments=[ClaimJudgment(
            claim_id=claim.claim_id, label=AutoLabel.NO_SUPPORT_FOUND,
            explanation="Initial candidates do not establish the assertion.",
            claim_error_type=ClaimErrorType.EXTERNAL_HALLUCINATION, severity=Severity.HIGH,
        )])

    def adjudicate_claim(self, claim, candidates, page_count):
        return self.judge_claims([(claim, candidates)], page_count)

    def review_missing_support(self, claim, candidates, page_count):
        self.reviews += 1
        assert any(c.chunk_id == "p2_b3" for c in candidates)
        if self.outcome == "failure":
            raise Hy3ResponseError("invalid response")
        evidence_id = next(c.evidence_id for c in candidates if c.chunk_id == "p2_b3")
        return EvidenceReview(
            evidence_sufficient=self.outcome != "uncertain",
            judgment=ClaimJudgment(
                claim_id="wrong-id" if self.outcome == "wrong_id" else claim.claim_id,
                label=AutoLabel.SUPPORTED if self.outcome != "invented" else AutoLabel.NO_SUPPORT_FOUND,
                evidence_ids=["unknown"] if self.outcome == "invalid_evidence" else [evidence_id],
                explanation="Supplementary review.",
                claim_error_type=ClaimErrorType.EXTERNAL_HALLUCINATION if self.outcome == "invented" else None,
            ),
        )


@pytest.mark.parametrize("outcome, label, severity", [
    ("supported", AutoLabel.SUPPORTED, Severity.NONE),
    ("invented", AutoLabel.NO_SUPPORT_FOUND, Severity.HIGH),
    ("uncertain", AutoLabel.ABSTAIN, Severity.NONE),
    ("failure", AutoLabel.ABSTAIN, Severity.NONE),
    ("wrong_id", AutoLabel.ABSTAIN, Severity.NONE),
    ("invalid_evidence", AutoLabel.ABSTAIN, Severity.NONE),
])
def test_one_supplementary_review_recovers_support_or_abstains_without_blindly_clearing_errors(outcome, label, severity):
    client = MissingClient(outcome=outcome)
    run = AuditService(Settings(api_base="https://example.invalid", api_key="test", model="fake"), client).audit(
        _paper(), "报告", [ClaimCategory.METHOD],
    )
    assert client.reviews == 1
    assert run.audits[0].judgment.label == label
    assert run.audits[0].judgment.severity == severity


def test_fabricated_page_is_flagged_locally_even_when_fact_needs_review():
    client = MissingClient(outcome="uncertain", anchor="（证据：论文第999页，表99）")
    run = AuditService(Settings(api_base="https://example.invalid", api_key="test", model="fake"), client).audit(
        _paper(), "报告", [ClaimCategory.METHOD],
    )
    judgment = run.audits[0].judgment
    assert judgment.label == AutoLabel.ABSTAIN
    assert judgment.evidence_error_type == EvidenceErrorType.FABRICATED_EVIDENCE
    assert judgment.severity == Severity.HIGH
    assert "999" in judgment.explanation
