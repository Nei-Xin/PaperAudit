from __future__ import annotations

from paperaudit.config import Settings
from paperaudit.models import (
    AnswerConclusionDraft,
    AnswerDraft,
    AnswerEvidenceDraft,
    AnswerStatus,
    AnswerSupportType,
    PageRect,
    PaperAnswer,
    PaperChunk,
    ParsedPaper,
    QuestionQuery,
)
from paperaudit.service import AuditService, match_selected_chunks


class FakeQuestionClient:
    def __init__(self, citation_ids: list[str], query: str = "Dataset A F1 3.2"):
        self.citation_ids = citation_ids
        self.query = query
        self.answer_called = False
        self.plan_called = False
        self.candidate_chunk_ids: list[str] = []
        self.selected_text: str | None = None

    def plan_question(
        self,
        title: str,
        question: str,
        history: list[PaperAnswer],
    ) -> QuestionQuery:
        self.plan_called = True
        if self.query == "unfindabletoken":
            return QuestionQuery(query_en=self.query)
        return QuestionQuery(query_en=self.query, entities=["Dataset A"], numbers=["3.2"])

    def answer_question(
        self,
        question: str,
        candidates: list,
        history: list[PaperAnswer],
        selected_text: str | None = None,
    ) -> AnswerDraft:
        self.answer_called = True
        self.candidate_chunk_ids = [candidate.chunk_id for candidate in candidates]
        self.selected_text = selected_text
        return AnswerDraft(
            answer="论文报告该方法在 Dataset A 上将 F1 提升了 3.2 个点。",
            status=AnswerStatus.ANSWERED,
            citation_chunk_ids=self.citation_ids,
            conclusions=(
                [
                    AnswerConclusionDraft(
                        text="该方法在 Dataset A 上将 F1 提升了 3.2 个点。",
                        support_type=AnswerSupportType.DIRECT,
                        evidence=[
                            AnswerEvidenceDraft(
                                chunk_id=self.citation_ids[0],
                                quote="On Dataset A, the method improves F1 by 3.2 points.",
                            )
                        ],
                    )
                ]
                if self.citation_ids
                else []
            ),
        )


class StructuredQuestionClient(FakeQuestionClient):
    def __init__(self, quote: str) -> None:
        super().__init__(["p2_b1"])
        self.quote = quote

    def answer_question(
        self,
        question: str,
        candidates: list,
        history: list[PaperAnswer],
        selected_text: str | None = None,
    ) -> AnswerDraft:
        return AnswerDraft(
            answer="该方法报告了明确的 F1 提升。",
            status=AnswerStatus.ANSWERED,
            citation_chunk_ids=["p2_b1"],
            conclusions=[
                AnswerConclusionDraft(
                    text="该方法在 Dataset A 上将 F1 提升了 3.2 个点。",
                    support_type=AnswerSupportType.DIRECT,
                    evidence=[
                        AnswerEvidenceDraft(
                            chunk_id="p2_b1",
                            quote=self.quote,
                        )
                    ],
                )
            ],
        )


def make_settings() -> Settings:
    return Settings(api_base="https://example.invalid/v1", api_key="test", model="hy3")


def make_paper() -> ParsedPaper:
    return ParsedPaper(
        title="Test Paper",
        page_count=2,
        chunks=[
            PaperChunk(chunk_id="p2_b0", page=2, content="Results on Dataset A."),
            PaperChunk(
                chunk_id="p2_b1",
                page=2,
                content="On Dataset A, the method improves F1 by 3.2 points.",
                rects=[PageRect(x0=72.0, y0=110.0, x1=330.0, y1=132.0)],
            ),
            PaperChunk(chunk_id="p2_b2", page=2, content="The result is reported in Table 2."),
        ],
    )


def test_question_answer_uses_only_valid_local_citations() -> None:
    client = FakeQuestionClient(["p2_b1", "invented_chunk"])
    service = AuditService(make_settings(), client=client)  # type: ignore[arg-type]

    answer = service.answer_question(make_paper(), "F1 提升了多少？")

    assert answer.status == AnswerStatus.ANSWERED
    assert [citation.chunk_id for citation in answer.citations] == ["p2_b1"]
    assert answer.citations[0].page == 2
    assert answer.citations[0].rects == [
        PageRect(x0=72.0, y0=110.0, x1=330.0, y1=132.0)
    ]
    assert answer.citations[0].context_text is not None
    assert "p2_b0" in answer.citations[0].context_text
    assert "p2_b2" in answer.citations[0].context_text
    assert {"p2_b0", "p2_b1", "p2_b2"}.issubset(client.candidate_chunk_ids)


