from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from difflib import SequenceMatcher
import hashlib
import json
import math
import re

from .config import Settings
from .audit_rules import (
    calibrate_judgment,
    choose_majority,
    judgment_signature,
    needs_evidence_retry,
    needs_second_pass,
    validate_judgment_references,
)
from .hy3_client import Hy3Client, Hy3ResponseError
from .models import (
    AtomicClaim,
    AnswerConclusion,
    AnswerStatus,
    AuditRun,
    AutoLabel,
    ClaimAudit,
    ClaimCategory,
    ClaimJudgment,
    JudgmentBatch,
    EvidenceAnchor,
    EvidenceCandidate,
    EvidenceErrorType,
    LearningReport,
    PeerReviewReport,
    PeerReviewRevision,
    RevisionDiff,
    RebuttalItem,
    ReviewConcern,
    IssueCategory,
    IssueSeverity,
    IssueStatus,
    IssueSupportType,
    HumanReviewDecision,
    LearningSectionType,
    PageRect,
    PaperAnswer,
    PaperChunk,
    ParsedPaper,
    ReportSection,
    ReviewDecision,
    PeerReviewVenue,
    RelatedWorkComparison,
    RelatedWorkReference,
    ReviewSeverity,
    Severity,
)
from .pdf_parser import parse_pdf
from .retrieval import EvidenceRetriever, build_claim_query, report_evidence_pages, supplement_claim_evidence
from .scoring import build_summary


ProgressCallback = Callable[[str, float], None]
MAX_AUDIT_REPORT_CHARS = 100_000

_PEER_SCORE_BANDS = {
    ReviewDecision.STRONG_ACCEPT: (9.0, 10.0),
    ReviewDecision.WEAK_ACCEPT: (7.0, 8.0),
    ReviewDecision.BORDERLINE: (5.0, 6.0),
    ReviewDecision.WEAK_REJECT: (3.0, 4.0),
    ReviewDecision.STRONG_REJECT: (1.0, 2.0),
}

_PEER_DECISION_TEXT = {
    ReviewDecision.STRONG_ACCEPT: "Strong Accept",
    ReviewDecision.WEAK_ACCEPT: "Weak Accept",
    ReviewDecision.BORDERLINE: "Borderline",
    ReviewDecision.WEAK_REJECT: "Weak Reject",
    ReviewDecision.STRONG_REJECT: "Strong Reject",
}
_PEER_DECISION_MENTION_PATTERN = re.compile(
    r"(?P<prefix>(?:最终|当前|综合|总体|投稿|评审|模拟|初步|因此|故|系统|\s)*"
    r"(?:建议|结论|推荐)(?:\s*(?:为|是|：|:|→|->))?\s*)"
    r"(?P<label>STRONG[ _]?ACCEPT|WEAK[ _]?ACCEPT|BORDERLINE|"
    r"WEAK[ _]?REJECT|STRONG[ _]?REJECT|Strong\s*Accept|Weak\s*Accept|"
    r"Borderline|Weak\s*Reject|Strong\s*Reject|强接收|弱接收|边缘|弱拒稿|强拒稿)"
    r"(?:（按当前评分标准重算）)?",
    re.IGNORECASE,
)
_PEER_DECISION_ALIASES = {
    ReviewDecision.STRONG_ACCEPT: ("STRONG_ACCEPT", "Strong Accept", "强接收"),
    ReviewDecision.WEAK_ACCEPT: ("WEAK_ACCEPT", "Weak Accept", "弱接收"),
    ReviewDecision.BORDERLINE: ("BORDERLINE", "Borderline", "边缘"),
    ReviewDecision.WEAK_REJECT: ("WEAK_REJECT", "Weak Reject", "弱拒稿"),
    ReviewDecision.STRONG_REJECT: ("STRONG_REJECT", "Strong Reject", "强拒稿"),
}

PEER_REVIEW_SCORE_CALCULATION_VERSION = "weighted-v1"
PEER_REVIEW_RUBRIC_CATALOG_VERSION = "catalog-v1"
PEER_REVIEW_RUBRIC_UPDATED_AT = "2026-08-31"
_PEER_REVIEW_RUBRIC_NOTES = {
    "general_ai_ml": "通用 AI/ML：均衡关注研究价值、创新性、技术可靠性和实验充分性。",
    "ijcai": "IJCAI：强调 AI 贡献、广泛意义、技术可靠性和完整评估。",
    "neurips": "NeurIPS：强调技术创新、严谨实验、强基线和统计可靠性。",
    "iclr": "ICLR：强调学习设定、方法/概念创新、清晰度和可复现性。",
    "aaai": "AAAI：强调有意义的 AI 贡献、完整评估和应用或理论相关性。",
}


