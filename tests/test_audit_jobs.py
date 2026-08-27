from __future__ import annotations

from pathlib import Path
from threading import Event
import time

from paperaudit.audit_jobs import AuditJobManager
from paperaudit.config import Settings
from paperaudit.models import (
    AuditJobStatus,
    AuditRuntimeSnapshot,
    ClaimCategory,
    LearningReport,
    PaperChunk,
    ParsedPaper,
)
from paperaudit.storage import ProjectStore
from paperaudit.ui.demo_data import get_demo_audit_run


def _store(tmp_path: Path) -> tuple[ProjectStore, str]:
    store = ProjectStore(tmp_path / "library")
    metadata = store.save_learning_project(
        b"background-audit-paper",
        "paper.pdf",
        ParsedPaper(
            title="Paper",
            page_count=1,
            chunks=[PaperChunk(chunk_id="p1_b1", page=1, content="Evidence")],
        ),
        LearningReport(
            paper_title="Paper",
            one_sentence_summary="Summary",
            sections=[],
        ),
    )
    return store, metadata.project_id


def _settings() -> Settings:
    return Settings(
        api_base="https://example.invalid/v1",
        api_key="test-secret-key",
        model="fake-model",
        reasoning_effort="high",
        retrieval_top_k=5,
        judge_batch_size=6,
    )


def _create_job(store: ProjectStore, project_id: str, text: str):
    return store.create_audit_job(
        project_id,
        report_text=text,
        source_type="uploaded_report",
        source_label=f"{text}.md",
        source_filename=f"{text}.md",
        scope=[ClaimCategory.CONTRIBUTION],
        audit_mode="audit_existing",
        runtime=AuditRuntimeSnapshot(
            model="fake-model",
            reasoning_effort="high",
            retrieval_top_k=5,
            judge_batch_size=6,
        ),
    )


def _wait_for(store: ProjectStore, project_id: str, job_id: str, status: AuditJobStatus):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        job = store.load_audit_job(project_id, job_id)
        if job.status == status:
            return job
        time.sleep(0.02)
    raise AssertionError(f"job did not reach {status}")


def test_background_manager_queues_and_persists_results(tmp_path: Path) -> None:
    store, project_id = _store(tmp_path)
    gate = Event()

    class BlockingRunner:
        def audit(self, paper, report_text, scope, *, mode, progress=None):
            assert paper.title == "Paper"
            if progress:
                progress("正在判断论断", 0.5)
            assert gate.wait(5)
            return get_demo_audit_run().model_copy(
                update={
                    "paper_title": paper.title,
                    "page_count": paper.page_count,
                    "mode": mode,
                    "scope": list(scope),
                    "report_text": report_text,
                }
            )

    first = _create_job(store, project_id, "first")
    second = _create_job(store, project_id, "second")
    manager = AuditJobManager(
        store,
        service_factory=lambda _: BlockingRunner(),
        mark_interrupted_on_start=False,
    )
    try:
        started_at = time.monotonic()
        manager.submit(project_id, first.job_id, _settings())
        manager.submit(project_id, second.job_id, _settings())
        assert time.monotonic() - started_at < 0.5
        _wait_for(store, project_id, first.job_id, AuditJobStatus.RUNNING)
        assert store.load_audit_job(project_id, second.job_id).status == AuditJobStatus.QUEUED

        gate.set()
        completed_first = _wait_for(
            store, project_id, first.job_id, AuditJobStatus.SUCCEEDED
        )
        completed_second = _wait_for(
            store, project_id, second.job_id, AuditJobStatus.SUCCEEDED
        )
    finally:
        gate.set()
        manager.shutdown()

    assert completed_first.audit_id
    assert completed_second.audit_id
    assert completed_first.audit_id != completed_second.audit_id
    assert len(store.list_audit_runs(project_id)) == 2
    _, first_run = store.load_audit_run(project_id, completed_first.audit_id)
    assert first_run.report_text == "first"


def test_background_failure_is_persisted_and_secret_is_hidden(tmp_path: Path) -> None:
    store, project_id = _store(tmp_path)
    job = _create_job(store, project_id, "failure")

    class FailingRunner:
        def audit(self, paper, report_text, scope, *, mode, progress=None):
            raise RuntimeError("request failed with test-secret-key")

    manager = AuditJobManager(
        store,
        service_factory=lambda _: FailingRunner(),
        mark_interrupted_on_start=False,
    )
    try:
        manager.submit(project_id, job.job_id, _settings())
        failed = _wait_for(store, project_id, job.job_id, AuditJobStatus.FAILED)
    finally:
        manager.shutdown()

    assert failed.audit_id is None
    assert failed.error is not None
    assert "test-secret-key" not in failed.error
    assert "[已隐藏]" in failed.error
    assert store.list_audit_runs(project_id) == []


def test_background_save_failure_is_not_reported_as_success(tmp_path: Path) -> None:
    store, project_id = _store(tmp_path)
    job = _create_job(store, project_id, "save-failure")

    class SuccessfulRunner:
        def audit(self, paper, report_text, scope, *, mode, progress=None):
            return get_demo_audit_run().model_copy(
                update={
                    "paper_title": paper.title,
                    "page_count": paper.page_count,
                    "mode": mode,
                    "scope": list(scope),
                    "report_text": report_text,
                }
            )

    original_save = store.save_audit_run

    def fail_save(*args, **kwargs):
        raise RuntimeError("result storage unavailable")

    store.save_audit_run = fail_save  # type: ignore[method-assign]
    manager = AuditJobManager(
        store,
        service_factory=lambda _: SuccessfulRunner(),
        mark_interrupted_on_start=False,
    )
    try:
        manager.submit(project_id, job.job_id, _settings())
        failed = _wait_for(store, project_id, job.job_id, AuditJobStatus.FAILED)
    finally:
        manager.shutdown()
        store.save_audit_run = original_save  # type: ignore[method-assign]

    assert failed.audit_id is None
    assert failed.stage == "审计失败"
    assert "result storage unavailable" in (failed.error or "")
    assert store.list_audit_runs(project_id) == []