def test_structured_answer_keeps_verified_minimal_quote_and_locator() -> None:
    quote = "the method improves F1 by 3.2 points."
    service = AuditService(
        make_settings(), client=StructuredQuestionClient(quote)  # type: ignore[arg-type]
    )

    answer = service.answer_question(make_paper(), "F1 提升了多少？")

    assert answer.status == AnswerStatus.ANSWERED
    assert len(answer.conclusions) == 1
    conclusion = answer.conclusions[0]
    assert answer.answer == conclusion.text
    assert conclusion.support_type == AnswerSupportType.DIRECT
    assert conclusion.citations[0].quote == quote
    assert conclusion.citations[0].locator is None


def test_structured_answer_rejects_quote_not_present_in_local_pdf() -> None:
    service = AuditService(
        make_settings(),
        client=StructuredQuestionClient("This sentence was never in the paper."),  # type: ignore[arg-type]
    )

    answer = service.answer_question(make_paper(), "F1 提升了多少？")

    assert answer.status == AnswerStatus.INSUFFICIENT_EVIDENCE
    assert answer.conclusions == []
    assert "本地 PDF" in answer.answer


def test_structured_quote_highlights_only_matching_pdf_lines() -> None:
    paper = make_paper().model_copy(
        update={
            "chunks": [
                PaperChunk(
                    chunk_id="p2_b1",
                    page=2,
                    content=(
                        "The comparison uses Dataset A.\n"
                        "The method improves F1 by 3.2 points.\n"
                        "Additional settings follow."
                    ),
                    rects=[
                        PageRect(x0=72, y0=90, x1=300, y1=104),
                        PageRect(x0=72, y0=106, x1=330, y1=120),
                        PageRect(x0=72, y0=122, x1=280, y1=136),
                    ],
                )
            ]
        }
    )
    service = AuditService(
        make_settings(),
        client=StructuredQuestionClient("The method improves F1 by 3.2 points."),  # type: ignore[arg-type]
    )

    answer = service.answer_question(paper, "F1 提升了多少？")

    assert answer.conclusions[0].citations[0].rects == [
        PageRect(x0=72, y0=106, x1=330, y1=120)
    ]


def test_answer_without_valid_citation_becomes_insufficient() -> None:
    client = FakeQuestionClient(["invented_chunk"])
    service = AuditService(make_settings(), client=client)  # type: ignore[arg-type]

    answer = service.answer_question(make_paper(), "F1 提升了多少？")

    assert answer.status == AnswerStatus.INSUFFICIENT_EVIDENCE
    assert answer.citations == []
    assert "本地 PDF" in answer.answer


def test_question_without_retrieval_results_skips_answer_call() -> None:
    client = FakeQuestionClient([], query="unfindabletoken")
    service = AuditService(make_settings(), client=client)  # type: ignore[arg-type]

    answer = service.answer_question(make_paper(), "论文有没有讨论量子计算？")

    assert answer.status == AnswerStatus.INSUFFICIENT_EVIDENCE
    assert not client.answer_called


def test_selected_text_matches_same_page_chunk() -> None:
    matches = match_selected_chunks(
        make_paper(),
        2,
        "the method improves F1 by 3.2 points",
    )

    assert matches
    assert matches[0].chunk_id == "p2_b1"


def test_selected_rectangle_disambiguates_common_text() -> None:
    paper = ParsedPaper(
        title="Two Column Paper",
        page_count=1,
        chunks=[
            PaperChunk(
                chunk_id="p1_left",
                page=1,
                content="Education systems need more resources.",
                rects=[PageRect(x0=40, y0=100, x1=280, y1=130)],
            ),
            PaperChunk(
                chunk_id="p1_right",
                page=1,
                content="Education videos require instructional design.",
                rects=[PageRect(x0=330, y0=100, x1=570, y1=130)],
            ),
        ],
    )

    matches = match_selected_chunks(
        paper,
        1,
        "Education",
        [PageRect(x0=335, y0=104, x1=390, y1=126)],
    )

    assert matches[0].chunk_id == "p1_right"


def test_selected_chunk_is_used_when_keyword_retrieval_fails() -> None:
    client = FakeQuestionClient(["p2_b1"], query="unfindabletoken")
    service = AuditService(make_settings(), client=client)  # type: ignore[arg-type]

    answer = service.answer_question(
        make_paper(),
        "解释这段内容",
        selected_chunk_ids=["p2_b1"],
        selected_text="On Dataset A, the method improves F1 by 3.2 points.",
    )

    assert answer.status == AnswerStatus.ANSWERED
    assert "p2_b1" in client.candidate_chunk_ids
    assert client.selected_text == "On Dataset A, the method improves F1 by 3.2 points."
    assert [citation.chunk_id for citation in answer.citations] == ["p2_b1"]