def peer_review_rubric_metadata(
    venue: PeerReviewVenue | str,
    weights: dict[str, float] | None = None,
) -> tuple[str, str, str]:
    """Return a stable rubric version, update date and human-readable change note."""
    venue_value = getattr(venue, "value", str(venue))
    normalized = normalize_peer_review_weights(weights)
    if venue_value == PeerReviewVenue.CUSTOM.value:
        digest = hashlib.sha256(
            json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()[:8]
        return f"custom@1.0+{digest}", PEER_REVIEW_RUBRIC_UPDATED_AT, "自定义六维权重（已归一化）"
    note = _PEER_REVIEW_RUBRIC_NOTES.get(venue_value, _PEER_REVIEW_RUBRIC_NOTES["general_ai_ml"])
    return f"{venue_value}@1.0", PEER_REVIEW_RUBRIC_UPDATED_AT, note
DEFAULT_PEER_REVIEW_WEIGHTS: dict[str, float] = {
    "significance": 0.20,
    "novelty": 0.20,
    "soundness": 0.20,
    "experimental_rigor": 0.20,
    "clarity": 0.10,
    "reproducibility": 0.10,
}

_DIMENSION_ALIASES = {
    "研究价值": "significance",
    "significance": "significance",
    "创新性": "novelty",
    "novelty": "novelty",
    "技术可靠性": "soundness",
    "soundness": "soundness",
    "实验充分性": "experimental_rigor",
    "experimental_rigor": "experimental_rigor",
    "clarity": "clarity",
    "表达清晰度": "clarity",
    "reproducibility": "reproducibility",
    "可复现性": "reproducibility",
}


def normalize_peer_review_weights(weights: dict[str, float] | None = None) -> dict[str, float]:
    """Validate and normalize rubric weights while keeping all six dimensions explicit."""
    values = dict(DEFAULT_PEER_REVIEW_WEIGHTS)
    if weights:
        for name, value in weights.items():
            canonical = _DIMENSION_ALIASES.get(str(name).strip())
            if canonical is None:
                raise ValueError(f"未知评审维度权重：{name}")
            try:
                number = float(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"评审维度权重必须是数字：{name}") from exc
            if not math.isfinite(number) or number < 0:
                raise ValueError(f"评审维度权重必须是非负有限数字：{name}")
            values[canonical] = number
    total = sum(values.values())
    if total <= 0:
        raise ValueError("评审维度权重总和必须大于 0。")
    return {name: round(value / total, 6) for name, value in values.items()}


def calculate_peer_review_score(
    dimensions: Sequence[object],
    concerns: Sequence[ReviewConcern] = (),
    rubric_weights: dict[str, float] | None = None,
) -> tuple[float, ReviewDecision, dict[str, float], dict[str, float]]:
    """Calculate a reproducible 1-10 score and five-level recommendation."""
    weights = normalize_peer_review_weights(rubric_weights)
    weighted_sum = 0.0
    weight_sum = 0.0
    breakdown: dict[str, float] = {}
    for dimension in dimensions:
        raw_name = str(getattr(dimension, "name", "")).strip()
        canonical = _DIMENSION_ALIASES.get(raw_name)
        if canonical is None or canonical in breakdown:
            continue
        score = float(getattr(dimension, "score", 0))
        if not 1 <= score <= 5:
            continue
        weight = weights[canonical]
        weighted_sum += score * weight
        weight_sum += weight
        # Store each present dimension's effective contribution after
        # renormalizing when a legacy/model response omits a dimension.
        breakdown[canonical] = round(score * weight, 4)
    if weight_sum <= 0:
        raise ValueError("评审缺少可识别的六维评分。")
    weighted_mean = weighted_sum / weight_sum
    if weight_sum != 1.0:
        breakdown = {
            name: round(value / weight_sum, 4) for name, value in breakdown.items()
        }
    mapped_score = 1 + (weighted_mean - 1) * 9 / 4
    # Integer scores keep the public five bands (1-2, 3-4, …) unambiguous.
    score = float(max(1, min(10, math.floor(mapped_score + 0.5))))
    active_p0 = any(
        item.severity_level == IssueSeverity.FATAL
        and item.human_decision != HumanReviewDecision.FALSE_POSITIVE
        for item in concerns
    )
    if active_p0:
        score = min(score, 4.0)
    if score >= 9:
        decision = ReviewDecision.STRONG_ACCEPT
    elif score >= 7:
        decision = ReviewDecision.WEAK_ACCEPT
    elif score >= 5:
        decision = ReviewDecision.BORDERLINE
    elif score >= 3:
        decision = ReviewDecision.WEAK_REJECT
    else:
        decision = ReviewDecision.STRONG_REJECT
    metadata = {"weighted_mean": round(weighted_mean, 4), "mapped_score": round(mapped_score, 4)}
    return score, decision, breakdown, metadata


def _synchronize_peer_review_decision_text(text: str, decision: ReviewDecision) -> str:
    """Replace stale explicit recommendation mentions after deterministic rescoring."""
    if not text:
        return text
    final_label = _PEER_DECISION_TEXT[decision]

    def replace(match: re.Match[str]) -> str:
        raw_label = re.sub(r"[ _]", "", match.group("label")).casefold()
        expected = re.sub(r"[ _]", "", final_label).casefold()
        if raw_label == expected:
            return match.group(0)
        return f"{match.group('prefix')}{final_label}（按当前评分标准重算）"

    return _PEER_DECISION_MENTION_PATTERN.sub(replace, text)


def _synchronize_adjacent_decision_explanation(
    text: str, decision: ReviewDecision
) -> str:
    """Discard an adjacent-band explanation that explicitly rejects the final band."""
    if not text:
        return text
    aliases = _PEER_DECISION_ALIASES[decision]
    negative = r"(?:不建议|不推荐|不应|不宜|不是|并非|not\s+(?:a\s+)?)"
    if any(
        re.search(negative + r"\s*" + re.escape(alias), text, flags=re.IGNORECASE)
        for alias in aliases
    ):
        label = _PEER_DECISION_TEXT[decision]
        return (
            f"当前六维评分按所选评审标准重算为 {label}；原始相邻档位说明与重算结果不一致，"
            "请结合各维度评分和已列原文证据进行人工复核。"
        )
    return text


def recalculate_peer_review(report: PeerReviewReport, rubric_weights: dict[str, float] | None = None) -> PeerReviewReport:
    """Recompute the system score after human concern edits or legacy loading."""
    weights = normalize_peer_review_weights(rubric_weights or report.rubric_weights or None)
    concerns = [*report.major_concerns, *report.minor_concerns]
    score, decision, breakdown, _ = calculate_peer_review_score(report.dimensions, concerns, weights)
    return report.model_copy(update={
        "overall_score": score,
        "decision": decision,
        "summary": _synchronize_peer_review_decision_text(report.summary, decision),
        "decision_rationale": _synchronize_peer_review_decision_text(
            report.decision_rationale, decision
        ),
        "why_not_adjacent": _synchronize_adjacent_decision_explanation(
            report.why_not_adjacent, decision
        ),
        "rubric_weights": weights,
        "score_breakdown": breakdown,
        "score_calculation_version": PEER_REVIEW_SCORE_CALCULATION_VERSION,
    })


def peer_review_consistency_warnings(report: PeerReviewReport) -> list[str]:
    """Return actionable warnings when a generated review is internally inconsistent."""
    warnings: list[str] = []
    low, high = _PEER_SCORE_BANDS[report.decision]
    if not low <= report.overall_score <= high:
        warnings.append(
            f"综合评分 {report.overall_score:.1f} 不在 {report.decision.value} 建议区间 {low:.0f}-{high:.0f} 内。"
        )
    if report.confidence <= 2 and not report.confidence_rationale.strip():
        warnings.append("评审置信度较低，但没有说明导致不确定的证据缺口。")
    if report.decision in {ReviewDecision.WEAK_REJECT, ReviewDecision.STRONG_REJECT}:
        if not report.acceptance_blockers:
            warnings.append("拒稿建议缺少明确的接收阻碍。")
    if report.decision == ReviewDecision.STRONG_REJECT and not report.fatal_flaws:
        warnings.append("Strong Reject 建议缺少致命问题说明。")
    if report.decision == ReviewDecision.STRONG_ACCEPT and report.fatal_flaws:
        warnings.append("Strong Accept 不应同时列出致命问题，请复核结论。")
    if not report.why_not_adjacent.strip():
        warnings.append("缺少与相邻投稿建议档位的比较说明。")
    for concern in [*report.major_concerns, *report.minor_concerns]:
        severity = concern.severity_level
        if severity == IssueSeverity.FATAL and concern.severity.value != "major":
            warnings.append(f"问题“{concern.title}”标记为 P0，但未归入主要问题。")
        if severity in {IssueSeverity.FATAL, IssueSeverity.MAJOR} and not concern.evidence:
            warnings.append(f"问题“{concern.title}”为 {severity.value}，但没有可定位原文依据。")
        if concern.confidence <= 2 and not concern.evidence:
            warnings.append(f"问题“{concern.title}”置信度较低且缺少证据，请人工复核。")
        if concern.support_type == IssueSupportType.FACT and not concern.evidence:
            warnings.append(f"问题“{concern.title}”标记为事实判断，但没有可定位原文依据。")
        # An evidence-gap concern may legitimately cite a nearby passage as
        # context.  Do not warn merely because ``insufficient_evidence`` and a
        # quote coexist; the support type describes the claim, not the absence
        # of a useful locator.
        if severity in {IssueSeverity.FATAL, IssueSeverity.MAJOR} and concern.confidence <= 2:
            warnings.append(f"问题“{concern.title}”为 {severity.value} 且置信度不高，不应直接作为确定性拒稿依据。")
    return warnings


def _dedupe_review_concerns(concerns: Sequence[ReviewConcern]) -> list[ReviewConcern]:
    """Collapse duplicate critiques without hiding distinct evidence or actions.

    Models often return the same issue twice with slightly different wording.  A
    title-only key is too aggressive (the same topic may have different evidence),
    so we require either identical evidence, or the same normalized claim *and*
    remediation.  This is intentionally lexical and deterministic; it is not an
    embedding-based semantic merge.
    """

    def normalize(value: object) -> str:
        text = str(value or "").casefold()
        text = re.sub(r"[^\w\u4e00-\u9fff]+", " ", text)
        return " ".join(text.split())

    def token_set(value: object) -> set[str]:
        return {token for token in normalize(value).split() if len(token) >= 2}

    result: list[ReviewConcern] = []
    seen_evidence_titles: set[tuple[tuple[str, ...], str, str]] = set()
    seen_claim_actions: set[tuple[str, str, str]] = set()
    for concern in concerns:
        evidence_key = tuple(sorted(anchor.chunk_id for anchor in concern.evidence))
        title_key = normalize(concern.title)
        claim_text = " ".join(
            part
            for part in (concern.title, concern.description, concern.why_it_matters)
            if part
        )
        claim_tokens = token_set(claim_text)
        action_key = normalize(concern.suggestion)
        category_key = normalize(getattr(concern.category, "value", concern.category))
        # A compact claim fingerprint keeps common Chinese stop-words from making
        # unrelated concerns collide while still catching paraphrased duplicates.
        claim_key = " ".join(sorted(claim_tokens))
        fingerprint = (category_key, claim_key, action_key)
        if evidence_key and (evidence_key, category_key, title_key) in seen_evidence_titles:
            continue
        if claim_key and action_key and fingerprint in seen_claim_actions:
            continue
        if evidence_key:
            seen_evidence_titles.add((evidence_key, category_key, title_key))
        if claim_key and action_key:
            seen_claim_actions.add(fingerprint)
        result.append(concern)
    return result


_CONCERN_NUMBER_PATTERN = re.compile(r"(?<![A-Za-z])\d+(?:\.\d+)?\s*%?")
_CONCERN_METRIC_PATTERN = re.compile(
    r"\b(?:accuracy|precision|recall|f1|bleu|rouge|auc|rmse|mae|sota)\b|"
    r"准确率|精确率|召回率|宏平均|微平均|指标|数据集|模型|baseline|基线",
    re.IGNORECASE,
)
_CONCERN_ENTITY_PATTERN = re.compile(
    r"\b(?:[A-Z][A-Za-z0-9-]{1,}|[A-Za-z][A-Za-z0-9-]*(?:dataset|bench|net|bert|gpt|llama))\b"
)


def _concern_consistency_warnings(concern: ReviewConcern) -> list[str]:
    """Check that concrete numeric/metric assertions occur in cited quotes."""
    # ``insufficient_evidence`` deliberately describes an unverified gap.  Its
    # prose often mentions the numbers/entities that would need checking; those
    # are not asserted paper facts and should not trigger numeric mismatch
    # warnings or force a second downgrade.
    if concern.support_type == IssueSupportType.INSUFFICIENT_EVIDENCE:
        return []
    if not concern.evidence:
        warnings: list[str] = []
        if concern.support_type == IssueSupportType.FACT:
            warnings.append(f"问题“{concern.title}”标记为事实判断，但没有可逐字核验的引用。")
        return warnings
    narrative = " ".join(
        part for part in (concern.title, concern.description, concern.why_it_matters) if part
    )
    # The quote is the preferred citation, while the locally enriched anchor
    # text is a second verification surface for long numeric/table passages.
    # Checking both avoids downgrading a valid issue merely because the model
    # selected a shorter quote from the same verified chunk.
    evidence_text = " ".join(
        part for anchor in concern.evidence for part in (anchor.quote or "", anchor.text or "") if part
    )
    warnings: list[str] = []
    narrative_numbers = {
        re.sub(r"\s+", "", match)
        for match in _CONCERN_NUMBER_PATTERN.findall(narrative)
    }
    evidence_numbers = {
        re.sub(r"\s+", "", match)
        for match in _CONCERN_NUMBER_PATTERN.findall(evidence_text)
    }
    missing_numbers = sorted(narrative_numbers - evidence_numbers)
    if missing_numbers:
        warnings.append(
            f"问题“{concern.title}”中的数字 {', '.join(missing_numbers)} 未出现在引用原文中。"
        )
    # A metric assertion without any metric-bearing text in the quote is a useful
    # signal for review, but do not reject ordinary qualitative concerns.
    if _CONCERN_METRIC_PATTERN.search(narrative) and not _CONCERN_METRIC_PATTERN.search(evidence_text):
        warnings.append(f"问题“{concern.title}”的指标/数据集/模型表述无法在引用原文中核验。")
    narrative_entities = {token.casefold() for token in _CONCERN_ENTITY_PATTERN.findall(narrative)}
    quoted_entities = {token.casefold() for token in _CONCERN_ENTITY_PATTERN.findall(evidence_text)}
    # Only flag distinctive ASCII entity names (e.g. GPT-4, ImageNet, BLEU), not
    # ordinary prose words, so this remains a conservative consistency check.
    missing_entities = sorted(narrative_entities - quoted_entities)
    if missing_entities:
        warnings.append(
            f"问题“{concern.title}”中的模型/数据集名称 {', '.join(missing_entities[:4])} 未出现在引用原文中。"
        )
    return warnings


def build_revision_diff(old: ParsedPaper, new: ParsedPaper) -> RevisionDiff:
    """Build a compact, paragraph-level diff between two parsed paper versions."""
    old_texts = [chunk.content.strip() for chunk in old.chunks if chunk.content.strip()]
    new_texts = [chunk.content.strip() for chunk in new.chunks if chunk.content.strip()]
    matcher = SequenceMatcher(a=old_texts, b=new_texts, autojunk=False)
    added = removed = changed = 0
    added_samples: list[str] = []
    removed_samples: list[str] = []
    changed_samples: list[str] = []
    for tag, old_start, old_end, new_start, new_end in matcher.get_opcodes():
        if tag == "insert":
            added += new_end - new_start
            added_samples.extend(new_texts[new_start:new_end][:2])
        elif tag == "delete":
            removed += old_end - old_start
            removed_samples.extend(old_texts[old_start:old_end][:2])
        elif tag == "replace":
            changed += max(old_end - old_start, new_end - new_start)
            changed_samples.extend(new_texts[new_start:new_end][:2])
    summary = f"新增 {added} 段，删除 {removed} 段，修改 {changed} 段；页数 {old.page_count} → {new.page_count}。"
    return RevisionDiff(
        added_chunks=added,
        removed_chunks=removed,
        changed_chunks=changed,
        added_samples=added_samples[:4],
        removed_samples=removed_samples[:4],
        changed_samples=changed_samples[:4],
        summary=summary,
    )

_LOCATION_QUESTION_PATTERN = re.compile(
    r"第\s*几\s*页|哪(?:些|几)?\s*页|在(?:哪|哪里|哪儿)|位于|位置|"
    r"\bwhere\b|\bwhich\s+pages?\b|\bwhat\s+pages?\b",
    re.IGNORECASE,
)
_EXISTENCE_QUESTION_PATTERN = re.compile(
    r"有没有|有无|是否(?:有|包含|存在|提到)|有.+吗|包含.+吗|提到.+吗|"
    r"\bdoes\b.+\bhave\b|\bis\s+there\b|\bcontains?\b",
    re.IGNORECASE,
)
_DOCUMENT_STRUCTURE_TARGETS = (
    (
        "补充材料",
        ("补充材料", "补充内容", "supplementary", "supplemental"),
        ("supplementary material", "supplemental material", "supplementary"),
    ),
    (
        "附录",
        ("附录", "appendix", "appendices"),
        ("appendix", "appendices"),
    ),
    (
        "参考文献",
        ("参考文献", "references", "bibliography"),
        ("references", "bibliography"),
    ),
    (
        "致谢",
        ("致谢", "acknowledgment", "acknowledgement"),
        ("acknowledgments", "acknowledgements", "acknowledgment", "acknowledgement"),
    ),
)
_LOCATION_SECTION_TERMS = (
    (
        LearningSectionType.RESULTS,
        ("实验结果", "结果", "性能", "对比实验", "消融", "results", "performance"),
    ),
    (
        LearningSectionType.EXPERIMENTS,
        (
            "实验内容",
            "实验部分",
            "实验设计",
            "实验设置",
            "实验",
            "数据集",
            "评估设置",
            "experiments",
            "dataset",
            "evaluation setup",
        ),
    ),
    (
        LearningSectionType.METHOD,
        ("方法论", "研究方法", "方法", "框架", "流程", "methodology", "method", "framework"),
    ),
    (
        LearningSectionType.CONTRIBUTIONS,
        ("主要贡献", "贡献", "创新", "contribution", "innovation"),
    ),
    (
        LearningSectionType.RESEARCH_PROBLEM,
        ("研究问题", "研究目标", "research problem", "objective"),
    ),
    (
        LearningSectionType.LIMITATIONS,
        ("研究局限", "局限", "限制", "不足", "limitation"),
    ),
    (
        LearningSectionType.KEY_TERMS,
        ("关键术语", "术语", "概念", "key terms", "terminology"),
    ),
)
_LOCATION_SECTION_NAMES = {
    LearningSectionType.RESEARCH_PROBLEM: "研究问题",
    LearningSectionType.CONTRIBUTIONS: "主要贡献",
    LearningSectionType.METHOD: "研究方法",
    LearningSectionType.EXPERIMENTS: "实验设计",
    LearningSectionType.RESULTS: "实验结果",
    LearningSectionType.LIMITATIONS: "研究局限",
    LearningSectionType.KEY_TERMS: "关键术语",
}
_SECTION_HEADING_TERMS = {
    LearningSectionType.RESEARCH_PROBLEM: ("introduction",),
    LearningSectionType.CONTRIBUTIONS: ("introduction",),
    LearningSectionType.METHOD: ("methodology", "methods", "method", "approach", "framework"),
    LearningSectionType.EXPERIMENTS: ("experiments", "experimental", "evaluation"),
    LearningSectionType.RESULTS: ("results", "experiments", "experimental", "evaluation"),
    LearningSectionType.LIMITATIONS: ("limitations", "discussion", "conclusion"),
    LearningSectionType.KEY_TERMS: (),
}


@dataclass(frozen=True)
class _PaperSectionLocation:
    number: str
    title: str
    start_page: int
    end_page: int
    heading_chunk: PaperChunk


@dataclass(frozen=True)
class _DocumentStructureTarget:
    name: str
    heading_terms: tuple[str, ...]


@dataclass(frozen=True)
class LearningPagePoint:
    section_type: LearningSectionType
    section_title: str
    title: str
    explanation: str
    evidence: tuple[EvidenceAnchor, ...]


@dataclass(frozen=True)
class LearningPageContext:
    page: int
    paper_section: str | None
    report_section: str | None
    relation: str | None
    points: tuple[LearningPagePoint, ...]
    suggested_questions: tuple[str, ...]

    @property
    def chunk_ids(self) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(
                anchor.chunk_id
                for point in self.points
                for anchor in point.evidence
            )
        )


