from __future__ import annotations

from paperaudit.audit_view import (
    normalize_evidence_display,
    selected_evidence,
)
from demo_data import get_demo_audit_run


def test_evidence_display_collapses_whitespace_without_mutating_source() -> None:
    audit = get_demo_audit_run().audits[0]
    source = "context-adaptive in-\nstructional\tmode   selection"
    candidate = audit.candidates[0].model_copy(update={"text": source})
    updated = audit.model_copy(update={"candidates": [candidate]})

    normalized = normalize_evidence_display(updated.candidates[0].text)

    assert normalized == "context-adaptive instructional mode selection"
    assert updated.candidates[0].text == source


def test_missing_evidence_id_is_ignored() -> None:
    audit = get_demo_audit_run().audits[0]
    judgment = audit.judgment.model_copy(update={"evidence_ids": ["missing"], "suggestion": None})

    assert selected_evidence(audit.model_copy(update={"judgment": judgment})) == []
