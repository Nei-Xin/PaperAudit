from __future__ import annotations

from paperaudit.models import AutoLabel, ClaimCategory, ClaimErrorType, Severity
from paperaudit.ui.audit_view import (
    QUICK_ABSTAIN,
    QUICK_ALL,
    QUICK_ATTENTION,
    QUICK_CONTRADICTED,
    QUICK_NO_SUPPORT,
    SORT_REPORT,
    SORT_RISK,
    audit_counts,
    filter_audits,
    is_attention_required,
    normalize_evidence_display,
    selected_evidence,
    sort_audits,
)
from paperaudit.ui.components import (
    build_audit_detail_html,
    build_audit_summary_html,
)
from paperaudit.ui.demo_data import get_demo_audit_run


def test_evidence_display_collapses_whitespace_without_mutating_source() -> None:
    audit = get_demo_audit_run().audits[0]
    source = "context-adaptive in-\nstructional\tmode   selection"
    candidate = audit.candidates[0].model_copy(update={"text": source})
    updated = audit.model_copy(update={"candidates": [candidate]})

    normalized = normalize_evidence_display(updated.candidates[0].text)

    assert normalized == "context-adaptive instructional mode selection"
    assert updated.candidates[0].text == source


def test_attention_and_quick_filter_counts() -> None:
    audits = get_demo_audit_run().audits
    counts = audit_counts(audits)

    assert is_attention_required(audits[0]) is False
    assert is_attention_required(audits[-1]) is True
    assert counts == {
        QUICK_ALL: 6,
        QUICK_ATTENTION: 5,
        QUICK_CONTRADICTED: 1,
        QUICK_NO_SUPPORT: 1,
        QUICK_ABSTAIN: 1,
    }


def test_quick_and_advanced_filters_are_composable() -> None:
    audits = get_demo_audit_run().audits
    changed = audits[2].model_copy(
        update={
            "claim": audits[2].claim.model_copy(
                update={
                    "category": ClaimCategory.RESULTS,
                    "text": "模型结果存在关键冲突",
                }
            )
        }
    )
    source = [audits[0], audits[1], changed, *audits[3:]]

    filtered = filter_audits(
        source,
        quick_filter=QUICK_CONTRADICTED,
        category=ClaimCategory.RESULTS,
        severity=Severity.CRITICAL,
        search_query="关键冲突",
    )

    assert [audit.claim.claim_id for audit in filtered] == ["C003"]


def test_search_matches_claim_id_and_candidate_evidence() -> None:
    audits = get_demo_audit_run().audits

    by_id = filter_audits(audits, quick_filter=QUICK_ALL, search_query="C004")
    by_evidence = filter_audits(
        audits, quick_filter=QUICK_ALL, search_query="source evidence for claim 5"
    )

    assert [audit.claim.claim_id for audit in by_id] == ["C004"]
    assert [audit.claim.claim_id for audit in by_evidence] == ["C005"]


def test_risk_sort_and_report_order() -> None:
    audits = get_demo_audit_run().audits

    assert [audit.claim.claim_id for audit in sort_audits(audits, SORT_REPORT)] == [
        "C001",
        "C002",
        "C003",
        "C004",
        "C005",
        "C006",
    ]
    assert [audit.judgment.severity for audit in sort_audits(audits, SORT_RISK)] == [
        Severity.CRITICAL,
        Severity.HIGH,
        Severity.MEDIUM,
        Severity.LOW,
        Severity.NONE,
        Severity.NONE,
    ]


def test_missing_evidence_id_is_ignored_and_empty_detail_is_explicit() -> None:
    audit = get_demo_audit_run().audits[0]
    judgment = audit.judgment.model_copy(
        update={"evidence_ids": ["missing"], "suggestion": None}
    )
    updated = audit.model_copy(update={"judgment": judgment})

    assert selected_evidence(updated) == []
    html = build_audit_detail_html(updated, "核心贡献")
    assert "修改建议" not in html
    assert "当前没有已验证的原文证据" in html
    assert "pa-audit-evidence-item" not in html


def test_summary_renders_unscored_state() -> None:
    summary = get_demo_audit_run().summary.model_copy(update={"total_score": None})

    html = build_audit_summary_html(summary)

    assert "未评分" in html
    assert "None" not in html


def test_detail_uses_chinese_error_type_and_limits_primary_evidence() -> None:
    audit = get_demo_audit_run().audits[0]
    candidates = [
        audit.candidates[0].model_copy(
            update={"evidence_id": f"E{index}", "chunk_id": f"p1_b{index}"}
        )
        for index in range(1, 4)
    ]
    updated = audit.model_copy(
        update={
            "candidates": candidates,
            "judgment": audit.judgment.model_copy(
                update={
                    "evidence_ids": [candidate.evidence_id for candidate in candidates],
                    "claim_error_type": ClaimErrorType.MISSING_CONDITION,
                }
            ),
        }
    )

    html = build_audit_detail_html(updated, "主要结果")

    assert "遗漏成立条件" in html
    assert "p1_b1" in html and "p1_b2" in html
    assert "p1_b3" not in html