@dataclass(frozen=True)
class LearningLogicNode:
    role: str
    title: str
    explanation: str
    evidence: tuple[EvidenceAnchor, ...]


def _noop_progress(_: str, __: float) -> None:
    return None


def validate_audit_report_text(report_text: str) -> None:
    """Reject empty or unbounded report input before persistence or API calls."""

    if not report_text.strip():
        raise ValueError("报告内容不能为空。")
    if len(report_text) > MAX_AUDIT_REPORT_CHARS:
        raise ValueError("报告内容超过 100,000 个字符，请精简或拆分后重试。")


def _numbered_heading(chunk: PaperChunk) -> tuple[str, str] | None:
    lines = [line.strip() for line in chunk.content.splitlines() if line.strip()]
    if not lines:
        return None
    number = ""
    title = ""
    if re.fullmatch(r"\d+(?:\.\d+)*\.?", lines[0]) and len(lines) > 1:
        number, title = lines[0].rstrip("."), lines[1]
    else:
        match = re.fullmatch(r"(\d+(?:\.\d+)*)\.?\s+(.+)", lines[0])
        if match:
            number, title = match.groups()
    if (
        not number
        or not re.search(r"[A-Za-z]", title)
        or len(title) > 100
        or title.rstrip().endswith("?")
    ):
        return None
    return number, title


def _paper_sections(paper: ParsedPaper) -> list[_PaperSectionLocation]:
    numbered = [
        (number, title, chunk)
        for chunk in paper.chunks
        if (heading := _numbered_heading(chunk)) is not None
        for number, title in [heading]
    ]
    top_level = [item for item in numbered if "." not in item[0]]
    top_level.sort(key=lambda item: (item[2].page, int(item[0])))
    sections: list[_PaperSectionLocation] = []
    for index, (number, title, chunk) in enumerate(top_level):
        subsection_pages = [
            item_chunk.page
            for item_number, _, item_chunk in numbered
            if item_number.startswith(f"{number}.")
        ]
        next_start = (
            top_level[index + 1][2].page
            if index + 1 < len(top_level)
            else paper.page_count + 1
        )
        end_page = max(
            [chunk.page, next_start - 1, *subsection_pages],
        )
        end_page = min(end_page, paper.page_count)
        sections.append(
            _PaperSectionLocation(
                number=number,
                title=title,
                start_page=chunk.page,
                end_page=end_page,
                heading_chunk=chunk,
            )
        )
    return sections


