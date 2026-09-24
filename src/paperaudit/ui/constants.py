from __future__ import annotations

from paperaudit.models import ClaimCategory, PeerReviewVenue


CATEGORY_LABELS = {
    ClaimCategory.RESEARCH_QUESTION: "研究问题",
    ClaimCategory.CONTRIBUTION: "核心贡献",
    ClaimCategory.METHOD: "方法",
    ClaimCategory.DATASET_SETUP: "数据集与实验设置",
    ClaimCategory.RESULTS: "主要结果",
    ClaimCategory.LIMITATIONS: "局限性",
}
FULL_SCOPE = list(CATEGORY_LABELS)
DIMENSION_NAMES = {
    "factual_support": "事实支持度",
    "evidence_correctness": "证据正确性",
    "evidence_completeness": "证据完整性",
    "numeric_consistency": "数字与指标一致性",
    "content_coverage": "内容覆盖度",
    "conclusion_boundary": "结论边界",
}

PEER_REVIEW_VENUE_OPTIONS = {
    PeerReviewVenue.GENERAL.value: "通用 AI/ML",
    PeerReviewVenue.IJCAI.value: "IJCAI",
    PeerReviewVenue.NEURIPS.value: "NeurIPS",
    PeerReviewVenue.ICLR.value: "ICLR",
    PeerReviewVenue.AAAI.value: "AAAI",
    PeerReviewVenue.CUSTOM.value: "自定义标准",
}
PEER_REVIEW_WEIGHT_LABELS = {
    "significance": "研究价值",
    "novelty": "创新性",
    "soundness": "技术可靠性",
    "experimental_rigor": "实验充分性",
    "clarity": "表达清晰度",
    "reproducibility": "可复现性",
}
