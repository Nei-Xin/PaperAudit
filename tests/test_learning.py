from __future__ import annotations

import pytest

from paperaudit.config import Settings
from paperaudit.hy3_client import Hy3ResponseError
from paperaudit.models import (
    EvidenceAnchor,
    ExplanationPoint,
    LearningReport,
    LearningSectionType,
    PageRect,
    PaperChunk,
    ParsedPaper,
    ReportSection,
)
from paperaudit.reporting import render_learning_markdown
from paperaudit.service import (
    AuditService,
    build_learning_logic_chain,
    build_learning_page_context,
    refresh_learning_report_evidence,
)


def make_report(
    anchor_id: str = "p2_b1",
    quote: str | None = None,
) -> LearningReport:
    sections = []
    for section_type in LearningSectionType:
        sections.append(
            ReportSection(
                section_type=section_type,
                title=section_type.value,
                overview=f"{section_type.value} overview",
                points=[
                    ExplanationPoint(
                        title=f"{section_type.value} point",
                        explanation="结构化中文讲解。",
                        key_point=section_type == LearningSectionType.CONTRIBUTIONS,
                        evidence=[EvidenceAnchor(chunk_id=anchor_id, quote=quote)],
                    )
                ],
            )
        )
    return LearningReport(
        paper_title="model title",
        one_sentence_summary="一句话理解。",
        sections=sections,
        suggested_pages=[2, 99, 2],
    )


class FakeLearningClient:
    def __init__(self, report: LearningReport):
        self.report = report

    def generate_learning_report(self, title: str, chunks: list[PaperChunk]) -> LearningReport:
        return self.report


def make_paper() -> ParsedPaper:
    return ParsedPaper(
        title="Test Paper",
        page_count=3,
        chunks=[
            PaperChunk(
                chunk_id="p2_b1",
                page=2,
                content="The cited paper evidence.",
                rects=[PageRect(x0=72.0, y0=90.0, x1=240.0, y1=112.0)],
            )
        ],
    )


def test_learning_report_enriches_and_validates_evidence() -> None:
    settings = Settings(api_base="https://example.invalid/v1", api_key="test", model="hy3")
    service = AuditService(settings, client=FakeLearningClient(make_report()))  # type: ignore[arg-type]

    report = service.generate_learning_report(make_paper())

    contribution = next(
        section for section in report.sections
        if section.section_type == LearningSectionType.CONTRIBUTIONS
    )
    anchor = contribution.points[0].evidence[0]
    assert report.paper_title == "Test Paper"
    assert anchor.page == 2
    assert anchor.text == "The cited paper evidence."
    assert anchor.rects == [PageRect(x0=72.0, y0=90.0, x1=240.0, y1=112.0)]
    assert report.suggested_pages == [2]


def test_learning_report_adds_same_page_neighbor_context() -> None:
    settings = Settings(api_base="https://example.invalid/v1", api_key="test", model="hy3")
    service = AuditService(settings, client=FakeLearningClient(make_report()))  # type: ignore[arg-type]
    paper = ParsedPaper(
        title="Test Paper",
        page_count=3,
        chunks=[
            PaperChunk(chunk_id="p1_b9", page=1, content="Previous page."),
            PaperChunk(chunk_id="p2_b0", page=2, content="Table header."),
            PaperChunk(chunk_id="p2_b1", page=2, content="The cited paper evidence."),
            PaperChunk(chunk_id="p2_b2", page=2, content="Table caption."),
            PaperChunk(chunk_id="p3_b1", page=3, content="Next page."),
        ],
    )

    report = service.generate_learning_report(paper)
    contribution = next(
        section for section in report.sections
        if section.section_type == LearningSectionType.CONTRIBUTIONS
    )
    anchor = contribution.points[0].evidence[0]

    assert anchor.text == "The cited paper evidence."
    assert anchor.context_text is not None
    assert "p2_b0\nTable header." in anchor.context_text
    assert "p2_b2\nTable caption." in anchor.context_text
    assert "Previous page." not in anchor.context_text
    assert "Next page." not in anchor.context_text


