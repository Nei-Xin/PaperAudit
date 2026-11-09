"""Rendering for the report-audit result workspace."""

from __future__ import annotations

from collections.abc import Mapping
from hashlib import sha256
from html import escape

import streamlit as st

from paperaudit.models import (
    AuditRun,
    AutoLabel,
    ClaimCategory,
    EvidenceAnchor,
    ParsedPaper,
    Severity,
)
from paperaudit.reporting import SKIP_REASON_LABELS, render_markdown
from paperaudit.evidence import refresh_evidence_anchors
from paperaudit.ui.components import (
    audit_evidence_label,
    render_audit_detail,
    render_audit_summary,
    render_audit_summary_details,
)
from paperaudit.ui.pdf_selector import render_selectable_pdf_page
from paperaudit.ui.audit_view import (
    QUICK_ALL,
    QUICK_ATTENTION,
    SORT_REPORT,
    SORT_RISK,
    audit_counts,
    compact_claim_text,
    filter_audits,
    selected_evidence,
    sort_audits,
)
from paperaudit.ui.visualizations import render_dimension_radar_or_bar
from paperaudit.ui.investigation import render_investigation


_FILTER_ALL = "all"
_FILTER_ATTENTION = "attention"
_PAGE_SIZE = 8


@st.dialog("审计证据原文", width="large")
def _show_audit_evidence(pdf_bytes: bytes, anchor: EvidenceAnchor) -> None:
    st.caption(audit_evidence_label(anchor))
    if anchor.page is None:
        st.error("该证据缺少有效页码，无法打开 PDF。")
        return
    render_selectable_pdf_page(
        pdf_bytes,
        anchor.page,
        anchor.rects,
        key=f"audit-evidence-pdf-{anchor.chunk_id}-{anchor.page}",
        selection_enabled=False,
        zoom_percent=120,
        focus_highlight=bool(anchor.rects),
    )


def _audit_evidence_anchors(
    run: AuditRun,
    paper: ParsedPaper | None,
) -> dict[str, EvidenceAnchor]:
    anchors: dict[str, EvidenceAnchor] = {}
    for audit in run.audits:
        for candidate in selected_evidence(audit):
            anchors.setdefault(
                candidate.chunk_id,
                EvidenceAnchor(
                    chunk_id=candidate.chunk_id,
                    page=candidate.page,
                    text=candidate.text,
                ),
            )
    if paper is None:
        return anchors
    refreshed = refresh_evidence_anchors(list(anchors.values()), paper)
    anchors.update({anchor.chunk_id: anchor for anchor in refreshed})
    return anchors


def _audit_run_key(run: AuditRun) -> str:
    judgments = "|".join(
        f"{audit.claim.claim_id}:{audit.judgment.label.value}:"
        f"{audit.judgment.severity.value}"
        for audit in run.audits
    )
    source = f"{run.paper_title}\0{run.report_text}\0{judgments}"
    return sha256(source.encode("utf-8")).hexdigest()[:12]


def _reset_audit_filters(
    category_key: str,
    severity_key: str,
    status_key: str,
    search_key: str,
    sort_key: str,
    page_key: str,
) -> None:
    st.session_state[category_key] = _FILTER_ALL
    st.session_state[severity_key] = _FILTER_ALL
    st.session_state[status_key] = _FILTER_ALL
    st.session_state[search_key] = ""
    st.session_state[sort_key] = SORT_RISK
    st.session_state[page_key] = 1


def _select_audit_claim(selection_key: str, claim_id: str, page_key: str, page: int) -> None:
    st.session_state[selection_key] = claim_id
    st.session_state[page_key] = page