def test_page_location_question_uses_pdf_section_heading() -> None:
    client = FakeQuestionClient([])
    service = AuditService(make_settings(), client=client)  # type: ignore[arg-type]
    heading_rects = [
        PageRect(x0=72, y0=90, x1=82, y1=104),
        PageRect(x0=92, y0=90, x1=180, y1=104),
        PageRect(x0=72, y0=112, x1=300, y1=126),
    ]
    paper = ParsedPaper(
        title="Test Paper",
        page_count=7,
        chunks=[
            PaperChunk(
                chunk_id="p3_b2",
                page=3,
                content="3\nMethodology\nMethod overview.",
                rects=heading_rects,
            ),
            PaperChunk(chunk_id="p4_b1", page=4, content="3.4\nModel Details"),
            PaperChunk(
                chunk_id="p5_b29",
                page=5,
                content="4\nExperiments\n4.1\nExperimental Setup",
                rects=heading_rects,
            ),
            PaperChunk(chunk_id="p6_b19", page=6, content="4.5\nAutomated Evaluation"),
            PaperChunk(chunk_id="p7_b53", page=7, content="5\nConclusion"),
        ],
    )

    first = service.answer_question(paper, "实验结果在第几页？")
    second = service.answer_question(paper, "实验结果在哪里？")
    method = service.answer_question(paper, "方法论在哪几页？")

    assert first.answer == second.answer
    assert "第 5—6 页" in first.answer
    assert first.citations[0].chunk_id == "p5_b29"
    assert first.citations[0].rects == heading_rects[:2]
    assert "第 3—4 页" in method.answer
    assert method.citations[0].chunk_id == "p3_b2"
    assert method.citations[0].text == "3 Methodology"
    assert not client.plan_called
    assert not client.answer_called


def test_document_structure_questions_scan_local_full_text() -> None:
    client = FakeQuestionClient([])
    service = AuditService(make_settings(), client=client)  # type: ignore[arg-type]
    paper = ParsedPaper(
        title="Paper with appendix",
        page_count=8,
        chunks=[
            PaperChunk(chunk_id="p1_b1", page=1, content="1\nIntroduction"),
            PaperChunk(
                chunk_id="p8_b1",
                page=8,
                content="Appendix A\nAdditional examples.",
                rects=[PageRect(x0=72, y0=90, x1=170, y1=104)],
            ),
        ],
    )

    existence = service.answer_question(paper, "有附录内容吗？")
    location = service.answer_question(paper, "附录在第几页？")
    missing = service.answer_question(make_paper(), "是否有附录？")

    assert "识别到附录" in existence.answer
    assert "第 8 页" in existence.answer
    assert location.citations[0].chunk_id == "p8_b1"
    assert "未检索到附录" in missing.answer
    assert not client.plan_called
    assert not client.answer_called


class RetryQuestionClient(FakeQuestionClient):
    def __init__(self) -> None:
        super().__init__([], query="target")
        self.answer_calls = 0

    def answer_question(
        self,
        question: str,
        candidates: list,
        history: list[PaperAnswer],
        selected_text: str | None = None,
    ) -> AnswerDraft:
        self.answer_calls += 1
        if self.answer_calls == 1:
            return AnswerDraft(
                answer="当前候选证据不足。",
                status=AnswerStatus.INSUFFICIENT_EVIDENCE,
                conclusions=[],
            )
        return AnswerDraft(
            answer="扩展检索后找到证据。",
            status=AnswerStatus.ANSWERED,
            citation_chunk_ids=[candidates[-1].chunk_id],
            conclusions=[
                AnswerConclusionDraft(
                    text="扩展检索后找到目标证据。",
                    support_type=AnswerSupportType.DIRECT,
                    evidence=[
                        AnswerEvidenceDraft(
                            chunk_id=candidates[-1].chunk_id,
                            quote=candidates[-1].text,
                        )
                    ],
                )
            ],
        )


def test_insufficient_answer_retries_with_expanded_local_candidates() -> None:
    client = RetryQuestionClient()
    service = AuditService(make_settings(), client=client)  # type: ignore[arg-type]
    paper = ParsedPaper(
        title="Retrieval expansion",
        page_count=4,
        chunks=[
            PaperChunk(
                chunk_id=f"p{index // 5 + 1}_b{index}",
                page=index // 5 + 1,
                content=f"Target evidence passage number {index}.",
            )
            for index in range(20)
        ],
    )

    answer = service.answer_question(paper, "目标证据是什么？")

    assert client.answer_calls == 2
    assert answer.status == AnswerStatus.ANSWERED
    assert answer.citations
