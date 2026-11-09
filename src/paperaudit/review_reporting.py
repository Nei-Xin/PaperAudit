"""Peer review export without a dependency on Streamlit."""
from paperaudit.models import (PeerReviewReport, PeerReviewVenue, IssueCategory, HumanReviewDecision, ReviewConcern, IssueSeverity)

_DIMENSION_LABELS = {
    "significance": "研究价值",
    "novelty": "创新性",
    "soundness": "技术可靠性",
    "experimental_rigor": "实验充分性",
    "clarity": "表达清晰度",
    "reproducibility": "可复现性",
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

_HUMAN_DECISION_LABELS = {
    HumanReviewDecision.UNREVIEWED: "未复核",
    HumanReviewDecision.CONFIRMED: "确认问题",
    HumanReviewDecision.PARTIAL: "部分成立",
    HumanReviewDecision.FALSE_POSITIVE: "误报",
    HumanReviewDecision.INSUFFICIENT_EVIDENCE: "证据不足",
}

def _severity_for(concern: ReviewConcern) -> IssueSeverity:
    return concern.severity_level or (
        IssueSeverity.MAJOR if concern.severity.value == "major" else IssueSeverity.MINOR
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
