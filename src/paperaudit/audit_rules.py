from __future__ import annotations

from collections.abc import Sequence
import re

from .models import AutoLabel, CitationReview, ClaimErrorType, ClaimJudgment, EvidenceCandidate, Severity


_HIGH_RISK_ERRORS = {
    ClaimErrorType.CONTRADICTION,
    ClaimErrorType.EXTERNAL_HALLUCINATION,
    ClaimErrorType.NUMERIC_OR_METRIC_MISMATCH,
    ClaimErrorType.WRONG_ATTRIBUTION,
}
_MEDIUM_RISK_ERRORS = {
    ClaimErrorType.MISSING_CONDITION,
    ClaimErrorType.OVERGENERALIZATION,
}


def judgment_signature(judgment: ClaimJudgment) -> tuple[str, str | None]:
    return (
        judgment.label.value,
        judgment.claim_error_type.value if judgment.claim_error_type else None,
    )


def choose_majority(judgments: Sequence[ClaimJudgment]) -> ClaimJudgment:
    """Choose the most frequent label/error pair, preserving its evidence details."""

    if not judgments:
        raise ValueError("至少需要一个裁决结果。")
    counts: dict[tuple[str, str | None], int] = {}
    for judgment in judgments:
        key = judgment_signature(judgment)
        counts[key] = counts.get(key, 0) + 1
    winner = max(counts, key=lambda key: (counts[key], -next(
        index for index, judgment in enumerate(judgments) if judgment_signature(judgment) == key
    )))
    return next(judgment for judgment in judgments if judgment_signature(judgment) == winner)


def needs_evidence_retry(
    judgment: ClaimJudgment | None, candidates: list[EvidenceCandidate]
) -> bool:
    """Retry unresolved or structurally invalid model output once automatically."""

    if not candidates:
        return False
    if judgment is None or judgment.label == AutoLabel.ABSTAIN:
        return True
    allowed_ids = {candidate.evidence_id for candidate in candidates}
    returned_ids = set(judgment.evidence_ids)
    requires_evidence = judgment.label in {
        AutoLabel.SUPPORTED,
        AutoLabel.PARTIALLY_SUPPORTED,
        AutoLabel.CONTRADICTED,
    }
    return not returned_ids.issubset(allowed_ids) or (requires_evidence and not returned_ids)


def validate_judgment_references(
    judgment: ClaimJudgment | None, candidates: list[EvidenceCandidate]
) -> ClaimJudgment:
    """Ensure model evidence references belong to the supplied candidate list."""

    if judgment is None:
        claim_id = candidates[0].evidence_id.rsplit("_e", 1)[0] if candidates else "unknown"
        return ClaimJudgment(
            claim_id=claim_id,
            label=AutoLabel.ABSTAIN,
            explanation="Hy3 未返回该论断的结构化判断。",
            severity=Severity.NONE,
        )
    if not candidates:
        return judgment
    allowed_ids = {candidate.evidence_id for candidate in candidates}
    returned_ids = set(judgment.evidence_ids)
    requires_evidence = judgment.label in {
        AutoLabel.SUPPORTED,
        AutoLabel.PARTIALLY_SUPPORTED,
        AutoLabel.CONTRADICTED,
    }
    if not returned_ids.issubset(allowed_ids) or (requires_evidence and not returned_ids):
        return judgment.model_copy(
            update={
                "label": AutoLabel.ABSTAIN,
                "evidence_ids": [],
                "explanation": "自动裁决未返回有效证据编号，暂时无法可靠判断。",
                "claim_error_type": None,
                "evidence_error_type": None,
                "severity": Severity.NONE,
            }
        )
    return judgment


