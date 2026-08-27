from __future__ import annotations

from paperaudit.display import (
    LABEL_NAMES,
    SEVERITY_NAMES,
    claim_error_name,
    evidence_error_name,
    fully_supported_rate,
    label_counts,
)
from paperaudit.models import AuditRun, AutoLabel, ClaimAudit, LearningReport, Severity
from paperaudit.ui.audit_view import normalize_evidence_display, selected_evidence


_DIMENSION_LABELS = {
    "factual_support": "事实支持度",
    "evidence_correctness": "证据正确性",
    "evidence_completeness": "证据完整性",
    "numeric_consistency": "数字与指标一致性",
    "content_coverage": "内容覆盖度",
    "conclusion_boundary": "结论边界",
}


def render_markdown(run: AuditRun) -> str:
    summary = run.summary
    counts = label_counts(run.audits)
    lines = [
        "# Hy3 论文学习助手 · 审计报告",
        "",
        f"- 论文：{run.paper_title}",
        f"- 页数：{run.page_count}",
        f"- 可信等级：{summary.grade.value}",
        f"- 总分：{summary.total_score if summary.total_score is not None else 'N/A'}",
        f"- 自动审计覆盖率：{summary.audit_coverage}%",
        f"- 本次审计论断：{len(run.audits)} 条（根据报告内容自动拆分，数量并非固定）",
        f"- 完全支持论断率：{fully_supported_rate(run.audits)}%",
        f"- 候选证据检索覆盖率：{summary.evidence_discovery_rate}%",
        "",
        "> 综合总分同时考虑内容覆盖和引用情况，不等同于事实正确率。",
        "",
        "## 审计结果分布",
        "",
        "| 结果 | 数量 |",
        "| --- | ---: |",
        *[
            f"| {LABEL_NAMES[label]} | {counts[label]} |"
            for label in AutoLabel
        ],
        "",
        "## 维度得分",
        "",
        "| 维度 | 得分 |",
        "| --- | ---: |",
    ]
    for key, value in summary.dimensions.model_dump().items():
        lines.append(f"| {_DIMENSION_LABELS[key]} | {value if value is not None else 'N/A'} |")

    attention = sorted(
        [
            audit
            for audit in run.audits
            if not (
                audit.judgment.label == AutoLabel.SUPPORTED
                and audit.judgment.severity == Severity.NONE
            )
        ],
        key=lambda audit: _severity_rank(audit.judgment.severity),
    )
    confirmed = [
        audit
        for audit in run.audits
        if audit.judgment.label == AutoLabel.SUPPORTED
        and audit.judgment.severity == Severity.NONE
    ]

    lines.extend(["", f"## 待修改与复核（{len(attention)} 条）", ""])
    if not attention:
        lines.extend(["未发现需要修改或复核的论断。", ""])
    for audit in attention:
        lines.extend(_render_issue(audit))

    lines.extend([f"## 已确认内容（{len(confirmed)} 条）", ""])
    for audit in confirmed:
        location = f" · {audit.claim.report_location}" if audit.claim.report_location else ""
        lines.append(f"- **{audit.claim.claim_id}{location}**：{audit.claim.text}")
    lines.append("")

    lines.extend(["## 完整原文依据附录", ""])
    lines.append("以下保留模型选中的全部候选片段，便于复核。")
    lines.append("")
    for audit in run.audits:
        evidence = selected_evidence(audit)
        if not evidence:
            continue
        heading = _evidence_heading(audit)
        lines.extend(
            [
                f"### {audit.claim.claim_id} · {LABEL_NAMES[audit.judgment.label]}",
                "",
                f"**{heading}**",
                "",
            ]
        )
        for item in evidence:
            lines.extend(
                [
                    f"- 第 {item.page} 页，`{item.chunk_id}`",
                    "",
                    f"> {normalize_evidence_display(item.text)}",
                    "",
                ]
            )

    if run.parse_warnings:
        lines.extend(["## 解析提示", ""])
        lines.extend(f"- {warning}" for warning in run.parse_warnings)
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _severity_rank(severity: Severity) -> int:
    return {
        Severity.CRITICAL: 0,
        Severity.HIGH: 1,
        Severity.MEDIUM: 2,
        Severity.LOW: 3,
        Severity.NONE: 4,
    }[severity]


def _evidence_heading(audit: ClaimAudit) -> str:
    if audit.judgment.label == AutoLabel.NO_SUPPORT_FOUND:
        return "候选片段（不足以支持该论断）"
    if audit.judgment.label == AutoLabel.ABSTAIN:
        return "候选片段（尚不足以判断）"
    return "关键原文依据"


def _render_issue(audit: ClaimAudit) -> list[str]:
    judgment = audit.judgment
    lines = [
        f"### {audit.claim.claim_id} · {LABEL_NAMES[judgment.label]} · {SEVERITY_NAMES[judgment.severity]}",
        "",
        f"> {audit.claim.text}",
        "",
        *(
            [f"- 报告位置：{audit.claim.report_location}"]
            if audit.claim.report_location
            else []
        ),
        f"- 论断问题：{claim_error_name(judgment.claim_error_type)}",
        f"- 证据问题：{evidence_error_name(judgment.evidence_error_type)}",
        f"- 判断说明：{judgment.explanation}",
    ]
    if judgment.suggestion:
        lines.append(f"- 修改建议：{judgment.suggestion}")
    key_evidence = selected_evidence(audit)[:2]
    if key_evidence:
        lines.append(f"- {_evidence_heading(audit)}：")
        for item in key_evidence:
            excerpt = normalize_evidence_display(item.text)
            if len(excerpt) > 360:
                excerpt = excerpt[:359].rstrip() + "…"
            lines.extend(
                [
                    f"  - 第 {item.page} 页，`{item.chunk_id}`",
                    "",
                    f"    > {excerpt}",
                ]
            )
    lines.append("")
    return lines


def render_learning_markdown(report: LearningReport) -> str:
    lines = [
        "# 论文学习讲解",
        "",
        f"- 论文：{report.paper_title}",
        "",
        "## 一句话理解",
        "",
        report.one_sentence_summary,
        "",
    ]
    for section in report.sections:
        lines.extend([f"## {section.title}", "", section.overview, ""])
        for point in section.points:
            marker = "（关键知识点）" if point.key_point else ""
            lines.extend([f"### {point.title}{marker}", "", point.explanation, ""])
            if point.evidence:
                lines.extend(["原文证据：", ""])
                for anchor in point.evidence:
                    locator = f" · {anchor.locator}" if anchor.locator else ""
                    precision = "精确摘录" if anchor.quote else "证据块"
                    lines.append(
                        f"- 第 {anchor.page} 页 `{anchor.chunk_id}`{locator} · {precision}"
                    )
                    if anchor.quote:
                        lines.extend(["", f"> {anchor.quote}", ""])
                lines.append("")

    if report.suggested_pages:
        pages = "、".join(str(page) for page in report.suggested_pages)
        lines.extend(["## 建议重点阅读", "", f"第 {pages} 页", ""])
    return "\n".join(lines).strip() + "\n"
