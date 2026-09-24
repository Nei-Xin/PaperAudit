from __future__ import annotations

from pathlib import Path
import time

from paperaudit.config import Settings
from paperaudit.models import (
    AuditJobStatus,
    AuditRuntimeSnapshot,
    EvidenceAnchor,
    ParsedPaper,
    PaperChunk,
    PeerReviewReport,
    ReviewDecision,
    ReviewDimension,
)
from paperaudit.peer_review_jobs import PeerReviewJobManager
from paperaudit.storage import ProjectStore


def _settings() -> Settings:
    return Settings(api_base="https://example.invalid/v1", api_key="test-secret", model="fake-model")


def _runtime() -> AuditRuntimeSnapshot:
    return AuditRuntimeSnapshot(model="fake-model", reasoning_effort="high", retrieval_top_k=5, judge_batch_size=6)


def _store(tmp_path: Path) -> tuple[ProjectStore, str]:
    store = ProjectStore(tmp_path / "library")
    metadata = store.save_paper_project(
        b"paper", "paper.pdf", ParsedPaper(
            title="Paper", page_count=1,
            chunks=[PaperChunk(chunk_id="p1_b1", page=1, content="The method improves accuracy.")],
        )
    )
    return store, metadata.project_id


def _wait_for(store: ProjectStore, project_id: str, job_id: str, status: AuditJobStatus):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        current = store.load_peer_review_job(project_id, job_id)
        if current.status == status:
            return current
        time.sleep(0.02)
    raise AssertionError(f"job did not reach {status}")


def _report() -> PeerReviewReport:
    return PeerReviewReport(
        paper_title="Paper", decision=ReviewDecision.BORDERLINE, overall_score=5,
        summary="summary", decision_rationale="rationale",
        dimensions=[ReviewDimension(name="soundness", score=3, rationale="", evidence=[EvidenceAnchor(chunk_id="p1_b1", quote="The method improves accuracy.")])],
    )


def test_peer_review_job_persists_stage_and_runtime_metadata(tmp_path: Path) -> None:
    store, project_id = _store(tmp_path)

    class Runner:
        def generate_peer_review(self, paper, *, venue, rubric_weights):
            return _report()

    job = store.create_peer_review_job(project_id, runtime=_runtime())
    manager = PeerReviewJobManager(store, service_factory=lambda _: Runner(), mark_interrupted_on_start=False)
    try:
        manager.submit(project_id, job.job_id, _settings())
        completed = _wait_for(store, project_id, job.job_id, AuditJobStatus.SUCCEEDED)
    finally:
        manager.shutdown()
    assert completed.progress == 1.0
    assert completed.stage == "模拟评审已完成"
    saved = store.load_peer_review(project_id)
    assert saved is not None
    assert saved.model_name == "fake-model"
    assert saved.prompt_version == "peer-review-v5"
    assert saved.elapsed_seconds is not None


def test_peer_review_failure_keeps_failed_stage_and_hides_secret(tmp_path: Path) -> None:
    store, project_id = _store(tmp_path)

    class Runner:
        def generate_peer_review(self, paper, *, venue, rubric_weights):
            raise RuntimeError("request failed with test-secret")

    job = store.create_peer_review_job(project_id, runtime=_runtime())
    manager = PeerReviewJobManager(store, service_factory=lambda _: Runner(), mark_interrupted_on_start=False)
    try:
        manager.submit(project_id, job.job_id, _settings())
        failed = _wait_for(store, project_id, job.job_id, AuditJobStatus.FAILED)
    finally:
        manager.shutdown()
    assert failed.stage.endswith("失败")
    assert "test-secret" not in (failed.error or "")
    assert "[已隐藏]" in (failed.error or "")


def _revision_pdf() -> bytes:
    import pymupdf
    with pymupdf.open() as document:
        page = document.new_page()
        page.insert_text((72, 72), "Revised paper with improved evidence.")
        return document.tobytes()


