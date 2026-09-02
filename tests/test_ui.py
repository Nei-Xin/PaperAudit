from __future__ import annotations

from paperaudit.models import (
    AutoLabel,
    EvidenceAnchor,
    PageRect,
    PaperChunk,
    ParsedPaper,
    Severity,
)
from paperaudit.ui.audit_results import _audit_evidence_anchors
from paperaudit.ui.components import (
    audit_evidence_label,
    build_audit_detail_html,
    highlight_keywords,
    render_severity_badge,
    render_status_badge,
)
from paperaudit.ui.demo_data import get_demo_audit_run
from paperaudit.ui.learning import (
    _group_learning_citations,
    _learning_citation_help,
    _learning_citation_label,
    _reflow_pdf_text,
)


def test_status_badges() -> None:
    cases = {
        AutoLabel.SUPPORTED: "支持",
        AutoLabel.PARTIALLY_SUPPORTED: "部分支持",
        AutoLabel.CONTRADICTED: "冲突",
        AutoLabel.NO_SUPPORT_FOUND: "未找到支持证据",
        AutoLabel.ABSTAIN: "证据不足",
    }
    for label, expected in cases.items():
        badge = render_status_badge(label)
        assert expected in badge
    assert "badge-supported" in render_status_badge(AutoLabel.SUPPORTED)


def test_severity_badges() -> None:
    cases = {
        Severity.NONE: "无风险",
        Severity.LOW: "低风险",
        Severity.MEDIUM: "中风险",
        Severity.HIGH: "高风险",
        Severity.CRITICAL: "严重",
    }
    for severity, expected in cases.items():
        badge = render_severity_badge(severity)
        assert expected in badge
    assert "badge-sev-critical" in render_severity_badge(Severity.CRITICAL)


def test_highlight_keywords() -> None:
    highlighted = highlight_keywords(
        "EduMDL achieves 92.4% mAP on EduDoc-Bench dataset.",
        ["EduMDL", "92.4%", "EduDoc-Bench"],
    )
    assert '<mark class="pa-mark">' in highlighted
    assert "EduMDL" in highlighted


def test_demo_audit_run() -> None:
    demo_run = get_demo_audit_run()
    assert len(demo_run.audits) == 6
    assert demo_run.summary.total_score is not None
    assert demo_run.summary.critical_count == 1


def test_audit_detail_shows_report_location_when_present() -> None:
    audit = get_demo_audit_run().audits[0]
    located = audit.model_copy(
        update={
            "claim": audit.claim.model_copy(
                update={"report_location": "PPT 第 4 页"}
            )
        }
    )

    rendered = build_audit_detail_html(located, "主要结果")

    assert "PPT 第 4 页" in rendered


def test_pdf_evidence_text_is_reflowed_for_display() -> None:
    text = "context-adaptive in-\nstructional mode\nselection"

    rendered = _reflow_pdf_text(text)

    assert rendered == "context-adaptive instructional mode selection"


def test_identical_learning_citation_labels_are_grouped() -> None:
    evidence = [
        EvidenceAnchor(chunk_id="p4_b1", page=4, locator="§2 Task", text="First"),
        EvidenceAnchor(chunk_id="p4_b2", page=4, locator="§2 Task", text="Second"),
        EvidenceAnchor(chunk_id="p5_b1", page=5, locator="§3 Method", text="Third"),
    ]

    grouped = _group_learning_citations(evidence)

    assert [label for label, _ in grouped] == [
        "P4 · §2 Task · 仅页码",
        "P5 · §3 Method · 仅页码",
    ]
    assert [anchor.chunk_id for anchor in grouped[0][1]] == ["p4_b1", "p4_b2"]


def test_learning_citation_help_uses_reader_facing_copy() -> None:
    anchor = EvidenceAnchor(
        chunk_id="p4_b1",
        page=4,
        locator="§2 Segment Anything Task",
        text="Task. We start by translating the idea of a prompt.",
    )

    help_text = _learning_citation_help(anchor)

    assert "点击可跳转 PDF 并高亮对应内容" not in help_text
    assert "原文预览" in help_text
    assert "已定位到" not in help_text
    assert "旧报告" not in help_text
    assert "本地校验" not in help_text


def test_learning_citation_label_distinguishes_exact_block_and_page_only() -> None:
    rect = PageRect(x0=10, y0=20, x1=100, y1=35)

    assert _learning_citation_label(
        EvidenceAnchor(chunk_id="p4_b1", page=4, quote="Exact quote", rects=[rect])
    ) == "P4 · 原文"
    assert _learning_citation_label(
        EvidenceAnchor(chunk_id="p4_b2", page=4, text="Paragraph", rects=[rect])
    ) == "P4 · 段落"
    assert _learning_citation_label(
        EvidenceAnchor(chunk_id="p4_b3", page=4, text="Page only")
    ) == "P4 · 仅页码"


def test_saved_audit_evidence_is_enriched_from_the_local_paper_index() -> None:
    run = get_demo_audit_run()
    rect = PageRect(x0=72, y0=100, x1=320, y1=116)
    paper = ParsedPaper(
        title=run.paper_title,
        page_count=run.page_count,
        chunks=[
            PaperChunk(chunk_id="p1_h", page=1, content="1 Introduction"),
            PaperChunk(
                chunk_id="p1_b1",
                page=1,
                content="The educational document setting motivates this work.",
                rects=[rect],
            ),
        ],
    )

    anchor = _audit_evidence_anchors(run, paper)["p1_b1"]

    assert anchor.locator == "§1 Introduction · 第 1 段"
    assert anchor.rects == [rect]
    assert audit_evidence_label(anchor) == "P1 · §1 Introduction · 第 1 段 · 段落"
