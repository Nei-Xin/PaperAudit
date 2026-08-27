from __future__ import annotations

from pathlib import Path
import time

from paperaudit.config import Settings
from paperaudit.learning_jobs import LearningJobManager
from paperaudit.models import (
    AuditJobStatus,
    AuditRuntimeSnapshot,
    LearningReport,
    PaperChunk,
    ParsedPaper,
)
from paperaudit.storage import ProjectStore
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
