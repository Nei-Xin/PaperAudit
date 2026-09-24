from __future__ import annotations
from collections.abc import Sequence
from difflib import SequenceMatcher
import hashlib
import json
import math
import re
from .models import PeerReviewReport, RevisionDiff, ReviewConcern, IssueSeverity, IssueSupportType, HumanReviewDecision, ParsedPaper, ReviewDecision, PeerReviewVenue


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