def test_learning_report_validates_quote_and_uses_matching_line_rects() -> None:
    report = make_report(quote="The cited paper evidence.")
    settings = Settings(api_base="https://example.invalid/v1", api_key="test", model="hy3")
    service = AuditService(settings, client=FakeLearningClient(report))  # type: ignore[arg-type]
    paper = ParsedPaper(
        title="Test Paper",
        page_count=2,
        chunks=[
            PaperChunk(
                chunk_id="p2_h1",
                page=2,
                content="2\nMethodology",
                rects=[
                    PageRect(x0=72, y0=60, x1=82, y1=74),
                    PageRect(x0=90, y0=60, x1=180, y1=74),
                ],
            ),
            PaperChunk(
                chunk_id="p2_b1",
                page=2,
                content="Context line.\nThe cited paper evidence.\nFollowing line.",
                rects=[
                    PageRect(x0=72, y0=90, x1=180, y1=104),
                    PageRect(x0=72, y0=106, x1=240, y1=120),
                    PageRect(x0=72, y0=122, x1=180, y1=136),
                ],
            ),
        ],
    )

    enriched = service.generate_learning_report(paper)
    anchor = enriched.sections[1].points[0].evidence[0]

    assert anchor.quote == "The cited paper evidence."
    assert anchor.locator == "§2 Methodology · 第 1 段"
    assert anchor.rects == [PageRect(x0=72, y0=106, x1=240, y1=120)]


def test_learning_locator_uses_caption_but_ignores_body_mention() -> None:
    settings = Settings(api_base="https://example.invalid/v1", api_key="test", model="hy3")
    service = AuditService(
        settings,
        client=FakeLearningClient(make_report(quote="The cited paper evidence.")),  # type: ignore[arg-type]
    )
    paper = ParsedPaper(
        title="Test Paper",
        page_count=2,
        chunks=[
            PaperChunk(chunk_id="p2_h", page=2, content="2. Methodology"),
            PaperChunk(
                chunk_id="p2_b1",
                page=2,
                content="The cited paper evidence. It is reported in Table 8.",
            ),
            PaperChunk(chunk_id="p2_cap", page=2, content="Figure 3: System overview."),
        ],
    )

    anchor = service.generate_learning_report(paper).sections[1].points[0].evidence[0]

    assert anchor.locator == "§2 Methodology · 第 1 段 · Figure 3"
    assert "Table 8" not in anchor.locator


def test_learning_report_invalid_quote_falls_back_to_verified_chunk() -> None:
    report = make_report(quote="Fabricated sentence that is absent from the PDF.")
    settings = Settings(api_base="https://example.invalid/v1", api_key="test", model="hy3")
    service = AuditService(settings, client=FakeLearningClient(report))  # type: ignore[arg-type]

    enriched = service.generate_learning_report(make_paper())
    anchor = enriched.sections[1].points[0].evidence[0]

    assert anchor.quote is None
    assert anchor.text == "The cited paper evidence."
    assert anchor.rects == [PageRect(x0=72.0, y0=90.0, x1=240.0, y1=112.0)]


def test_old_learning_report_without_precise_evidence_fields_still_loads() -> None:
    report = LearningReport.model_validate(
        {
            "paper_title": "Old project",
            "one_sentence_summary": "summary",
            "sections": [
                {
                    "section_type": section_type.value,
                    "title": section_type.value,
                    "overview": "overview",
                    "points": [
                        {
                            "title": "point",
                            "explanation": "explanation",
                            "evidence": [{"chunk_id": "p2_b1", "page": 2, "text": "Evidence"}],
                        }
                    ],
                }
                for section_type in LearningSectionType
            ],
        }
    )

    anchor = report.sections[0].points[0].evidence[0]
    assert anchor.quote is None
    assert anchor.locator is None
    assert anchor.rects == []

    refreshed = refresh_learning_report_evidence(report, make_paper())
    refreshed_anchor = refreshed.sections[0].points[0].evidence[0]
    assert refreshed_anchor.page == 2
    assert refreshed_anchor.text == "The cited paper evidence."


def test_learning_report_limits_key_points_and_suggested_pages() -> None:
    sections = []
    for section_type in LearningSectionType:
        sections.append(
            ReportSection(
                section_type=section_type,
                title=section_type.value,
                overview="overview",
                points=[
                    ExplanationPoint(
                        title=f"point {index}",
                        explanation="explanation",
                        key_point=True,
                        evidence=[EvidenceAnchor(chunk_id="p2_b1")],
                    )
                    for index in range(3)
                ],
            )
        )
    generated = LearningReport(
        paper_title="model title",
        one_sentence_summary="summary",
        sections=sections,
        suggested_pages=[1, 2, 3, 4, 5, 6, 7],
    )
    settings = Settings(api_base="https://example.invalid/v1", api_key="test", model="hy3")
    service = AuditService(settings, client=FakeLearningClient(generated))  # type: ignore[arg-type]
    paper = ParsedPaper(
        title="Test Paper",
        page_count=7,
        chunks=[PaperChunk(chunk_id="p2_b1", page=2, content="Evidence.")],
    )

    report = service.generate_learning_report(paper)

    assert sum(point.key_point for section in report.sections for point in section.points) == 14
    assert all(sum(point.key_point for point in section.points) <= 2 for section in report.sections)
    assert len(report.suggested_pages) == 5
    assert 2 in report.suggested_pages


