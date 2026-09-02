from __future__ import annotations

import json
from pathlib import Path

import pytest

from paperaudit.config import Settings
from paperaudit.models import (
    EvidenceAnchor,
    ParsedPaper,
    PaperChunk,
    PeerReviewReport,
    ReviewConcern,
    ReviewDecision,
    ReviewDimension,
    ReviewSeverity,
    IssueSeverity,
    IssueStatus,
    IssueSupportType,
    HumanReviewDecision,
    RelatedWorkComparison,
    RelatedWorkReference,
)
from paperaudit.service import (
    AuditService,
    _concern_consistency_warnings,
    _dedupe_review_concerns,
    build_revision_diff,
    calculate_peer_review_score,
    normalize_peer_review_weights,
    peer_review_rubric_metadata,
    peer_review_consistency_warnings,
    recalculate_peer_review,
)
from paperaudit.ui.peer_review import render_peer_review_markdown
from paperaudit.storage import ProjectStore


def _paper() -> ParsedPaper:
    return ParsedPaper(
        title="Test Paper",
        page_count=1,
        chunks=[PaperChunk(chunk_id="p1_b1", page=1, content="The method improves accuracy.")],
    )


def _review() -> PeerReviewReport:
    anchor = EvidenceAnchor(chunk_id="p1_b1", quote="The method improves accuracy.")
    return PeerReviewReport(
        paper_title="Test Paper",
        decision=ReviewDecision.BORDERLINE,
        overall_score=5.0,
        summary="Promising but incomplete.",
        strengths=["问题有意义"],
        major_concerns=[ReviewConcern(
            title="实验不足", severity=ReviewSeverity.MAJOR, description="缺少消融。",
            why_it_matters="无法判断贡献。", suggestion="补充消融实验。", evidence=[anchor]
        )],
        dimensions=[ReviewDimension(name="soundness", score=3, rationale="基本合理。", evidence=[anchor])],
        decision_rationale="需要补充实验。",
        top_priorities=["补充消融"],
    )


class _Client:
    def generate_peer_review(self, title: str, chunks: list[PaperChunk]) -> PeerReviewReport:
        return _review()


class _InvalidEvidenceClient:
    def generate_peer_review(self, title: str, chunks: list[PaperChunk]) -> PeerReviewReport:
        concern = _review().major_concerns[0].model_copy(update={
            "severity_level": IssueSeverity.FATAL,
            "evidence": [EvidenceAnchor(chunk_id="p1_b1", quote="not in paper")],
        })
        return _review().model_copy(update={"major_concerns": [concern]})


class _ComparisonClient(_Client):
    def compare_related_work(self, title: str, chunks: list[PaperChunk], references: list[dict[str, object]]) -> RelatedWorkComparison:
        return RelatedWorkComparison(
            assessment="差异仍需由相关工作原文进一步确认。",
            distinctions=["输入范式不同"],
            gaps=["缺少统一实验对照"],
            confidence=2,
        )


def test_peer_review_enriches_local_evidence() -> None:
    settings = Settings(api_base="https://example.invalid/v1", api_key="test", model="hy3")
    report = AuditService(settings, client=_Client()).generate_peer_review(_paper())  # type: ignore[arg-type]
    assert report.paper_title == "Test Paper"
    assert report.model_raw_score == 5.0
    assert report.score_calculation_version == "weighted-v1"
    assert report.rubric_weights["soundness"] > 0
    assert report.major_concerns[0].evidence[0].page == 1
    assert report.dimensions[0].evidence[0].quote == "The method improves accuracy."


def test_peer_review_downgrades_unverifiable_high_severity_evidence() -> None:
    settings = Settings(api_base="https://example.invalid/v1", api_key="test", model="hy3")
    report = AuditService(settings, client=_InvalidEvidenceClient()).generate_peer_review(_paper())  # type: ignore[arg-type]
    concern = report.major_concerns[0]
    assert concern.evidence == []
    assert concern.severity_level == IssueSeverity.MAJOR
    assert concern.status == IssueStatus.NEEDS_REVIEW
    assert concern.support_type == IssueSupportType.INSUFFICIENT_EVIDENCE
    assert any("逐字核验" in warning for warning in report.parse_warnings)


