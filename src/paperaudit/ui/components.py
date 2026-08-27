from __future__ import annotations

from collections.abc import Callable, Mapping
from html import escape
import re

import streamlit as st

from paperaudit.display import (
    LABEL_NAMES,
    SEVERITY_NAMES,
    claim_error_name,
    evidence_error_name,
    fully_supported_rate,
    label_counts,
)
from paperaudit.models import (
    AuditSummary,
    AutoLabel,
    ClaimAudit,
    EvidenceAnchor,
    Severity,
    TrustGrade,
)
from paperaudit.ui.audit_view import normalize_evidence_display, selected_evidence


_STATUS_BADGES = {
    AutoLabel.SUPPORTED: "badge-supported",
    AutoLabel.PARTIALLY_SUPPORTED: "badge-partially",
    AutoLabel.CONTRADICTED: "badge-contradicted",
    AutoLabel.NO_SUPPORT_FOUND: "badge-no-support",
    AutoLabel.ABSTAIN: "badge-abstain",
}
_SEVERITY_BADGES = {
    Severity.NONE: "badge-sev-none",
    Severity.LOW: "badge-sev-low",
    Severity.MEDIUM: "badge-sev-medium",
    Severity.HIGH: "badge-sev-high",
    Severity.CRITICAL: "badge-sev-critical",
}


def render_status_badge(label: AutoLabel) -> str:
    return f'<span class="pa-badge {_STATUS_BADGES[label]}">{LABEL_NAMES[label]}</span>'


def render_severity_badge(severity: Severity) -> str:
    return f'<span class="pa-badge {_SEVERITY_BADGES[severity]}">{SEVERITY_NAMES[severity]}</span>'


def highlight_keywords(text: str, keywords: list[str]) -> str:
    escaped_text = escape(text)
    escaped_keywords = sorted(
        {escape(keyword) for keyword in keywords if keyword.strip()},
        key=len,
        reverse=True,
    )
    if not escaped_keywords:
        return escaped_text
    pattern = re.compile("|".join(re.escape(keyword) for keyword in escaped_keywords), re.IGNORECASE)
    return pattern.sub(lambda match: f'<mark class="pa-mark">{match.group(0)}</mark>', escaped_text)