def apply_citation_review(
    judgment: ClaimJudgment,
    candidates: list[EvidenceCandidate],
    review: CitationReview | None,
) -> ClaimJudgment:
    """Accept a definitive judgment only with locally verifiable quotations.

    The model assesses semantic coverage; this check proves only that each
    quotation exists in its own selected passage. Never union the candidate pool
    into the citations or infer support from a keyword/number match.
    """
    if judgment.label not in {AutoLabel.SUPPORTED, AutoLabel.CONTRADICTED}:
        return judgment
    passages = {c.evidence_id: c.text for c in candidates}
    valid = bool(
        review is not None and review.claim_id == judgment.claim_id
        and review.reviewed_label == judgment.label.value
        and review.complete and not review.missing_aspects
        and review.aspects and review.evidence_ids
        and set(review.evidence_ids).issubset(passages)
    )
    if valid and judgment.suggestion:
        # Historical support reviews predate this field and remain loadable.
        # New contradiction reviews must opt in explicitly: a correct label is
        # insufficient when its suggested correction contains extra claims.
        valid = (
            review.suggestion_verified is True
            and not review.suggestion_missing_aspects
        ) if judgment.label == AutoLabel.CONTRADICTED else (
            review.suggestion_verified is not False
            and not review.suggestion_missing_aspects
        )
    if valid:
        assert review is not None
        quoted_ids = set()
        for aspect in review.aspects:
            if not aspect.aspect.strip() or not aspect.reasoning.strip():
                valid = False
            for citation in aspect.citations:
                quote = " ".join(citation.quote.split())
                source = " ".join(passages.get(citation.evidence_id, "").split())
                if not quote or quote not in source:
                    valid = False
                quoted_ids.add(citation.evidence_id)
        valid = valid and quoted_ids == set(review.evidence_ids)
    if not valid:
        explanation = (
            "引用完整性复核未能提供同一主体及条件下的明确冲突依据，暂时无法可靠判断，请结合论文原文复核。"
            if judgment.label == AutoLabel.CONTRADICTED else
            "引用完整性复核未能提供覆盖论断全部条件的有效原文依据，暂时无法可靠判断，请结合论文原文复核。"
        )
        if review is not None and judgment.suggestion and review.suggestion_verified is not True:
            explanation = "纠正建议中的具体数值或条件未被完整引文验证，暂时无法可靠判断，请结合论文原文复核。"
        return judgment.model_copy(update={
            "label": AutoLabel.ABSTAIN,
            "evidence_ids": [],
            "explanation": explanation,
            "claim_error_type": None,
            "evidence_error_type": None,
            "severity": Severity.NONE,
            "suggestion": None,
        })
    assert review is not None
    return judgment.model_copy(update={
        "evidence_ids": list(dict.fromkeys(review.evidence_ids)),
        "explanation": judgment.explanation + " 引用完整性复核：" + review.explanation,
    })


def needs_second_pass(judgment: ClaimJudgment, claim_text: str = "") -> bool:
    """Flag only internally inconsistent judgments for a focused retry."""

    error = judgment.claim_error_type
    lowered = claim_text.casefold()
    # Review suspiciously mild results, without assigning risk from keywords.
    if error in _MEDIUM_RISK_ERRORS and (
        re.search(r"\d|证明|最优|保证|\b(?:prov\w*|optimal\w*|guarantee\w*)\b", lowered)
    ):
        return True
    if any(
        marker in lowered
        for marker in (
            "all tasks",
            "所有任务",
            "所有",
            "全部",
            "every",
            "always",
            "任何训练资源",
            "不需要",
            "无需",
            "不依赖",
            "without training",
        )
    ):
        return True
    if "days" in lowered or "天" in lowered:
        return True
    if error is None:
        return False
    if judgment.label == AutoLabel.SUPPORTED:
        return True
    if judgment.label == AutoLabel.CONTRADICTED and error in _MEDIUM_RISK_ERRORS:
        return True
    if judgment.label == AutoLabel.PARTIALLY_SUPPORTED and error in _HIGH_RISK_ERRORS:
        return True
    if judgment.label == AutoLabel.NO_SUPPORT_FOUND and error in _HIGH_RISK_ERRORS:
        return True
    if judgment.label == AutoLabel.PARTIALLY_SUPPORTED and error == ClaimErrorType.MISSING_CONDITION:
        return True
    return False


def calibrate_severity(judgment: ClaimJudgment) -> ClaimJudgment:
    """Apply the deterministic project risk rubric after Hy3's judgment."""

    if judgment.label in {AutoLabel.SUPPORTED, AutoLabel.ABSTAIN}:
        target = Severity.NONE
    elif judgment.claim_error_type in _HIGH_RISK_ERRORS or judgment.label == AutoLabel.CONTRADICTED:
        target = Severity.HIGH
    elif judgment.claim_error_type in _MEDIUM_RISK_ERRORS:
        target = Severity.MEDIUM
    else:
        return judgment
    return judgment if judgment.severity == target else judgment.model_copy(update={"severity": target})


def calibrate_judgment(judgment: ClaimJudgment) -> ClaimJudgment:
    """Align labels and severity with the project's error taxonomy."""

    if judgment.label == AutoLabel.ABSTAIN:
        return calibrate_severity(judgment)
    error = judgment.claim_error_type
    if error == ClaimErrorType.EXTERNAL_HALLUCINATION:
        target_label = AutoLabel.NO_SUPPORT_FOUND
    elif error in _HIGH_RISK_ERRORS:
        target_label = AutoLabel.CONTRADICTED
    elif error in _MEDIUM_RISK_ERRORS:
        target_label = AutoLabel.PARTIALLY_SUPPORTED
    elif error is None:
        # A missing optional taxonomy field must never promote a negative
        # model judgment to SUPPORTED. Preserve the label and let the
        # evidence validator enforce the requirements for that label.
        target_label = judgment.label
    else:
        target_label = judgment.label
    aligned = (
        judgment
        if judgment.label == target_label
        else judgment.model_copy(update={"label": target_label})
    )
    return calibrate_severity(aligned)
