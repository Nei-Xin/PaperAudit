from __future__ import annotations

from pathlib import Path

from paperaudit.models import LearningReport, ParsedPaper, PaperChunk, ReportSection, LearningSectionType
from paperaudit.storage import ProjectStore
from paperaudit.ui.project_session import PROJECT_SESSION_KEYS, ProjectSession


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
    state = {key: key for key in PROJECT_SESSION_KEYS}
    state["global_setting"] = "kept"
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
