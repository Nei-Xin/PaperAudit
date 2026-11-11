"""Which evidence an audit judgment relies on, and how it is shown."""

from __future__ import annotations

import re

from paperaudit.models import AutoLabel, ClaimAudit
from paperaudit.audit_rules import apply_citation_review


def citation_review_passed(audit: ClaimAudit) -> bool:
    before = audit.judgment_before_citation_review or audit.judgment
    return bool(
        audit.citation_review is not None
        and before.label in {AutoLabel.SUPPORTED, AutoLabel.CONTRADICTED}
        and apply_citation_review(before, audit.candidates, audit.citation_review).label == before.label
    )


def normalize_evidence_display(text: str) -> str:
    """Collapse PDF extraction whitespace without mutating stored evidence."""

    # Rejoin the common PDF line-wrap form "instruc-\ntional" while retaining
    # real hyphenated terms that are not split by a newline.
    reflowed = re.sub(r"(?<=\w)-\s*[\r\n]+\s*(?=\w)", "", text)
    return " ".join(reflowed.split())


def selected_evidence(audit: ClaimAudit):
    """Return locally available evidence selected by the judgment."""

    selected_ids = set(audit.judgment.evidence_ids)
    return [
        candidate
        for candidate in audit.candidates
        if candidate.evidence_id in selected_ids
    ]


