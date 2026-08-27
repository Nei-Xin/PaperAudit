"""Learning-report workspace and local PDF page preview."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from html import escape
import re

import pymupdf
import streamlit as st

from paperaudit.hy3_client import Hy3ResponseError
from paperaudit.models import (
    AnswerSupportType,
    AnswerStatus,
    AuditJob,
    AuditJobStatus,
    ClaimCategory,
    EvidenceAnchor,
    LearningReport,
    PageRect,
    PaperAnswer,
    ParsedCodebase,
    ParsedPaper,
)
from paperaudit.code_service import CodeLearningService
from paperaudit.reporting import render_learning_markdown
from paperaudit.report_input import parse_report_file
from paperaudit.service import (
    AuditService,
    build_learning_logic_chain,
    build_learning_page_context,
    match_selected_chunks,
    refresh_evidence_anchors,
    refresh_learning_report_evidence,
)
from paperaudit.ui.pdf_selector import get_pdf_page_count, render_selectable_pdf_page
from paperaudit.ui.code_workspace import render_code_workspace
from paperaudit.storage import AuditRecordMetadata


_CONVERSATIONAL_INPUTS = {
    "好",
    "好的",
    "可以",
    "明白",
    "明白了",
    "知道了",
    "谢谢",
    "谢谢你",
    "ok",
    "okay",
}

_LEARNING_AUDIT_SCOPE = [
    ClaimCategory.RESEARCH_QUESTION,
    ClaimCategory.CONTRIBUTION,
    ClaimCategory.METHOD,
    ClaimCategory.DATASET_SETUP,
    ClaimCategory.RESULTS,
    ClaimCategory.LIMITATIONS,
]

_AUDIT_CATEGORY_LABELS = {
    ClaimCategory.RESEARCH_QUESTION: "研究问题",
    ClaimCategory.CONTRIBUTION: "核心贡献",
    ClaimCategory.METHOD: "方法",
    ClaimCategory.DATASET_SETUP: "数据集与实验设置",
    ClaimCategory.RESULTS: "主要结果",
    ClaimCategory.LIMITATIONS: "局限性",
}

AuditSubmitCallback = Callable[
    [str, str, str, str | None, list[ClaimCategory], str], AuditJob
]

_SECTION_READING_GUIDES = {
    "research_problem": "先区分现实场景中的困难、现有方法的缺口，以及论文真正希望解决的问题。",
    "contributions": "分别判断作者提出了什么、相比已有方法新在哪里，以及实验是否支撑这些贡献。",
    "method": "按照输入、核心模块、信息流和最终输出的顺序阅读，避免只记住模块名称。",
    "experiments": "重点关注数据、基线、评价指标和实验条件，它们决定结果能够说明什么。",
    "results": "先确认比较对象和指标，再判断提升是否稳定，以及结论适用于哪些条件。",
    "limitations": "区分作者明确承认的限制和根据实验边界可以合理推断的不足。",
    "key_terms": "把术语放回论文的方法或实验语境中理解，不要只记孤立定义。",
}

_SECTION_FOLLOWUPS = {
    "research_problem": (
        "现有方法的核心不足可以归纳为哪几类？",
        "这个研究问题为什么值得解决？",
        "论文如何把现实需求转化为研究目标？",
    ),
    "contributions": (
        "这篇论文最重要的创新是什么？",
        "这些贡献与已有方法相比新在哪里？",
        "哪些实验结果能够支撑作者声称的贡献？",
    ),
    "method": (
        "请按输入、处理流程和输出解释论文方法。",
        "方法中的核心模块分别承担什么作用？",
        "这个方法最关键的设计选择是什么？",
    ),
    "experiments": (
        "实验使用了哪些数据、基线和评价指标？",
        "实验设计能否公平验证论文方法？",
        "消融实验分别验证了哪些模块？",
    ),
    "results": (
        "论文最关键的实验结果是什么？",
        "结果在哪些指标或场景下提升最明显？",
        "实验结果支持哪些结论，又不能支持哪些结论？",
    ),
    "limitations": (
        "论文明确承认了哪些局限？",
        "这些局限会影响哪些使用场景？",
        "后续研究可以优先改进什么？",
    ),
    "key_terms": (
        "这些关键术语之间是什么关系？",
        "哪些术语是理解论文方法的前提？",
        "请用一个具体例子解释这些术语。",
    ),
}


@st.cache_data(show_spinner=False, max_entries=8)
def _render_pdf_page(
    pdf_bytes: bytes,
    page_number: int,
    highlight_rects: tuple[tuple[float, float, float, float], ...] = (),
) -> bytes:
    document = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    try:
        if page_number < 1 or page_number > document.page_count:
            raise ValueError("PDF 页码超出范围。")
        page = document.load_page(page_number - 1)
        for coordinates in highlight_rects:
            rect = pymupdf.Rect(*coordinates) & page.rect
            if rect.is_empty or rect.is_infinite:
                continue
            page.draw_rect(
                rect,
                color=None,
                fill=(1.0, 0.88, 0.25),
                fill_opacity=0.3,
                overlay=True,
            )
        pixmap = page.get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5), alpha=False)
        return pixmap.tobytes("png")
    finally:
        document.close()


def _rect_coordinates(
    rects: list[PageRect],
) -> tuple[tuple[float, float, float, float], ...]:
    return tuple((rect.x0, rect.y0, rect.x1, rect.y1) for rect in rects)


@st.dialog("PDF 原文定位", width="large")
def _show_pdf_page(
    pdf_bytes: bytes,
    page_number: int,
    chunk_id: str,
    rects: list[PageRect],
) -> None:
    st.caption(f"第 {page_number} 页 · 证据块 {chunk_id}")
    if rects:
        st.caption("黄色高亮区域为当前证据在论文中的位置。")
    else:
        st.caption("该证据没有坐标信息，当前仅定位到对应页面。")
    try:
        st.image(
            _render_pdf_page(pdf_bytes, page_number, _rect_coordinates(rects)),
            width="stretch",
        )
    except (ValueError, RuntimeError) as exc:
        st.error(f"无法显示 PDF 页面：{exc}")


def _all_anchors(report: LearningReport) -> dict[str, EvidenceAnchor]:
    anchors: dict[str, EvidenceAnchor] = {}
    for section in report.sections:
        for point in section.points:
            for anchor in point.evidence:
                if anchor.page is not None and anchor.text:
                    anchors.setdefault(anchor.chunk_id, anchor)
    return anchors


def _context_should_expand(text: str | None) -> bool:
    if not text:
        return False
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    short_lines = sum(len(line) <= 18 for line in lines)
    return len(text) < 180 or (len(lines) >= 4 and short_lines / len(lines) >= 0.6)


def _reflow_pdf_text(text: str | None) -> str:
    if not text:
        return ""
    reflowed = re.sub(
        r"(?<=[A-Za-z])-\s*\n\s*(?=[a-z]{3,}\b)",
        "",
        text,
    )
    reflowed = re.sub(r"\s*\n\s*", " ", reflowed)
    return re.sub(r"[ \t]+", " ", reflowed).strip()


def _reflow_context(text: str | None) -> str:
    if not text:
        return ""
    return "\n\n".join(_reflow_pdf_text(part) for part in text.split("\n\n"))


def _learning_citation_label(anchor: EvidenceAnchor) -> str:
    parts = [f"P{anchor.page}" if anchor.page is not None else "页码未知"]
    if anchor.locator:
        parts.append(anchor.locator)
    if not anchor.rects:
        parts.append("仅页码")
    elif anchor.quote:
        parts.append("原文")
    else:
        parts.append("段落")
    return " · ".join(parts)


def _learning_citation_help(anchor: EvidenceAnchor) -> str:
    excerpt = _reflow_pdf_text(anchor.quote or anchor.text)
    if len(excerpt) > 240:
        excerpt = excerpt[:237].rstrip() + "…"
    lines: list[str] = []
    if excerpt:
        lines.extend(["原文预览", excerpt])
    else:
        lines.append("该引用暂时无法显示原文预览。")
    return "\n".join(lines)


def _group_learning_citations(
    evidence: list[EvidenceAnchor] | tuple[EvidenceAnchor, ...],
) -> list[tuple[str, list[EvidenceAnchor]]]:
    """Group anchors that would otherwise render as identical citation chips."""

    grouped: dict[str, list[EvidenceAnchor]] = {}
    for anchor in evidence:
        grouped.setdefault(_learning_citation_label(anchor), []).append(anchor)
    return list(grouped.items())


def _render_source_panel(
    anchors: dict[str, EvidenceAnchor],
    selected_id: str | None,
    pdf_bytes: bytes,
    paper: ParsedPaper | None,
    key_prefix: str,
    title: str = "论文原文",
) -> None:
    selected_state_key = f"{key_prefix}_selected_evidence"
    group_state_key = f"{key_prefix}_evidence_group"
    page_state_key = f"{key_prefix}_pdf_page"
    anchor_sync_key = f"{key_prefix}_pdf_anchor_sync"
    zoom_state_key = f"{key_prefix}_pdf_zoom"
    focus_state_key = f"{key_prefix}_focus_evidence"
    group_ids = [
        chunk_id
        for chunk_id in st.session_state.get(group_state_key, [])
        if chunk_id in anchors
    ]
    if selected_id in anchors and selected_id not in group_ids:
        group_ids = [selected_id]
    if selected_id not in anchors:
        selected_id = group_ids[0] if group_ids else None
    if not group_ids and selected_id:
        group_ids = [selected_id]

    page_count = paper.page_count if paper is not None else get_pdf_page_count(pdf_bytes)
    selected = anchors.get(selected_id) if selected_id else None
    if selected and st.session_state.get(anchor_sync_key) != selected_id:
        st.session_state[page_state_key] = selected.page or 1
        st.session_state[anchor_sync_key] = selected_id
    st.session_state.setdefault(page_state_key, selected.page if selected else 1)
    st.session_state[page_state_key] = min(
        max(int(st.session_state[page_state_key]), 1),
        page_count,
    )
    st.session_state.setdefault(zoom_state_key, 100)
    st.session_state[zoom_state_key] = min(
        max(int(st.session_state[zoom_state_key]), 100), 180
    )

    def change_pdf_page(delta: int) -> None:
        current_page = int(st.session_state.get(page_state_key, 1))
        st.session_state[page_state_key] = min(
            max(current_page + delta, 1),
            page_count,
        )

    def change_pdf_zoom(delta: int) -> None:
        current_zoom = int(st.session_state.get(zoom_state_key, 100))
        st.session_state[zoom_state_key] = min(max(current_zoom + delta, 100), 180)

    def fit_pdf_width() -> None:
        st.session_state[zoom_state_key] = 100

    def toggle_pdf_focus() -> None:
        if key_prefix == "learning":
            st.session_state["learning_pdf_focus"] = not bool(
                st.session_state.get("learning_pdf_focus", False)
            )

    with st.container(key=f"{key_prefix}_source_panel"):
        st.markdown('<div class="pa-learning-source-marker"></div>', unsafe_allow_html=True)
        evidence_status = ""
        if group_ids:
            current_index = group_ids.index(selected_id) + 1 if selected_id in group_ids else 1
            evidence_status = f" · 证据 {current_index}/{len(group_ids)}"
        with st.container(key=f"{key_prefix}_pdf_toolbar"):
            title_col, previous_col, page_col, next_col, zoom_out_col, zoom_col, zoom_in_col, fit_col = st.columns(
                [2.7, 0.55, 1.25, 0.55, 0.55, 0.8, 0.55, 1.45],
                vertical_alignment="center",
                gap="small",
            )
            title_col.markdown(
                f'<div class="pa-pdf-panel-title">{escape(title)}'
                f'<span>{evidence_status}</span></div>',
                unsafe_allow_html=True,
            )
            previous_col.button(
                "‹",
                key=f"{key_prefix}-pdf-previous",
                disabled=st.session_state[page_state_key] <= 1,
                width="stretch",
                on_click=change_pdf_page,
                args=(-1,),
            )
            with page_col:
                current_page_col, total_page_col = st.columns(
                    [1, 0.8], vertical_alignment="center", gap="small"
                )
                current_page_col.number_input(
                    f"PDF 页码，共 {page_count} 页",
                    min_value=1,
                    max_value=page_count,
                    step=1,
                    key=page_state_key,
                    label_visibility="collapsed",
                )
                total_page_col.markdown(
                    f'<div class="pa-pdf-page-total">/ {page_count}</div>',
                    unsafe_allow_html=True,
                )
            next_col.button(
                "›",
                key=f"{key_prefix}-pdf-next",
                disabled=st.session_state[page_state_key] >= page_count,
                width="stretch",
                on_click=change_pdf_page,
                args=(1,),
            )
            zoom_out_col.button(
                "−",
                key=f"{key_prefix}-pdf-zoom-out",
                disabled=st.session_state[zoom_state_key] <= 100,
                width="stretch",
                on_click=change_pdf_zoom,
                args=(-10,),
            )
            zoom_col.markdown(
                f'<div class="pa-pdf-zoom">{st.session_state[zoom_state_key]}%</div>',
                unsafe_allow_html=True,
            )
            zoom_in_col.button(
                "+",
                key=f"{key_prefix}-pdf-zoom-in",
                disabled=st.session_state[zoom_state_key] >= 180,
                width="stretch",
                on_click=change_pdf_zoom,
                args=(10,),
            )
            if key_prefix == "learning":
                fit_action, focus_action = fit_col.columns(
                    [2.6, 1], vertical_alignment="center", gap="small"
                )
                fit_action.button(
                    "适应宽度",
                    key=f"{key_prefix}-pdf-fit-width",
                    width="stretch",
                    on_click=fit_pdf_width,
                )
                focus_action.button(
                    "⛶",
                    key=f"{key_prefix}-pdf-focus-toggle",
                    width="stretch",
                    on_click=toggle_pdf_focus,
                    help="进入或退出 PDF 专注阅读",
                )
            else:
                fit_col.button(
                    "适应宽度",
                    key=f"{key_prefix}-pdf-fit-width",
                    width="stretch",
                    on_click=fit_pdf_width,
                )
        if group_ids:
            group_columns = st.columns(min(len(group_ids), 3))
            for group_index, chunk_id in enumerate(group_ids):
                anchor = anchors[chunk_id]
                with group_columns[group_index % len(group_columns)]:
                    if st.button(
                        f"证据 {group_index + 1} · 第 {anchor.page} 页",
                        key=f"{key_prefix}-group-{group_index}-{chunk_id}",
                        type=(
                            "primary"
                            if chunk_id == selected_id
                            and st.session_state[page_state_key] == anchor.page
                            else "secondary"
                        ),
                        width="stretch",
                    ):
                        selected_id = chunk_id
                        st.session_state[selected_state_key] = chunk_id
                        st.session_state[page_state_key] = anchor.page or 1
                        st.session_state[anchor_sync_key] = chunk_id
                        st.session_state[focus_state_key] = chunk_id
                        st.rerun()

        selected = anchors.get(selected_id) if selected_id else None
        display_page = int(st.session_state[page_state_key])
        selected_on_page = bool(selected and selected.page == display_page)
        highlights = selected.rects if selected_on_page and selected else []
        focus_highlight = bool(
            selected_on_page
            and selected_id
            and st.session_state.get(focus_state_key) == selected_id
        )
        try:
            selection = render_selectable_pdf_page(
                pdf_bytes,
                display_page,
                highlights,
                key=f"{key_prefix}-selectable-pdf",
                zoom_percent=int(st.session_state[zoom_state_key]),
                focus_highlight=focus_highlight,
            )
            if focus_highlight:
                st.session_state.pop(focus_state_key, None)
        except (ValueError, RuntimeError) as exc:
            st.error(f"无法显示 PDF 页面：{exc}")
            selection = None
        if selection and paper is not None:
            selection_text = str(selection.get("text", "")).strip()
            selection_page = int(selection.get("page", display_page))
            selection_rects: list[PageRect] = []
            for coordinates in selection.get("rects", []):
                try:
                    selection_rects.append(PageRect.model_validate(coordinates))
                except (TypeError, ValueError):
                    continue
            matched = match_selected_chunks(
                paper,
                selection_page,
                selection_text,
                selection_rects,
            )
            st.session_state["paper_text_selection"] = {
                "page": selection_page,
                "text": selection_text,
                "chunk_ids": [chunk.chunk_id for chunk in matched],
            }
            if key_prefix == "learning":
                st.session_state["learning_switch_to_qa"] = True
            st.rerun()
        if selected_on_page and selected:
            if highlights:
                st.caption("黄色区域为刚刚点击定位的原文；也可继续拖选文字发起追问。")
            else:
                st.caption("该引用缺少可用坐标，已跳转到对应页面但未显示高亮。")
        else:
            if selected:
                st.caption(
                    f"当前手动查看第 {display_page} 页；点击上方证据按钮可返回第 {selected.page} 页。"
                )
            elif key_prefix == "learning":
                st.caption("当前为无高亮原文；点击右侧知识点的“定位并高亮”后显示对应位置。")
            else:
                st.caption("当前为无高亮原文；点击回答引用的“定位并高亮”后显示对应位置。")


def _render_report_tab(
    report: LearningReport,
    pdf_bytes: bytes,
    paper: ParsedPaper | None,
    focus_pdf: bool = False,
    question_available: bool = False,
    joint_questions: bool = False,
) -> None:
    anchors = _all_anchors(report)
    section_values = [section.section_type.value for section in report.sections]
    section_labels = {
        "research_problem": "研究问题",
        "contributions": "主要贡献",
        "method": "研究方法",
        "experiments": "实验设计",
        "results": "实验结果",
        "limitations": "研究局限",
        "key_terms": "关键术语",
    }
    if st.session_state.get("learning_active_section") not in section_values:
        st.session_state["learning_active_section"] = section_values[0]

    with st.container(key="learning_section_bar"):
        active_section_value = st.segmented_control(
            "阅读章节",
            section_values,
            format_func=section_labels.get,
            key="learning_active_section",
            required=True,
            label_visibility="collapsed",
            width="stretch",
        )

    active_section = next(
        section
        for section in report.sections
        if section.section_type.value == active_section_value
    )
    if st.session_state.get("learning_evidence_section") != active_section_value:
        st.session_state["learning_evidence_group"] = []
        st.session_state["learning_selected_evidence"] = None
        st.session_state["learning_active_point"] = None
        st.session_state["learning_evidence_section"] = active_section_value

    selected_id = st.session_state.get("learning_selected_evidence")
    if selected_id not in anchors:
        selected_id = None
        st.session_state["learning_selected_evidence"] = None

    section_label = section_labels.get(active_section_value, "论文讲解")
    display_title = active_section.title.strip()
    for separator in ("：", ":"):
        prefix = f"{section_label}{separator}"
        if display_title.startswith(prefix):
            display_title = display_title[len(prefix) :].strip()
            break
    section_anchor_ids = list(
        dict.fromkeys(
            anchor.chunk_id
            for point in active_section.points
            for anchor in point.evidence
            if anchor.chunk_id in anchors
        )
    )

    term_section = next(
        (
            section
            for section in report.sections
            if section.section_type.value == "key_terms"
        ),
        None,
    )
    concept_titles = [point.title for point in (term_section.points if term_section else [])]
    if not concept_titles:
        concept_titles = [point.title for point in active_section.points]
    concept_titles = list(dict.fromkeys(concept_titles))[:4]

    def queue_question(
        question: str,
        selected_chunk_ids: list[str] | tuple[str, ...] | None = None,
    ) -> None:
        pending = {
            "question": question,
            "selected_chunk_ids": list(
                section_anchor_ids
                if selected_chunk_ids is None
                else selected_chunk_ids
            ),
            "selected_text": None,
        }
        if joint_questions:
            pending["scope"] = "paper"
            st.session_state["joint_qa_pending"] = pending
            st.session_state["joint_layout_mode_pending"] = "balanced"
        else:
            st.session_state["paper_qa_pending"] = pending
        st.session_state["learning_switch_to_qa"] = True
        st.rerun()

    def activate_evidence(
        anchor: EvidenceAnchor,
        group: list[EvidenceAnchor] | tuple[EvidenceAnchor, ...],
        point_id: str,
    ) -> None:
        st.session_state["learning_evidence_group"] = [
            item.chunk_id for item in group if item.chunk_id in anchors
        ]
        st.session_state["learning_selected_evidence"] = anchor.chunk_id
        st.session_state["learning_active_point"] = point_id
        st.session_state["learning_focus_evidence"] = anchor.chunk_id
        st.rerun()

    def render_anchor_buttons(
        evidence: list[EvidenceAnchor] | tuple[EvidenceAnchor, ...],
        key_prefix: str,
        point_id: str,
    ) -> None:
        valid = [anchor for anchor in evidence if anchor.chunk_id in anchors]
        if not valid:
            return
        columns = st.columns(1)
        for anchor_index, anchor in enumerate(valid):
            with columns[anchor_index % len(columns)]:
                if st.button(
                    f"📄 {_learning_citation_label(anchor)} ↗",
                    key=f"{key_prefix}-{anchor_index}-{anchor.chunk_id}",
                    type="tertiary",
                    help=_learning_citation_help(anchor),
                    width="stretch",
                ):
                    activate_evidence(anchor, valid, point_id)

    def render_logic_chain() -> None:
        logic_nodes = build_learning_logic_chain(report)
        if not logic_nodes:
            return
        with st.expander("论文逻辑链", expanded=active_section_value == "research_problem"):
            st.caption("问题 → 原因与约束 → 作者方案 → 验证证据")
            for node_index, node in enumerate(logic_nodes):
                st.markdown(
                    f'<div class="pa-logic-node">'
                    f'<span>{escape(node.role)}</span>'
                    f'<strong>{escape(node.title)}</strong>'
                    f'<p>{escape(node.explanation)}</p></div>',
                    unsafe_allow_html=True,
                )
                render_anchor_buttons(
                    node.evidence,
                    f"learning-logic-{node_index}",
                    f"logic:{node_index}",
                )

    def render_page_context() -> None:
        display_page = int(st.session_state.get("learning_pdf_page", 1))
        if paper is None:
            st.info("当前项目缺少本地论文索引，重新生成讲解后可使用当前页伴读。")
            return
        page_context = build_learning_page_context(report, paper, display_page)
        with st.container(
            key=f"learning_page_context_scroll_v2_{display_page}",
            height="stretch",
            border=False,
        ):
            st.markdown(
                f'<div class="pa-learning-section-kicker">当前阅读位置 · P{display_page}</div>'
                f'<h2 class="pa-learning-section-title">'
                f'{escape(page_context.paper_section or "当前页尚未识别到章节标题")}</h2>',
                unsafe_allow_html=True,
            )
            if page_context.relation:
                st.markdown(
                    f'<div class="pa-page-relation"><strong>与全文逻辑的关系</strong>'
                    f'<span>{escape(page_context.relation)}</span></div>',
                    unsafe_allow_html=True,
                )
            if page_context.points:
                st.markdown(
                    '<div class="pa-learning-block-heading">本页相关知识点</div>',
                    unsafe_allow_html=True,
                )
                for point_index, point in enumerate(page_context.points):
                    with st.container(key=f"learning_page_point_{display_page}_{point_index}"):
                        st.markdown(
                            f'<div class="pa-page-point-section">'
                            f'{escape(point.section_title)}</div>'
                            f'<div class="pa-learning-point-title">'
                            f'{escape(point.title)}</div>',
                            unsafe_allow_html=True,
                        )
                        st.write(point.explanation)
                        render_anchor_buttons(
                            point.evidence,
                            f"learning-page-evidence-{display_page}-{point_index}",
                            f"page:{display_page}:{point_index}",
                        )
            else:
                st.info("当前页没有已绑定的讲解知识点。你仍可在左侧拖选原文后发起追问。")

            st.markdown(
                '<div class="pa-learning-recommend-label">基于当前页的推荐追问</div>',
                unsafe_allow_html=True,
            )
            for question_index, suggested_question in enumerate(
                page_context.suggested_questions
            ):
                if st.button(
                    f"↗ {suggested_question}",
                    key=f"learning-page-followup-{display_page}-{question_index}",
                    type="tertiary",
                    width="stretch",
                    disabled=not question_available,
                ):
                    queue_question(suggested_question, page_context.chunk_ids)

    def render_report_content() -> None:
        with st.container(key="learning_explanation_header"):
            scope_title, scope_control = st.columns(
                [1, 1.7], vertical_alignment="center", gap="small"
            )
            scope_title.markdown(
                '<div class="pa-explanation-panel-title">论文讲解</div>',
                unsafe_allow_html=True,
            )
            explanation_scope = scope_control.segmented_control(
                "讲解范围",
                ["global", "page"],
                format_func={"global": "全局", "page": "当前页"}.get,
                key="learning_explanation_scope",
                required=True,
                label_visibility="collapsed",
                width="stretch",
            )
        if explanation_scope == "page":
            render_page_context()
            return
        with st.container(
            key=f"learning_report_scroll_v2_{active_section_value}",
            height="stretch",
            border=False,
        ):
            st.markdown(
                f'<div class="pa-learning-section-kicker">{escape(section_label)}</div>'
                f'<h2 class="pa-learning-section-title">{escape(display_title)}</h2>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<div class="pa-learning-section-overview">'
                f'{escape(active_section.overview)}</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                '<div class="pa-learning-block-heading">关键知识点</div>',
                unsafe_allow_html=True,
            )
            section_index = report.sections.index(active_section)
            for point_index, point in enumerate(active_section.points):
                point_id = f"{active_section_value}:{point_index}"
                point_active = st.session_state.get("learning_active_point") == point_id
                with st.container(key=f"learning_point_{section_index}_{point_index}"):
                    active_class = " is-active" if point_active else ""
                    marker = '<span class="pa-learning-key">核心</span>' if point.key_point else ""
                    st.markdown(
                        f'<div class="pa-learning-point-marker{active_class}"></div>'
                        + marker
                        + f'<div class="pa-learning-point-title{active_class}">'
                        f'{escape(point.title)}</div>',
                        unsafe_allow_html=True,
                    )
                    st.write(point.explanation)
                    if point.evidence:
                        columns = st.columns(1)
                        citation_groups = _group_learning_citations(point.evidence)
                        for anchor_index, (label, grouped_anchors) in enumerate(
                            citation_groups
                        ):
                            anchor = grouped_anchors[0]
                            group_ids = [
                                item.chunk_id
                                for item in point.evidence
                                if item.chunk_id in anchors
                            ]
                            count_suffix = (
                                f" · {len(grouped_anchors)} 处证据"
                                if len(grouped_anchors) > 1
                                else ""
                            )
                            with columns[anchor_index % len(columns)]:
                                if st.button(
                                    f"📄 {label}{count_suffix} ↗",
                                    key=f"learning-evidence-{section_index}-{point_index}-{anchor_index}-{anchor.chunk_id}",
                                    type=(
                                        "primary"
                                        if point_active and selected_id in group_ids
                                        else "tertiary"
                                    ),
                                    help=_learning_citation_help(anchor),
                                ):
                                    st.session_state["learning_evidence_group"] = group_ids
                                    st.session_state["learning_selected_evidence"] = anchor.chunk_id
                                    st.session_state["learning_active_point"] = point_id
                                    st.session_state["learning_focus_evidence"] = anchor.chunk_id
                                    st.rerun()

            render_logic_chain()

            with st.container(key="learning_section_support"):
                st.markdown(
                    '<div class="pa-learning-block-heading">深入理解</div>'
                    f'<div class="pa-learning-guide"><strong>本节怎么读</strong>'
                    f'<span>{escape(_SECTION_READING_GUIDES.get(active_section_value, "结合原文证据理解本节结论及其适用边界。"))}</span></div>',
                    unsafe_allow_html=True,
                )
                if concept_titles:
                    concept_html = "".join(
                        f"<span>{escape(title)}</span>" for title in concept_titles
                    )
                    st.markdown(
                        '<div class="pa-learning-concepts-label">相关概念</div>'
                        f'<div class="pa-learning-concepts">{concept_html}</div>',
                        unsafe_allow_html=True,
                    )

                st.markdown(
                    '<div class="pa-learning-recommend-label">推荐追问</div>',
                    unsafe_allow_html=True,
                )
                for question_index, suggested_question in enumerate(
                    _SECTION_FOLLOWUPS.get(active_section_value, ())
                ):
                    if st.button(
                        f"↗ {suggested_question}",
                        key=f"learning-followup-{section_index}-{question_index}",
                        type="tertiary",
                        width="stretch",
                        disabled=not question_available,
                    ):
                        queue_question(suggested_question)

        with st.container(key="learning_section_followup"):
            with st.form(
                f"learning-section-question-{active_section_value}",
                clear_on_submit=True,
            ):
                st.markdown(
                    '<div class="pa-learning-followup-form-marker"></div>',
                    unsafe_allow_html=True,
                )
                question_col, send_col = st.columns([5, 1], vertical_alignment="center")
                question = question_col.text_input(
                    "针对当前章节追问",
                    placeholder=f"继续追问“{section_label}”…",
                    max_chars=1000,
                    label_visibility="collapsed",
                    disabled=not question_available,
                )
                submitted = send_col.form_submit_button(
                    "发送",
                    type="primary",
                    width="stretch",
                    disabled=not question_available,
                )
            if not question_available:
                st.caption("配置 API 后即可针对当前章节继续追问。")
            if submitted:
                normalized_question = question.strip()
                if normalized_question:
                    queue_question(normalized_question)
                else:
                    st.warning("请输入需要追问的内容。")

    if focus_pdf:
        _render_source_panel(anchors, selected_id, pdf_bytes, paper, "learning")
        return

    source_col, report_col = st.columns([1.38, 1], gap="medium")
    with source_col:
        _render_source_panel(anchors, selected_id, pdf_bytes, paper, "learning")
    with report_col:
        render_report_content()


def _qa_anchors(
    history: list[PaperAnswer],
    paper: ParsedPaper | None,
) -> dict[str, EvidenceAnchor]:
    anchors = {
        citation.chunk_id: citation
        for answer in history
        for citation in answer.citations
        if citation.page is not None and citation.text
    }
    selection = st.session_state.get("paper_text_selection")
    if paper is not None and isinstance(selection, dict):
        chunk_map = {chunk.chunk_id: chunk for chunk in paper.chunks}
        for chunk_id in selection.get("chunk_ids", []):
            chunk = chunk_map.get(chunk_id)
            if chunk is not None:
                anchors.setdefault(
                    chunk_id,
                    EvidenceAnchor(
                        chunk_id=chunk.chunk_id,
                        page=chunk.page,
                        text=chunk.content,
                        rects=chunk.rects,
                    ),
                )
    if paper is not None:
        return {
            anchor.chunk_id: anchor
            for anchor in refresh_evidence_anchors(list(anchors.values()), paper)
        }
    return anchors


def _citation_label(citation: EvidenceAnchor) -> str:
    return _learning_citation_label(citation)


def _render_qa_tab(
    paper: ParsedPaper | None,
    pdf_bytes: bytes,
    service: AuditService | None,
    focus_pdf: bool = False,
) -> None:
    st.markdown(
        '<div class="pa-qa-intro">💬 回答仅使用当前论文检索到的原文证据；'
        '证据不足时不会用外部知识补全。</div>',
        unsafe_allow_html=True,
    )
    history: list[PaperAnswer] = st.session_state.setdefault("paper_qa_history", [])

    if paper is None:
        st.info("请重新生成一次论文讲解，以建立追问所需的本地论文索引。")
        return
    if service is None:
        st.warning("请先在侧边栏配置 Hy3 API，才能进行论文追问。")
        return

    anchors = _qa_anchors(history, paper)
    selected_id = st.session_state.get("qa_selected_evidence")
    if selected_id not in anchors and isinstance(
        st.session_state.get("paper_text_selection"), dict
    ):
        selected_ids = st.session_state["paper_text_selection"].get("chunk_ids", [])
        selected_id = next((item for item in selected_ids if item in anchors), None)
    if selected_id not in anchors:
        selected_id = None
        st.session_state["qa_selected_evidence"] = None

    def render_source() -> None:
        _render_source_panel(
            anchors,
            selected_id,
            pdf_bytes,
            paper,
            "qa",
            title="论文原文 · 回答依据",
        )

    def render_conversation() -> None:
        pending = st.session_state.get("paper_qa_pending")
        action_left, action_right = st.columns([4, 1])
        action_left.caption(f"保留最近 {min(len(history), 10)} 轮对话")
        if action_right.button(
            "清空", width="stretch", disabled=not history and not pending
        ):
            history.clear()
            st.session_state.pop("qa_selected_evidence", None)
            st.session_state.pop("qa_evidence_group", None)
            st.session_state.pop("paper_qa_pending", None)
            st.rerun()

        selected_text = st.session_state.get("paper_text_selection")
        if isinstance(selected_text, dict) and selected_text.get("text"):
            with st.container(border=True, key="qa_selected_quote"):
                quote_col, clear_col = st.columns([6, 1], vertical_alignment="center")
                quote_col.markdown(
                    f'<div class="pa-selected-quote-label">已选原文 · 第 '
                    f'{int(selected_text.get("page", 1))} 页</div>'
                    f'<div class="pa-selected-quote">“'
                    f'{escape(str(selected_text["text"]))}”</div>',
                    unsafe_allow_html=True,
                )
                if clear_col.button("取消", key="clear-paper-selection", width="stretch"):
                    st.session_state.pop("paper_text_selection", None)
                    st.rerun()

        with st.container(key="qa_history_scroll"):
            if not history and not pending:
                st.info("还没有追问。可以从论文的方法、实验数字、结果原因或局限性开始。")
            for answer_index, answer in enumerate(history):
                with st.container(border=True):
                    st.markdown(
                        f'<div class="pa-qa-question">{escape(answer.question)}</div>',
                        unsafe_allow_html=True,
                    )
                    if answer.status == AnswerStatus.INSUFFICIENT_EVIDENCE:
                        status_text = "⚠️ 当前证据不足"
                    elif answer.conclusions:
                        status_text = "✓ 逐结论证据已校验"
                    else:
                        status_text = "✓ 基于原文回答"
                    st.markdown(
                        f'<div class="pa-qa-answer-head"><span class="pa-qa-answer-label">'
                        f'{status_text}</span></div>',
                        unsafe_allow_html=True,
                    )
                    if not answer.conclusions:
                        st.markdown(
                            f'<div class="pa-qa-answer">{escape(answer.answer)}</div>',
                            unsafe_allow_html=True,
                        )
                    if answer.conclusions:
                        for conclusion_index, conclusion in enumerate(answer.conclusions):
                            support_label = (
                                "论文明确陈述"
                                if conclusion.support_type == AnswerSupportType.DIRECT
                                else "AI 基于论文证据推断"
                            )
                            support_class = (
                                "is-direct"
                                if conclusion.support_type == AnswerSupportType.DIRECT
                                else "is-inference"
                            )
                            st.markdown(
                                f'<div class="pa-answer-conclusion">'
                                f'<span class="pa-answer-support {support_class}">'
                                f'{support_label}</span>'
                                f'<div class="pa-answer-conclusion-text">'
                                f'{escape(conclusion.text)}</div></div>',
                                unsafe_allow_html=True,
                            )
                            for citation_index, citation in enumerate(conclusion.citations):
                                display_citation = anchors.get(citation.chunk_id, citation)
                                quote = display_citation.quote or display_citation.text or ""
                                quote_col, locate_col = st.columns(
                                    [3.6, 1.4], vertical_alignment="center"
                                )
                                quote_col.markdown(
                                    f'<div class="pa-answer-evidence">'
                                    f'<span>原文证据</span>“{escape(quote)}”</div>',
                                    unsafe_allow_html=True,
                                )
                                if locate_col.button(
                                    f"{_citation_label(display_citation)} ↗",
                                    key=(
                                        f"qa-conclusion-citation-{answer_index}-"
                                        f"{conclusion_index}-{citation_index}-"
                                        f"{citation.chunk_id}"
                                    ),
                                    help=_learning_citation_help(display_citation),
                                    width="stretch",
                                ):
                                    st.session_state["qa_evidence_group"] = [
                                        item.chunk_id for item in conclusion.citations
                                    ]
                                    st.session_state["qa_selected_evidence"] = citation.chunk_id
                                    st.rerun()
                    elif answer.citations:
                        display_citations = [
                            anchors.get(citation.chunk_id, citation)
                            for citation in answer.citations
                        ]
                        st.markdown(
                            f'<div class="pa-qa-citation-count">已引用 {len(display_citations)} '
                            f'段原文，点击可在左侧查看</div>',
                            unsafe_allow_html=True,
                        )
                        columns = st.columns(min(len(display_citations), 3))
                        for citation_index, citation in enumerate(display_citations):
                            with columns[citation_index % len(columns)]:
                                if st.button(
                                    f"{_citation_label(citation)} ↗",
                                    key=f"qa-citation-{answer_index}-{citation_index}-{citation.chunk_id}",
                                    help=_learning_citation_help(citation),
                                    width="stretch",
                                ):
                                    st.session_state["qa_evidence_group"] = [
                                        item.chunk_id for item in answer.citations
                                    ]
                                    st.session_state["qa_selected_evidence"] = citation.chunk_id
                                    st.rerun()
            if isinstance(pending, dict):
                with st.container(border=True):
                    st.markdown(
                        f'<div class="pa-qa-question">'
                        f'{escape(str(pending.get("question", "")))}</div>',
                        unsafe_allow_html=True,
                    )
                    st.markdown("⏳ 正在检索原文并生成回答…")

        with st.form("paper-question-form", clear_on_submit=True):
            st.markdown('<div class="pa-qa-form-marker"></div>', unsafe_allow_html=True)
            input_col, submit_col = st.columns([5, 1])
            question = input_col.text_input(
                "针对当前论文追问",
                placeholder=(
                    "例如：请解释这段话的含义和作用…"
                    if isinstance(selected_text, dict)
                    else "针对方法、实验结果或局限性继续提问…"
                ),
                max_chars=1000,
                label_visibility="collapsed",
                disabled=isinstance(pending, dict),
            )
            submitted = submit_col.form_submit_button(
                "发送",
                type="primary",
                width="stretch",
                disabled=isinstance(pending, dict),
            )

        if submitted:
            normalized_question = question.strip()
            if not normalized_question:
                st.error("追问内容不能为空。")
            elif normalized_question.casefold().rstrip("。！!") in _CONVERSATIONAL_INPUTS:
                st.info("好的，可以继续针对论文内容提问。")
            else:
                st.session_state["paper_qa_pending"] = {
                    "question": normalized_question,
                    "selected_chunk_ids": (
                        list(selected_text.get("chunk_ids", []))
                        if isinstance(selected_text, dict)
                        else []
                    ),
                    "selected_text": (
                        str(selected_text.get("text", ""))
                        if isinstance(selected_text, dict)
                        else None
                    ),
                }
                st.rerun()

        if isinstance(pending, dict):
            try:
                answer = service.answer_question(
                    paper,
                    str(pending.get("question", "")),
                    history,
                    selected_chunk_ids=pending.get("selected_chunk_ids", []),
                    selected_text=pending.get("selected_text"),
                )
                st.session_state.pop("paper_qa_pending", None)
                history.append(answer)
                del history[:-10]
                if answer.citations:
                    st.session_state["qa_selected_evidence"] = None
                    st.session_state["qa_evidence_group"] = []
                st.rerun()
            except (Hy3ResponseError, ValueError) as exc:
                st.session_state.pop("paper_qa_pending", None)
                st.error(str(exc))
            except Exception as exc:
                st.session_state.pop("paper_qa_pending", None)
                st.error(f"追问失败：{exc}")

    if focus_pdf:
        render_source()
        return

    source_col, conversation_col = st.columns([1.65, 1], gap="large")
    with source_col:
        render_source()
    with conversation_col:
        with st.container(key="qa_conversation_panel"):
            render_conversation()


def _local_time(value: str) -> str:
    try:
        return datetime.fromisoformat(value).astimezone().strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return value


@st.dialog("审计其他报告")
def render_report_audit_dialog(on_submit: AuditSubmitCallback) -> None:
    input_mode = st.segmented_control(
        "报告输入方式",
        ["上传文件", "粘贴文本"],
        key="workspace_audit_input_mode",
        default="上传文件",
        label_visibility="collapsed",
        width="stretch",
    )
    report_text = ""
    source_label = "粘贴报告"
    source_filename: str | None = None
    input_error: str | None = None
    if input_mode == "粘贴文本":
        report_text = st.text_area(
            "报告内容",
            key="workspace_audit_pasted_text",
            height=220,
            placeholder="粘贴针对当前论文的中文总结、解读或阅读笔记…",
            label_visibility="collapsed",
        )
    else:
        report_file = st.file_uploader(
            "选择报告文件",
            type=["txt", "md", "pptx"],
            accept_multiple_files=False,
            key="workspace_audit_report_file",
            help="支持 .txt / .md / .pptx；PPTX 会提取每页文字、表格、图表数据和备注。",
        )
        if report_file is not None:
            source_filename = report_file.name
            source_label = report_file.name
            try:
                parsed_report = parse_report_file(
                    report_file.getvalue(), report_file.name
                )
                report_text = parsed_report.text
            except ValueError as exc:
                input_error = str(exc)
                st.error(input_error)
            else:
                if parsed_report.kind == "pptx":
                    st.caption(
                        f"已读取 {parsed_report.page_count} 页幻灯片 · "
                        f"{len(report_text)} 个字符"
                    )
                    for warning in parsed_report.warnings:
                        st.warning(warning)
                else:
                    st.caption(f"已读取 {len(report_text)} 个字符")

    scope_mode = st.segmented_control(
        "审计范围",
        ["完整解读", "自定义重点"],
        key="workspace_audit_scope_mode",
        default="完整解读",
        width="stretch",
    )
    scope = list(_LEARNING_AUDIT_SCOPE)
    if scope_mode == "自定义重点":
        selected_labels = st.multiselect(
            "选择检查范围",
            list(_AUDIT_CATEGORY_LABELS.values()),
            default=["核心贡献", "方法", "主要结果"],
            key="workspace_audit_scope_values",
        )
        scope = [
            category
            for category, label in _AUDIT_CATEGORY_LABELS.items()
            if label in selected_labels
        ]

    cancel_col, submit_col = st.columns([1, 2])
    if cancel_col.button("取消", width="stretch"):
        st.rerun()
    if submit_col.button(
        "在后台开始审计",
        type="primary",
        width="stretch",
        disabled=bool(input_error) or not report_text.strip() or not scope,
    ):
        try:
            job = on_submit(
                report_text,
                "uploaded_report",
                source_label,
                source_filename,
                scope,
                "audit_existing",
            )
        except (ValueError, RuntimeError) as exc:
            st.error(str(exc))
        else:
            st.session_state["audit_submit_notice"] = (
                f"“{job.source_label}”已提交后台审计，可继续阅读论文。"
            )
            st.rerun()


def _render_task_item(
    job: AuditJob,
    *,
    on_open_audit: Callable[[str], None],
    on_submit: AuditSubmitCallback | None,
    key_suffix: str,
) -> None:
    status_labels = {
        AuditJobStatus.QUEUED: "等待执行",
        AuditJobStatus.RUNNING: "正在审计",
        AuditJobStatus.SUCCEEDED: "已完成",
        AuditJobStatus.FAILED: "失败",
        AuditJobStatus.INTERRUPTED: "已中断",
    }
    st.markdown(f"**{escape(job.source_label)}** · {status_labels[job.status]}")
    if job.status in {AuditJobStatus.QUEUED, AuditJobStatus.RUNNING}:
        st.progress(job.progress, text=job.stage)
    else:
        st.caption(f"{_local_time(job.created_at)} · {job.stage}")
    if job.error:
        st.error(job.error)
    if job.status == AuditJobStatus.SUCCEEDED and job.audit_id:
        if st.button(
            "查看结果",
            key=f"open-audit-job-{key_suffix}-{job.job_id}",
            width="stretch",
        ):
            try:
                on_open_audit(job.audit_id)
            except RuntimeError as exc:
                st.error(f"审计结果无法打开：{exc}")
            else:
                st.rerun()
    elif (
        job.status in {AuditJobStatus.FAILED, AuditJobStatus.INTERRUPTED}
        and on_submit is not None
    ):
        if st.button(
            "重新提交",
            key=f"retry-audit-job-{key_suffix}-{job.job_id}",
            width="stretch",
        ):
            try:
                on_submit(
                    job.report_text,
                    job.source_type,
                    job.source_label,
                    job.source_filename,
                    list(job.scope),
                    job.audit_mode,
                )
            except (ValueError, RuntimeError) as exc:
                st.error(str(exc))
            else:
                st.rerun()


@st.fragment(run_every=2)
def _render_audit_activity(
    load_jobs: Callable[[], list[AuditJob]],
    on_open_audit: Callable[[str], None],
) -> None:
    try:
        jobs = load_jobs()
    except RuntimeError as exc:
        st.warning(f"审计任务状态暂时无法读取：{exc}")
        return
    active = [
        job
        for job in jobs
        if job.status in {AuditJobStatus.QUEUED, AuditJobStatus.RUNNING}
    ]
    if active:
        current = next(
            (job for job in active if job.status == AuditJobStatus.RUNNING),
            active[-1],
        )
        with st.container(key="audit_activity_strip"):
            left, right = st.columns([5, 1], vertical_alignment="center")
            left.caption(
                f"后台审计 · {current.source_label} · {current.stage}"
                + (f" · 另有 {len(active) - 1} 项等待" if len(active) > 1 else "")
            )
            right.progress(current.progress)
        return
    latest = jobs[0] if jobs else None
    if latest is not None and latest.status == AuditJobStatus.SUCCEEDED and latest.audit_id:
        with st.container(key="audit_activity_strip"):
            message_col, action_col = st.columns([6, 1], vertical_alignment="center")
            message_col.caption(f"最近审计已完成 · {latest.source_label}")
            if action_col.button(
                "查看结果",
                key=f"open-latest-audit-{latest.job_id}",
                width="stretch",
            ):
                try:
                    on_open_audit(latest.audit_id)
                except RuntimeError as exc:
                    st.error(f"审计结果无法打开：{exc}")
                else:
                    st.rerun()


def _render_audit_task_list(
    jobs: list[AuditJob],
    on_open_audit: Callable[[str], None],
    on_submit: AuditSubmitCallback | None,
) -> None:
    active = [
        job
        for job in jobs
        if job.status in {AuditJobStatus.QUEUED, AuditJobStatus.RUNNING}
    ]
    visible = [*active, *[job for job in jobs if job not in active][:3]]
    if not visible:
        st.caption("当前没有审计任务。")
        return
    for index, job in enumerate(visible):
        if index:
            st.divider()
        _render_task_item(
            job,
            on_open_audit=on_open_audit,
            on_submit=on_submit,
            key_suffix="menu",
        )


def _render_audit_history(
    records: list[AuditRecordMetadata],
    on_open_audit: Callable[[str], None],
) -> None:
    if not records:
        st.caption("尚无已保存的审计记录。")
        return
    for index, record in enumerate(records):
        if index:
            st.divider()
        score = "未评分" if record.total_score is None else f"{record.total_score:.0f} 分"
        st.markdown(
            f"**{escape(record.source_label)}**  \n"
            f"{_local_time(record.created_at)} · {escape(record.grade)} · {score}"
        )
        st.caption(
            f"覆盖率 {record.audit_coverage:.0f}% · 严重 {record.critical_count} · "
            f"高风险 {record.high_count}"
        )
        if st.button(
            "查看",
            key=f"open-audit-record-{record.audit_id}",
            width="stretch",
        ):
            try:
                on_open_audit(record.audit_id)
            except RuntimeError as exc:
                st.error(f"审计记录无法打开：{exc}")
            else:
                st.rerun()


def render_learning_workspace(
    report: LearningReport,
    pdf_bytes: bytes,
    paper: ParsedPaper | None = None,
    qa_service: AuditService | None = None,
    codebase: ParsedCodebase | None = None,
    code_service: CodeLearningService | None = None,
    submit_audit_job: AuditSubmitCallback | None = None,
    load_audit_jobs: Callable[[], list[AuditJob]] | None = None,
    load_audit_records: Callable[[], list[AuditRecordMetadata]] | None = None,
    on_open_audit: Callable[[str], None] | None = None,
) -> None:
    if paper is not None:
        report = refresh_learning_report_evidence(report, paper)
    if st.session_state.pop("learning_switch_to_qa", False):
        st.session_state["learning_workspace_mode"] = "code" if codebase is not None else "qa"
    workspace_options = ["lecture", "code"] if codebase is not None else ["lecture", "qa"]
    workspace_labels = (
        {
            "lecture": "论文讲解",
            "code": "论文与代码",
            "qa": "内容追问",
        }
        if codebase is not None
        else {"lecture": "论文讲解", "qa": "论文追问"}
    )
    if codebase is not None and st.session_state.get("learning_workspace_mode") == "qa":
        st.session_state["learning_workspace_mode"] = "code"
    if st.session_state.get("learning_workspace_mode") not in workspace_options:
        st.session_state["learning_workspace_mode"] = "lecture"

    with st.container(key="learning_primary_nav"):
        header_left, header_mode, header_right = st.columns(
            [4.5, 2.8, 1], vertical_alignment="center"
        )
        with header_left:
            st.markdown(
                f'<div class="pa-workspace-header">'
                f'<div class="pa-workspace-brand-icon" aria-hidden="true">▤</div>'
                f'<div class="pa-workspace-copy"><div class="pa-workspace-title-row">'
                f'<div class="pa-workspace-title">{escape(report.paper_title)}</div>'
                f'<div class="pa-workspace-summary" title="{escape(report.one_sentence_summary)}">'
                f'{escape(report.one_sentence_summary)}</div></div></div></div>',
                unsafe_allow_html=True,
            )
        with header_mode:
            workspace_mode = st.segmented_control(
                "学习工作区",
                workspace_options,
                format_func=workspace_labels.get,
                key="learning_workspace_mode",
                required=True,
                label_visibility="collapsed",
                width="stretch",
            )
        with header_right:
            with st.popover("报告操作", width="stretch"):
                if codebase is None or workspace_mode == "lecture":
                    focus_pdf = st.toggle(
                        "专注 PDF",
                        key="learning_pdf_focus",
                        help="临时隐藏讲解或对话侧栏，让 PDF 占满工作区。",
                    )
                else:
                    focus_pdf = False
                if report.suggested_pages:
                    st.caption(
                        "建议重点阅读：第 "
                        + "、".join(map(str, report.suggested_pages))
                        + " 页"
                    )
                if st.button(
                    "审计本讲解",
                    type="primary",
                    width="stretch",
                    disabled=submit_audit_job is None or paper is None,
                    help="使用当前论文原文检查这份讲解中的事实论断。",
                ) and submit_audit_job is not None:
                    try:
                        job = submit_audit_job(
                            render_learning_markdown(report),
                            "generated_learning_report",
                            "当前论文讲解",
                            None,
                            list(_LEARNING_AUDIT_SCOPE),
                            "audit_generated",
                        )
                    except (ValueError, RuntimeError) as exc:
                        st.error(f"任务提交失败：{exc}")
                    else:
                        st.session_state["audit_submit_notice"] = (
                            f"“{job.source_label}”已提交后台审计，可继续阅读论文。"
                        )
                        st.rerun()
                if st.button(
                    "审计其他报告…",
                    width="stretch",
                    disabled=submit_audit_job is None or paper is None,
                    help="上传 .txt / .md / .pptx 或粘贴另一份报告，使用当前论文原文审计。",
                ) and submit_audit_job is not None:
                    render_report_audit_dialog(submit_audit_job)
                if submit_audit_job is None:
                    st.caption("配置并连接 Hy3 API 后可审计当前讲解。")
                jobs: list[AuditJob] = []
                records: list[AuditRecordMetadata] = []
                if load_audit_jobs is not None:
                    try:
                        jobs = load_audit_jobs()
                    except RuntimeError as exc:
                        st.warning(f"审计任务无法读取：{exc}")
                if load_audit_records is not None:
                    try:
                        records = load_audit_records()
                    except RuntimeError as exc:
                        st.warning(f"审计记录无法读取：{exc}")
                active_job_count = sum(
                    job.status in {AuditJobStatus.QUEUED, AuditJobStatus.RUNNING}
                    for job in jobs
                )
                if jobs:
                    task_label = (
                        f"进行中的审计（{active_job_count}）"
                        if active_job_count
                        else "审计任务"
                    )
                    with st.expander(task_label, expanded=bool(active_job_count)):
                        if on_open_audit is not None:
                            _render_audit_task_list(
                                jobs,
                                on_open_audit,
                                submit_audit_job,
                            )
                        else:
                            st.caption("当前没有可用的论文项目。")
                if records:
                    with st.expander(f"审计记录（{len(records)}）", expanded=False):
                        if on_open_audit is not None:
                            _render_audit_history(records, on_open_audit)
                        else:
                            st.caption("当前没有可用的论文项目。")
                if not jobs and not records:
                    st.markdown(
                        '<div class="pa-audit-empty-note"><strong>暂无审计记录</strong></div>',
                        unsafe_allow_html=True,
                    )
                st.divider()
                st.caption("导出讲解")
                markdown_col, json_col = st.columns(2)
                markdown_col.download_button(
                    "Markdown",
                    render_learning_markdown(report),
                    file_name="paper-learning-report.md",
                    mime="text/markdown",
                    width="stretch",
                )
                json_col.download_button(
                    "JSON",
                    report.model_dump_json(indent=2),
                    file_name="paper-learning-report.json",
                    mime="application/json",
                    width="stretch",
                )
                if st.button("更换论文并返回", type="tertiary", width="stretch"):
                    for state_key in (
                    "learning_report",
                    "learning_pdf_bytes",
                    "learning_paper",
                    "result_mode",
                    "learning_selected_evidence",
                    "learning_evidence_group",
                    "learning_evidence_section",
                    "learning_active_section",
                    "learning_active_point",
                    "learning_pdf_page",
                    "learning_pdf_zoom",
                    "learning_pdf_anchor_sync",
                    "learning_focus_evidence",
                    "qa_selected_evidence",
                    "qa_evidence_group",
                    "qa_pdf_page",
                    "qa_pdf_zoom",
                    "qa_pdf_anchor_sync",
                    "qa_focus_evidence",
                    "paper_qa_history",
                    "paper_text_selection",
                    "learning_workspace_mode",
                    "learning_switch_to_qa",
                    "learning_pdf_focus",
                    "learning_explanation_scope",
                    "parsed_codebase",
                    "code_parse_warning",
                    "joint_qa_history",
                    "joint_qa_pending",
                    "joint_paper_selection",
                    "joint_active_paper_citation",
                    "joint_active_code_citation",
                    "joint_code_selection",
                    "joint_code_path",
                    "joint_code_path_pending",
                    "joint_code_rendered_path",
                    "joint_pdf_page",
                    "joint_layout_mode",
                    "joint_layout_mode_pending",
                    "active_project_id",
                    "project_original_filename",
                    "project_save_error",
                    "paper_pdf_upload",
                    "source_code_upload",
                    ):
                        st.session_state.pop(state_key, None)
                    st.query_params.pop("project", None)
                    st.rerun()
    notice = st.session_state.pop("audit_submit_notice", None)
    if notice:
        st.success(str(notice))
    if load_audit_jobs is not None and on_open_audit is not None:
        _render_audit_activity(load_audit_jobs, on_open_audit)
    if workspace_mode == "lecture":
        _render_report_tab(
            report,
            pdf_bytes,
            paper,
            focus_pdf,
            question_available=(
                code_service is not None if codebase is not None else qa_service is not None
            ),
            joint_questions=codebase is not None,
        )
    elif workspace_mode == "code" and paper is not None and codebase is not None:
        render_code_workspace(
            paper,
            pdf_bytes,
            codebase,
            code_service,
        )
    else:
        _render_qa_tab(paper, pdf_bytes, qa_service, focus_pdf)
