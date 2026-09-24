from __future__ import annotations

from pathlib import Path
from dataclasses import replace
import time

from paperaudit.config import Settings
from paperaudit.learning_jobs import LearningJobManager
from paperaudit.models import (
    AuditJobStatus,
    AuditRuntimeSnapshot,
    LearningReport,
    PaperChunk,
    ParsedPaper,
    PaperAnswer,
    AnswerStatus,
)
from paperaudit.storage import ProjectStore, make_conversation
from paperaudit.ui.demo_data import get_demo_audit_run


def _settings() -> Settings:
    return Settings(
        api_base="https://example.invalid/v1",
        api_key="test-secret-key",
        model="fake-model",
        reasoning_effort="high",
        retrieval_top_k=5,
        judge_batch_size=6,
    )


def _runtime() -> AuditRuntimeSnapshot:
    return AuditRuntimeSnapshot(
        model="fake-model",
        reasoning_effort="high",
        retrieval_top_k=5,
        judge_batch_size=6,
    )


def _wait_for(store: ProjectStore, project_id: str, job_id: str, status: AuditJobStatus):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        job = store.load_learning_job(project_id, job_id)
        if job.status == status:
            return job
        time.sleep(0.02)
    raise AssertionError(f"job did not reach {status}")


def test_background_learning_upgrades_audit_only_project_and_preserves_audits(
    tmp_path: Path,
) -> None:
    store = ProjectStore(tmp_path / "library")
    paper = ParsedPaper(
        title="Paper",
        page_count=1,
        chunks=[PaperChunk(chunk_id="p1_b1", page=1, content="Evidence")],
    )
    metadata = store.save_paper_project(b"learning-paper", "paper.pdf", paper)
    store.save_audit_run(
        metadata.project_id,
        get_demo_audit_run().model_copy(
            update={"paper_title": paper.title, "page_count": paper.page_count}
        ),
        source_type="uploaded_report",
        source_label="slides.pptx",
        model="fake-model",
        reasoning_effort="high",
        retrieval_top_k=5,
        judge_batch_size=6,
    )

    class Runner:
        def generate_learning_report(self, parsed_paper):
            assert parsed_paper.title == "Paper"
            return LearningReport(
                paper_title=parsed_paper.title,
                one_sentence_summary="Generated summary",
                sections=[],
            )

    job = store.create_learning_job(metadata.project_id, runtime=_runtime())
    manager = LearningJobManager(
        store,
        service_factory=lambda _: Runner(),
        mark_interrupted_on_start=False,
    )
    try:
        manager.submit(metadata.project_id, job.job_id, _settings())
        completed = _wait_for(
            store, metadata.project_id, job.job_id, AuditJobStatus.SUCCEEDED
        )
    finally:
        manager.shutdown()

    saved = store.load_learning_project(metadata.project_id)
    assert completed.progress == 1.0
    assert saved.report is not None
    assert saved.report.one_sentence_summary == "Generated summary"
    assert len(store.list_audit_runs(metadata.project_id)) == 1


def test_learning_job_failure_is_persisted_without_exposing_secret(tmp_path: Path) -> None:
    store = ProjectStore(tmp_path / "library")
    metadata = store.save_paper_project(
        b"failure-paper",
        "paper.pdf",
        ParsedPaper(
            title="Paper",
            page_count=1,
            chunks=[PaperChunk(chunk_id="p1_b1", page=1, content="Evidence")],
        ),
    )

    class Runner:
        def generate_learning_report(self, paper):
            raise RuntimeError("request failed with test-secret-key")

    job = store.create_learning_job(metadata.project_id, runtime=_runtime())
    manager = LearningJobManager(
        store,
        service_factory=lambda _: Runner(),
        mark_interrupted_on_start=False,
    )
    try:
        manager.submit(metadata.project_id, job.job_id, _settings())
        failed = _wait_for(store, metadata.project_id, job.job_id, AuditJobStatus.FAILED)
    finally:
        manager.shutdown()

    assert failed.error is not None
    assert "test-secret-key" not in failed.error
    assert "[已隐藏]" in failed.error
    assert store.load_learning_project(metadata.project_id).report is None


