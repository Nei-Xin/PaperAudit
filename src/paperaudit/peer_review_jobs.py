"""Background workflows for initial reviews and uploaded paper revisions."""

from __future__ import annotations

from collections.abc import Callable
from time import perf_counter
from typing import Protocol

from paperaudit.config import Settings
from paperaudit.job_runner import BackgroundJobManager, JobContext, utc_now
from paperaudit.models import PeerReviewJob, PeerReviewRevisionJob, PeerReviewReport, PeerReviewVenue
from paperaudit.pdf_parser import parse_pdf
from paperaudit.peer_review_revision import build_revision_payload
from paperaudit.service import AuditService
from paperaudit.storage import ProjectStore


class PeerReviewRunner(Protocol):
    def generate_peer_review(self, paper: object, *, venue: PeerReviewVenue = PeerReviewVenue.GENERAL,
                             rubric_weights: dict[str, float] | None = None) -> PeerReviewReport: ...


def _runtime_report(review: PeerReviewReport, job_id: str, settings: Settings,
                    started: float) -> PeerReviewReport:
    return review.model_copy(update={
        "run_id": job_id, "generated_at": utc_now(), "model_name": settings.model,
        "reasoning_effort": settings.reasoning_effort,
        "elapsed_seconds": round(perf_counter() - started, 3),
    })


class PeerReviewJobManager(BackgroundJobManager[PeerReviewJob]):
    start_stage = "正在启动评审任务"
    success_stage = "模拟评审已完成"

    def __init__(self, store: ProjectStore, *,
                 service_factory: Callable[[Settings], PeerReviewRunner] = AuditService,
                 mark_interrupted_on_start: bool = True) -> None:
        self._store = store
        super().__init__(service_factory=service_factory, thread_name_prefix="paperaudit-review",
                         recover=store.mark_interrupted_peer_review_jobs if mark_interrupted_on_start else None)

    def _load_job(self, project_id: str, job_id: str) -> PeerReviewJob:
        return self._store.load_peer_review_job(project_id, job_id)

    def _update_job(self, project_id: str, job: PeerReviewJob) -> None:
        self._store.update_peer_review_job(project_id, job)

    def _execute(self, context: JobContext[PeerReviewJob], settings: Settings) -> dict[str, str]:
        started = perf_counter()
        job = context.job
        context.progress("正在解析论文并准备检索上下文", 0.2)
        saved = self._store.load_learning_project(job.project_id)
        context.progress("正在生成结构化评审", 0.4)
        review = self._service_factory(settings).generate_peer_review(
            saved.paper, venue=job.venue, rubric_weights=job.rubric_weights,
        )
        review = _runtime_report(review, job.job_id, settings, started)
        context.progress("正在保存评审结果", 0.9)
        self._store.save_peer_review(job.project_id, review)
        return {}


class PeerReviewRevisionJobManager(BackgroundJobManager[PeerReviewRevisionJob]):
    start_stage = "正在准备修改稿复审"
    success_stage = "修改稿复审已完成"

    def __init__(self, store: ProjectStore, *,
                 service_factory: Callable[[Settings], PeerReviewRunner] = AuditService,
                 mark_interrupted_on_start: bool = True) -> None:
        self._store = store
        super().__init__(service_factory=service_factory, thread_name_prefix="paperaudit-revision",
                         recover=store.mark_interrupted_peer_review_revision_jobs if mark_interrupted_on_start else None)

    def _load_job(self, project_id: str, job_id: str) -> PeerReviewRevisionJob:
        return self._store.load_peer_review_revision_job(project_id, job_id)

    def _update_job(self, project_id: str, job: PeerReviewRevisionJob) -> None:
        self._store.update_peer_review_revision_job(project_id, job)

    def _execute(self, context: JobContext[PeerReviewRevisionJob], settings: Settings) -> dict[str, str]:
        started = perf_counter()
        job = context.job
        pdf_bytes, previous = self._store.load_peer_review_revision_input(job.project_id, job.job_id)
        original = self._store.load_learning_project(job.project_id).paper
        context.progress("正在解析修改稿", 0.15)
        paper = parse_pdf(pdf_bytes)
        context.progress("正在生成修改稿评审", 0.3)
        review = self._service_factory(settings).generate_peer_review(
            paper, venue=job.venue, rubric_weights=job.rubric_weights,
        )
        review = _runtime_report(review, job.job_id, settings, started)
        context.progress("正在对比修改稿问题", 0.8)
        payload = build_revision_payload(original, paper, previous, review)
        context.progress("正在保存修改稿复审", 0.9)
        revision = self._store.save_peer_review_revision(
            job.project_id, pdf_bytes=pdf_bytes, original_filename=job.original_filename,
            paper=paper, report=review, **payload,
        )
        return {"revision_id": revision.revision_id}
