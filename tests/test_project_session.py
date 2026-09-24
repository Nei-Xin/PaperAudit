from __future__ import annotations

from pathlib import Path

from paperaudit.models import LearningReport, ParsedPaper, PaperChunk, ReportSection, LearningSectionType
from paperaudit.storage import ProjectStore
from paperaudit.ui.project_session import ProjectSession


def _paper(title: str) -> ParsedPaper:
    return ParsedPaper(
        title=title,
        page_count=1,
        chunks=[PaperChunk(chunk_id="p1_b1", page=1, content="Evidence")],
    )


def _report(title: str) -> LearningReport:
    return LearningReport(
        paper_title=title,
        one_sentence_summary="Summary",
        sections=[
            ReportSection(
                section_type=LearningSectionType.RESEARCH_PROBLEM,
                title="Problem",
                overview="Overview",
                points=[],
            )
        ],
    )


def test_project_session_clear_removes_all_project_scoped_state() -> None:
    state = {
        "peer_review": object(),
        "learning_report": object(),
        "active_project_id": "p1",
        "peer_review_revision_pdf": b"previous revision",
        "paper_qa_pending": {"question": "previous question"},
        "paper_pdf_upload": object(),
        "global_setting": "kept",
    }
    query = {"project": "p1", "page": "learning"}

    ProjectSession(state, query).clear()

    assert state == {"global_setting": "kept"}
    assert query == {"page": "learning"}


def test_project_session_switch_isolates_transient_state(tmp_path: Path) -> None:
    store = ProjectStore(tmp_path / "library")
    first = store.save_learning_project(b"one", "one.pdf", _paper("One"), _report("One"))
    second = store.save_learning_project(b"two", "two.pdf", _paper("Two"), _report("Two"))
    state = {
        "active_project_id": first.project_id,
        "project_conversations": [],
        "paper_qa_history": [],
        "learning_focus_evidence": "old-project-evidence",
    }
    query: dict[str, str] = {"project": first.project_id}

    ProjectSession(state, query).open(store, second.project_id)

    assert state["active_project_id"] == second.project_id
    assert state["learning_paper"].title == "Two"
    assert "learning_focus_evidence" not in state
    assert query["project"] == second.project_id


def test_switch_clears_review_edits_revision_preview_and_audit_filters(tmp_path):
    store = ProjectStore(tmp_path / "library")
    target = store.save_paper_project(b"target", "target.pdf", _paper("Target"))
    state = {
        "peer_review_revision_pdf": b"old revision",
        "peer_review_revision_pdf_name": "old.pdf",
        "peer_review_pdf_focus": {"page": 9},
        "peer-major-0-manual-note": "Do not reuse for another paper",
        "peer-review-related-work-input": "Old reference",
        "peer-review-action-done-Same title-0": True,
        "audit_search_query_old": "old claim",
        "paper_qa_pending": {"question": "Old question"},
        "joint_code_selection": "old code",
        "custom_api_key": "session-config",
        "peer_review_venue": "iclr",
        "peer-review-weight-novelty": 1.5,
    }
    session = ProjectSession(state, {})
    session.open(store, target.project_id)
    assert state["result_mode"] == "audit_project"
    assert state["paper_qa_history"] == []
    assert state["custom_api_key"] == "session-config"
    assert state["peer_review_venue"] == "iclr"
    assert state["peer-review-weight-novelty"] == 1.5
    for key in (
        "peer_review_revision_pdf", "peer_review_revision_pdf_name",
        "peer_review_pdf_focus", "peer-major-0-manual-note",
        "peer-review-related-work-input", "peer-review-action-done-Same title-0",
        "audit_search_query_old", "paper_qa_pending", "joint_code_selection",
    ):
        assert key not in state


def test_failed_switch_keeps_active_project_and_saves_its_history(tmp_path, monkeypatch):
    import pytest
    from paperaudit.models import PaperAnswer, AnswerStatus
    from paperaudit.storage import StorageError

    store = ProjectStore(tmp_path / "library")
    first = store.save_paper_project(b"one", "one.pdf", _paper("One"))
    second = store.save_paper_project(b"two", "two.pdf", _paper("Two"))
    answer = PaperAnswer(question="Question", answer="Answer", status=AnswerStatus.ANSWERED)
    state = {"active_project_id": first.project_id, "paper_qa_history": [answer]}
    query = {"project": first.project_id}
    before = dict(state)

    def fail_review(_):
        raise StorageError("Unreadable review")

    monkeypatch.setattr(store, "load_peer_review", fail_review)
    with pytest.raises(StorageError, match="Unreadable review"):
        ProjectSession(state, query).open(store, second.project_id)
    assert state == before
    assert query["project"] == first.project_id
    assert store.load_learning_project(first.project_id).paper_history == [answer]


def test_learning_initialization_keeps_upload_and_resets_previous_project():
    upload = object()
    state = {
        "paper_pdf_upload": upload,
        "peer_review_revision_pdf": b"previous",
        "project_conversations": ["old conversation"],
        "active_project_id": "old",
        "paper_qa_pending": {"question": "old"},
    }
    query = {"project": "old"}
    ProjectSession(state, query).initialize_learning(
        _paper("New"), b"new", _report("New"), None, "Code parsing failed", "new.pdf",
    )
    assert state["paper_pdf_upload"] is upload
    assert state["learning_paper"].title == "New"
    assert state["paper_qa_history"] == state["joint_qa_history"] == []
    assert state["code_parse_warning"] == "Code parsing failed"
    assert "project_conversations" not in state
    assert "peer_review_revision_pdf" not in state
    assert "active_project_id" not in state and "project" not in query