def test_peer_review_caps_unverified_p1_at_p2() -> None:
    concern = _review().major_concerns[0].model_copy(update={
        "severity_level": IssueSeverity.MAJOR,
        "evidence": [],
    })
    class _NoEvidenceClient:
        def generate_peer_review(self, title: str, chunks: list[PaperChunk]) -> PeerReviewReport:
            return _review().model_copy(update={"major_concerns": [concern]})
    settings = Settings(api_base="https://example.invalid/v1", api_key="test", model="hy3")
    report = AuditService(settings, client=_NoEvidenceClient()).generate_peer_review(_paper())  # type: ignore[arg-type]
    assert report.major_concerns[0].severity_level == IssueSeverity.MINOR
    assert report.major_concerns[0].status == IssueStatus.NEEDS_REVIEW


def test_review_concern_accepts_missing_legacy_severity() -> None:
    concern = ReviewConcern.model_validate({
        "title": "缺少统计检验",
        "severity_level": "P1",
        "description": "需要补充统计检验。",
        "why_it_matters": "否则无法判断稳健性。",
        "suggestion": "报告置信区间。",
    })
    assert concern.severity == ReviewSeverity.MAJOR


def test_related_work_comparison_uses_only_supplied_references() -> None:
    settings = Settings(api_base="https://example.invalid/v1", api_key="test", model="hy3")
    service = AuditService(settings, client=_ComparisonClient())
    comparison = service.compare_related_work(
        _paper(),
        [RelatedWorkReference(citation="Example et al.", year=2024, distinction="不同输入")],
    )
    assert comparison.references[0].citation == "Example et al."
    assert comparison.confidence == 2


def test_peer_review_storage_round_trip(tmp_path: Path) -> None:
    store = ProjectStore(tmp_path / "library")
    paper = _paper()
    metadata = store.save_paper_project(b"pdf", "paper.pdf", paper)
    review = _review().model_copy(update={
        "major_concerns": [
            _review().major_concerns[0].model_copy(
                update={
                    "human_reviewed": True,
                    "human_decision": HumanReviewDecision.CONFIRMED,
                    "human_note": "已核对原文。",
                }
            )
        ]
    })
    store.save_peer_review(metadata.project_id, review)
    loaded = store.load_peer_review(metadata.project_id)
    assert loaded is not None
    assert loaded.decision == ReviewDecision.BORDERLINE
    assert loaded.major_concerns[0].title == "实验不足"
    assert loaded.major_concerns[0].issue_id.startswith("issue-")
    assert loaded.major_concerns[0].human_decision == HumanReviewDecision.CONFIRMED
    assert loaded.major_concerns[0].human_note == "已核对原文。"


def test_peer_review_storage_preserves_ai_original_and_user_revision(tmp_path: Path) -> None:
    store = ProjectStore(tmp_path / "library")
    metadata = store.save_paper_project(b"pdf", "paper.pdf", _paper())
    concern = _review().major_concerns[0].model_copy(update={
        "ai_severity_level": IssueSeverity.MAJOR,
        "severity_level": IssueSeverity.MINOR,
        "status": IssueStatus.IGNORED,
        "human_reviewed": True,
    })
    store.save_peer_review(metadata.project_id, _review().model_copy(update={"major_concerns": [concern]}))
    loaded = store.load_peer_review(metadata.project_id)
    assert loaded is not None
    saved = loaded.major_concerns[0]
    assert saved.ai_severity_level == IssueSeverity.MAJOR
    assert saved.severity_level == IssueSeverity.MINOR
    assert saved.status == IssueStatus.IGNORED


def test_peer_review_storage_migrates_page_only_evidence(tmp_path: Path) -> None:
    store = ProjectStore(tmp_path / "library")
    metadata = store.save_paper_project(b"pdf", "paper.pdf", _paper())
    payload = _review().model_dump(mode="json")
    payload["major_concerns"][0]["evidence"] = [
        {"chunk_id": "p1_b1", "page": 1, "quote": None}
    ]
    review_path = store._project_dir(metadata.project_id) / "peer-review.json"  # type: ignore[attr-defined]
    review_path.write_text(json.dumps(payload), encoding="utf-8")

    loaded = store.load_peer_review(metadata.project_id)

    assert loaded is not None
    concern = loaded.major_concerns[0]
    assert concern.evidence == []
    assert concern.status == IssueStatus.NEEDS_REVIEW
    assert concern.support_type == IssueSupportType.INSUFFICIENT_EVIDENCE
    assert concern.confidence == 2
    assert any("历史评审证据" in warning for warning in loaded.parse_warnings)