def test_page_context_and_questions_change_with_pdf_page() -> None:
    sections = []
    for section_type in LearningSectionType:
        evidence_page = 2 if section_type == LearningSectionType.METHOD else 4
        sections.append(
            ReportSection(
                section_type=section_type,
                title=f"{section_type.value} title",
                overview=f"{section_type.value} overview",
                points=[
                    ExplanationPoint(
                        title=f"{section_type.value} point",
                        explanation=f"{section_type.value} explanation",
                        evidence=[
                            EvidenceAnchor(
                                chunk_id=f"p{evidence_page}_{section_type.value}",
                                page=evidence_page,
                                text="evidence",
                            )
                        ],
                    )
                ],
            )
        )
    report = LearningReport(
        paper_title="Test Paper",
        one_sentence_summary="summary",
        sections=sections,
    )
    paper = ParsedPaper(
        title="Test Paper",
        page_count=5,
        chunks=[
            PaperChunk(chunk_id="p1_h", page=1, content="1\nIntroduction"),
            PaperChunk(chunk_id="p2_h", page=2, content="2\nMethodology"),
            PaperChunk(chunk_id="p4_h", page=4, content="3\nExperiments"),
        ],
    )

    method_context = build_learning_page_context(report, paper, 2)
    experiment_context = build_learning_page_context(report, paper, 4)

    assert method_context.paper_section == "§2 Methodology"
    assert any(point.section_type == LearningSectionType.METHOD for point in method_context.points)
    assert method_context.chunk_ids == ("p2_method",)
    assert "第 2 页" in method_context.suggested_questions[0]
    assert experiment_context.paper_section == "§3 Experiments"
    assert experiment_context.chunk_ids != method_context.chunk_ids
    assert experiment_context.suggested_questions != method_context.suggested_questions


def test_page_context_recognizes_numbered_heading_with_period() -> None:
    report = make_report()
    paper = ParsedPaper(
        title="Heading formats",
        page_count=3,
        chunks=[
            PaperChunk(chunk_id="p1_h", page=1, content="1. Introduction"),
            PaperChunk(chunk_id="p2_h", page=2, content="2. Methodology"),
            PaperChunk(chunk_id="p3_h", page=3, content="3. Experiments"),
        ],
    )

    context = build_learning_page_context(report, paper, 2)

    assert context.paper_section == "§2 Methodology"


def test_logic_chain_contains_only_evidence_backed_nodes() -> None:
    report = make_report()

    nodes = build_learning_logic_chain(report)

    assert [node.role for node in nodes] == ["问题", "作者方案", "验证证据"]
    assert all(node.evidence for node in nodes)


def test_key_point_requires_valid_evidence() -> None:
    settings = Settings(api_base="https://example.invalid/v1", api_key="test", model="hy3")
    service = AuditService(
        settings,
        client=FakeLearningClient(make_report("invented_chunk")),  # type: ignore[arg-type]
    )

    with pytest.raises(Hy3ResponseError, match="关键知识点缺少有效原文证据"):
        service.generate_learning_report(make_paper())


def test_learning_markdown_contains_real_anchor() -> None:
    settings = Settings(api_base="https://example.invalid/v1", api_key="test", model="hy3")
    service = AuditService(settings, client=FakeLearningClient(make_report()))  # type: ignore[arg-type]
    report = service.generate_learning_report(make_paper())

    markdown = render_learning_markdown(report)

    assert "# 论文学习讲解" in markdown
    assert "第 2 页 `p2_b1`" in markdown
    assert "invented_chunk" not in markdown


def test_learning_markdown_exports_verified_quote_and_locator() -> None:
    settings = Settings(api_base="https://example.invalid/v1", api_key="test", model="hy3")
    service = AuditService(
        settings,
        client=FakeLearningClient(make_report(quote="The cited paper evidence.")),  # type: ignore[arg-type]
    )
    report = service.generate_learning_report(make_paper())

    markdown = render_learning_markdown(report)

    assert "精确摘录" in markdown
    assert "> The cited paper evidence." in markdown