def render_header_banner() -> None:
    st.markdown(
        """
        <div class="pa-header">
          <div>
            <div class="pa-header-title">📄 Hy3 论文学习助手</div>
            <div class="pa-header-subtitle">结构化论文讲解 · 原文证据定位 · 报告审计</div>
          </div>
          <div class="pa-header-badge">学术实战作品 · 基于 Hy3 大模型</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_grade_hero(grade: TrustGrade, score: float | None) -> None:
    grade_class = {
        TrustGrade.TRUSTED: "trusted",
        TrustGrade.REVIEW: "review",
        TrustGrade.UNTRUSTED: "untrusted",
    }.get(grade, "review")
    score_text = f"{score:.1f} 分" if score is not None else "暂不评分"
    st.markdown(
        f'<div class="pa-grade pa-grade-{grade_class}">'
        f'<div class="pa-grade-title">整体结论：{escape(grade.value)}</div>'
        f'<div class="pa-grade-detail">综合结果：{score_text}</div></div>',
        unsafe_allow_html=True,
    )


def render_metric_cards(
    total_score: float | None,
    coverage: float,
    evidence_rate: float,
    review_count: int,
    critical_count: int,
    high_count: int,
) -> None:
    columns = st.columns(6)
    columns[0].metric("总分", f"{total_score:.1f}" if total_score is not None else "N/A")
    columns[1].metric("审计覆盖率", f"{coverage:.1f}%")
    columns[2].metric("候选证据检索覆盖率", f"{evidence_rate:.1f}%")
    columns[3].metric("待复核", review_count)
    columns[4].metric("严重问题", critical_count)
    columns[5].metric("高风险", high_count)


def build_audit_summary_html(
    summary: AuditSummary, audits: list[ClaimAudit] | None = None
) -> str:
    grade_class = {
        TrustGrade.TRUSTED: "trusted",
        TrustGrade.REVIEW: "review",
        TrustGrade.UNTRUSTED: "untrusted",
    }.get(summary.grade, "unrated")
    score_text = (
        f"{summary.total_score:.1f}<small>分</small>"
        if summary.total_score is not None
        else "<small>未评分</small>"
    )
    audits = audits or []
    counts = label_counts(audits)
    attention_count = sum(
        not (
            audit.judgment.label == AutoLabel.SUPPORTED
            and audit.judgment.severity == Severity.NONE
        )
        for audit in audits
    )
    priority_count = sum(
        audit.judgment.severity in {Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM}
        or audit.judgment.label in {AutoLabel.CONTRADICTED, AutoLabel.NO_SUPPORT_FOUND}
        for audit in audits
    )
    metrics = (
        ("需关注", str(attention_count), "is-warning" if attention_count else ""),
        ("冲突", str(counts[AutoLabel.CONTRADICTED]), "is-danger" if counts[AutoLabel.CONTRADICTED] else ""),
        ("未找到证据", str(counts[AutoLabel.NO_SUPPORT_FOUND]), ""),
        ("证据不足", str(counts[AutoLabel.ABSTAIN]), ""),
        ("优先检查", str(priority_count), "is-warning" if priority_count else ""),
    )
    metric_html = "".join(
        f'<div class="pa-audit-summary-metric {css_class}">'
        f'<span>{escape(label)}</span><strong>{escape(value)}</strong></div>'
        for label, value, css_class in metrics
    )
    return (
        f'<div class="pa-audit-summary">'
        f'<div class="pa-audit-summary-grade is-{grade_class}">'
        f'<span>审计结果</span><strong>{escape(summary.grade.value)}</strong></div>'
        f'<div class="pa-audit-summary-score">{score_text}</div>'
        f'<div class="pa-audit-summary-metrics">{metric_html}</div></div>'
    )


def render_audit_summary(summary: AuditSummary, audits: list[ClaimAudit]) -> None:
    counts = label_counts(audits)
    st.markdown(
        build_audit_summary_html(summary, audits),
        unsafe_allow_html=True,
    )
    st.caption(
        f"本次根据报告内容自动拆分并审计 {len(audits)} 条论断，数量并非固定。 "
        f"支持 {counts[AutoLabel.SUPPORTED]} · "
        f"部分支持 {counts[AutoLabel.PARTIALLY_SUPPORTED]} · "
        f"冲突 {counts[AutoLabel.CONTRADICTED]} · "
        f"未找到支持 {counts[AutoLabel.NO_SUPPORT_FOUND]} · "
        f"证据不足 {counts[AutoLabel.ABSTAIN]} · "
        f"完全支持率 {fully_supported_rate(audits):.1f}% · "
        f"候选证据检索覆盖率 {summary.evidence_discovery_rate:.1f}%。"
    )
    st.caption("综合总分同时考虑内容覆盖和引用情况，不等同于事实正确率。")


def build_audit_detail_html(
    audit: ClaimAudit, category_label: str, *, evidence_limit: int = 2
) -> str:
    highlighted_claim = highlight_keywords(
        audit.claim.text,
        [*audit.claim.entities, *audit.claim.numbers],
    )
    explanation = escape(audit.judgment.explanation)
    report_location = (
        f" · {escape(audit.claim.report_location)}"
        if audit.claim.report_location
        else ""
    )
    suggestion_html = ""
    if audit.judgment.suggestion and audit.judgment.suggestion.strip():
        suggestion_html = (
            '<section class="pa-audit-detail-section">'
            '<div class="pa-audit-detail-label">修改建议</div>'
            f'<div class="pa-audit-detail-copy">'
            f'{escape(audit.judgment.suggestion.strip())}</div></section>'
        )

    selected = selected_evidence(audit)[:evidence_limit]
    if selected:
        evidence_label = (
            "候选片段（不足以支持）"
            if audit.judgment.label == AutoLabel.NO_SUPPORT_FOUND
            else "候选片段（不足以判断）"
            if audit.judgment.label == AutoLabel.ABSTAIN
            else "关键原文依据"
        )
        evidence_items = "".join(
            '<article class="pa-audit-evidence-item">'
            f'<div class="pa-audit-evidence-meta">证据 {index} · '
            f'P{item.page} · {escape(item.chunk_id)}</div>'
            f'<div class="pa-audit-evidence-text">'
            f'{escape(normalize_evidence_display(item.text))}</div></article>'
            for index, item in enumerate(selected, start=1)
        )
        evidence_html = (
            '<section class="pa-audit-detail-section">'
            f'<div class="pa-audit-detail-label">{evidence_label} · {len(selected)}</div>'
            f'<div class="pa-audit-evidence-list">{evidence_items}</div></section>'
        )
    else:
        evidence_html = (
            '<section class="pa-audit-detail-section">'
            '<div class="pa-audit-detail-label">原文证据</div>'
            '<div class="pa-audit-empty-inline">当前没有已验证的原文证据</div>'
            '</section>'
        )

    return (
        '<div class="pa-audit-detail">'
        '<div class="pa-audit-detail-head">'
        f'<div class="pa-audit-meta">{escape(audit.claim.claim_id)} · '
        f'{escape(category_label)}{report_location}</div>'
        f'<div class="pa-audit-tags">{render_status_badge(audit.judgment.label)}'
        f'{render_severity_badge(audit.judgment.severity)}</div></div>'
        '<section class="pa-audit-detail-section">'
        '<div class="pa-audit-detail-label">完整论断</div>'
        f'<div class="pa-audit-claim">{highlighted_claim}</div></section>'
        '<section class="pa-audit-detail-section">'
        '<div class="pa-audit-detail-label">判断说明</div>'
        f'<div class="pa-audit-detail-copy">{explanation}</div></section>'
        '<section class="pa-audit-detail-section">'
        '<div class="pa-audit-detail-label">问题分类</div>'
        f'<div class="pa-audit-detail-copy">论断：{escape(claim_error_name(audit.judgment.claim_error_type))} · '
        f'证据：{escape(evidence_error_name(audit.judgment.evidence_error_type))}</div></section>'
        f'{suggestion_html}{evidence_html}</div>'
    )


def audit_evidence_label(anchor: EvidenceAnchor) -> str:
    parts = [f"P{anchor.page}" if anchor.page is not None else "页码未知"]
    if anchor.locator:
        parts.append(anchor.locator)
    if not anchor.rects:
        parts.append("仅页码")
    else:
        parts.append("段落")
    return " · ".join(parts)


def _audit_evidence_help(anchor: EvidenceAnchor) -> str:
    excerpt = normalize_evidence_display(anchor.quote or anchor.text or "")
    if len(excerpt) > 240:
        excerpt = excerpt[:237].rstrip() + "…"
    return f"原文预览\n{excerpt}" if excerpt else "该引用暂时无法显示原文预览。"


def render_audit_detail(
    audit: ClaimAudit,
    category_label: str,
    *,
    evidence_anchors: Mapping[str, EvidenceAnchor] | None = None,
    on_open_evidence: Callable[[EvidenceAnchor], None] | None = None,
) -> None:
    st.markdown(
        build_audit_detail_html(audit, category_label),
        unsafe_allow_html=True,
    )
    selected = selected_evidence(audit)
    if on_open_evidence is not None and selected:
        action_columns = st.columns(min(len(selected[:2]), 2))
        for index, item in enumerate(selected[:2]):
            anchor = (
                evidence_anchors.get(item.chunk_id)
                if evidence_anchors is not None
                else None
            ) or EvidenceAnchor(
                chunk_id=item.chunk_id,
                page=item.page,
                text=item.text,
            )
            if action_columns[index].button(
                f"{audit_evidence_label(anchor)} ↗",
                key=f"audit-evidence-{audit.claim.claim_id}-{index}-{item.chunk_id}",
                type="tertiary",
                help=_audit_evidence_help(anchor),
                width="stretch",
            ):
                on_open_evidence(anchor)

    remaining = selected[2:]
    if remaining:
        with st.expander(f"查看其余 {len(remaining)} 条原文依据"):
            for index, item in enumerate(remaining, start=2):
                st.caption(f"第 {item.page} 页 · {item.chunk_id}")
                st.code(normalize_evidence_display(item.text), language=None)
                if on_open_evidence is not None:
                    anchor = (
                        evidence_anchors.get(item.chunk_id)
                        if evidence_anchors is not None
                        else None
                    ) or EvidenceAnchor(
                        chunk_id=item.chunk_id,
                        page=item.page,
                        text=item.text,
                    )
                    if st.button(
                        f"{audit_evidence_label(anchor)} ↗",
                        key=f"audit-evidence-{audit.claim.claim_id}-{index}-{item.chunk_id}",
                        type="tertiary",
                        help=_audit_evidence_help(anchor),
                    ):
                        on_open_evidence(anchor)


def render_audit_card(
    audit: ClaimAudit,
    category_label: str,
    label_name: str,
    severity_name: str,
) -> None:
    selected = [
        candidate
        for candidate in audit.candidates
        if candidate.evidence_id in audit.judgment.evidence_ids
    ]
    evidence_html = "".join(
        f'<div class="pa-evidence"><strong>第 {item.page} 页 · '
        f'{escape(item.chunk_id)}</strong><br>{escape(item.text)}</div>'
        for item in selected
    )
    suggestion = (
        f'<div class="pa-audit-explanation"><strong>修改建议：</strong>'
        f'{escape(audit.judgment.suggestion)}</div>'
        if audit.judgment.suggestion
        else ""
    )
    highlighted_claim = highlight_keywords(
        audit.claim.text,
        [*audit.claim.entities, *audit.claim.numbers],
    )
    st.markdown(
        f'<div class="pa-audit-card">'
        f'<div class="pa-audit-head"><div class="pa-audit-meta">'
        f'{escape(audit.claim.claim_id)} · {escape(category_label)}</div>'
        f'<div class="pa-audit-tags">{render_status_badge(audit.judgment.label)}'
        f'{render_severity_badge(audit.judgment.severity)}</div></div>'
        f'<div class="pa-audit-claim">{highlighted_claim}</div>'
        f'<div class="pa-audit-explanation">{escape(audit.judgment.explanation)}</div>'
        f'{suggestion}{evidence_html}</div>',
        unsafe_allow_html=True,
    )