def _document_structure_target(question: str) -> _DocumentStructureTarget | None:
    normalized = question.lower()
    for name, question_terms, heading_terms in _DOCUMENT_STRUCTURE_TARGETS:
        if any(term in normalized for term in question_terms):
            return _DocumentStructureTarget(name=name, heading_terms=heading_terms)
    return None


def _find_document_heading(
    paper: ParsedPaper,
    target: _DocumentStructureTarget,
) -> PaperChunk | None:
    for chunk in paper.chunks:
        lines = [line.strip() for line in chunk.content.splitlines() if line.strip()]
        if not lines:
            continue
        first_line = re.sub(r"\s+", " ", lines[0]).strip(" :.-").lower()
        if any(
            first_line == term or first_line.startswith(f"{term} ")
            for term in target.heading_terms
        ):
            return chunk
    return None


def _document_structure_answer(
    question: str,
    paper: ParsedPaper,
) -> PaperAnswer | None:
    target = _document_structure_target(question)
    is_location = bool(_LOCATION_QUESTION_PATTERN.search(question))
    is_existence = bool(_EXISTENCE_QUESTION_PATTERN.search(question))
    if target is None or not (is_location or is_existence):
        return None

    heading_chunk = _find_document_heading(paper, target)
    if heading_chunk is not None:
        if is_location:
            answer = f"{target.name}从第 {heading_chunk.page} 页开始。"
        else:
            answer = f"当前 PDF 中识别到{target.name}，从第 {heading_chunk.page} 页开始。"
        return PaperAnswer(
            question=question,
            answer=answer,
            status=AnswerStatus.ANSWERED,
            citations=[
                EvidenceAnchor(
                    chunk_id=heading_chunk.chunk_id,
                    page=heading_chunk.page,
                    text=heading_chunk.content.splitlines()[0].strip(),
                    context_text=heading_chunk.content,
                    rects=heading_chunk.rects[:1],
                )
            ],
        )

    mentions_by_page: dict[int, PaperChunk] = {}
    for chunk in paper.chunks:
        lowered = chunk.content.lower()
        if any(term in lowered for term in target.heading_terms):
            mentions_by_page.setdefault(chunk.page, chunk)
    if mentions_by_page:
        pages = "、".join(str(page) for page in sorted(mentions_by_page))
        return PaperAnswer(
            question=question,
            answer=(
                f"未识别到独立的{target.name}章节，但全文文本在第 {pages} 页出现了相关提及。"
            ),
            status=AnswerStatus.ANSWERED,
            citations=[
                EvidenceAnchor(
                    chunk_id=chunk.chunk_id,
                    page=page,
                    text=chunk.content,
                    rects=chunk.rects,
                )
                for page, chunk in sorted(mentions_by_page.items())
            ],
        )

    return PaperAnswer(
        question=question,
        answer=f"当前 PDF 的章节标题和全文文本索引中未检索到{target.name}。",
        status=AnswerStatus.ANSWERED,
    )


def _paper_location_answer(
    question: str,
    paper: ParsedPaper,
) -> PaperAnswer | None:
    if not _LOCATION_QUESTION_PATTERN.search(question):
        return None
    normalized = question.lower()
    section_type = next(
        (
            candidate_type
            for candidate_type, terms in _LOCATION_SECTION_TERMS
            if any(term in normalized for term in terms)
        ),
        None,
    )
    if section_type is None:
        return PaperAnswer(
            question=question,
            answer="请说明需要定位研究问题、主要贡献、研究方法、实验或研究局限中的哪一部分。",
            status=AnswerStatus.INSUFFICIENT_EVIDENCE,
        )

    sections = _paper_sections(paper)
    section = next(
        (
            candidate
            for heading_term in _SECTION_HEADING_TERMS[section_type]
            for candidate in sections
            if heading_term in candidate.title.lower()
        ),
        None,
    )
    if section is None:
        section_name = _LOCATION_SECTION_NAMES[section_type]
        return PaperAnswer(
            question=question,
            answer=f"未在 PDF 中识别到独立的{section_name}章节标题，暂时无法可靠定位。",
            status=AnswerStatus.INSUFFICIENT_EVIDENCE,
        )

    if section.start_page == section.end_page:
        page_text = f"第 {section.start_page} 页"
    else:
        page_text = f"第 {section.start_page}—{section.end_page} 页"
    section_name = _LOCATION_SECTION_NAMES[section_type]
    heading_rects = section.heading_chunk.rects[:2]
    heading_text = f"{section.number} {section.title}"
    return PaperAnswer(
        question=question,
        answer=(
            f"{section_name}相关内容位于“{section.title}”章节（{page_text}），"
            f"章节从第 {section.start_page} 页开始。"
        ),
        status=AnswerStatus.ANSWERED,
        citations=[
            EvidenceAnchor(
                chunk_id=section.heading_chunk.chunk_id,
                page=section.start_page,
                text=heading_text,
                context_text=section.heading_chunk.content,
                rects=heading_rects,
            )
        ],
    )


def _neighbor_context(
    chunk_id: str,
    chunks: list[PaperChunk],
    chunk_positions: dict[str, int],
) -> str | None:
    """Return immediate same-page context without changing the cited evidence block."""
    index = chunk_positions[chunk_id]
    current = chunks[index]
    context_parts: list[str] = []
    for neighbor_index, label in ((index - 1, "前文"), (index + 1, "后文")):
        if 0 <= neighbor_index < len(chunks):
            neighbor = chunks[neighbor_index]
            if neighbor.page == current.page:
                context_parts.append(
                    f"{label} · {neighbor.chunk_id}\n{neighbor.content}"
                )
    return "\n\n".join(context_parts) or None


def refresh_learning_report_evidence(
    report: LearningReport,
    paper: ParsedPaper,
) -> LearningReport:
    """Rebuild every report anchor from the local PDF, including legacy projects."""

    refreshed_sections: list[ReportSection] = []
    for section in report.sections:
        refreshed_points = []
        for point in section.points:
            refreshed_anchors = refresh_evidence_anchors(point.evidence, paper)
            refreshed_points.append(point.model_copy(update={"evidence": refreshed_anchors}))
        refreshed_sections.append(section.model_copy(update={"points": refreshed_points}))
    return report.model_copy(
        update={"paper_title": paper.title, "sections": refreshed_sections}
    )


def refresh_evidence_anchors(
    evidence: Sequence[EvidenceAnchor],
    paper: ParsedPaper,
) -> list[EvidenceAnchor]:
    """Rebuild citation metadata from the trusted local PDF index."""

    chunk_map = {chunk.chunk_id: chunk for chunk in paper.chunks}
    chunk_positions = {chunk.chunk_id: index for index, chunk in enumerate(paper.chunks)}
    refreshed: list[EvidenceAnchor] = []
    seen: set[str] = set()
    for anchor in evidence:
        chunk = chunk_map.get(anchor.chunk_id)
        if chunk is None or chunk.chunk_id in seen:
            continue
        seen.add(chunk.chunk_id)
        quote = (
            _validated_evidence_quote(anchor.quote, chunk.content)
            if anchor.quote
            else None
        )
        refreshed.append(
            EvidenceAnchor(
                chunk_id=chunk.chunk_id,
                page=chunk.page,
                text=chunk.content,
                quote=quote,
                locator=_evidence_locator(
                    chunk.chunk_id,
                    paper.chunks,
                    chunk_positions,
                ),
                context_text=_neighbor_context(
                    chunk.chunk_id,
                    paper.chunks,
                    chunk_positions,
                ),
                rects=_quote_rects(chunk, quote),
            )
        )
    return refreshed


_FIGURE_TABLE_CAPTION_PATTERN = re.compile(
    r"^\s*(Figure|Fig\.?|Table)\s*(\d+(?:[A-Za-z]|\([A-Za-z]\))?)"
    r"\s*(?=[:.]|\s|$)",
    re.IGNORECASE,
)


def _validated_evidence_quote(requested: str, source: str) -> str | None:
    quote = re.sub(r"\s+", " ", requested).strip(" \t\r\n\"'“”‘’…")
    normalized_source = re.sub(r"\s+", " ", source).strip()
    if len(quote) < 8 or len(quote) > 320:
        return None
    if quote.casefold() not in normalized_source.casefold():
        return None
    return quote


def _quote_rects(chunk: PaperChunk, quote: str | None) -> list[dict[str, float]]:
    """Return PDF rectangles in a form accepted by strict Pydantic models.

    Parsed chunks expose ``PageRect`` model instances, while ``EvidenceAnchor``
    is built with strict validation.  Passing those instances through directly
    fails on rerender (and made the UI appear inconsistently across layouts), so
    normalize them to plain dictionaries at this boundary.
    """
    source_rects = [rect.model_dump() for rect in chunk.rects]
    if not quote:
        return source_rects
    lines = [re.sub(r"\s+", " ", line).strip() for line in chunk.content.splitlines()]
    lines = [line for line in lines if line]
    if not lines or len(lines) != len(source_rects):
        return source_rects
    joined = " ".join(lines)
    start = joined.casefold().find(quote.casefold())
    if start < 0:
        return source_rects
    end = start + len(quote)
    selected_rects: list[dict[str, float]] = []
    cursor = 0
    for line, rect in zip(lines, source_rects, strict=True):
        line_start = cursor
        line_end = cursor + len(line)
        if line_start < end and line_end > start:
            selected_rects.append(rect)
        cursor = line_end + 1
    return selected_rects or source_rects


