"""UI for the simulated peer-review report."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from html import escape
import re

import streamlit as st

from paperaudit.models import (
    AuditJobStatus,
    PeerReviewRevisionJob,
    EvidenceAnchor,
    PeerReviewReport,
    PeerReviewRevision,
    PeerReviewVenue,
    IssueCategory,
    IssueSeverity,
    IssueStatus,
    IssueSupportType,
    HumanReviewDecision,
    RelatedWorkReference,
    ReviewConcern,
    ReviewDecision,
)
from paperaudit.ui.pdf_selector import get_pdf_page_count, render_selectable_pdf_page


_DIMENSION_LABELS = {
    "significance": "研究价值",
    "novelty": "创新性",
    "soundness": "技术可靠性",
    "experimental_rigor": "实验充分性",
    "clarity": "表达清晰度",
    "reproducibility": "可复现性",
}

_DECISION_LABELS = {
    ReviewDecision.STRONG_ACCEPT: ("Strong Accept", "强接收", "strong-accept"),
    ReviewDecision.WEAK_ACCEPT: ("Weak Accept", "弱接收", "weak-accept"),
    ReviewDecision.BORDERLINE: ("Borderline", "边缘", "borderline"),
    ReviewDecision.WEAK_REJECT: ("Weak Reject", "弱拒稿", "weak-reject"),
    ReviewDecision.STRONG_REJECT: ("Strong Reject", "强拒稿", "strong-reject"),
}

_VENUE_LABELS = {
    PeerReviewVenue.GENERAL: "通用 AI/ML",
    PeerReviewVenue.IJCAI: "IJCAI",
    PeerReviewVenue.NEURIPS: "NeurIPS",
    PeerReviewVenue.ICLR: "ICLR",
    PeerReviewVenue.AAAI: "AAAI",
    PeerReviewVenue.CUSTOM: "自定义标准",
}

_ISSUE_CATEGORY_LABELS = {
    IssueCategory.CORRECTNESS: "技术正确性",
    IssueCategory.EVIDENCE: "证据与主张",
    IssueCategory.EVALUATION: "实验与比较",
    IssueCategory.NOVELTY: "创新性与相关工作",
    IssueCategory.REPRODUCIBILITY: "可复现性",
    IssueCategory.ETHICS: "伦理与合规",
    IssueCategory.CLARITY: "表达与结构",
    IssueCategory.OTHER: "其他",
}
_ISSUE_STATUS_LABELS = {
    IssueStatus.OPEN: "待处理",
    IssueStatus.AUTHOR_REPLIED: "已回复",
    IssueStatus.PARTIAL: "部分解决",
    IssueStatus.RESOLVED: "已解决",
    IssueStatus.UNRESOLVED: "未解决",
    IssueStatus.NEEDS_REVIEW: "需人工复核",
    IssueStatus.IGNORED: "已忽略",
}
_HUMAN_DECISION_LABELS = {
    HumanReviewDecision.UNREVIEWED: "未复核",
    HumanReviewDecision.CONFIRMED: "确认问题",
    HumanReviewDecision.PARTIAL: "部分成立",
    HumanReviewDecision.FALSE_POSITIVE: "误报",
    HumanReviewDecision.INSUFFICIENT_EVIDENCE: "证据不足",
}
_SUPPORT_TYPE_LABELS = {
    IssueSupportType.FACT: "事实",
    IssueSupportType.INFERENCE: "推断",
    IssueSupportType.INSUFFICIENT_EVIDENCE: "证据不足",
}


def _severity_for(concern: ReviewConcern) -> IssueSeverity:
    return concern.severity_level or (
        IssueSeverity.MAJOR if concern.severity.value == "major" else IssueSeverity.MINOR
    )


def _main_rejection_risk(report: PeerReviewReport) -> str:
    concerns = [*report.major_concerns, *report.minor_concerns]
    ranked = sorted(
        concerns,
        key=lambda item: list(IssueSeverity).index(_severity_for(item)),
    )
    titles = [item.title.strip() for item in ranked if item.title.strip()][:3]
    if not titles:
        titles = [item.strip() for item in report.acceptance_blockers if item.strip()][:3]
    if titles:
        return "、".join(titles)[:100]
    return report.summary.strip()[:100]


def _strength_title(text: str, index: int) -> str:
    normalized = text.strip()
    for separator in ("：", ":", "，", ",", "。", ";", "；"):
        prefix = normalized.split(separator, 1)[0].strip()
        if 3 <= len(prefix) <= 18:
            return prefix
    return normalized[:16].rstrip() or f"优势 {index}"


def _suggestion_checklist(text: str) -> list[str]:
    """Turn one model suggestion into a compact, meaning-preserving checklist."""
    normalized = " ".join(text.strip().split())
    if not normalized:
        return []
    clauses = [part.strip(" ，,；;。.") for part in re.split(r"[；;]", normalized) if part.strip(" ，,；;。.")]
    items: list[str] = []
    for clause in clauses:
        if "包括" in clause:
            lead, details = clause.split("包括", 1)
            lead = lead.strip(" ，,、")
            if lead:
                items.append(lead)
            details = re.sub(r"并报告", "", details).strip(" ，,、")
            details = re.sub(r"、(?=[^、]+$)", "、", details)
            for item in re.split(r"、|，|,", details):
                item = item.strip(" ，,、")
                if item:
                    items.append(item)
        else:
            items.append(clause)
    # Keep the important fallback action visible instead of dropping it when
    # the model lists many experiment details.
    fallback = next((clause for clause in clauses[1:] if clause.startswith(("若", "如果"))), "")
    if fallback and fallback not in items:
        if items:
            items[0] = f"{items[0]}；{fallback}"
        else:
            items.append(fallback)
    # Keep the fallback readable when a model returns a single long sentence.
    if len(items) == 1 and len(items[0]) > 42:
        items = [part.strip(" ，,、") for part in re.split(r"，|,", items[0]) if part.strip(" ，,、")]
    visible = items[:6]
    if fallback and fallback not in visible:
        if visible:
            visible[-1] = fallback
        else:
            visible.append(fallback)
    return visible

@st.dialog("评审依据原文", width="large")
def _show_evidence(pdf_bytes: bytes, anchor: EvidenceAnchor) -> None:
    if anchor.page is None:
        st.error("该评审意见没有有效页码。")
        return
    st.caption(f"第 {anchor.page} 页 · {anchor.locator or anchor.chunk_id}")
    render_selectable_pdf_page(
        pdf_bytes,
        anchor.page,
        anchor.rects,
        key=f"peer-review-{anchor.chunk_id}-{anchor.page}",
        selection_enabled=False,
        zoom_percent=120,
        focus_highlight=bool(anchor.rects),
    )


def _evidence_buttons(
    anchors: Sequence[EvidenceAnchor],
    pdf_bytes: bytes | None,
    key: str,
    *,
    issue_title: str = "",
) -> None:
    unique: list[EvidenceAnchor] = []
    seen: set[tuple[int | None, str]] = set()
    for anchor in anchors:
        anchor_key = (anchor.page, anchor.chunk_id)
        if anchor_key in seen:
            continue
        seen.add(anchor_key)
        unique.append(anchor)
    if not unique:
        return
    with st.container(key=f"{key}-evidence-actions"):
        button_cols = st.columns(min(len(unique[:2]), 2), gap="small")
        for index, anchor in enumerate(unique[:2]):
            label = f"定位原文 · 第 {anchor.page} 页" if anchor.page else "查看依据"
            if pdf_bytes and button_cols[index].button(label, key=f"{key}-{index}", type="secondary"):
                st.session_state["peer_review_pdf_focus"] = {
                    "page": anchor.page,
                    "rects": anchor.rects,
                    "issue_title": issue_title,
                    "locator": anchor.locator or anchor.chunk_id,
                }
                st.rerun()
            if anchor.quote and index == 0:
                st.caption(f"“{anchor.quote}”")


def _render_concern(concern: ReviewConcern, pdf_bytes: bytes | None, key: str) -> None:
    severity = _severity_for(concern)
    st.markdown(
        f'<div class="pa-peer-concern-head severity-{severity.value.lower()}">'
        f'<span class="pa-peer-severity-badge">{escape(severity.value)}</span>'
        f'<span class="pa-peer-category-inline">{escape(_ISSUE_CATEGORY_LABELS.get(concern.category, "其他"))}</span>'
        f'<span class="pa-peer-title-separator">·</span>'
        f'<strong>{escape(concern.title)}</strong>'
        f'<span class="pa-peer-status-badge">{escape(_ISSUE_STATUS_LABELS.get(concern.status, concern.status.value))}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
    if concern.evidence:
        st.caption(f"已绑定 {len(concern.evidence)} 条原文依据，可点击下方按钮定位。")
    else:
        st.caption("证据不足 · 当前判断需人工复核")
    st.markdown('<div class="pa-peer-subsection-label">问题说明</div>', unsafe_allow_html=True)
    st.write(concern.description)
    st.markdown(
        f'<div class="pa-peer-metadata">类别：{escape(_ISSUE_CATEGORY_LABELS.get(concern.category, "其他"))}'
        f'<span>置信度：{concern.confidence} / 5</span><span>判断类型：{escape(concern.support_type.value)}</span>'
        f'<em>{escape(_ISSUE_STATUS_LABELS.get(concern.status, concern.status.value))}</em></div>',
        unsafe_allow_html=True,
    )
    ai_level = concern.ai_severity_level or _severity_for(concern)
    ai_category = concern.ai_category or concern.category
    if ai_level != _severity_for(concern) or ai_category != concern.category:
        st.caption(
            f"AI 原始判断：{ai_level.value} · {_ISSUE_CATEGORY_LABELS.get(ai_category, '其他')}；"
            "当前值为用户修订结果。"
        )
    st.markdown('<div class="pa-peer-subsection-label pa-peer-subsection-muted">为什么重要</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="pa-peer-why-text">{escape(concern.why_it_matters)}</div>',
        unsafe_allow_html=True,
    )
    checklist = _suggestion_checklist(concern.suggestion)
    checklist_html = "".join(f'<li>□ {escape(item)}</li>' for item in checklist)
    st.markdown(
        f'<div class="pa-peer-action-callout"><strong>修改任务</strong>'
        f'<ul>{checklist_html}</ul></div>',
        unsafe_allow_html=True,
    )
    # One primary evidence action per issue keeps the operation row unambiguous.
    _evidence_buttons(concern.evidence[:1], pdf_bytes, key, issue_title=concern.title)


def _manual_review_controls(
    report: PeerReviewReport,
    concern: ReviewConcern,
    key: str,
    on_update_report: Callable[[PeerReviewReport], object] | None,
) -> None:
    with st.expander("人工复核（可选）", expanded=concern.status is IssueStatus.NEEDS_REVIEW):
        severity_values = list(IssueSeverity)
        category_values = list(IssueCategory)
        severity = st.selectbox(
            "确认严重度", severity_values,
            index=severity_values.index(_severity_for(concern)),
            format_func=lambda item: item.value,
            key=f"{key}-manual-severity",
        )
        category = st.selectbox(
            "确认类别", category_values,
            index=category_values.index(concern.category),
            format_func=lambda item: _ISSUE_CATEGORY_LABELS.get(item, item.value),
            key=f"{key}-manual-category",
        )
        status_values = list(IssueStatus)
        status = st.selectbox(
            "处理状态", status_values,
            index=status_values.index(concern.status),
            format_func=lambda item: _ISSUE_STATUS_LABELS.get(item, item.value),
            key=f"{key}-manual-status",
        )
        support_values = list(IssueSupportType)
        support_type = st.selectbox(
            "证据判断", support_values,
            index=support_values.index(concern.support_type),
            format_func=lambda item: _SUPPORT_TYPE_LABELS.get(item, item.value),
            key=f"{key}-manual-support",
        )
        decision_values = list(HumanReviewDecision)
        human_decision = st.selectbox(
            "人工结论", decision_values,
            index=decision_values.index(concern.human_decision),
            format_func=lambda item: _HUMAN_DECISION_LABELS[item],
            key=f"{key}-manual-decision",
        )
        reviewed = st.checkbox("已人工确认", value=concern.human_reviewed, key=f"{key}-manual-reviewed")
        note = st.text_area("复核备注", value=concern.human_note, key=f"{key}-manual-note", height=70)
        if st.button("保存人工修订", key=f"{key}-manual-save", disabled=on_update_report is None):
            updated = concern.model_copy(update={
                "severity_level": severity,
                "category": category,
                "status": status,
                "support_type": support_type,
                "human_decision": human_decision,
                "human_reviewed": reviewed,
                "human_note": note.strip(),
            })
            target_key = concern.issue_id or concern.title
            concerns = [
                updated if (item.issue_id or item.title) == target_key else item
                for item in [*report.major_concerns, *report.minor_concerns]
            ]
            major = [item for item in concerns if item.severity.value == "major"]
            minor = [item for item in concerns if item.severity.value != "major"]
            next_report = report.model_copy(update={"major_concerns": major, "minor_concerns": minor})
            if on_update_report is not None:
                try:
                    on_update_report(next_report)
                except (OSError, RuntimeError, ValueError) as exc:
                    st.error(f"人工修订保存失败：{exc}")
                else:
                    st.success("人工修订已保存，AI 原始判断仍保留在记录中。")


def _render_submission_risks(report: PeerReviewReport, pdf_bytes: bytes | None) -> None:
    concerns = [*report.major_concerns, *report.minor_concerns]
    concerns.sort(key=lambda item: (list(IssueSeverity).index(_severity_for(item)), -item.confidence))
    st.markdown("### 投稿风险")
    if not concerns:
        st.info("当前评审没有生成结构化问题，请结合综合结论人工复核。")
        return
    for index, concern in enumerate(concerns[:4]):
        severity = _severity_for(concern)
        risk_class = "pa-peer-risk-high" if severity in {IssueSeverity.FATAL, IssueSeverity.MAJOR} else "pa-peer-risk-medium"
        confidence = "High" if concern.confidence >= 4 else "Medium" if concern.confidence >= 3 else "Low"
        # Keep the card and its evidence action in one bordered container. This
        # prevents Streamlit's adjacent blocks from pulling the button over the
        # card's lower border on narrower layouts.
        with st.container(border=True, key=f"peer-risk-card-{index}"):
            st.markdown(
                f'<div class="pa-peer-risk-card {risk_class}">'
                f'<div><strong>{escape(severity.value)} · {escape(concern.title)}</strong>'
                f'<span>{escape(confidence)}</span></div>'
                f'<p>{escape(concern.description)}</p>'
                f'<small>{len(concern.evidence)} 处证据 · {_ISSUE_STATUS_LABELS.get(concern.status, concern.status.value)}</small>'
                f'</div>',
                unsafe_allow_html=True,
            )
            _evidence_buttons(
                concern.evidence[:1],
                pdf_bytes,
                f"peer-risk-{index}",
                issue_title=concern.title,
            )
            if not concern.evidence:
                st.caption("需人工复核 · 当前判断没有可定位原文证据")


def _render_action_plan(report: PeerReviewReport) -> None:
    actions = list(report.top_priorities or report.required_changes)
    if not actions:
        actions = [
            concern.suggestion
            for concern in [*report.major_concerns, *report.minor_concerns]
            if concern.suggestion.strip()
        ][:3]
    if not actions:
        return
    done_count = sum(
        bool(st.session_state.get(f"peer-review-action-done-{report.paper_title}-{index}"))
        for index in range(min(len(actions), 5))
    )
    st.markdown(
        f'### 投稿前 Action Plan <span class="pa-peer-plan-progress">{done_count}/{min(len(actions), 5)} 已完成</span>',
        unsafe_allow_html=True,
    )
    for index, action in enumerate(actions[:5]):
        priority = "P0" if index < 2 else "P1"
        with st.container(key=f"peer-action-item-{index}"):
            action_col, check_col = st.columns([5.8, 1], vertical_alignment="center", gap="small")
            action_col.markdown(
                f'<div class="pa-peer-action-card"><div class="pa-peer-action-title">'
                f'<span class="pa-peer-action-priority priority-{priority.lower()}">{priority}</span>'
                f'<strong>修改任务 {index + 1}</strong></div>'
                f'<p>{escape(action)}</p></div>',
                unsafe_allow_html=True,
            )
            related = [
                concern.title
                for concern in [*report.major_concerns, *report.minor_concerns]
                if concern.suggestion.strip() == action.strip()
                or any(token in concern.suggestion for token in action.split()[:4] if len(token) >= 3)
            ][:3]
            if related:
                action_col.caption("关联问题：" + "、".join(dict.fromkeys(related)))
            check_col.checkbox(
                "完成",
                key=f"peer-review-action-done-{report.paper_title}-{index}",
                help="仅记录作者的内部修改进度，不表示 AI 已确认问题解决。",
            )


def _render_revision_jobs(
    load_jobs: Callable[[], Sequence[PeerReviewRevisionJob]] | None,
    was_active: bool,
) -> None:
    if load_jobs is None:
        return

    @st.fragment(run_every=2 if was_active else None)
    def status_panel() -> None:
        jobs = list(load_jobs())
        active = next((job for job in jobs if job.status in {
            AuditJobStatus.QUEUED, AuditJobStatus.RUNNING,
        }), None)
        if was_active and active is None:
            # Refresh saved revisions and unlock the uploader after completion.
            st.rerun()
        if active is not None:
            st.info(f"{active.original_filename} 正在后台复审，可继续阅读或切换项目。")
            st.progress(active.progress, text=active.stage)
        failed = next((job for job in jobs if job.status in {
            AuditJobStatus.FAILED, AuditJobStatus.INTERRUPTED,
        }), None)
        if failed is not None and (not jobs or jobs[0] == failed):
            st.warning(f"{failed.original_filename}：{failed.error or failed.stage} 可重新上传修改稿重试。")

    status_panel()


def render_peer_review(
    report: PeerReviewReport,
    pdf_bytes: bytes | None = None,
    *,
    on_submit_revision: Callable[[bytes, str], object] | None = None,
    load_revision_jobs: Callable[[], Sequence[PeerReviewRevisionJob]] | None = None,
    on_update_report: Callable[[PeerReviewReport], object] | None = None,
    on_compare_related_work: Callable[[list[RelatedWorkReference]], object] | None = None,
    load_revisions: Callable[[], Sequence[PeerReviewRevision]] | None = None,
    load_revision_pdf: Callable[[str], bytes] | None = None,
    on_update_revision: Callable[[PeerReviewRevision], object] | None = None,
) -> None:
    label, _, decision_class = _DECISION_LABELS[report.decision]
    rubric_meta = f"标准 {report.rubric_version}"
    if report.rubric_updated_at:
        rubric_meta += f"（更新于 {report.rubric_updated_at}）"
    meta_items = [
        f"基于当前论文原文的 AI 辅助预审 · {rubric_meta} · 不代表真实会议录用决定。"
    ]
    if report.rubric_change_note:
        meta_items.append(f"标准说明：{report.rubric_change_note}")
    run_details: list[str] = []
    if report.run_id or report.generated_at:
        run_details = [
            item for item in (
                f"运行 {report.run_id}" if report.run_id else "",
                f"模型 {report.model_name}" if report.model_name else "",
                f"推理 {report.reasoning_effort}" if report.reasoning_effort else "",
                f"Prompt {report.prompt_version}" if report.prompt_version else "",
                f"耗时 {report.elapsed_seconds:.1f}s" if report.elapsed_seconds is not None else "",
            ) if item
        ]
    with st.container(key="peer_review_overview"):
        with st.container(key="peer_review_header"):
            title_col, result_col = st.columns(
                [3.5, 2.5], vertical_alignment="center"
            )
            with title_col:
                st.markdown(
                    f'<div class="pa-workspace-header">'
                    f'<div class="pa-workspace-brand-icon" aria-hidden="true">✎</div>'
                    f'<div class="pa-workspace-copy"><div class="pa-workspace-title-row">'
                    f'<div class="pa-workspace-title">{escape(report.paper_title)}</div>'
                    f'<div class="pa-workspace-summary">模拟投稿评审 · {_VENUE_LABELS.get(report.venue, "通用 AI/ML")}</div>'
                    f'</div></div></div>',
                    unsafe_allow_html=True,
                )
            with result_col:
                st.markdown(
                    f'<div class="pa-peer-readonly-result pa-peer-decision-{decision_class}">'
                    f'<span>模拟评审结果</span><strong>{escape(label)}</strong>'
                    f'<b>{report.overall_score:.1f} / 10</b><small>置信度 {report.confidence} / 5</small></div>',
                    unsafe_allow_html=True,
                )
        meta_html = "".join(f"<span>{escape(item)}</span>" for item in meta_items)
        if run_details:
            meta_html += f'<small>{escape(" · ".join(run_details))}</small>'
        st.markdown(
            f'<div class="pa-peer-meta-line">{meta_html}</div>',
            unsafe_allow_html=True,
        )
        if pdf_bytes:
            st.markdown(
                f'<div class="pa-peer-summary-strip"><strong>当前主要拒稿风险</strong>'
                f'<span>{escape(_main_rejection_risk(report))}</span></div>',
                unsafe_allow_html=True,
            )
    if pdf_bytes:
        with st.container(key="peer_review_workspace"):
            paper_col, review_col = st.columns([1.6, 1], gap="medium")
            with paper_col:
                page_count = get_pdf_page_count(pdf_bytes)
                page_key = f"peer_review_page_{report.paper_title}"
                zoom_key = f"peer_review_zoom_{report.paper_title}"
                focus = st.session_state.get("peer_review_pdf_focus") or {}
                if focus.get("page"):
                    st.session_state[page_key] = int(focus["page"])
                st.session_state[page_key] = min(max(int(st.session_state.get(page_key, 1)), 1), page_count)
                st.session_state[zoom_key] = min(max(int(st.session_state.get(zoom_key, 100)), 80), 160)
                with st.container(key="peer_review_source_panel"):
                    with st.container(key="peer_review_pdf_toolbar"):
                        title_col, prev_col, page_col, next_col, zoom_out_col, zoom_col, zoom_in_col, fit_col = st.columns(
                            [2.7, .55, 1.25, .55, .55, .8, .55, 1.45],
                            vertical_alignment="center",
                            gap="small",
                        )
                        title_col.markdown('<div class="pa-pdf-panel-title">论文原文</div>', unsafe_allow_html=True)
                        if prev_col.button("‹", key=f"{page_key}-prev", disabled=st.session_state[page_key] <= 1, width="stretch"):
                            st.session_state[page_key] -= 1
                            st.rerun()
                        page_col.markdown(
                            f'<div class="pa-peer-page-label">{st.session_state[page_key]} <span>/ {page_count}</span></div>',
                            unsafe_allow_html=True,
                        )
                        if next_col.button("›", key=f"{page_key}-next", disabled=st.session_state[page_key] >= page_count, width="stretch"):
                            st.session_state[page_key] += 1
                            st.rerun()
                        if zoom_out_col.button("−", key=f"{zoom_key}-out", disabled=st.session_state[zoom_key] <= 80, width="stretch"):
                            st.session_state[zoom_key] -= 10
                            st.rerun()
                        zoom_col.markdown(f'<div class="pa-pdf-zoom">{st.session_state[zoom_key]}%</div>', unsafe_allow_html=True)
                        if zoom_in_col.button("+", key=f"{zoom_key}-in", disabled=st.session_state[zoom_key] >= 160, width="stretch"):
                            st.session_state[zoom_key] += 10
                            st.rerun()
                        fit_col.button("适应宽度", key=f"{zoom_key}-fit", width="stretch", on_click=lambda: st.session_state.__setitem__(zoom_key, 100))
                    if focus.get("issue_title"):
                        st.markdown(
                            f'<div class="pa-peer-pdf-focus">当前问题 · {escape(str(focus["issue_title"]))}'
                            f'<span>证据来自第 {st.session_state[page_key]} 页</span></div>',
                            unsafe_allow_html=True,
                        )
                    with st.container(border=True, key="peer_review_pdf_panel"):
                        render_selectable_pdf_page(
                            pdf_bytes,
                            st.session_state[page_key],
                            focus.get("rects", []) if focus.get("page") == st.session_state[page_key] else [],
                            key=f"peer-review-page-{report.paper_title}-{st.session_state[page_key]}",
                            selection_enabled=False,
                            zoom_percent=st.session_state[zoom_key],
                            fit_scale=1.0,
                        )
            content_col = review_col
    else:
        content_col = st.container()

    with content_col:
        with st.container(key="peer_review_side_panel"):
            if not pdf_bytes:
                st.markdown(
                    f'<div class="pa-peer-section-card pa-peer-summary-card">'
                    f'<strong>当前主要拒稿风险</strong><div>{escape(_main_rejection_risk(report))}</div></div>',
                    unsafe_allow_html=True,
                )
            tab_overview, tab_dimensions, tab_concerns, tab_export = st.tabs(
                ["评审意见", "维度评分", "问题", "导出"]
            )
            with tab_overview:
                _render_submission_risks(report, pdf_bytes)
                _render_action_plan(report)
                st.markdown("### 综合结论")
                st.markdown(
                    f'<div class="pa-peer-conclusion"><div><strong>总体判断</strong>'
                    f'<span class="pa-peer-decision-{decision_class}">{escape(label)}</span></div>'
                    f'<p>{escape(report.decision_rationale)}</p></div>',
                    unsafe_allow_html=True,
                )
                with st.expander("展开完整 AI 评审总结"):
                    st.write(report.summary)
                    if report.why_not_adjacent:
                        st.markdown("**为什么不是相邻档位**")
                        st.write(report.why_not_adjacent)
                if report.core_contributions:
                    st.markdown("### 核心贡献")
                    for index, item in enumerate(report.core_contributions, start=1):
                        st.markdown(
                            f'<div class="pa-peer-point-card pa-peer-contribution-card">'
                            f'<strong>贡献 {index}</strong>{escape(item)}</div>',
                            unsafe_allow_html=True,
                        )
                if report.strengths:
                    with st.expander(f"论文已有优势（{len(report.strengths)} 项）"):
                        for index, item in enumerate(report.strengths, start=1):
                            st.markdown(
                                f'<div class="pa-peer-strength-row"><strong>{escape(_strength_title(item, index))}</strong>'
                                f'<p>{escape(item)}</p></div>',
                                unsafe_allow_html=True,
                            )
                if report.acceptance_blockers:
                    st.markdown("### 接收阻碍")
                    for index, item in enumerate(report.acceptance_blockers, start=1):
                        st.markdown(
                            f'<div class="pa-peer-point-card pa-peer-blocker-card">'
                            f'<strong>阻碍 {index}</strong>{escape(item)}</div>',
                            unsafe_allow_html=True,
                        )
                if report.fatal_flaws:
                    st.markdown("### 致命问题")
                    for index, item in enumerate(report.fatal_flaws, start=1):
                        st.markdown(
                            f'<div class="pa-peer-point-card pa-peer-fatal-card">'
                            f'<strong>致命问题 {index}</strong>{escape(item)}</div>',
                            unsafe_allow_html=True,
                        )
                if report.required_changes:
                    st.markdown("### 必须修改")
                    for index, item in enumerate(report.required_changes, start=1):
                        st.markdown(
                            f'<div class="pa-peer-point-card pa-peer-required-card">'
                            f'<strong>必须修改 {index}</strong>{escape(item)}</div>',
                            unsafe_allow_html=True,
                        )
                if report.suggested_changes:
                    st.markdown("### 建议修改")
                    for index, item in enumerate(report.suggested_changes, start=1):
                        st.markdown(
                            f'<div class="pa-peer-point-card pa-peer-suggested-card">'
                            f'<strong>建议修改 {index}</strong>{escape(item)}</div>',
                            unsafe_allow_html=True,
                        )
                if report.confidence_rationale:
                    st.markdown("### 置信度说明")
                    st.caption(report.confidence_rationale)
                review_limitations = report.review_limitations or [
                    "本评审仅基于上传论文文本；代码、完整附录、数据泄漏和未报告实验无法独立验证。"
                ]
                if review_limitations:
                    st.markdown("### 评审边界")
                    st.caption("以下项目无法仅凭上传论文正文独立确认，不应视为已证实的缺陷。")
                    for item in review_limitations:
                        st.markdown(f"- {escape(item)}")
                with st.expander("相关工作对比（可选）"):
                    st.caption("仅使用你主动提供的文献记录，不会自动抓取或推断外部资料。最多 5 条。")
                    related_text = st.text_area(
                        "相关工作记录",
                        value="",
                        placeholder="每行一条：标题 | 年份 | URL（可选） | 与本文差异（可选）",
                        key="peer-review-related-work-input",
                        height=120,
                    )
                    if st.button(
                        "生成创新性对比",
                        key="peer-review-related-work-submit",
                        disabled=on_compare_related_work is None or not related_text.strip(),
                    ):
                        references: list[RelatedWorkReference] = []
                        for raw_line in related_text.splitlines():
                            parts = [part.strip() for part in raw_line.split("|", 3)]
                            if not parts or not parts[0]:
                                continue
                            year = None
                            if len(parts) > 1 and parts[1].isdigit():
                                year = int(parts[1])
                            references.append(RelatedWorkReference(
                                citation=parts[0],
                                year=year,
                                url=parts[2] if len(parts) > 2 else "",
                                distinction=parts[3] if len(parts) > 3 else "",
                            ))
                        if not references:
                            st.error("请至少提供一条有效的相关工作记录。")
                        elif on_compare_related_work is not None:
                            try:
                                on_compare_related_work(references[:5])
                            except (OSError, RuntimeError, ValueError) as exc:
                                st.error(f"相关工作对比失败：{exc}")
                            else:
                                st.success("相关工作对比已保存。")
                                st.rerun()
                    comparison = report.related_work_comparison
                    if comparison is not None:
                        st.markdown("**创新性判断**")
                        st.write(comparison.assessment or "未形成明确判断。")
                        if comparison.distinctions:
                            st.markdown("**可支持的差异**")
                            for item in comparison.distinctions:
                                st.markdown(f"- {item}")
                        if comparison.gaps:
                            st.markdown("**仍需补充**")
                            for item in comparison.gaps:
                                st.markdown(f"- {item}")
                        st.caption(f"对比置信度：{comparison.confidence} / 5")
            with tab_dimensions:
                if report.score_breakdown:
                    weights = " · ".join(
                        f"{_DIMENSION_LABELS.get(name, name)} {value:.0%}"
                        for name, value in report.rubric_weights.items()
                    )
                    st.caption(
                        f"系统评分：按六维加权平均映射到 1–10（{report.score_calculation_version}）。"
                        + (f" 当前权重：{weights}" if weights else "")
                    )
                for dimension in report.dimensions:
                    with st.container(border=True):
                        left, right = st.columns([3, 1])
                        dimension_label = _DIMENSION_LABELS.get(dimension.name, dimension.name)
                        left.markdown(f"**{dimension_label}** · {dimension.score} / 5")
                        right.caption(f"置信度 {dimension.confidence} / 5")
                        st.write(dimension.rationale)
                        if dimension.evidence:
                            st.caption(f"原文依据 {len(dimension.evidence)} 条")
                        else:
                            st.caption("AI 评审判断 · 未绑定可定位原文依据")
                        _evidence_buttons(dimension.evidence, pdf_bytes, f"peer-dimension-{dimension.name}")
            with tab_concerns:
                all_concerns = [*report.major_concerns, *report.minor_concerns]
                severity_options = {"全部": None, **{item.value: item for item in IssueSeverity}}
                category_options = {"全部类别": None, **{label: value for value, label in _ISSUE_CATEGORY_LABELS.items()}}
                status_options = {"全部状态": None, **{label: value for value, label in _ISSUE_STATUS_LABELS.items()}}
                filter_col, category_col, status_col, sort_col = st.columns(4)
                selected_severity = filter_col.selectbox(
                    "严重度", list(severity_options), key="peer-review-severity-filter"
                )
                selected_category = category_col.selectbox(
                    "问题类别", list(category_options), key="peer-review-category-filter"
                )
                selected_status = status_col.selectbox(
                    "处理状态", list(status_options), key="peer-review-status-filter"
                )
                sort_mode = sort_col.selectbox(
                    "排序", ["严重度", "置信度", "原顺序"], key="peer-review-issue-sort"
                )
                filtered = [
                    concern for concern in all_concerns
                    if (severity_options[selected_severity] is None or concern.severity_level == severity_options[selected_severity])
                    and (category_options[selected_category] is None or concern.category == category_options[selected_category])
                    and (status_options[selected_status] is None or concern.status == status_options[selected_status])
                ]
                if not filtered:
                    st.info("当前筛选条件下没有问题。")
                p3_items = [item for item in all_concerns if _severity_for(item) is IssueSeverity.EDITORIAL and item.status is not IssueStatus.IGNORED]
                if p3_items and on_update_report is not None:
                    if st.button(
                        f"将 {len(p3_items)} 条 P3 标记为已忽略",
                        key="peer-review-ignore-p3",
                        type="secondary",
                        help="仅改变当前处理状态，不修改 AI 原始严重度、类别或证据。",
                    ):
                        updated_items = [
                            item.model_copy(update={"status": IssueStatus.IGNORED})
                            if item in p3_items else item
                            for item in all_concerns
                        ]
                        next_report = report.model_copy(update={
                            "major_concerns": [item for item in updated_items if item.severity.value == "major"],
                            "minor_concerns": [item for item in updated_items if item.severity.value != "major"],
                        })
                        try:
                            on_update_report(next_report)
                        except (OSError, RuntimeError, ValueError) as exc:
                            st.error(f"批量更新失败：{exc}")
                        else:
                            st.success("P3 问题已标记为已忽略。")
                severity_rank = {item: index for index, item in enumerate(IssueSeverity)}
                if sort_mode == "严重度":
                    filtered.sort(key=lambda concern: severity_rank.get(concern.severity_level, 9))
                elif sort_mode == "置信度":
                    filtered.sort(key=lambda concern: -concern.confidence)
                visible_major = [concern for concern in filtered if concern.severity.value == "major"]
                visible_minor = [concern for concern in filtered if concern.severity.value != "major"]
                needs_review_count = sum(item.status is IssueStatus.NEEDS_REVIEW for item in filtered)
                if needs_review_count:
                    st.info(f"待人工复核：{needs_review_count} 条。相关卡片已默认展开。")
                if visible_major:
                    st.markdown("### 主要问题")
                    for index, concern in enumerate(visible_major):
                        with st.container(border=True, key=f"peer-major-card-{index}"):
                            _render_concern(concern, pdf_bytes, f"peer-major-{index}")
                            _manual_review_controls(report, concern, f"peer-major-{index}", on_update_report)
                if visible_minor:
                    st.markdown("### 次要问题")
                    for index, concern in enumerate(visible_minor):
                        with st.container(border=True, key=f"peer-minor-card-{index}"):
                            _render_concern(concern, pdf_bytes, f"peer-minor-{index}")
                            _manual_review_controls(report, concern, f"peer-minor-{index}", on_update_report)
            with tab_export:
                st.markdown("### 修改稿复审")
                st.caption("上传新版本后保留当前评审，并生成段落级差异与新的五档投稿建议。问题状态仅作轻量匹配，低置信匹配会标记为待确认。")
                revision_jobs = list(load_revision_jobs() if load_revision_jobs else [])
                active_revision = next((job for job in revision_jobs if job.status in {
                    AuditJobStatus.QUEUED, AuditJobStatus.RUNNING,
                }), None)
                _render_revision_jobs(load_revision_jobs, active_revision is not None)
                revision_file = st.file_uploader(
                    "上传修改稿 PDF",
                    type=["pdf"],
                    key="peer_review_revision_upload",
                    label_visibility="collapsed",
                    disabled=on_submit_revision is None or active_revision is not None,
                )
                if st.button(
                    "上传修改稿并复审",
                    type="primary",
                    width="stretch",
                    key="peer-review-submit-revision",
                    disabled=on_submit_revision is None or revision_file is None or active_revision is not None,
                ) and on_submit_revision is not None and revision_file is not None:
                    try:
                        on_submit_revision(revision_file.getvalue(), revision_file.name)
                    except (OSError, RuntimeError, ValueError) as exc:
                        st.error(f"修改稿复审失败：{exc}")
                    else:
                        st.toast("修改稿已加入后台复审队列。")
                        st.rerun()
                revisions = list(load_revisions() if load_revisions is not None else [])
                revision_result = revisions[0] if revisions else None
                if revision_result is not None:
                    diff = revision_result.diff
                    st.success(f"已保存修改稿版本：{revision_result.original_filename}")
                    st.info(diff.summary)
                    old_label = _DECISION_LABELS[report.decision][0]
                    new_label = _DECISION_LABELS[revision_result.report.decision][0]
                    st.markdown(
                        f"**评审变化**：{old_label} · {report.overall_score:.1f} / 10 → "
                        f"{new_label} · {revision_result.report.overall_score:.1f} / 10"
                    )
                    score_delta = revision_result.report.overall_score - report.overall_score
                    delta_label = "提升" if score_delta > 0 else "下降" if score_delta < 0 else "未变化"
                    st.caption(f"评分变化原因：{delta_label} {abs(score_delta):.1f} 分，主要由六维加权评分决定。")
                    old_dimensions = {item.name: item.score for item in report.dimensions}
                    dimension_changes = [
                        f"{_DIMENSION_LABELS.get(item.name, item.name)} {old_dimensions[item.name]}→{item.score}"
                        for item in revision_result.report.dimensions
                        if item.name in old_dimensions and old_dimensions[item.name] != item.score
                    ]
                    if dimension_changes:
                        st.caption("维度变化：" + " · ".join(dimension_changes[:6]))
                    if revision_result.report.rubric_version != report.rubric_version:
                        st.warning(
                            f"本次复审使用了不同评审标准（{report.rubric_version} → {revision_result.report.rubric_version}），评分变化不能直接归因于论文修改。"
                        )
                    st.caption(
                        f"问题状态：已解决 {len(revision_result.resolved_concerns)} · "
                        f"仍存在 {len(revision_result.remaining_concerns)} · "
                        f"新增 {len(revision_result.new_concerns)} · "
                        f"待确认匹配 {len(revision_result.ambiguous_matches)}"
                    )
                    if diff.changed_samples:
                        st.caption("修改片段示例：" + "；".join(diff.changed_samples[:2]))
                if revisions:
                    st.markdown("### 历史修改稿")
                    st.caption("每个版本都保留独立 PDF 与复审结果，可重新打开查看。")
                    for revision in revisions:
                        old_label = _DECISION_LABELS[report.decision][0]
                        new_label = _DECISION_LABELS[revision.report.decision][0]
                        with st.container(border=True):
                            left, right = st.columns([3, 1])
                            left.markdown(
                                f"**{revision.original_filename}**  ·  {revision.created_at.replace('T', ' ')[:19]}"
                            )
                            left.caption(
                                f"{revision.diff.summary}  |  {old_label} {report.overall_score:.1f} → "
                                f"{new_label} {revision.report.overall_score:.1f}"
                            )
                            if revision.resolved_concerns:
                                left.success("已解决：" + "、".join(revision.resolved_concerns[:3]))
                            if revision.remaining_concerns:
                                left.warning("仍存在：" + "、".join(revision.remaining_concerns[:3]))
                            if revision.new_concerns:
                                left.info("新增问题：" + "、".join(revision.new_concerns[:3]))
                            if revision.ambiguous_matches:
                                left.warning("需人工确认匹配：" + "、".join(revision.ambiguous_matches[:3]))
                                confirmed = left.checkbox(
                                    "我已确认该版本的问题匹配",
                                    value=revision.match_confirmed,
                                    key=f"peer-revision-confirm-{revision.revision_id}",
                                    disabled=on_update_revision is None,
                                )
                                if confirmed != revision.match_confirmed and on_update_revision is not None:
                                    if left.button("保存匹配确认", key=f"peer-revision-confirm-save-{revision.revision_id}"):
                                        try:
                                            on_update_revision(revision.model_copy(update={"match_confirmed": confirmed}))
                                        except (OSError, RuntimeError, ValueError) as exc:
                                            left.error(f"匹配确认保存失败：{exc}")
                                        else:
                                            left.success("匹配确认已保存。")
                                            st.rerun()
                            if load_revision_pdf is not None and right.button(
                                "查看修改稿", key=f"peer-revision-open-{revision.revision_id}", width="stretch"
                            ):
                                st.session_state["peer_review_revision_pdf"] = load_revision_pdf(revision.revision_id)
                                st.session_state["peer_review_revision_pdf_name"] = revision.original_filename
                                st.rerun()
                revision_pdf = st.session_state.get("peer_review_revision_pdf")
                if revision_pdf:
                    st.markdown(f"### 当前查看：{st.session_state.get('peer_review_revision_pdf_name', '修改稿')}")
                    render_selectable_pdf_page(
                        revision_pdf,
                        min(int(st.session_state.get("peer_review_revision_page", 1)), get_pdf_page_count(revision_pdf)),
                        [],
                        key="peer-review-revision-preview",
                        selection_enabled=False,
                        zoom_percent=90,
                    )
                st.download_button(
                    "下载 Markdown 评审",
                    render_peer_review_markdown(report),
                    file_name="paperaudit-peer-review.md",
                    mime="text/markdown",
                    width="stretch",
                )


def render_peer_review_markdown(report: PeerReviewReport) -> str:
    lines = [
        "# PaperAudit · 模拟投稿评审",
        "",
        f"- 论文：{report.paper_title}",
        f"- 评审标准：{_VENUE_LABELS.get(report.venue, report.venue.value)}",
        *( [f"- Rubric 版本：{report.rubric_version}"] if report.rubric_version else [] ),
        *( [f"- Rubric 更新时间：{report.rubric_updated_at}"] if report.rubric_updated_at else [] ),
        *( [f"- Rubric 说明：{report.rubric_change_note}"] if report.rubric_change_note else [] ),
        f"- 投稿建议：{report.decision.value}",
        f"- 综合评分：{report.overall_score:.1f} / 10",
        f"- 评审置信度：{report.confidence} / 5",
        "",
        "> 本报告为基于当前论文原文的 AI 辅助预审，不代表真实会议录用决定。",
        *( [f"- 模型原始评分（仅供审计）：{report.model_raw_score:.1f} / 10"]
           if report.model_raw_score is not None else [] ),
        *( [f"- 系统评分算法：{report.score_calculation_version}（六维加权后映射）"]
           if report.score_breakdown else [] ),
        *( ["- 当前权重：" + "、".join(f"{_DIMENSION_LABELS.get(name, name)} {value:.1%}" for name, value in report.rubric_weights.items())]
           if report.rubric_weights else [] ),
        "",
        report.summary,
        "",
        "## 核心贡献",
        "",
        *[f"- {item}" for item in report.core_contributions],
        "",
        "## 主要优点",
        "",
        *[f"- {item}" for item in report.strengths],
        "",
        "## 决策理由",
        "",
        report.decision_rationale,
        "",
        "## 为什么不是相邻档位",
        "",
        report.why_not_adjacent,
        "",
        "## 接收阻碍",
        "",
        *[f"- {item}" for item in report.acceptance_blockers],
        "",
        "## 致命问题",
        "",
        *[f"- {item}" for item in report.fatal_flaws],
        "",
        "## 置信度说明",
        "",
        report.confidence_rationale,
        "",
        "## 评审边界",
        "",
        *[f"- {item}" for item in (report.review_limitations or [
            "本评审仅基于上传论文文本；代码、完整附录、数据泄漏和未报告实验无法独立验证。"
        ])],
        "",
        "## 必须修改",
        "",
        *[f"- {item}" for item in report.required_changes],
        "",
        "## 建议修改",
        "",
        *[f"- {item}" for item in report.suggested_changes],
        "",
        "## 维度评分",
        "",
        *[f"- {_DIMENSION_LABELS.get(item.name, item.name)}：{item.score} / 5（置信度 {item.confidence} / 5）— {item.rationale}" for item in report.dimensions],
        "",
    ]
    if report.related_work_comparison is not None:
        comparison = report.related_work_comparison
        lines.extend(["## 相关工作对比", "", comparison.assessment, ""])
        if comparison.distinctions:
            lines.extend(["可支持的差异：", *[f"- {item}" for item in comparison.distinctions], ""])
        if comparison.gaps:
            lines.extend(["仍需补充：", *[f"- {item}" for item in comparison.gaps], ""])
        lines.extend([f"对比置信度：{comparison.confidence}/5", ""])
    for heading, concerns in (("主要问题", report.major_concerns), ("次要问题", report.minor_concerns)):
        lines.extend([f"## {heading}", ""])
        for item in concerns:
            lines.extend([
                f"### {item.title}", "",
                f"{item.description}", "",
                f"为什么重要：{item.why_it_matters}", "",
                f"建议：{item.suggestion}", "",
                f"AI 原始判断：严重度 {(item.ai_severity_level or _severity_for(item)).value} · 类别 {_ISSUE_CATEGORY_LABELS.get(item.ai_category or item.category, (item.ai_category or item.category).value)} · "
                f"当前采用：严重度 {(_severity_for(item)).value} · 类别 {_ISSUE_CATEGORY_LABELS.get(item.category, item.category.value)} · "
                f"证据判断 {item.support_type.value} · 置信度 {item.confidence}/5", "",
                f"人工结论：{_HUMAN_DECISION_LABELS.get(item.human_decision, item.human_decision.value)} · "
                f"人工已确认：{'是' if item.human_reviewed else '否'}",
                f"人工备注：{item.human_note}" if item.human_note else "",
                "",
                *[f"- 第 {anchor.page} 页：{anchor.quote or anchor.text[:240]}" for anchor in item.evidence],
                "",
            ])
    lines.extend(["## 最优先修改的事项", "", *[f"1. {item}" for item in report.top_priorities], ""])
    return "\n".join(lines).strip() + "\n"
