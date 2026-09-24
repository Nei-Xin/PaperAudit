"""Background workflow for persisted paper-audit jobs."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from paperaudit.config import Settings
from paperaudit.job_runner import BackgroundJobManager, JobContext
from paperaudit.models import AuditJob, AuditRun
from paperaudit.service import AuditService
from paperaudit.storage import ProjectStore


class AuditRunner(Protocol):
    def audit(self, paper: object, report_text: str, scope: object, *, mode: str,
              progress: Callable[[str, float], None] | None = None) -> AuditRun: ...


class AuditJobManager(BackgroundJobManager[AuditJob]):
    start_stage = "正在准备论文索引"
    success_stage = "审计完成"

    def __init__(self, store: ProjectStore, *,
                 service_factory: Callable[[Settings], AuditRunner] = AuditService,
                 mark_interrupted_on_start: bool = True) -> None:
        self._store = store
        super().__init__(service_factory=service_factory, thread_name_prefix="paperaudit-audit",
                         recover=store.mark_interrupted_audit_jobs if mark_interrupted_on_start else None)

    def _load_job(self, project_id: str, job_id: str) -> AuditJob:
        return self._store.load_audit_job(project_id, job_id)

    def _update_job(self, project_id: str, job: AuditJob) -> None:
        self._store.update_audit_job(project_id, job)

    def _execute(self, context: JobContext[AuditJob], settings: Settings) -> dict[str, str]:
        job = context.job
        paper = self._store.load_learning_project(job.project_id).paper
        run = self._service_factory(settings).audit(
            paper, job.report_text, job.scope, mode=job.audit_mode, progress=context.progress,
        )
        context.progress("正在保存审计结果", 0.99)
        record = self._store.save_audit_run(
            job.project_id, run, source_type=job.source_type, source_label=job.source_label,
            model=job.runtime.model, reasoning_effort=job.runtime.reasoning_effort,
            retrieval_top_k=job.runtime.retrieval_top_k, judge_batch_size=job.runtime.judge_batch_size,
        )
        return {"audit_id": record.audit_id}