def test_peer_review_consistency_warns_on_score_band_and_missing_rationale() -> None:
    report = _review().model_copy(update={"overall_score": 8.5})
    warnings = peer_review_consistency_warnings(report)
    assert any("不在" in item for item in warnings)
    assert any("相邻投稿建议" in item for item in warnings)


def test_revision_diff_counts_added_removed_and_changed_chunks() -> None:
    old = ParsedPaper(
        title="Test Paper", page_count=1,
        chunks=[
            PaperChunk(chunk_id="a", page=1, content="Introduction"),
            PaperChunk(chunk_id="b", page=1, content="Old result"),
            PaperChunk(chunk_id="c", page=1, content="Conclusion"),
        ],
    )
    new = ParsedPaper(
        title="Test Paper", page_count=2,
        chunks=[
            PaperChunk(chunk_id="a", page=1, content="Introduction"),
            PaperChunk(chunk_id="b2", page=1, content="New result"),
            PaperChunk(chunk_id="d", page=2, content="Additional analysis"),
        ],
    )
    diff = build_revision_diff(old, new)
    assert diff.changed_chunks == 2
    assert diff.removed_chunks == 0
    assert diff.added_chunks == 0
    assert "页数 1 → 2" in diff.summary


def test_peer_review_warns_when_high_severity_issue_lacks_evidence() -> None:
    report = _review().model_copy(update={
        "major_concerns": [
            _review().major_concerns[0].model_copy(
                update={"severity_level": IssueSeverity.FATAL, "evidence": []}
            )
        ]
    })
    warnings = peer_review_consistency_warnings(report)
    assert any("P0" in item and "依据" in item for item in warnings)


def test_peer_review_warns_when_fact_has_no_evidence() -> None:
    report = _review().model_copy(update={
        "major_concerns": [
            _review().major_concerns[0].model_copy(
                update={"support_type": IssueSupportType.FACT, "evidence": []}
            )
        ]
    })
    warnings = peer_review_consistency_warnings(report)
    assert any("事实判断" in item and "依据" in item for item in warnings)


def test_peer_review_warns_when_high_severity_confidence_is_low() -> None:
    report = _review().model_copy(update={
        "major_concerns": [
            _review().major_concerns[0].model_copy(
                update={"severity_level": IssueSeverity.MAJOR, "confidence": 2}
            )
        ]
    })
    warnings = peer_review_consistency_warnings(report)
    assert any("置信度不高" in item for item in warnings)


def test_peer_review_weights_are_normalized_and_reject_invalid_values() -> None:
    weights = normalize_peer_review_weights({"novelty": 3, "clarity": 1})
    assert round(sum(weights.values()), 6) == 1.0
    assert weights["novelty"] > weights["clarity"]
    with pytest.raises(ValueError):
        normalize_peer_review_weights({"unknown": 1})
    with pytest.raises(ValueError):
        normalize_peer_review_weights({"novelty": -1})


def test_peer_review_rubric_metadata_is_stable_and_custom_weights_are_versioned() -> None:
    general = peer_review_rubric_metadata("general_ai_ml")
    assert general[0] == "general_ai_ml@1.0"
    assert general[1]
    custom_a = peer_review_rubric_metadata("custom", {"novelty": 2, "clarity": 1})
    custom_b = peer_review_rubric_metadata("custom", {"clarity": 1, "novelty": 2})
    assert custom_a == custom_b
    assert custom_a[0].startswith("custom@1.0+")


def test_peer_review_score_and_decision_are_deterministic() -> None:
    dimensions = [
        ReviewDimension(name="significance", score=4, rationale=""),
        ReviewDimension(name="novelty", score=4, rationale=""),
        ReviewDimension(name="soundness", score=4, rationale=""),
        ReviewDimension(name="experimental_rigor", score=4, rationale=""),
        ReviewDimension(name="clarity", score=4, rationale=""),
        ReviewDimension(name="reproducibility", score=4, rationale=""),
    ]
    score, decision, breakdown, metadata = calculate_peer_review_score(dimensions)
    assert score == 8.0
    assert decision == ReviewDecision.WEAK_ACCEPT
    assert set(breakdown) == {"significance", "novelty", "soundness", "experimental_rigor", "clarity", "reproducibility"}
    assert metadata["weighted_mean"] == 4.0