def render_audit_results(
    run: AuditRun,
    category_labels: Mapping[ClaimCategory, str],
    label_names: Mapping[AutoLabel, str],
    severity_names: Mapping[Severity, str],
    dimension_names: Mapping[str, str],
    *,
    show_return_to_learning: bool = False,
    paper: ParsedPaper | None = None,
    pdf_bytes: bytes | None = None,
) -> bool:
    """Render one audit run and return whether the user requested the learning view."""

    if show_return_to_learning and st.button("← 返回论文讲解", key="audit_return_learning"):
        return True

    evidence_anchors = _audit_evidence_anchors(run, paper)

    # Only the score strip stays above the work area; metric definitions,
    # deep-audit and extraction notes live in the 统计与核对 tab.
    render_audit_summary(run.summary, run.audits, show_details=False)
    tab_audit, tab_dimensions, tab_report = st.tabs(
        ["逐条审计", "统计与核对", "报告导出"]
    )

    with tab_audit:
        counts = audit_counts(run.audits)
        default_status = _FILTER_ALL
        run_key = _audit_run_key(run)
        category_key = f"audit_category_filter_{run_key}"
        severity_key = f"audit_severity_filter_{run_key}"
        status_key = f"audit_status_filter_v2_{run_key}"
        search_key = f"audit_search_query_{run_key}"
        sort_key = f"audit_sort_mode_{run_key}"
        page_key = f"audit_page_{run_key}"
        selection_key = f"audit_selected_claim_{run_key}"
        st.session_state.setdefault(status_key, default_status)
        st.session_state.setdefault(page_key, 1)

        with st.container(key="audit_advanced_filters"):
            search_col, status_col, more_col = st.columns(
                [3, 1.2, 0.8], vertical_alignment="bottom"
            )
            more_filters = more_col.popover("更多筛选", icon=":material/tune:", width="stretch")
            filter_col = severity_col = sort_col = more_filters
            search_query = search_col.text_input(
                "搜索",
                placeholder="搜索论断、证据或内容…",
                key=search_key,
                label_visibility="collapsed",
            )
            category = filter_col.selectbox(
                "分类",
                [_FILTER_ALL, *category_labels.keys()],
                format_func=lambda value: (
                    "全部分类"
                    if value == _FILTER_ALL
                    else category_labels.get(value, "其他")
                ),
                key=category_key,
            )
            severity = severity_col.selectbox(
                "风险",
                [
                    _FILTER_ALL,
                    Severity.CRITICAL,
                    Severity.HIGH,
                    Severity.MEDIUM,
                    Severity.LOW,
                    Severity.NONE,
                ],
                format_func=lambda value: (
                    "全部风险" if value == _FILTER_ALL else severity_names[value]
                ),
                key=severity_key,
            )
            status = status_col.selectbox(
                "状态",
                [_FILTER_ATTENTION, _FILTER_ALL, *AutoLabel],
                format_func=lambda value: (
                    "需关注"
                    if value == _FILTER_ATTENTION
                    else "全部状态"
                    if value == _FILTER_ALL
                    else label_names[value]
                ),
                key=status_key,
                label_visibility="collapsed",
            )
            sort_mode = sort_col.selectbox(
                "排序",
                [SORT_RISK, SORT_REPORT],
                format_func=lambda value: (
                    "风险优先" if value == SORT_RISK else "报告顺序"
                ),
                key=sort_key,
            )

        filtered_audits = filter_audits(
            run.audits,
            quick_filter=(
                QUICK_ATTENTION if status == _FILTER_ATTENTION else QUICK_ALL
            ),
            category=None if category == _FILTER_ALL else category,
            severity=None if severity == _FILTER_ALL else severity,
            search_query=search_query,
        )
        if isinstance(status, AutoLabel):
            filtered_audits = [
                audit for audit in filtered_audits if audit.judgment.label == status
            ]
        filtered_audits = sort_audits(filtered_audits, sort_mode)

        if not filtered_audits:
            st.markdown(
                '<div class="pa-audit-empty"><strong>当前筛选条件下没有论断</strong>'
                '<span>可以清除筛选后查看完整审计结果。</span></div>',
                unsafe_allow_html=True,
            )
            st.button(
                "清除筛选",
                key=f"audit_clear_filters_{run_key}",
                on_click=_reset_audit_filters,
                args=(
                    category_key,
                    severity_key,
                    status_key,
                    search_key,
                    sort_key,
                    page_key,
                ),
            )
        else:
            page_count = max(1, (len(filtered_audits) + _PAGE_SIZE - 1) // _PAGE_SIZE)
            current_page = min(max(int(st.session_state[page_key]), 1), page_count)
            st.session_state[page_key] = current_page
            filtered_ids = [audit.claim.claim_id for audit in filtered_audits]
            selected_id = st.session_state.get(selection_key)
            if selected_id not in filtered_ids:
                selected_id = filtered_ids[0]
                st.session_state[selection_key] = selected_id
            selected_index = filtered_ids.index(selected_id)
            selected_page = selected_index // _PAGE_SIZE + 1
            if selected_page != current_page:
                current_page = selected_page
                st.session_state[page_key] = current_page
            start = (current_page - 1) * _PAGE_SIZE
            visible_audits = filtered_audits[start : start + _PAGE_SIZE]
            selected_audit = filtered_audits[selected_index]

            source_key = f"audit_source_chunk_{run_key}"
            if pdf_bytes:
                list_col, detail_col, source_col = st.columns([0.27, 0.43, 0.30], gap="small")
            else:
                list_col, detail_col = st.columns([0.32, 0.68], gap="small")
                source_col = None
            with list_col, st.container(key="audit_list_card"):
                st.markdown(
                    f'<div class="pa-audit-list-title"><strong>论断</strong>'
                    f'<span>{len(filtered_audits)} 条 · 需关注 {counts[QUICK_ATTENTION]}</span></div>',
                    unsafe_allow_html=True,
                )
                for audit in visible_audits:
                    is_selected = audit.claim.claim_id == selected_id
                    item_key = (
                        f"audit_claim_item_active_{audit.claim.claim_id}"
                        if is_selected
                        else f"audit_claim_item_{audit.claim.claim_id}"
                    )
                    with st.container(key=item_key):
                        # One HTML block draws the whole row; a transparent button
                        # stretched over it (CSS) makes the row clickable. Splitting
                        # text and meta into separate widgets let the highlight
                        # box end mid-row.
                        st.markdown(
                            f'<div class="pa-row-body">'
                            f'<div class="pa-row-title">{escape(audit.claim.text)}</div>'
                            f'<div class="pa-audit-row-meta">'
                            f'<span class="pa-label-dot label-{audit.judgment.label.value.lower()}"></span>'
                            f'{escape(audit.claim.claim_id)} · {label_names[audit.judgment.label]}'
                            f' · {severity_names[audit.judgment.severity]}</div></div>',
                            unsafe_allow_html=True,
                        )
                        st.button(
                            compact_claim_text(audit.claim.text, 70),
                            key=f"select_audit_claim_{run_key}_{audit.claim.claim_id}",
                            width="stretch",
                            type="tertiary",
                            on_click=_select_audit_claim,
                            args=(selection_key, audit.claim.claim_id, page_key, current_page),
                        )
                if page_count > 1:
                    _, prev_page, page_label, next_page, _ = st.columns([0.6, 0.5, 0.8, 0.5, 0.6])
                    prev_page.button(
                        ":material/chevron_left:",
                        disabled=current_page <= 1,
                        type="tertiary",
                        key=f"audit_page_prev_{run_key}",
                        on_click=_select_audit_claim,
                        args=(
                            selection_key,
                            filtered_audits[max(0, start - _PAGE_SIZE)].claim.claim_id,
                            page_key,
                            current_page - 1,
                        ),
                    )
                    page_label.markdown(
                        f'<div class="pa-audit-page-label">{current_page} / {page_count}</div>',
                        unsafe_allow_html=True,
                    )
                    next_page.button(
                        ":material/chevron_right:",
                        disabled=current_page >= page_count,
                        type="tertiary",
                        key=f"audit_page_next_{run_key}",
                        on_click=_select_audit_claim,
                        args=(
                            selection_key,
                            filtered_audits[min(len(filtered_audits) - 1, start + _PAGE_SIZE)].claim.claim_id,
                            page_key,
                            current_page + 1,
                        ),
                    )

            def open_source(anchor: EvidenceAnchor) -> None:
                # With a source card on screen, evidence opens there instead of a dialog.
                st.session_state[source_key] = anchor.chunk_id
                st.rerun()

            with detail_col, st.container(key="audit_detail_card"):
                with st.container(key="audit_detail_navigation"):
                    position_col, previous_col, next_col = st.columns(
                        [4, 0.5, 0.5], vertical_alignment="center", gap="small"
                    )
                    position_col.markdown(
                        f'<div class="pa-audit-position">论断 {selected_index + 1} / {len(filtered_audits)}</div>',
                        unsafe_allow_html=True,
                    )
                    previous_col.button(
                        ":material/arrow_upward:",
                        help="上一条",
                        disabled=selected_index == 0,
                        type="tertiary",
                        key=f"audit_claim_prev_{run_key}",
                        on_click=_select_audit_claim,
                        args=(
                            selection_key,
                            filtered_audits[max(0, selected_index - 1)].claim.claim_id,
                            page_key,
                            max(1, (selected_index - 1) // _PAGE_SIZE + 1),
                        ),
                    )
                    next_col.button(
                        ":material/arrow_downward:",
                        help="下一条",
                        disabled=selected_index >= len(filtered_audits) - 1,
                        type="tertiary",
                        key=f"audit_claim_next_{run_key}",
                        on_click=_select_audit_claim,
                        args=(
                            selection_key,
                            filtered_audits[
                                min(len(filtered_audits) - 1, selected_index + 1)
                            ].claim.claim_id,
                            page_key,
                            min(page_count, (selected_index + 1) // _PAGE_SIZE + 1),
                        ),
                    )
                with st.container(key="audit_selected_detail"):
                    render_investigation(selected_audit)
                    render_audit_detail(
                        selected_audit,
                        category_labels.get(selected_audit.claim.category, "其他"),
                        evidence_anchors=evidence_anchors,
                        on_open_evidence=(
                            open_source if source_col is not None
                            else (lambda anchor: _show_audit_evidence(pdf_bytes, anchor))
                            if pdf_bytes
                            else None
                        ),
                    )

            if source_col is not None:
                with source_col, st.container(key="audit_source_card"):
                    claim_chunks = [candidate.chunk_id for candidate in selected_evidence(selected_audit)]
                    chosen = st.session_state.get(source_key)
                    if chosen not in claim_chunks:
                        chosen = claim_chunks[0] if claim_chunks else None
                    anchor = evidence_anchors.get(chosen) if chosen else None
                    if anchor is None or anchor.page is None:
                        st.markdown(
                            '<div class="pa-audit-source-empty">这条论断没有可定位的原文证据。</div>',
                            unsafe_allow_html=True,
                        )
                    else:
                        st.markdown(
                            f'<div class="pa-audit-source-head">原文 · 第 {anchor.page} 页</div>',
                            unsafe_allow_html=True,
                        )
                        render_selectable_pdf_page(
                            pdf_bytes,
                            anchor.page,
                            anchor.rects,
                            key=f"audit-source-{run_key}-{anchor.chunk_id}",
                            selection_enabled=False,
                            zoom_percent=100,
                            focus_highlight=bool(anchor.rects),
                            fit_scale=1.0,
                        )

    with tab_dimensions:
        render_audit_summary_details(run.summary, run.audits)
        if run.deep_audit:
            st.caption(f"本次使用深度核验 · {sum(a.investigation is not None for a in run.audits)} 条论断启动调查")
        if run.source_count:
            with st.expander(f"原文抽取核对 · {run.source_count} 句 · {len(run.skipped_sources)} 句未抽取"):
                st.caption("已核对每句均有返回。模型跳过的内容列在下方；句内是否漏掉事实仍需结合原文复核。")
                for source in run.skipped_sources:
                    st.text(f"{source.report_location} · {SKIP_REASON_LABELS[source.reason]}\n{source.text}")
        dim_left, dim_right = st.columns([1.4, 1])
        with dim_left:
            st.markdown("**六维评估体系得分**")
            render_dimension_radar_or_bar(
                run.summary.dimensions.model_dump(), dimension_names
            )
        with dim_right:
            st.markdown("**风险问题统计**")
            r_col1, r_col2, r_col3 = st.columns(3)
            r_col1.metric("严重问题", run.summary.critical_count)
            r_col2.metric("高风险", run.summary.high_count)
            r_col3.metric("中风险", run.summary.medium_count)
            for warning in run.parse_warnings:
                st.warning(warning)

    with tab_report:
        st.markdown("**导出完整审计报告**")
        markdown_report = render_markdown(run)
        d_col1, d_col2 = st.columns(2)
        d_col1.download_button(
            "下载 Markdown 报告",
            markdown_report,
            file_name="paperaudit-report.md",
            mime="text/markdown",
            width="stretch",
        )
        d_col2.download_button(
            "下载 JSON 结果",
            run.model_dump_json(indent=2),
            file_name="paperaudit-result.json",
            mime="application/json",
            width="stretch",
        )
        with st.expander("预览 Markdown 报告内容"):
            st.code(markdown_report, language="markdown")

    return False
