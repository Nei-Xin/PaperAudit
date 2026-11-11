"""Background workflow for persisted paper-code consistency audits."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from paperaudit.code_service import CodeLearningService
from paperaudit.config import Settings
from paperaudit.job_runner import BackgroundJobManager, JobContext
from paperaudit.models import ConsistencyJob, ConsistencyReport
from paperaudit.storage import ProjectStore, StorageError


class ConsistencyRunner(Protocol):
    def audit_consistency(self, paper: object, codebase: object, *, max_checkpoints: int,
                          progress: Callable[[str, float], None] | None = None) -> ConsistencyReport: ...


class ConsistencyJobManager(BackgroundJobManager[ConsistencyJob]):
    start_stage = "正在准备论文与代码索引"
    success_stage = "一致性审计完成"

    def __init__(self, store: ProjectStore, *,
                 service_factory: Callable[[Settings], ConsistencyRunner] = CodeLearningService,
                 mark_interrupted_on_start: bool = True) -> None:
        self._store = store
        super().__init__(service_factory=service_factory, thread_name_prefix="paperaudit-consistency-job",
                         recover=store.mark_interrupted_consistency_jobs if mark_interrupted_on_start else None)

    def _load_job(self, project_id: str, job_id: str) -> ConsistencyJob:
        return self._store.load_consistency_job(project_id, job_id)

    def _update_job(self, project_id: str, job: ConsistencyJob) -> None:
        self._store.update_consistency_job(project_id, job)

    def _execute(self, context: JobContext[ConsistencyJob], settings: Settings) -> dict[str, str]:
        job = context.job
        saved = self._store.load_learning_project(job.project_id)
        if saved.codebase is None:
            raise StorageError("项目中的代码已被移除，无法执行一致性审计。")
        report = self._service_factory(settings).audit_consistency(
            saved.paper, saved.codebase, max_checkpoints=job.max_checkpoints, progress=context.progress,
        )
        context.progress("正在保存一致性审计结果", 0.99)
        return {"report_id": self._store.save_consistency_report(job.project_id, report).report_id}
