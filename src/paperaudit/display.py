"""Shared Chinese presentation labels and audit display statistics."""

from __future__ import annotations

from collections.abc import Sequence

from paperaudit.models import (
    AutoLabel,
    ClaimAudit,
    ClaimErrorType,
    EvidenceErrorType,
    Severity,
    ParsedPaper,
)


LABEL_NAMES = {
    AutoLabel.SUPPORTED: "支持",
    AutoLabel.PARTIALLY_SUPPORTED: "部分支持",
    AutoLabel.CONTRADICTED: "与原文冲突",
    AutoLabel.NO_SUPPORT_FOUND: "未找到支持证据",
    AutoLabel.ABSTAIN: "证据不足",
}

SEVERITY_NAMES = {
    Severity.NONE: "无风险",
    Severity.LOW: "低风险",
    Severity.MEDIUM: "中风险",
    Severity.HIGH: "高风险",
    Severity.CRITICAL: "严重",
}

CLAIM_ERROR_NAMES = {
    ClaimErrorType.NUMERIC_OR_METRIC_MISMATCH: "数字或指标不一致",
    ClaimErrorType.WRONG_ATTRIBUTION: "结果归属错误",
    ClaimErrorType.MISSING_CONDITION: "遗漏成立条件",
    ClaimErrorType.OVERGENERALIZATION: "过度概括",
    ClaimErrorType.EXTERNAL_HALLUCINATION: "引入论文外信息",
    ClaimErrorType.CONTRADICTION: "与原文含义相反",
}

EVIDENCE_ERROR_NAMES = {
    EvidenceErrorType.EVIDENCE_MISMATCH: "证据不匹配",
    EvidenceErrorType.FABRICATED_EVIDENCE: "证据不存在",
}


def label_counts(audits: Sequence[ClaimAudit]) -> dict[AutoLabel, int]:
    return {
        label: sum(audit.judgment.label == label for audit in audits)
        for label in AutoLabel
    }


def fully_supported_rate(audits: Sequence[ClaimAudit]) -> float:
    if not audits:
        return 0.0
    supported = sum(
        audit.judgment.label == AutoLabel.SUPPORTED for audit in audits
    )
    return round(supported / len(audits) * 100, 1)


def claim_error_name(value: ClaimErrorType | None) -> str:
    return CLAIM_ERROR_NAMES.get(value, "无") if value is not None else "无"


def evidence_error_name(value: EvidenceErrorType | None) -> str:
    return EVIDENCE_ERROR_NAMES.get(value, "无") if value is not None else "无"


def recover_paper_title(paper: ParsedPaper) -> str:
    """Use the first title block when stored PDF metadata is clearly truncated."""

    title = " ".join(paper.title.split()).strip()
    words = title.rstrip(" :;,-").casefold().split()
    if not words or words[-1] not in {
        "and", "as", "at", "by", "for", "from", "in", "of", "on", "or", "to", "with", "without"
    }:
        return title
    for chunk in paper.chunks:
        if chunk.page != 1:
            continue
        candidate = " ".join(chunk.content.split()).strip()
        if candidate.casefold().startswith(title.casefold()) and len(candidate) > len(title):
            return candidate[:240].strip()
    return f"{title}…"
