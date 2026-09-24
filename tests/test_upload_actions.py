"""Check all upload workflows against real local persistence and fake model calls."""
from types import SimpleNamespace

import pytest

from paperaudit.config import Settings
from paperaudit.models import LearningReport, PaperChunk, ParsedPaper
from paperaudit.storage import ProjectStore
from paperaudit.ui import upload_actions
from paperaudit.ui.project_session import ProjectSession
from paperaudit.ui.upload import UploadSubmission


class Rerun(BaseException):
    pass


@pytest.mark.parametrize("mode", ["learn", "peer_review", "audit_existing"])
def test_upload_saves_project_and_routes_to_requested_workflow(tmp_path, monkeypatch, mode):
    state = {
        "peer_review_revision_pdf": b"old",
        "peer-major-0-manual-note": "old note",
        "paper_pdf_upload": object(),
        "peer_review_venue": "iclr",
    }
    query = {}
    statuses = []
    errors = []
    submitted = []
    store = ProjectStore(tmp_path)
    paper = ParsedPaper(title="New paper", page_count=1, chunks=[
        PaperChunk(chunk_id="p1_b1", page=1, content="New evidence"),
    ])
    report = LearningReport(paper_title=paper.title, one_sentence_summary="Summary", sections=[])
    monkeypatch.setattr(upload_actions, "AuditService", lambda settings: SimpleNamespace(
        parse=lambda pdf: paper, generate_learning_report=lambda paper: report,
    ))

    def rerun():
        raise Rerun()

    monkeypatch.setattr(upload_actions, "st", SimpleNamespace(
        session_state=state, query_params=query, rerun=rerun, error=errors.append,
    ))
    submission = UploadSubmission(
        pdf_bytes=b"new pdf", filename="new.pdf", mode=mode,
        report_text="A claim", report_source_label="Notes", report_source_filename=None,
        scope=[], code_bytes=None, code_filename=None, codebase=None,
        status=SimpleNamespace(update=lambda **kwargs: statuses.append(kwargs)),
        progress_bar=SimpleNamespace(progress=lambda *args, **kwargs: None),
    )

    def submit_review():
        submitted.append(("review", state["active_project_id"], state["peer_review_venue"]))
        return SimpleNamespace(job_id="review-job")

    def submit_audit(*args):
        submitted.append(("audit", state["active_project_id"], args))
        return SimpleNamespace(job_id="audit-job")

    with pytest.raises(Rerun):
        upload_actions.process_upload(
            submission, Settings("", "", "fake"), store,
            ProjectSession(state, query), submit_review, submit_audit,
        )
    assert errors == []
    assert statuses[-1]["state"] == "complete"
    saved = store.load_learning_project(state["active_project_id"])
    assert saved.pdf_bytes == b"new pdf"
    assert query["project"] == saved.metadata.project_id
    assert "peer_review_revision_pdf" not in state
    assert "peer-major-0-manual-note" not in state
    assert "paper_pdf_upload" in state
    if mode == "learn":
        assert saved.report == report
        assert state["result_mode"] == "learning"
        assert submitted == []
    elif mode == "peer_review":
        assert state["result_mode"] == "peer_review"
        assert state["peer_review_job_id"] == "review-job"
        assert submitted == [("review", saved.metadata.project_id, "iclr")]
    else:
        assert "result_mode" not in state
        assert state["launch_audit_job_id"] == "audit-job"
        assert submitted[0][0:2] == ("audit", saved.metadata.project_id)
        assert submitted[0][2][0] == "A claim"
