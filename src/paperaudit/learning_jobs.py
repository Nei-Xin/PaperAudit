"""Single-process background generation for persisted learning-report jobs."""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime, timezone
from threading import Lock
from typing import Protocol

from paperaudit.config import Settings
from paperaudit.models import AuditJobStatus, LearningJob, LearningReport
from paperaudit.service import AuditService
from paperaudit.storage import ProjectStore


class LearningRunner(Protocol):
    def generate_learning_report(self, paper: object) -> LearningReport: ...


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class LearningJobManager:
    """Generate and save a learning report without touching Streamlit state."""

    def __init__(
        self,
        store: ProjectStore,
        *,
        service_factory: Callable[[Settings], LearningRunner] = AuditService,
        mark_interrupted_on_start: bool = True,
    ) -> None:
        self._store = store
        self._service_factory = service_factory
        self._executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="paperaudit-learning",
        )
        self._futures: dict[str, Future[None]] = {}
        self._lock = Lock()
        if mark_interrupted_on_start:
            self._store.mark_interrupted_learning_jobs()

    def submit(self, project_id: str, job_id: str, settings: Settings) -> None:
        job = self._store.load_learning_job(project_id, job_id)
        if job.status != AuditJobStatus.QUEUED:
            raise ValueError("只有等待中的讲解任务可以提交。")
        with self._lock:
            existing = self._futures.get(job_id)
            if existing is not None and not existing.done():
                raise ValueError("该论文讲解任务已经提交。")
            future = self._executor.submit(self._run_job, project_id, job_id, settings)
            self._futures[job_id] = future
        future.add_done_callback(lambda _: self._forget(job_id))

    def _forget(self, job_id: str) -> None:
        with self._lock:
            self._futures.pop(job_id, None)

    def _run_job(self, project_id: str, job_id: str, settings: Settings) -> None:
        job = self._store.load_learning_job(project_id, job_id)
        job = job.model_copy(
            update={
                "status": AuditJobStatus.RUNNING,
                "started_at": _utc_now(),
                "progress": 0.15,
                "stage": "正在生成结构化论文讲解",
                "error": None,
            }
        )
        self._store.update_learning_job(project_id, job)
        try:
            saved = self._store.load_learning_project(project_id)
            report = self._service_factory(settings).generate_learning_report(saved.paper)
            self._store.save_learning_project(
                saved.pdf_bytes,
                saved.metadata.original_filename,
                saved.paper,
                report,
                saved.codebase,
                saved.paper_history,
                saved.joint_history,
            )
            completed = job.model_copy(
                update={
                    "status": AuditJobStatus.SUCCEEDED,
                    "completed_at": _utc_now(),
                    "progress": 1.0,
                    "stage": "论文讲解已完成",
                    "error": None,
                }
            )
            self._store.update_learning_job(project_id, completed)
        except Exception as exc:
            failed = job.model_copy(
                update={
                    "status": AuditJobStatus.FAILED,
                    "completed_at": _utc_now(),
                    "stage": "论文讲解生成失败",
                    "error": self._safe_error(exc, settings),
                }
            )
            try:
                self._store.update_learning_job(project_id, failed)
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