def _evidence_locator(
    chunk_id: str,
    chunks: list[PaperChunk],
    chunk_positions: dict[str, int],
) -> str | None:
    index = chunk_positions[chunk_id]
    current = chunks[index]
    parts: list[str] = []
    for heading_index in range(index, -1, -1):
        heading = _numbered_heading(chunks[heading_index])
        if heading is not None:
            parts.append(f"§{heading[0]} {heading[1]}")
            break

    paragraph_number = _paragraph_number(index, chunks)
    if paragraph_number is not None:
        parts.append(f"第 {paragraph_number} 段")

    nearby_texts = [current.content]
    for neighbor_index in (index - 1, index + 1):
        if 0 <= neighbor_index < len(chunks) and chunks[neighbor_index].page == current.page:
            nearby_texts.append(chunks[neighbor_index].content)
    object_match = next(
        (
            match
            for nearby_text in nearby_texts
            for line in nearby_text.splitlines()
            if (match := _FIGURE_TABLE_CAPTION_PATTERN.match(line)) is not None
        ),
        None,
    )
    if object_match:
        object_kind = "Table" if object_match.group(1).lower().startswith("table") else "Figure"
        object_number = object_match.group(2).replace("(", "").replace(")", "")
        parts.append(f"{object_kind} {object_number}")
    return " · ".join(parts) or None


def _paragraph_number(index: int, chunks: list[PaperChunk]) -> int | None:
    """Return a best-effort paragraph ordinal within the nearest numbered section."""

    current = chunks[index]
    if _numbered_heading(current) is not None:
        return None
    if any(
        _FIGURE_TABLE_CAPTION_PATTERN.match(line)
        for line in current.content.splitlines()
    ):
        return None

    section_start: int | None = None
    for candidate_index in range(index - 1, -1, -1):
        if _numbered_heading(chunks[candidate_index]) is not None:
            section_start = candidate_index + 1
            break
    if section_start is None:
        return None

    body_indices = [
        candidate_index
        for candidate_index in range(section_start, index + 1)
        if _numbered_heading(chunks[candidate_index]) is None
        and not any(
            _FIGURE_TABLE_CAPTION_PATTERN.match(line)
            for line in chunks[candidate_index].content.splitlines()
        )
    ]
    try:
        return body_indices.index(index) + 1
    except ValueError:
        return None


def build_learning_logic_chain(report: LearningReport) -> tuple[LearningLogicNode, ...]:
    """Build a compact, evidence-backed paper logic chain from existing report points."""

    sections = {section.section_type: section for section in report.sections}

    def evidenced_points(section_type: LearningSectionType):
        section = sections.get(section_type)
        if section is None:
            return []
        return [point for point in section.points if point.evidence]

    nodes: list[LearningLogicNode] = []
    problem_points = evidenced_points(LearningSectionType.RESEARCH_PROBLEM)
    if problem_points:
        point = problem_points[0]
        nodes.append(
            LearningLogicNode(
                role="问题",
                title=point.title,
                explanation=point.explanation,
                evidence=tuple(point.evidence),
            )
        )
    if len(problem_points) > 1:
        point = problem_points[1]
        nodes.append(
            LearningLogicNode(
                role="原因与约束",
                title=point.title,
                explanation=point.explanation,
                evidence=tuple(point.evidence),
            )
        )

    solution_points = evidenced_points(LearningSectionType.CONTRIBUTIONS)
    if not solution_points:
        solution_points = evidenced_points(LearningSectionType.METHOD)
    if solution_points:
        point = solution_points[0]
        nodes.append(
            LearningLogicNode(
                role="作者方案",
                title=point.title,
                explanation=point.explanation,
                evidence=tuple(point.evidence),
            )
        )

    verification_points = evidenced_points(LearningSectionType.RESULTS)
    if not verification_points:
        verification_points = evidenced_points(LearningSectionType.EXPERIMENTS)
    if verification_points:
        point = verification_points[0]
        nodes.append(
            LearningLogicNode(
                role="验证证据",
                title=point.title,
                explanation=point.explanation,
                evidence=tuple(point.evidence),
            )
        )
    return tuple(nodes)


def _report_section_for_paper_heading(title: str) -> LearningSectionType | None:
    normalized = title.casefold()
    keyword_map = (
        (LearningSectionType.RESULTS, ("result", "analysis")),
        (LearningSectionType.EXPERIMENTS, ("experiment", "evaluation", "dataset")),
        (LearningSectionType.METHOD, ("method", "approach", "framework", "system")),
        (LearningSectionType.LIMITATIONS, ("limitation", "discussion", "conclusion")),
        (LearningSectionType.RESEARCH_PROBLEM, ("introduction", "background")),
    )
    return next(
        (
            section_type
            for section_type, keywords in keyword_map
            if any(keyword in normalized for keyword in keywords)
        ),
        None,
    )


def build_learning_page_context(
    report: LearningReport,
    paper: ParsedPaper,
    page: int,
) -> LearningPageContext:
    """Resolve a page to existing report knowledge without making a model call."""

    if not 1 <= page <= paper.page_count:
        raise ValueError("PDF 页码超出范围。")

    paper_section = next(
        (
            section
            for section in _paper_sections(paper)
            if section.start_page <= page <= section.end_page
        ),
        None,
    )
    paper_section_label = (
        f"§{paper_section.number} {paper_section.title}"
        if paper_section is not None
        else None
    )

    page_points: list[LearningPagePoint] = []
    for section in report.sections:
        for point in section.points:
            page_evidence = tuple(anchor for anchor in point.evidence if anchor.page == page)
            if not page_evidence:
                continue
            page_points.append(
                LearningPagePoint(
                    section_type=section.section_type,
                    section_title=section.title,
                    title=point.title,
                    explanation=point.explanation,
                    evidence=page_evidence,
                )
            )

    report_section = None
    if page_points:
        mapped_type = page_points[0].section_type
    elif paper_section is not None:
        mapped_type = _report_section_for_paper_heading(paper_section.title)
    else:
        mapped_type = None
    mapped_section = next(
        (section for section in report.sections if section.section_type == mapped_type),
        None,
    )
    relation = None
    if mapped_section is not None:
        report_section = mapped_section.title
        if paper_section_label:
            relation = (
                f"本页位于论文“{paper_section_label}”，对应讲解中的“{mapped_section.title}”。"
                f"{mapped_section.overview}"
            )
        else:
            relation = f"本页对应讲解中的“{mapped_section.title}”。{mapped_section.overview}"

    questions: list[str] = []
    if page_points:
        questions.append(f'“{page_points[0].title}”在第 {page} 页由哪些原文证据支持？')
    if paper_section is not None:
        questions.append(
            f'请结合第 {page} 页解释“{paper_section.title}”在论文整体方法中的作用。'
        )
    if mapped_section is not None:
        questions.append(f'第 {page} 页的内容如何支撑“{mapped_section.title}”？')
    if not questions:
        questions.append(f"请解释论文第 {page} 页的主要内容，并指出可验证的原文依据。")

    return LearningPageContext(
        page=page,
        paper_section=paper_section_label,
        report_section=report_section,
        relation=relation,
        points=tuple(page_points),
        suggested_questions=tuple(dict.fromkeys(questions))[:3],
    )


def _expand_question_candidates(
    candidates: list[EvidenceCandidate],
    chunks: list[PaperChunk],
    limit: int = 10,
) -> list[EvidenceCandidate]:
    """Add immediate same-page neighbors so broad answers and table rows retain context."""
    positions = {chunk.chunk_id: index for index, chunk in enumerate(chunks)}
    expanded: list[tuple[PaperChunk, float]] = []
    seen: set[str] = set()
    for candidate in candidates:
        index = positions.get(candidate.chunk_id)
        if index is None:
            continue
        for neighbor_index, score_offset in ((index, 0.0), (index - 1, -0.1), (index + 1, -0.1)):
            if not 0 <= neighbor_index < len(chunks):
                continue
            chunk = chunks[neighbor_index]
            if chunk.page != candidate.page or chunk.chunk_id in seen:
                continue
            seen.add(chunk.chunk_id)
            expanded.append((chunk, candidate.score + score_offset))
            if len(expanded) >= limit:
                break
        if len(expanded) >= limit:
            break
    return [
        EvidenceCandidate(
            evidence_id=f"Q_e{index + 1}",
            chunk_id=chunk.chunk_id,
            page=chunk.page,
            text=chunk.content,
            score=round(score, 6),
        )
        for index, (chunk, score) in enumerate(expanded)
    ]


def _normalize_selected_text(value: str) -> str:
    value = re.sub(r"(?<=[A-Za-z])-\s+(?=[a-z])", "", value)
    return re.sub(r"\s+", " ", value).strip().casefold()


