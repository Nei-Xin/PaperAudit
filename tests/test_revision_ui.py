"""Exercise the Streamlit revision status path without network calls."""

from streamlit.testing.v1 import AppTest


def test_revision_panel_restores_running_failed_and_completed_states():
    app = AppTest.from_string('''
import streamlit as st
from paperaudit.models import AuditRuntimeSnapshot, PeerReviewRevisionJob
from paperaudit.ui.peer_review import _render_revision_jobs
status = st.session_state.get("job_status", "RUNNING")
job = PeerReviewRevisionJob(
    job_id="revision-job-1", project_id="abc", created_at="2026-09-24",
    original_filename="revision.pdf", pdf_hash="hash", status=status,
    runtime=AuditRuntimeSnapshot(model="fake", reasoning_effort="high", retrieval_top_k=5, judge_batch_size=6),
    error="input corrupted" if status == "FAILED" else None,
)
_render_revision_jobs(lambda: [job], status == "RUNNING")
''').run()
    assert not app.exception
    assert any("后台复审" in item.value for item in app.info)
    app.session_state["job_status"] = "FAILED"
    app.run()
    assert not app.exception
    assert any("重新上传" in item.value for item in app.warning)
    app.session_state["job_status"] = "SUCCEEDED"
    app.run()
    assert not app.exception
    assert not app.warning and not app.info


def test_review_page_disables_revision_submission_during_background_work():
    app = AppTest.from_string('''
from paperaudit.models import AuditRuntimeSnapshot, PeerReviewRevisionJob, PeerReviewReport
from paperaudit.ui.peer_review import render_peer_review
report = PeerReviewReport(paper_title="Paper", decision="BORDERLINE", overall_score=5,
    summary="Summary", decision_rationale="Rationale")
job = PeerReviewRevisionJob(job_id="revision-job-1", project_id="abc", created_at="2026-09-24",
    original_filename="revision.pdf", pdf_hash="hash", status="RUNNING",
    runtime=AuditRuntimeSnapshot(model="fake", reasoning_effort="high", retrieval_top_k=5, judge_batch_size=6))
render_peer_review(report, on_submit_revision=lambda data, name: None,
    load_revision_jobs=lambda: [job], load_revisions=lambda: [])
''').run()
    assert not app.exception
    assert app.button(key="peer-review-submit-revision").disabled
    assert any("后台复审" in item.value for item in app.info)
