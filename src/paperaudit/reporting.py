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

SKIP_REASON_LABELS = {
    "heading": "标题或页码标记",
    "opinion": "主观意见",
    "out_of_scope": "不在本次审计范围",
    "non_claim": "非事实论断",
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
        f"- 已抽取论断的非弃权比例：{summary.audit_coverage}%（不代表报告原文抽取完整率）",
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

    if run.source_count:
        lines.extend([
            "", "## 报告原文抽取核对", "",
            f"原文 {run.source_count} 句；其中 {len(run.skipped_sources)} 句被模型标记为不抽取。",
            "逐句返回已校验；跳过理由和句内论断完整性仍需结合原文复核。", "",
        ])
        for source in run.skipped_sources:
            lines.append(f"- {source.report_location} · {SKIP_REASON_LABELS[source.reason]}：{source.text}")

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
        review_lines = _render_review(audit)
        if review_lines:
            lines.extend(review_lines)
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
    lines.extend(_render_review(audit))
    if judgment.suggestion:
        lines.append(f"- 修改建议：{judgment.suggestion}")
    if audit.claim.source_quote:
        lines.append(f"- 报告原句摘录：{audit.claim.source_quote}")
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


def _render_review(audit: ClaimAudit) -> list[str]:
    lines: list[str] = []
    gap = audit.candidate_gap_review
    if gap is not None:
        changed = (
            audit.judgment_before_candidate_gap_review is not None
            and audit.judgment_before_candidate_gap_review.label != audit.judgment.label
        )
        status = "复审后恢复支持" if changed and audit.judgment.label == AutoLabel.SUPPORTED else (
            "复审完成，最终判断未改变" if gap.evidence_relevant else "复审未发现足够依据"
        )
        lines.extend([f"- 候选证据复审：{status}", f"- 复审说明：{gap.explanation}"])
    review = audit.citation_review or audit.citation_review_before_repair
    if review is not None:
        status = "通过" if audit.citation_review is not None and review.complete and not review.missing_aspects else "未通过，需人工核对"
        lines.extend([f"- 引用完整性复核：{status}", f"- 引用复核说明：{review.explanation}"])
        for aspect in review.aspects:
            citation_text = "；".join(f"{item.evidence_id}：{item.quote}" for item in aspect.citations)
            lines.append(f"  - {aspect.aspect}：{aspect.reasoning}（引文：{citation_text}）")
        if review.missing_aspects:
            lines.append(f"- 引用缺口：{'、'.join(review.missing_aspects)}")
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