def match_selected_chunks(
    paper: ParsedPaper,
    page: int,
    selected_text: str,
    selected_rects: Sequence[PageRect] = (),
    limit: int = 3,
) -> list[PaperChunk]:
    """Match browser-selected PDF text back to same-page local paper chunks."""
    normalized_selection = _normalize_selected_text(selected_text)
    if len(normalized_selection) < 4:
        return []

    selected_tokens = set(re.findall(r"[a-z0-9]+", normalized_selection))
    scored: list[tuple[float, int, PaperChunk]] = []
    for index, chunk in enumerate(paper.chunks):
        if chunk.page != page:
            continue
        normalized_chunk = _normalize_selected_text(chunk.content)
        if not normalized_chunk:
            continue
        overlap_area = 0.0
        selected_area = sum(
            max(rect.x1 - rect.x0, 0.0) * max(rect.y1 - rect.y0, 0.0)
            for rect in selected_rects
        )
        if selected_area and chunk.rects:
            overlap_area = sum(
                max(min(selected.x1, source.x1) - max(selected.x0, source.x0), 0.0)
                * max(min(selected.y1, source.y1) - max(selected.y0, source.y0), 0.0)
                for selected in selected_rects
                for source in chunk.rects
            )
        if overlap_area > 0:
            score = 5.0 + min(overlap_area / selected_area, 1.0)
        elif normalized_selection in normalized_chunk:
            score = 3.0 + len(normalized_selection) / max(len(normalized_chunk), 1)
        elif normalized_chunk in normalized_selection:
            score = 2.0 + len(normalized_chunk) / max(len(normalized_selection), 1)
        else:
            chunk_tokens = set(re.findall(r"[a-z0-9]+", normalized_chunk))
            token_overlap = len(selected_tokens & chunk_tokens) / max(
                min(len(selected_tokens), len(chunk_tokens)), 1
            )
            similarity = SequenceMatcher(
                None,
                normalized_selection[:1600],
                normalized_chunk[:1600],
                autojunk=False,
            ).ratio()
            score = token_overlap * 0.65 + similarity * 0.35
            if score < 0.28:
                continue
        scored.append((score, -index, chunk))
    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [item[2] for item in scored[: max(1, limit)]]


def _merge_question_candidates(
    selected_chunk_ids: Sequence[str],
    retrieved: list[EvidenceCandidate],
    chunks: list[PaperChunk],
    limit: int,
) -> list[EvidenceCandidate]:
    chunk_map = {chunk.chunk_id: chunk for chunk in chunks}
    selected_candidates = [
        EvidenceCandidate(
            evidence_id=f"S_e{index + 1}",
            chunk_id=chunk.chunk_id,
            page=chunk.page,
            text=chunk.content,
            score=2.0 - index * 0.01,
        )
        for index, chunk_id in enumerate(dict.fromkeys(selected_chunk_ids))
        if (chunk := chunk_map.get(chunk_id)) is not None
    ]
    seeded = _expand_question_candidates(selected_candidates, chunks, limit=limit)
    expanded = _expand_question_candidates(retrieved, chunks, limit=limit)
    merged: list[EvidenceCandidate] = []
    seen: set[str] = set()
    for candidate in [*seeded, *expanded]:
        if candidate.chunk_id in seen:
            continue
        seen.add(candidate.chunk_id)
        merged.append(
            candidate.model_copy(update={"evidence_id": f"Q_e{len(merged) + 1}"})
        )
        if len(merged) >= limit:
            break
    return merged