def test_background_learning_preserves_changes_made_during_generation(tmp_path: Path) -> None:
    store = ProjectStore(tmp_path / "library")
    paper = ParsedPaper(title="Paper", page_count=1, chunks=[])
    metadata = store.save_paper_project(b"concurrent-learning", "paper.pdf", paper)
    first = replace(make_conversation("First"), paper_history=[PaperAnswer(
        question="First?", answer="First answer", status=AnswerStatus.ANSWERED,
    )])
    second = replace(make_conversation("Second"), paper_history=[PaperAnswer(
        question="Second?", answer="Second answer", status=AnswerStatus.ANSWERED,
    )])
    store.save_conversations(metadata.project_id, [first], first.conversation_id)

    class Runner:
        def generate_learning_report(self, parsed_paper):
            # Happens after the worker has read its snapshot, before it saves.
            store.save_conversations(metadata.project_id, [first, second], second.conversation_id)
            store.update_project_title(metadata.project_id, "Updated title")
            return LearningReport(paper_title="Paper", one_sentence_summary="New report", sections=[])

    job = store.create_learning_job(metadata.project_id, runtime=_runtime())
    manager = LearningJobManager(store, service_factory=lambda _: Runner(), mark_interrupted_on_start=False)
    try:
        manager.submit(metadata.project_id, job.job_id, _settings())
        _wait_for(store, metadata.project_id, job.job_id, AuditJobStatus.SUCCEEDED)
    finally:
        manager.shutdown()
    saved = store.load_learning_project(metadata.project_id)
    assert saved.conversations == [first, second]
    assert saved.active_conversation_id == second.conversation_id
    assert saved.metadata.title == "Updated title"
    assert saved.report.one_sentence_summary == "New report"


def test_shared_runner_persists_executor_submission_failure(tmp_path):
    import pytest
    store = ProjectStore(tmp_path / "library")
    project = store.save_paper_project(b"submission-failure", "paper.pdf",
        ParsedPaper(title="Paper", page_count=1, chunks=[]))
    job = store.create_learning_job(project.project_id, runtime=_runtime())
    manager = LearningJobManager(store, mark_interrupted_on_start=False)
    manager.shutdown()
    with pytest.raises(RuntimeError):
        manager.submit(project.project_id, job.job_id, _settings())
    failed = store.load_learning_job(project.project_id, job.job_id)
    assert failed.status == AuditJobStatus.FAILED
    assert failed.stage == "任务提交失败"


def test_shared_runner_handles_initial_status_write_failure(tmp_path, monkeypatch):
    store = ProjectStore(tmp_path / "library")
    project = store.save_paper_project(b"status-failure", "paper.pdf",
        ParsedPaper(title="Paper", page_count=1, chunks=[]))
    job = store.create_learning_job(project.project_id, runtime=_runtime())
    original_update = store.update_learning_job

    def update(project_id, value):
        if value.status == AuditJobStatus.RUNNING:
            raise OSError("write failed test-secret-key")
        original_update(project_id, value)

    monkeypatch.setattr(store, "update_learning_job", update)
    manager = LearningJobManager(store, mark_interrupted_on_start=False)
    manager.submit(project.project_id, job.job_id, _settings())
    manager.shutdown()
    failed = store.load_learning_job(project.project_id, job.job_id)
    assert failed.status == AuditJobStatus.FAILED
    assert "test-secret-key" not in failed.error


def test_shared_runner_shutdown_marks_queued_work_interrupted(tmp_path):
    from threading import Event
    store = ProjectStore(tmp_path / "library")
    paper = ParsedPaper(title="Paper", page_count=1, chunks=[])
    first = store.save_paper_project(b"first", "first.pdf", paper)
    second = store.save_paper_project(b"second", "second.pdf", paper)
    entered, release = Event(), Event()

    class Runner:
        def generate_learning_report(self, paper):
            entered.set()
            assert release.wait(5)
            return LearningReport(paper_title="Paper", one_sentence_summary="Done", sections=[])

    manager = LearningJobManager(store, service_factory=lambda _: Runner(), mark_interrupted_on_start=False)
    a = store.create_learning_job(first.project_id, runtime=_runtime())
    b = store.create_learning_job(second.project_id, runtime=_runtime())
    try:
        manager.submit(first.project_id, a.job_id, _settings())
        assert entered.wait(5)
        manager.submit(second.project_id, b.job_id, _settings())
        manager.shutdown(wait=False)
        assert store.load_learning_job(second.project_id, b.job_id).status == AuditJobStatus.INTERRUPTED
    finally:
        release.set()
        manager.shutdown()
    assert store.load_learning_job(first.project_id, a.job_id).status == AuditJobStatus.SUCCEEDED
