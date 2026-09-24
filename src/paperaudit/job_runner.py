"""Single-process lifecycle for all persisted background jobs."""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timezone
import logging
from threading import Lock
from typing import Any, Generic, TypeVar

from paperaudit.config import Settings
from paperaudit.models import (
    AuditJob, AuditJobStatus, LearningJob, PeerReviewJob, PeerReviewRevisionJob,
)

JobT = TypeVar("JobT", AuditJob, LearningJob, PeerReviewJob, PeerReviewRevisionJob)
logger = logging.getLogger(__name__)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class JobContext(Generic[JobT]):
    """Track monotonic progress and the latest stage for failure reporting."""

    def __init__(self, job: JobT, save: Callable[[str, JobT], None]):
        self.job = job
        self._save = save

    def progress(self, stage: str, value: float) -> None:
        value = max(self.job.progress, min(max(float(value), 0.0), 0.99))
        stage = stage.strip() or self.job.stage
        if stage == self.job.stage and value - self.job.progress < 0.02:
            return
        self.job = self.job.model_copy(update={"stage": stage, "progress": value})
        self._save(self.job.project_id, self.job)


class BackgroundJobManager(Generic[JobT]):
    """One worker per domain; storage remains the source of truth for status.

    API retries/timeouts belong to the model client. Entire jobs are never
    automatically replayed after failure, avoiding duplicate paid requests.
    """

    start_stage = "正在准备任务"
    success_stage = "任务已完成"

    def __init__(self, *, service_factory: Callable[[Settings], Any],
                 thread_name_prefix: str,
                 recover: Callable[[], int] | None = None) -> None:
        self._service_factory = service_factory
        if recover is not None:
            recover()
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix=thread_name_prefix)
        self._futures: dict[str, Future[None]] = {}
        self._lock = Lock()

    def submit(self, project_id: str, job_id: str, settings: Settings) -> None:
        # Load inside the guard as well: a second caller must not resubmit a job
        # that completed while it was waiting for this lock.
        with self._lock:
            existing = self._futures.get(job_id)
            if existing is not None:
                raise ValueError("该任务已经提交。")
            job = self._load_job(project_id, job_id)
            if job.status != AuditJobStatus.QUEUED:
                raise ValueError("只有等待中的任务可以提交。")
            try:
                future = self._executor.submit(self._run_job, job, settings)
            except Exception as exc:
                self._fail(job, exc, settings, "任务提交失败")
                raise
            self._futures[job_id] = future
        # Completed futures invoke callbacks immediately; do not hold _lock.
        future.add_done_callback(lambda done: self._finished(job, done))

    def _finished(self, job: JobT, future: Future[None]) -> None:
        if future.cancelled():
            try:
                self._update_job(job.project_id, job.model_copy(update={
                    "status": AuditJobStatus.INTERRUPTED, "completed_at": utc_now(),
                    "stage": "任务已中断", "error": "应用关闭，等待中的任务未执行。",
                }))
            except Exception:
                logger.error("Could not persist cancelled job %s", job.job_id)
        with self._lock:
            self._futures.pop(job.job_id, None)

    def _run_job(self, job: JobT, settings: Settings) -> None:
        # Non-secret controls come from the immutable submission snapshot.
        settings = replace(settings, model=job.runtime.model,
                           reasoning_effort=job.runtime.reasoning_effort,
                           retrieval_top_k=job.runtime.retrieval_top_k,
                           judge_batch_size=job.runtime.judge_batch_size)
        context = JobContext(job.model_copy(update={
            "status": AuditJobStatus.RUNNING, "started_at": utc_now(),
            "progress": 0.01, "stage": self.start_stage, "error": None,
        }), self._update_job)
        try:
            self._update_job(job.project_id, context.job)
            result = self._execute(context, settings)
            self._update_job(job.project_id, context.job.model_copy(update={
                **result, "status": AuditJobStatus.SUCCEEDED, "completed_at": utc_now(),
                "progress": 1.0, "stage": self.success_stage, "error": None,
            }))
        except Exception as exc:
            self._fail(context.job, exc, settings, f"{context.job.stage}失败")

    def _fail(self, job: JobT, exc: Exception, settings: Settings, stage: str) -> None:
        try:
            self._update_job(job.project_id, job.model_copy(update={
                "status": AuditJobStatus.FAILED, "completed_at": utc_now(),
                "stage": stage, "error": self._safe_error(exc, settings),
            }))
        except Exception:
            # Storage may itself be unavailable. Keep logs free of credentials;
            # the next startup recovery marks the unfinished job interrupted.
            logger.error("Could not persist failed job %s", job.job_id)

    def _load_job(self, project_id: str, job_id: str) -> JobT:
        raise NotImplementedError

    def _update_job(self, project_id: str, job: JobT) -> None:
        raise NotImplementedError

    def _execute(self, context: JobContext[JobT], settings: Settings) -> dict[str, Any]:
        raise NotImplementedError

    @staticmethod
    def _safe_error(exc: Exception, settings: Settings) -> str:
        message = str(exc).strip() or exc.__class__.__name__
        for secret in (settings.api_key, settings.api_base):
            if secret:
                message = message.replace(secret, "[已隐藏]")
        return message[:500]

    def shutdown(self, *, wait: bool = True) -> None:
        self._executor.shutdown(wait=wait, cancel_futures=not wait)