class AuditService:
    def __init__(self, settings: Settings, client: Hy3Client | None = None):
        self.settings = settings
        self.client = client or Hy3Client(settings)

    def parse(self, pdf_bytes: bytes) -> ParsedPaper:
        return parse_pdf(pdf_bytes)

    def generate_report(self, paper: ParsedPaper) -> str:
        return self.client.generate_report(paper.title, paper.chunks)

    def generate_learning_report(self, paper: ParsedPaper) -> LearningReport:
        generated = self.client.generate_learning_report(paper.title, paper.chunks)
        required_sections = list(LearningSectionType)
        section_map: dict[LearningSectionType, ReportSection] = {}
        for section in generated.sections:
            if section.section_type in section_map:
                raise Hy3ResponseError(f"Hy3 重复生成了章节：{section.section_type.value}。")
            section_map[section.section_type] = section

        missing = [section.value for section in required_sections if section not in section_map]
        if missing:
            raise Hy3ResponseError(f"Hy3 讲解缺少必要章节：{', '.join(missing)}。")

        chunk_map = {chunk.chunk_id: chunk for chunk in paper.chunks}
        chunk_positions = {chunk.chunk_id: index for index, chunk in enumerate(paper.chunks)}
        invalid_key_points: list[str] = []
        enriched_sections: list[ReportSection] = []
        total_key_points = 0
        for section_type in required_sections:
            section = section_map[section_type]
            enriched_points = []
            section_key_points = 0
            for point in section.points:
                is_key_point = (
                    point.key_point
                    and section_key_points < 2
                    and total_key_points < 14
                )
                anchors: list[EvidenceAnchor] = []
                seen: set[str] = set()
                for anchor in point.evidence:
                    chunk = chunk_map.get(anchor.chunk_id)
                    if chunk is None or chunk.chunk_id in seen:
                        continue
                    seen.add(chunk.chunk_id)
                    quote = (
                        _validated_evidence_quote(anchor.quote, chunk.content)
                        if anchor.quote
                        else None
                    )
                    anchors.append(
                        EvidenceAnchor(
                            chunk_id=chunk.chunk_id,
                            page=chunk.page,
                            text=chunk.content,
                            quote=quote,
                            locator=_evidence_locator(
                                chunk.chunk_id,
                                paper.chunks,
                                chunk_positions,
                            ),
                            rects=_quote_rects(chunk, quote),
                            context_text=_neighbor_context(
                                chunk.chunk_id,
                                paper.chunks,
                                chunk_positions,
                            ),
                        )
                    )
                if is_key_point and not anchors:
                    invalid_key_points.append(point.title)
                if is_key_point:
                    section_key_points += 1
                    total_key_points += 1
                enriched_points.append(
                    point.model_copy(
                        update={"key_point": is_key_point, "evidence": anchors}
                    )
                )
            enriched_sections.append(section.model_copy(update={"points": enriched_points}))

        if invalid_key_points:
            names = "、".join(invalid_key_points[:5])
            raise Hy3ResponseError(f"关键知识点缺少有效原文证据：{names}。")

        suggested_pages = list(
            dict.fromkeys(page for page in generated.suggested_pages if 1 <= page <= paper.page_count)
        )
        if len(suggested_pages) > 5:
            page_weights = Counter(
                anchor.page
                for section in enriched_sections
                for point in section.points
                if point.key_point
                for anchor in point.evidence
                if anchor.page is not None
            )
            original_order = {page: index for index, page in enumerate(suggested_pages)}
            selected_pages = set(
                sorted(
                    suggested_pages,
                    key=lambda page: (-page_weights[page], original_order[page]),
                )[:5]
            )
            suggested_pages = [page for page in suggested_pages if page in selected_pages]
        return generated.model_copy(
            update={
                "paper_title": paper.title,
                "sections": enriched_sections,
                "suggested_pages": suggested_pages,
            }
        )

    def generate_peer_review(
        self,
        paper: ParsedPaper,
        *,
        venue: PeerReviewVenue = PeerReviewVenue.GENERAL,
        rubric_weights: dict[str, float] | None = None,
    ) -> PeerReviewReport:
        """Generate a venue-agnostic simulated peer review with locally verified evidence."""
        normalized_weights = normalize_peer_review_weights(rubric_weights)
        if venue == PeerReviewVenue.GENERAL and not rubric_weights:
            generated = self.client.generate_peer_review(paper.title, paper.chunks)
        else:
            generated = self.client.generate_peer_review(
                paper.title,
                paper.chunks,
                venue=venue,
                rubric_weights=normalized_weights,
            )
        rubric_version, rubric_updated_at, rubric_change_note = peer_review_rubric_metadata(
            venue, normalized_weights
        )
        chunk_map = {chunk.chunk_id: chunk for chunk in paper.chunks}
        chunk_positions = {chunk.chunk_id: index for index, chunk in enumerate(paper.chunks)}
        invalid_evidence_count = 0

        def enrich(anchors: Sequence[EvidenceAnchor]) -> list[EvidenceAnchor]:
            nonlocal invalid_evidence_count
            result: list[EvidenceAnchor] = []
            seen: set[str] = set()
            for anchor in anchors[:3]:
                if anchor.chunk_id in seen:
                    continue
                chunk = chunk_map.get(anchor.chunk_id)
                if chunk is None:
                    continue
                quote = _validated_evidence_quote(anchor.quote, chunk.content) if anchor.quote else None
                if not quote:
                    invalid_evidence_count += 1
                    continue
                result.append(
                    EvidenceAnchor(
                        chunk_id=chunk.chunk_id,
                        page=chunk.page,
                        text=chunk.content,
                        quote=quote,
                        locator=_evidence_locator(chunk.chunk_id, paper.chunks, chunk_positions),
                        rects=_quote_rects(chunk, quote),
                        context_text=_neighbor_context(chunk.chunk_id, paper.chunks, chunk_positions),
                    )
                )
                seen.add(anchor.chunk_id)
            return result

        dimensions = [item.model_copy(update={"evidence": enrich(item.evidence)}) for item in generated.dimensions[:6]]

        def normalize_concern(item: ReviewConcern) -> tuple[ReviewConcern, list[str]]:
            evidence = enrich(item.evidence)
            updates: dict[str, object] = {"evidence": evidence}
            raw_category = getattr(item, "category", IssueCategory.OTHER)
            try:
                category = raw_category if isinstance(raw_category, IssueCategory) else IssueCategory(str(raw_category))
            except (TypeError, ValueError):
                category = IssueCategory.OTHER
                updates["ai_category"] = IssueCategory.OTHER
                updates["status"] = IssueStatus.NEEDS_REVIEW
            updates["category"] = category
            raw_level = getattr(item, "severity_level", None)
            try:
                level = raw_level if isinstance(raw_level, IssueSeverity) else IssueSeverity(str(raw_level))
            except (TypeError, ValueError):
                level = IssueSeverity.MAJOR if item.severity == ReviewSeverity.MAJOR else IssueSeverity.MINOR
                updates["status"] = IssueStatus.NEEDS_REVIEW
            updates["severity_level"] = level
            try:
                confidence = int(item.confidence)
            except (TypeError, ValueError):
                confidence = 2
                updates["status"] = IssueStatus.NEEDS_REVIEW
            confidence = max(1, min(5, confidence))
            updates["confidence"] = confidence
            checked = item.model_copy(update={
                "evidence": evidence,
                "category": category,
                "severity_level": level,
                "confidence": confidence,
            })
            concern_warnings = _concern_consistency_warnings(checked)
            if concern_warnings:
                updates.update({
                    "status": IssueStatus.NEEDS_REVIEW,
                    "confidence": min(confidence, 2),
                    "support_type": IssueSupportType.INSUFFICIENT_EVIDENCE,
                })
            # A claim labelled as an evidence gap is never strong enough to be
            # an acceptance blocker, even when the model attached a nearby
            # context quote.  Keep the original AI level for auditability but
            # expose a conservative product-facing level.
            if item.support_type == IssueSupportType.INSUFFICIENT_EVIDENCE and not evidence and level in {
                IssueSeverity.FATAL,
                IssueSeverity.MAJOR,
            }:
                updates.update({
                    "severity_level": IssueSeverity.MAJOR if level == IssueSeverity.FATAL else IssueSeverity.MINOR,
                    "severity": ReviewSeverity.MAJOR if level == IssueSeverity.FATAL else ReviewSeverity.MINOR,
                    "confidence": min(confidence, 2),
                    "status": IssueStatus.NEEDS_REVIEW,
                })
                level = IssueSeverity.MAJOR if level == IssueSeverity.FATAL else IssueSeverity.MINOR
            elif not evidence and level in {IssueSeverity.FATAL, IssueSeverity.MAJOR}:
                updates.update({
                    # An unverified P0 remains a review-required P1 for safety;
                    # an unverified P1 is conservatively capped at P2.
                    "severity_level": IssueSeverity.MAJOR if level == IssueSeverity.FATAL else IssueSeverity.MINOR,
                    "severity": ReviewSeverity.MAJOR if level == IssueSeverity.FATAL else ReviewSeverity.MINOR,
                    "confidence": min(confidence, 2),
                    "status": IssueStatus.NEEDS_REVIEW,
                    "support_type": IssueSupportType.INSUFFICIENT_EVIDENCE,
                })
            return item.model_copy(update=updates), concern_warnings

        normalized_major: list[ReviewConcern] = []
        normalized_minor: list[ReviewConcern] = []
        concern_warnings: list[str] = []
        for item in generated.major_concerns[:6]:
            normalized, warnings = normalize_concern(item)
            normalized_major.append(normalized)
            concern_warnings.extend(warnings)
        for item in generated.minor_concerns[:6]:
            normalized, warnings = normalize_concern(item)
            normalized_minor.append(normalized)
            concern_warnings.extend(warnings)
        major = _dedupe_review_concerns(normalized_major)
        minor = _dedupe_review_concerns(normalized_minor)
        if not dimensions:
            raise Hy3ResponseError("模拟评审缺少维度评分。")
        enriched = generated.model_copy(
            update={
                "paper_title": paper.title,
                "venue": venue,
                "dimensions": dimensions,
                "major_concerns": major,
                "minor_concerns": minor,
                "rubric_version": rubric_version,
                "rubric_updated_at": rubric_updated_at,
                "rubric_change_note": rubric_change_note,
                "rubric_weights": normalized_weights,
                "model_raw_score": generated.overall_score,
                "questions_for_authors": [],
                "review_limitations": list(dict.fromkeys([
                    *generated.review_limitations,
                    "本评审仅基于上传论文文本；代码、完整附录、数据泄漏和未报告实验无法独立验证。",
                ])),
                "parse_warnings": [
                    *paper.warnings,
                    *concern_warnings,
                    *(["部分评审证据缺少可逐字核验的原文引文，已移除并标记为需人工复核。"] if invalid_evidence_count else []),
                ],
            }
        )
        enriched = recalculate_peer_review(enriched, normalized_weights)
        consistency_warnings = peer_review_consistency_warnings(enriched)
        return enriched.model_copy(
            update={
                "parse_warnings": list(dict.fromkeys(
                    [*enriched.parse_warnings, *consistency_warnings]
                ))
            }
        )

    def compare_related_work(
        self,
        paper: ParsedPaper,
        references: Sequence[RelatedWorkReference],
    ) -> RelatedWorkComparison:
        """Compare novelty only against references explicitly supplied by the user."""
        if not references:
            raise ValueError("请至少提供一条相关工作记录。")
        if len(references) > 5:
            raise ValueError("最多支持 5 条相关工作记录。")
        payload = [item.model_dump(mode="json") for item in references]
        result = self.client.compare_related_work(paper.title, paper.chunks, payload)
        return result.model_copy(update={"references": list(references)})

    def assess_rebuttal(
        self,
        report: PeerReviewReport,
        concern: ReviewConcern,
        response: str,
    ) -> RebuttalItem:
        """Ask Hy3 to classify one author response against the cited concern evidence."""
        evidence = "\n".join(
            anchor.quote or anchor.text[:600]
            for anchor in concern.evidence[:3]
        )
        draft = self.client.assess_rebuttal(
            report.paper_title,
            concern.title,
            concern.description,
            response.strip(),
            evidence,
        )
        return RebuttalItem(
            issue_id=concern.issue_id,
            concern_title=concern.title,
            response=response.strip(),
            resolution=draft.resolution,
            assessment=draft.assessment,
        )

    def answer_question(
        self,
        paper: ParsedPaper,
        question: str,
        history: Sequence[PaperAnswer] = (),
        selected_chunk_ids: Sequence[str] = (),
        selected_text: str | None = None,
    ) -> PaperAnswer:
        normalized_question = question.strip()
        if not normalized_question:
            raise ValueError("追问内容不能为空。")
        if len(normalized_question) > 1000:
            raise ValueError("追问内容过长，请控制在 1000 个字符以内。")
        normalized_selection = selected_text.strip()[:2000] if selected_text else None

        structure_answer = _document_structure_answer(normalized_question, paper)
        if structure_answer is not None:
            return structure_answer

        location_answer = _paper_location_answer(normalized_question, paper)
        if location_answer is not None:
            return location_answer

        query = self.client.plan_question(paper.title, normalized_question, history)
        retrieval_query = " ".join(
            value
            for value in [query.query_en, *query.entities, *query.numbers]
            if value.strip()
        )
        with EvidenceRetriever(paper.chunks) as retriever:
            candidates = retriever.search(
                retrieval_query,
                "Q",
                self.settings.retrieval_top_k,
            )

        candidates = _merge_question_candidates(
            selected_chunk_ids,
            candidates,
            paper.chunks,
            limit=min(max(self.settings.retrieval_top_k * 2, 8), 12),
        )

        if not candidates:
            return PaperAnswer(
                question=normalized_question,
                answer="当前论文中未检索到足够相关的原文证据，暂时无法可靠回答。",
                status=AnswerStatus.INSUFFICIENT_EVIDENCE,
            )

        draft = self.client.answer_question(
            normalized_question,
            candidates,
            history,
            normalized_selection,
        )
        if draft.status == AnswerStatus.INSUFFICIENT_EVIDENCE:
            expanded_limit = min(max(self.settings.retrieval_top_k * 4, 16), 24)
            with EvidenceRetriever(paper.chunks) as retriever:
                expanded_retrieved = retriever.search(
                    retrieval_query,
                    "QX",
                    expanded_limit,
                )
            expanded_candidates = _merge_question_candidates(
                selected_chunk_ids,
                expanded_retrieved,
                paper.chunks,
                limit=expanded_limit,
            )
            if {item.chunk_id for item in expanded_candidates} != {
                item.chunk_id for item in candidates
            }:
                candidates = expanded_candidates
                draft = self.client.answer_question(
                    normalized_question,
                    candidates,
                    history,
                    normalized_selection,
                )
        candidate_map = {candidate.chunk_id: candidate for candidate in candidates}
        chunk_map = {chunk.chunk_id: chunk for chunk in paper.chunks}
        chunk_positions = {chunk.chunk_id: index for index, chunk in enumerate(paper.chunks)}
        citations_by_id: dict[str, EvidenceAnchor] = {}

        def build_anchor(
            chunk_id: str,
            requested_quote: str | None = None,
        ) -> EvidenceAnchor | None:
            candidate = candidate_map.get(chunk_id)
            chunk = chunk_map.get(chunk_id)
            if candidate is None or chunk is None:
                return None
            quote = None
            if requested_quote is not None:
                quote = _validated_evidence_quote(requested_quote, chunk.content)
                if quote is None:
                    return None
            chunk = chunk_map[chunk_id]
            anchor = EvidenceAnchor(
                chunk_id=chunk_id,
                page=candidate.page,
                text=candidate.text,
                quote=quote,
                locator=_evidence_locator(
                    chunk_id,
                    paper.chunks,
                    chunk_positions,
                ),
                rects=_quote_rects(chunk, quote),
                context_text=_neighbor_context(
                    chunk_id,
                    paper.chunks,
                    chunk_positions,
                ),
            )
            existing = citations_by_id.get(chunk_id)
            if existing is None or (existing.quote is None and quote is not None):
                citations_by_id[chunk_id] = anchor
            return anchor

        for chunk_id in draft.citation_chunk_ids:
            build_anchor(chunk_id)

        conclusions: list[AnswerConclusion] = []
        for conclusion in draft.conclusions[:4]:
            conclusion_text = conclusion.text.strip()
            if not conclusion_text:
                continue
            conclusion_citations: list[EvidenceAnchor] = []
            conclusion_seen: set[str] = set()
            for evidence in conclusion.evidence[:2]:
                if evidence.chunk_id in conclusion_seen:
                    continue
                anchor = build_anchor(evidence.chunk_id, evidence.quote)
                if anchor is not None:
                    conclusion_seen.add(evidence.chunk_id)
                    conclusion_citations.append(anchor)
            if conclusion_citations:
                conclusions.append(
                    AnswerConclusion(
                        text=conclusion_text,
                        support_type=conclusion.support_type,
                        citations=conclusion_citations,
                    )
                )

        citations = list(citations_by_id.values())

        if draft.status == AnswerStatus.ANSWERED and not conclusions:
            return PaperAnswer(
                question=normalized_question,
                answer="模型返回的结论缺少可在本地 PDF 中核验的原文摘录，本次回答已转为证据不足。",
                status=AnswerStatus.INSUFFICIENT_EVIDENCE,
            )
        if draft.status == AnswerStatus.ANSWERED and not citations:
            return PaperAnswer(
                question=normalized_question,
                answer="模型未返回可验证的有效原文引用，本次回答已转为证据不足。",
                status=AnswerStatus.INSUFFICIENT_EVIDENCE,
            )
        if draft.status == AnswerStatus.INSUFFICIENT_EVIDENCE:
            citations = []

        verified_answer = draft.answer
        if conclusions:
            verified_answer = "\n".join(conclusion.text for conclusion in conclusions)
        return PaperAnswer(
            question=normalized_question,
            answer=verified_answer,
            status=draft.status,
            citations=citations,
            conclusions=conclusions,
        )

    def audit(
        self,
        paper: ParsedPaper,
        report_text: str,
        scope: Sequence[ClaimCategory],
        mode: str = "audit_existing",
        progress: ProgressCallback | None = None,
    ) -> AuditRun:
        validate_audit_report_text(report_text)
        notify = progress or _noop_progress
        notify("正在拆分原子论断", 0.1)
        extraction = self.client.extract_claims(report_text, [category.value for category in scope])
        claims = [
            claim.model_copy(update={"claim_id": f"C{index + 1:03d}"})
            for index, claim in enumerate(extraction.claims)
        ]
        if not claims:
            raise ValueError("报告中未提取到可审计的事实论断。")

        notify("正在检索候选证据", 0.25)
        candidates_by_claim: dict[str, list] = {}
        with EvidenceRetriever(paper.chunks) as retriever:
            for claim in claims:
                candidates_by_claim[claim.claim_id] = retriever.search(
                    build_claim_query(claim),
                    claim.claim_id,
                    self.settings.retrieval_top_k,
                )

        judgments: dict[str, ClaimJudgment] = {}
        judgment_votes: dict[str, list[ClaimJudgment]] = {}
        auditable = [claim for claim in claims if candidates_by_claim[claim.claim_id]]
        batch_size = max(1, self.settings.judge_batch_size)
        for start in range(0, len(auditable), batch_size):
            batch = auditable[start : start + batch_size]
            progress_value = 0.35 + 0.5 * min((start + len(batch)) / max(len(auditable), 1), 1.0)
            notify("正在判断证据支持关系", progress_value)
            try:
                response = self.client.judge_claims(
                    [(claim, candidates_by_claim[claim.claim_id]) for claim in batch],
                    paper.page_count,
                )
            except Hy3ResponseError:
                fallback = []
                for claim in batch:
                    try:
                        single = self.client.adjudicate_claim(
                            claim, candidates_by_claim[claim.claim_id], paper.page_count
                        )
                        fallback.extend(single.judgments)
                    except Hy3ResponseError:
                        continue
                response = JudgmentBatch(judgments=fallback)
            for judgment in response.judgments:
                judgments[judgment.claim_id] = judgment
                judgment_votes[judgment.claim_id] = [judgment]

        retry_claims = [
            claim
            for claim in auditable
            if claim.claim_id in judgments
            and needs_second_pass(judgments[claim.claim_id], claim.text + " " + claim.query_en)
        ]
        for claim in retry_claims:
            try:
                response = self.client.adjudicate_claim(
                    claim, candidates_by_claim[claim.claim_id], paper.page_count
                )
            except Hy3ResponseError:
                response = None
            if response and response.judgments:
                judgment_votes.setdefault(claim.claim_id, []).append(response.judgments[0])
                judgments[claim.claim_id] = choose_majority(judgment_votes[claim.claim_id])

        stabilize_claims = [
            claim
            for claim in retry_claims
            if len(judgment_votes.get(claim.claim_id, [])) == 2
            and judgment_signature(judgment_votes[claim.claim_id][0])
            != judgment_signature(judgment_votes[claim.claim_id][1])
        ]
        for claim in stabilize_claims:
            try:
                response = self.client.adjudicate_claim(
                    claim, candidates_by_claim[claim.claim_id], paper.page_count
                )
            except Hy3ResponseError:
                response = None
            if response and response.judgments:
                judgment_votes[claim.claim_id].append(response.judgments[0])
                judgments[claim.claim_id] = choose_majority(judgment_votes[claim.claim_id])

        evidence_retry_claims = [
            claim
            for claim in auditable
            if needs_evidence_retry(
                judgments.get(claim.claim_id), candidates_by_claim[claim.claim_id]
            )
        ]
        for claim in evidence_retry_claims:
            try:
                response = self.client.adjudicate_claim(
                    claim, candidates_by_claim[claim.claim_id], paper.page_count
                )
            except Hy3ResponseError:
                response = None
            if response and response.judgments:
                judgment_votes.setdefault(claim.claim_id, []).append(response.judgments[0])
                judgments[claim.claim_id] = response.judgments[0]

        audits: list[ClaimAudit] = []
        for claim in claims:
            candidates = candidates_by_claim[claim.claim_id]
            judgment = judgments.get(claim.claim_id)
            if not candidates:
                judgment = ClaimJudgment(
                    claim_id=claim.claim_id,
                    label=AutoLabel.ABSTAIN,
                    explanation="本地检索未返回候选证据，暂时无法可靠判断。",
                    severity=Severity.NONE,
                )
            elif judgment is None:
                judgment = ClaimJudgment(
                    claim_id=claim.claim_id,
                    label=AutoLabel.ABSTAIN,
                    explanation="Hy3 未返回该论断的结构化判断。",
                    severity=Severity.NONE,
                )
            judgment = calibrate_judgment(judgment)
            judgment = validate_judgment_references(judgment, candidates)
            if judgment.label == AutoLabel.NO_SUPPORT_FOUND and judgment.severity == Severity.HIGH:
                notify("正在补查高风险无支持结论", 0.9)
                candidates = supplement_claim_evidence(claim, paper.chunks, candidates)
                review = None
                try:
                    review = self.client.review_missing_support(claim, candidates, paper.page_count)
                except Hy3ResponseError:
                    pass
                if (review is not None and review.evidence_sufficient
                        and review.judgment.claim_id == claim.claim_id
                        and review.judgment.evidence_ids):
                    judgment = validate_judgment_references(calibrate_judgment(review.judgment), candidates)
                else:
                    judgment = ClaimJudgment(
                        claim_id=claim.claim_id, label=AutoLabel.ABSTAIN,
                        explanation="已补查引用页及其他候选片段，现有证据仍不足以可靠判断，请结合论文原文人工复核。",
                        severity=Severity.NONE,
                    )
            invalid_pages = sorted(page for page in report_evidence_pages(claim.provided_evidence)
                                   if not 1 <= page <= paper.page_count)
            if invalid_pages:
                # A locally provable citation error remains visible even if the
                # claim's support relationship is unresolved or supported.
                judgment = judgment.model_copy(update={
                    "evidence_error_type": EvidenceErrorType.FABRICATED_EVIDENCE,
                    "severity": Severity.HIGH,
                    "explanation": judgment.explanation + f" 报告引用页码 {invalid_pages} 超出论文的 1–{paper.page_count} 页范围。",
                })
            audits.append(ClaimAudit(claim=claim, candidates=candidates, judgment=judgment))

        notify("正在生成审计摘要", 0.95)
        summary = build_summary(audits, list(scope))
        notify("审计完成", 1.0)
        return AuditRun(
            paper_title=paper.title,
            page_count=paper.page_count,
            mode=mode,
            scope=list(scope),
            report_text=report_text,
            audits=audits,
            summary=summary,
            parse_warnings=paper.warnings,
            source_count=extraction.source_count,
            skipped_sources=extraction.skipped_sources,
        )
