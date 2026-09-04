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