def test_revision_is_nonblocking_persisted_and_keeps_baseline_snapshot(tmp_path):
    from threading import Event
    from paperaudit.models import PeerReviewVenue
    from paperaudit.peer_review_jobs import PeerReviewRevisionJobManager
    from paperaudit.storage import StorageError
    import pytest

    store, project_id = _store(tmp_path)
    baseline = _report().model_copy(update={"venue": PeerReviewVenue.ICLR, "rubric_weights": {"soundness": 1.0}})
    store.save_peer_review(project_id, baseline)
    pdf = _revision_pdf()
    job = store.create_peer_review_revision_job(project_id, pdf_bytes=pdf,
        original_filename="revision.pdf", runtime=_runtime())
    frozen = store.load_peer_review_revision_input(project_id, job.job_id)[1]
    # Later user edits must not change the queued comparison baseline/rubric.
    store.save_peer_review(project_id, _report().model_copy(update={"summary": "User edit"}))
    entered, release = Event(), Event()
    calls = []

    class Runner:
        def generate_peer_review(self, paper, *, venue, rubric_weights):
            calls.append((venue, rubric_weights))
            entered.set()
            assert release.wait(5)
            return _report()

    manager = PeerReviewRevisionJobManager(store, service_factory=lambda _: Runner(), mark_interrupted_on_start=False)
    try:
        manager.submit(project_id, job.job_id, _settings())
        assert entered.wait(5)
        assert store.load_peer_review_revision_job(project_id, job.job_id).status == AuditJobStatus.RUNNING
        assert not store.list_peer_review_revisions(project_id)
        with pytest.raises(ValueError):
            manager.submit(project_id, job.job_id, _settings())
        with pytest.raises(StorageError, match="修改稿复审"):
            store.delete_project(project_id)
        with pytest.raises(StorageError, match="已有"):
            store.create_peer_review_revision_job(project_id, pdf_bytes=pdf,
                original_filename="duplicate.pdf", runtime=_runtime())
    finally:
        release.set()
        manager.shutdown()
    completed = store.load_peer_review_revision_job(project_id, job.job_id)
    assert completed.status == AuditJobStatus.SUCCEEDED
    revisions = store.list_peer_review_revisions(project_id)
    assert len(revisions) == 1 and revisions[0].revision_id == completed.revision_id
    assert store.load_peer_review_revision_pdf(project_id, completed.revision_id) == pdf
    assert calls == [(frozen.venue, frozen.rubric_weights)]
    assert store.load_peer_review(project_id).summary == "User edit"
    assert revisions[0].report.run_id == job.job_id
    assert revisions[0].report.model_name == job.runtime.model
    assert revisions[0].report.reasoning_effort == job.runtime.reasoning_effort


def test_revision_corrupt_pdf_fails_before_model_call_and_can_be_resubmitted(tmp_path):
    from paperaudit.peer_review_jobs import PeerReviewRevisionJobManager
    store, project_id = _store(tmp_path)
    store.save_peer_review(project_id, _report())
    job = store.create_peer_review_revision_job(project_id, pdf_bytes=b"broken PDF",
        original_filename="broken.pdf", runtime=_runtime())
    calls = []
    manager = PeerReviewRevisionJobManager(store, service_factory=lambda settings: calls.append(settings), mark_interrupted_on_start=False)
    manager.submit(project_id, job.job_id, _settings())
    manager.shutdown()
    failed = store.load_peer_review_revision_job(project_id, job.job_id)
    assert failed.status == AuditJobStatus.FAILED
    assert failed.stage == "正在解析修改稿失败"
    assert not calls and not store.list_peer_review_revisions(project_id)
    retry = store.create_peer_review_revision_job(project_id, pdf_bytes=_revision_pdf(),
        original_filename="fixed.pdf", runtime=_runtime())
    assert retry.status == AuditJobStatus.QUEUED


def test_revision_recovery_hash_validation_and_result_identity(tmp_path):
    import pytest
    from paperaudit.peer_review_jobs import PeerReviewRevisionJobManager
    from paperaudit.storage import StorageError
    store, project_id = _store(tmp_path)
    store.save_peer_review(project_id, _report())
    job = store.create_peer_review_revision_job(project_id, pdf_bytes=_revision_pdf(),
        original_filename="revision.pdf", runtime=_runtime())
    manager = PeerReviewRevisionJobManager(store)
    manager.shutdown()
    interrupted = store.load_peer_review_revision_job(project_id, job.job_id)
    assert interrupted.status == AuditJobStatus.INTERRUPTED
    assert interrupted.completed_at is not None
    assert len(store.list_peer_review_revision_jobs(project_id)) == 1
    with pytest.raises(StorageError, match="缺少结果"):
        store.update_peer_review_revision_job(project_id, interrupted.model_copy(update={"status": AuditJobStatus.SUCCEEDED}))
    with pytest.raises(StorageError, match="ID 无效"):
        store.update_peer_review_revision_job(project_id, interrupted.model_copy(update={"revision_id": "../outside"}))
    (store._project_dir(project_id) / "revision-jobs" / f"{job.job_id}.pdf").write_bytes(b"tampered")
    with pytest.raises(StorageError, match="输入"):
        store.load_peer_review_revision_input(project_id, job.job_id)


def test_revision_save_failure_preserves_original_review(tmp_path, monkeypatch):
    from paperaudit.peer_review_jobs import PeerReviewRevisionJobManager
    store, project_id = _store(tmp_path)
    store.save_peer_review(project_id, _report())
    original = store.load_peer_review(project_id)
    job = store.create_peer_review_revision_job(project_id, pdf_bytes=_revision_pdf(),
        original_filename="revision.pdf", runtime=_runtime())

    class Runner:
        def generate_peer_review(self, *args, **kwargs):
            return _report()

    def fail(*args, **kwargs):
        raise RuntimeError("save failed test-secret")

    monkeypatch.setattr(store, "save_peer_review_revision", fail)
    manager = PeerReviewRevisionJobManager(store, service_factory=lambda _: Runner(), mark_interrupted_on_start=False)
    manager.submit(project_id, job.job_id, _settings())
    manager.shutdown()
    failed = store.load_peer_review_revision_job(project_id, job.job_id)
    assert failed.status == AuditJobStatus.FAILED
    assert failed.revision_id is None
    assert "test-secret" not in failed.error
    assert store.load_peer_review(project_id) == original
