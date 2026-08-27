"""Pure presentation helpers for the audit result workspace."""

from __future__ import annotations

from collections.abc import Sequence
import re

from paperaudit.models import AutoLabel, ClaimAudit, ClaimCategory, Severity


QUICK_ALL = "all"
QUICK_ATTENTION = "attention"
QUICK_CONTRADICTED = "contradicted"
QUICK_NO_SUPPORT = "no_support"
QUICK_ABSTAIN = "abstain"

SORT_RISK = "risk"
SORT_REPORT = "report"


def normalize_evidence_display(text: str) -> str:
    """Collapse PDF extraction whitespace without mutating stored evidence."""

    # Rejoin the common PDF line-wrap form "instruc-\ntional" while retaining
    # real hyphenated terms that are not split by a newline.
    reflowed = re.sub(r"(?<=\w)-\s*[\r\n]+\s*(?=\w)", "", text)
    return " ".join(reflowed.split())


def is_attention_required(audit: ClaimAudit) -> bool:
    """Return whether a claim needs review in the result workspace."""

    return not (
        audit.judgment.label == AutoLabel.SUPPORTED
        and audit.judgment.severity == Severity.NONE
    )


def audit_counts(audits: Sequence[ClaimAudit]) -> dict[str, int]:
    """Return counts used by the quick-filter labels."""

    return {
        QUICK_ALL: len(audits),
        QUICK_ATTENTION: sum(is_attention_required(audit) for audit in audits),
        QUICK_CONTRADICTED: sum(
            audit.judgment.label == AutoLabel.CONTRADICTED for audit in audits
        ),
        QUICK_NO_SUPPORT: sum(
            audit.judgment.label == AutoLabel.NO_SUPPORT_FOUND for audit in audits
        ),
        QUICK_ABSTAIN: sum(
            audit.judgment.label == AutoLabel.ABSTAIN for audit in audits
        ),
    }


def filter_audits(
    audits: Sequence[ClaimAudit],
    *,
    quick_filter: str,
    category: ClaimCategory | None = None,
    severity: Severity | None = None,
    search_query: str = "",
) -> list[ClaimAudit]:
    """Apply quick and advanced filters without changing report order."""

    filtered = list(audits)
    if quick_filter == QUICK_ATTENTION:
        filtered = [audit for audit in filtered if is_attention_required(audit)]
    elif quick_filter == QUICK_CONTRADICTED:
        filtered = [
            audit
            for audit in filtered
            if audit.judgment.label == AutoLabel.CONTRADICTED
        ]
    elif quick_filter == QUICK_NO_SUPPORT:
        filtered = [
            audit
            for audit in filtered
            if audit.judgment.label == AutoLabel.NO_SUPPORT_FOUND
        ]
    elif quick_filter == QUICK_ABSTAIN:
        filtered = [
            audit for audit in filtered if audit.judgment.label == AutoLabel.ABSTAIN
        ]
    elif quick_filter != QUICK_ALL:
        raise ValueError(f"未知快速筛选：{quick_filter}")

    if category is not None:
        filtered = [audit for audit in filtered if audit.claim.category == category]
    if severity is not None:
        filtered = [
            audit for audit in filtered if audit.judgment.severity == severity
        ]
    query = search_query.strip().casefold()
    if query:
        filtered = [
            audit
            for audit in filtered
            if query in audit.claim.claim_id.casefold()
            or query in audit.claim.text.casefold()
            or query in audit.judgment.explanation.casefold()
            or query in (audit.judgment.suggestion or "").casefold()
            or any(query in candidate.text.casefold() for candidate in audit.candidates)
        ]
    return filtered


def sort_audits(audits: Sequence[ClaimAudit], mode: str) -> list[ClaimAudit]:
    """Sort claims for review while retaining stable order within a risk level."""

    if mode == SORT_REPORT:
        return list(audits)
    if mode != SORT_RISK:
        raise ValueError(f"未知排序方式：{mode}")
    severity_order = {
        Severity.CRITICAL: 0,
        Severity.HIGH: 1,
        Severity.MEDIUM: 2,
        Severity.LOW: 3,
        Severity.NONE: 4,
    }
    return sorted(audits, key=lambda audit: severity_order[audit.judgment.severity])


def selected_evidence(audit: ClaimAudit):
    """Return locally available evidence selected by the judgment."""

    selected_ids = set(audit.judgment.evidence_ids)
    return [
        candidate
        for candidate in audit.candidates
        if candidate.evidence_id in selected_ids
    ]


def compact_claim_text(text: str, limit: int = 110) -> str:
    compact = normalize_evidence_display(text)
    if len(compact) <= limit:
        return compact
    return compact[: max(1, limit - 1)].rstrip() + "…"
