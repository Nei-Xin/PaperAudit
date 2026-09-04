"""Single-process background execution for simulated peer-review jobs."""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime, timezone
from time import perf_counter
from threading import Lock
from typing import Protocol

from paperaudit.config import Settings
from paperaudit.models import AuditJobStatus, PeerReviewJob, PeerReviewReport, PeerReviewVenue
from paperaudit.service import AuditService
from paperaudit.storage import ProjectStore


class PeerReviewRunner(Protocol):
    def generate_peer_review(
        self,
        paper: object,
        *,
        venue: PeerReviewVenue = PeerReviewVenue.GENERAL,
        rubric_weights: dict[str, float] | None = None,
    ) -> PeerReviewReport: ...


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class PeerReviewJobManager:
    def __init__(
        self,
        store: ProjectStore,
        *,
        service_factory: Callable[[Settings], PeerReviewRunner] = AuditService,
        mark_interrupted_on_start: bool = True,
    ) -> None:
        self._store = store
        self._service_factory = service_factory
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="paperaudit-review")
        self._futures: dict[str, Future[None]] = {}
        self._lock = Lock()
        if mark_interrupted_on_start:
            self._store.mark_interrupted_peer_review_jobs()

    def submit(self, project_id: str, job_id: str, settings: Settings) -> None:
        job = self._store.load_peer_review_job(project_id, job_id)
        if job.status != AuditJobStatus.QUEUED:
            raise ValueError("只有等待中的评审任务可以提交。")
        with self._lock:
            existing = self._futures.get(job_id)
            if existing is not None and not existing.done():
                raise ValueError("该评审任务已经提交。")
            future = self._executor.submit(self._run_job, project_id, job_id, settings)
            self._futures[job_id] = future
        future.add_done_callback(lambda _: self._forget(job_id))

    def _forget(self, job_id: str) -> None:
        with self._lock:
            self._futures.pop(job_id, None)

    def _run_job(self, project_id: str, job_id: str, settings: Settings) -> None:
        current_stage = "正在启动评审任务"
        job = self._store.load_peer_review_job(project_id, job_id).model_copy(
            update={
                "status": AuditJobStatus.RUNNING,
                "started_at": _utc_now(),
                "progress": 0.05,
                "stage": current_stage,
                "error": None,
            }
        )
        started_clock = perf_counter()
        try:
            self._store.update_peer_review_job(project_id, job)
            current_stage = "正在解析论文并准备检索上下文"
            job = job.model_copy(update={"progress": 0.2, "stage": current_stage})
            self._store.update_peer_review_job(project_id, job)
            saved = self._store.load_learning_project(project_id)
            current_stage = "正在生成结构化评审"
            job = job.model_copy(update={"progress": 0.4, "stage": current_stage})
            self._store.update_peer_review_job(project_id, job)
            review = self._service_factory(settings).generate_peer_review(
                saved.paper,
                venue=job.venue,
                rubric_weights=job.rubric_weights,
            )
            review = review.model_copy(update={
                "run_id": job.job_id,
                "generated_at": _utc_now(),
                "model_name": settings.model,
                "reasoning_effort": settings.reasoning_effort,
                "elapsed_seconds": round(perf_counter() - started_clock, 3),
            })
            current_stage = "正在校验评审证据"
            job = job.model_copy(update={"progress": 0.78, "stage": current_stage})
            self._store.update_peer_review_job(project_id, job)
            current_stage = "正在保存评审结果"
            job = job.model_copy(update={"progress": 0.9, "stage": current_stage})
            self._store.update_peer_review_job(project_id, job)
            self._store.save_peer_review(project_id, review)
            self._store.update_peer_review_job(
                project_id,
                job.model_copy(
                    update={
                        "status": AuditJobStatus.SUCCEEDED,
                        "completed_at": _utc_now(),
                        "progress": 1.0,
                        "stage": "模拟评审已完成",
                        "error": None,
                    }
                ),
            )
        except Exception as exc:
            failed = job.model_copy(
                update={
                    "status": AuditJobStatus.FAILED,
                    "completed_at": _utc_now(),
                    "stage": f"{current_stage}失败",
                    "error": self._safe_error(exc, settings),
                }
            )
            try:
                self._store.update_peer_review_job(project_id, failed)
            except Exception:
                pass

    @staticmethod
    def _safe_error(exc: Exception, settings: Settings) -> str:
        message = str(exc).strip() or exc.__class__.__name__
        for secret in (settings.api_key, settings.api_base):
            if secret:
                message = message.replace(secret, "[已隐藏]")
        return message[:500]

    def shutdown(self, *, wait: bool = True) -> None:
        self._executor.shutdown(wait=wait, cancel_futures=not wait)
