"""Single-process background execution for persisted paper-audit jobs."""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime, timezone
from threading import Lock
from typing import Protocol

from paperaudit.config import Settings
from paperaudit.models import AuditJob, AuditJobStatus, AuditRun
from paperaudit.service import AuditService
from paperaudit.storage import ProjectStore


class AuditRunner(Protocol):
    def audit(
        self,
        paper: object,
        report_text: str,
        scope: object,
        *,
        mode: str,
        progress: Callable[[str, float], None] | None = None,
    ) -> AuditRun: ...


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class AuditJobManager:
    """Run persisted audit jobs without touching Streamlit state or UI APIs."""

    def __init__(
        self,
        store: ProjectStore,
        *,
        service_factory: Callable[[Settings], AuditRunner] = AuditService,
        mark_interrupted_on_start: bool = True,
    ) -> None:
        self._store = store
        self._service_factory = service_factory
        self._executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="paperaudit-audit",
        )
        self._futures: dict[str, Future[None]] = {}
        self._lock = Lock()
        if mark_interrupted_on_start:
            self._store.mark_interrupted_audit_jobs()

    def submit(self, project_id: str, job_id: str, settings: Settings) -> None:
        """Queue one already-persisted job and return immediately."""

        job = self._store.load_audit_job(project_id, job_id)
        if job.status != AuditJobStatus.QUEUED:
            raise ValueError("只有等待中的审计任务可以提交。")
        with self._lock:
            existing = self._futures.get(job_id)
            if existing is not None and not existing.done():
                raise ValueError("该审计任务已经提交。")
            try:
                future = self._executor.submit(
                    self._run_job,
                    project_id,
                    job_id,
                    settings,
                )
            except Exception as exc:
                failed = job.model_copy(
                    update={
                        "status": AuditJobStatus.FAILED,
                        "completed_at": _utc_now(),
                        "stage": "任务提交失败",
                        "error": self._safe_error(exc, settings),
                    }
                )
                self._store.update_audit_job(project_id, failed)
                raise
            self._futures[job_id] = future
        future.add_done_callback(lambda _: self._forget(job_id))

    def _forget(self, job_id: str) -> None:
        with self._lock:
            self._futures.pop(job_id, None)

    def _run_job(self, project_id: str, job_id: str, settings: Settings) -> None:
        job = self._store.load_audit_job(project_id, job_id)
        job = job.model_copy(
            update={
                "status": AuditJobStatus.RUNNING,
                "started_at": _utc_now(),
                "progress": max(job.progress, 0.01),
                "stage": "正在准备论文索引",
                "error": None,
            }
        )
        self._store.update_audit_job(project_id, job)
        last_progress = job.progress
        last_stage = job.stage

        def update_progress(message: str, value: float) -> None:
            nonlocal job, last_progress, last_stage
            progress_value = min(max(float(value), 0.0), 0.99)
            stage = message.strip() or last_stage
            if stage == last_stage and progress_value - last_progress < 0.02:
                return
            job = job.model_copy(
                update={
                    "progress": max(last_progress, progress_value),
                    "stage": stage,
                }
            )
            self._store.update_audit_job(project_id, job)
            last_progress = job.progress
            last_stage = stage

        try:
            paper = self._store.load_learning_project(project_id).paper
            runner = self._service_factory(settings)
            run = runner.audit(
                paper,
                job.report_text,
                job.scope,
                mode=job.audit_mode,
                progress=update_progress,
            )
            record = self._store.save_audit_run(
                project_id,
                run,
                source_type=job.source_type,
                source_label=job.source_label,
                model=job.runtime.model,
                reasoning_effort=job.runtime.reasoning_effort,
                retrieval_top_k=job.runtime.retrieval_top_k,
                judge_batch_size=job.runtime.judge_batch_size,
            )
            completed = job.model_copy(
                update={
                    "status": AuditJobStatus.SUCCEEDED,
                    "completed_at": _utc_now(),
                    "progress": 1.0,
                    "stage": "审计完成",
                    "audit_id": record.audit_id,
                    "error": None,
                }
            )
            self._store.update_audit_job(project_id, completed)
        except Exception as exc:
            failed = job.model_copy(
                update={
                    "status": AuditJobStatus.FAILED,
                    "completed_at": _utc_now(),
                    "stage": "审计失败",
                    "error": self._safe_error(exc, settings),
                }
            )
            try:
                self._store.update_audit_job(project_id, failed)
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
        """Release the worker in tests or explicit application teardown."""

        self._executor.shutdown(wait=wait, cancel_futures=not wait)