def test_p0_caps_score_but_false_positive_does_not() -> None:
    dimensions = [ReviewDimension(name="significance", score=5, rationale="")]
    p0 = ReviewConcern(
        title="致命问题", severity=ReviewSeverity.MAJOR, severity_level=IssueSeverity.FATAL,
        description="", why_it_matters="", suggestion="",
    )
    score, decision, *_ = calculate_peer_review_score(dimensions, [p0])
    assert score == 4.0 and decision == ReviewDecision.WEAK_REJECT
    false_positive = p0.model_copy(update={"human_decision": HumanReviewDecision.FALSE_POSITIVE})
    score, decision, *_ = calculate_peer_review_score(dimensions, [false_positive])
    assert score == 10.0 and decision == ReviewDecision.STRONG_ACCEPT


def test_human_review_recalculation_updates_result() -> None:
    report = _review().model_copy(update={
        "dimensions": [ReviewDimension(name="significance", score=5, rationale="")],
        "major_concerns": [],
        "minor_concerns": [],
        "summary": "论文整体可靠，因此建议是BORDERLINE，优先修正文稿。",
        "decision_rationale": "综合建议为 Weak Reject。",
        "why_not_adjacent": "不建议STRONG_ACCEPT，因为仍有待核验项；不建议BORDERLINE或更弱。",
    })
    recalculated = recalculate_peer_review(report)
    assert recalculated.overall_score == 10.0
    assert recalculated.decision == ReviewDecision.STRONG_ACCEPT
    assert "建议是Strong Accept（按当前评分标准重算）" in recalculated.summary
    assert "建议为 Strong Accept（按当前评分标准重算）" in recalculated.decision_rationale
    assert "BORDERLINE" not in recalculated.summary
    assert "Weak Reject" not in recalculated.decision_rationale
    assert "不建议STRONG_ACCEPT" not in recalculated.why_not_adjacent
    assert "Strong Accept" in recalculated.why_not_adjacent


def test_peer_review_report_loads_without_new_scoring_fields() -> None:
    payload = _review().model_dump(mode="json")
    payload.pop("model_raw_score", None)
    payload.pop("rubric_weights", None)
    payload.pop("score_breakdown", None)
    payload.pop("score_calculation_version", None)
    loaded = PeerReviewReport.model_validate(payload)
    assert loaded.model_raw_score is None
    assert loaded.rubric_weights == {}


def test_peer_review_report_loads_without_rubric_metadata() -> None:
    payload = _review().model_dump(mode="json")
    payload.pop("rubric_updated_at", None)
    payload.pop("rubric_change_note", None)
    loaded = PeerReviewReport.model_validate(payload)
    assert loaded.rubric_version == "general_ai_ml@1.0"
    assert loaded.rubric_updated_at == ""


def test_peer_review_markdown_keeps_auxiliary_review_boundary_and_rubric_snapshot() -> None:
    report = _review().model_copy(update={
        "rubric_updated_at": "2026-08-31",
        "rubric_change_note": "通用标准",
        "major_concerns": [
            _review().major_concerns[0].model_copy(update={
                "ai_severity_level": IssueSeverity.MAJOR,
                "severity_level": IssueSeverity.MINOR,
            })
        ],
    })
    markdown = render_peer_review_markdown(report)
    assert "Rubric 版本" in markdown
    assert "AI 原始判断" in markdown
    assert "当前采用" in markdown
    assert "不代表真实会议录用决定" in markdown


def test_peer_review_dedupe_keeps_distinct_evidence_and_actions() -> None:
    first = _review().major_concerns[0]
    duplicate = first.model_copy()
    distinct = first.model_copy(update={
        "evidence": [EvidenceAnchor(chunk_id="p2_b1", quote="Another exact passage.")],
        "suggestion": "补充不同的对照实验。",
    })
    result = _dedupe_review_concerns([first, duplicate, distinct])
    assert len(result) == 2


def test_peer_review_consistency_warns_when_number_is_not_in_quote() -> None:
    concern = _review().major_concerns[0].model_copy(update={
        "description": "结果提升了 99%，但缺少消融。",
    })
    warnings = _concern_consistency_warnings(concern)
    assert any("99" in warning for warning in warnings)
