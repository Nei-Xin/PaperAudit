// Chinese presentation labels, ported from src/paperaudit/display.py,
// ui/constants.py and ui/peer_review.py so both UIs read the same.
import type {
  AutoLabel, ClaimCategory, ClaimErrorType, EvidenceErrorType, IssueCategory,
  IssueSeverity, IssueStatus, LearningSectionType, ReviewDecision, Severity, Venue,
} from "@/api/types";

export const LABEL_NAMES: Record<AutoLabel, string> = {
  SUPPORTED: "支持",
  PARTIALLY_SUPPORTED: "部分支持",
  CONTRADICTED: "与原文冲突",
  NO_SUPPORT_FOUND: "未找到支持证据",
  ABSTAIN: "证据不足",
};

/** Dot / text colour per label (tailwind classes). */
export const LABEL_TONE: Record<AutoLabel, { dot: string; chip: string }> = {
  SUPPORTED: { dot: "bg-ok", chip: "bg-ok-soft text-ok-text" },
  PARTIALLY_SUPPORTED: { dot: "bg-warn", chip: "bg-warn-soft text-warn-text" },
  CONTRADICTED: { dot: "bg-bad", chip: "bg-bad-soft text-bad" },
  NO_SUPPORT_FOUND: { dot: "bg-miss", chip: "bg-bad-soft text-bad-text" },
  ABSTAIN: { dot: "bg-mute", chip: "bg-line-soft text-ink-3" },
};

export const SEVERITY_NAMES: Record<Severity, string> = {
  none: "无风险", low: "低风险", medium: "中风险", high: "高风险", critical: "严重",
};

export const CATEGORY_LABELS: Record<ClaimCategory, string> = {
  research_question: "研究问题",
  contribution: "核心贡献",
  method: "方法",
  dataset_setup: "数据集与实验设置",
  results: "主要结果",
  limitations: "局限性",
  other: "其他",
};

export const CLAIM_ERROR_NAMES: Record<ClaimErrorType, string> = {
  numeric_or_metric_mismatch: "数字或指标不一致",
  wrong_attribution: "结果归属错误",
  missing_condition: "遗漏成立条件",
  overgeneralization: "过度概括",
  external_hallucination: "引入论文外信息",
  contradiction: "与原文含义相反",
};

export const EVIDENCE_ERROR_NAMES: Record<EvidenceErrorType, string> = {
  evidence_mismatch: "证据不匹配",
  fabricated_evidence: "证据不存在",
};

export const AUDIT_DIMENSION_NAMES: Record<string, string> = {
  factual_support: "事实支持度",
  evidence_correctness: "证据正确性",
  evidence_completeness: "证据完整性",
  numeric_consistency: "数字与指标一致性",
  content_coverage: "内容覆盖度",
  conclusion_boundary: "结论边界",
};

export const SECTION_LABELS: Record<LearningSectionType, string> = {
  research_problem: "研究问题",
  contributions: "主要贡献",
  method: "研究方法",
  experiments: "实验设计",
  results: "实验结果",
  limitations: "研究局限",
  key_terms: "关键术语",
};

export const DECISION_LABELS: Record<ReviewDecision, { en: string; zh: string; tone: string }> = {
  STRONG_ACCEPT: { en: "Strong Accept", zh: "强接收", tone: "text-ok-text" },
  WEAK_ACCEPT: { en: "Weak Accept", zh: "弱接收", tone: "text-ok-text" },
  BORDERLINE: { en: "Borderline", zh: "边缘", tone: "text-warn-text" },
  WEAK_REJECT: { en: "Weak Reject", zh: "弱拒稿", tone: "text-bad" },
  STRONG_REJECT: { en: "Strong Reject", zh: "强拒稿", tone: "text-bad" },
};

export const VENUE_LABELS: Record<Venue, string> = {
  general_ai_ml: "通用 AI/ML", ijcai: "IJCAI", neurips: "NeurIPS", iclr: "ICLR", aaai: "AAAI", custom: "自定义标准",
};

export const REVIEW_DIMENSION_NAMES: Record<string, string> = {
  significance: "研究价值",
  novelty: "创新性",
  soundness: "技术可靠性",
  experimental_rigor: "实验充分性",
  clarity: "表达清晰度",
  reproducibility: "可复现性",
};

export const ISSUE_SEVERITY_NAMES: Record<IssueSeverity, string> = {
  P0: "致命问题", P1: "主要问题", P2: "次要问题", P3: "文字问题",
};

export const ISSUE_CATEGORY_LABELS: Record<IssueCategory, string> = {
  correctness: "技术正确性",
  evidence: "证据与主张",
  evaluation: "实验与比较",
  novelty: "创新性与相关工作",
  reproducibility: "可复现性",
  ethics: "伦理与合规",
  clarity: "表达与结构",
  other: "其他",
};

export const ISSUE_STATUS_LABELS: Record<IssueStatus, string> = {
  open: "待处理",
  author_replied: "已回复",
  partially_resolved: "部分解决",
  resolved: "已解决",
  unresolved: "未解决",
  needs_manual_review: "需人工复核",
  ignored: "已忽略",
};

export function anchorLabel(anchor: { page: number | null; locator: string | null }): string {
  if (!anchor.page) return "页码未知";
  return anchor.locator ? `第 ${anchor.page} 页 · ${anchor.locator}` : `第 ${anchor.page} 页`;
}
