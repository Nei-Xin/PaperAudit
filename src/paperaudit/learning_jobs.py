"""Background workflow for persisted learning-report jobs."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from paperaudit.config import Settings
from paperaudit.job_runner import BackgroundJobManager, JobContext
from paperaudit.models import LearningJob, LearningReport
from paperaudit.service import AuditService
from paperaudit.storage import ProjectStore


class LearningRunner(Protocol):
    def generate_learning_report(self, paper: object) -> LearningReport: ...


class LearningJobManager(BackgroundJobManager[LearningJob]):
    start_stage = "正在生成结构化论文讲解"
    success_stage = "论文讲解已完成"

    def __init__(self, store: ProjectStore, *,
                 service_factory: Callable[[Settings], LearningRunner] = AuditService,
                 mark_interrupted_on_start: bool = True) -> None:
        self._store = store
        super().__init__(service_factory=service_factory, thread_name_prefix="paperaudit-learning",
                         recover=store.mark_interrupted_learning_jobs if mark_interrupted_on_start else None)

    def _load_job(self, project_id: str, job_id: str) -> LearningJob:
        return self._store.load_learning_job(project_id, job_id)

    def _update_job(self, project_id: str, job: LearningJob) -> None:
        self._store.update_learning_job(project_id, job)

    def _execute(self, context: JobContext[LearningJob], settings: Settings) -> dict[str, str]:
        saved = self._store.load_learning_project(context.job.project_id)
        report = self._service_factory(settings).generate_learning_report(saved.paper)
        context.progress("正在保存论文讲解", 0.9)
        self._store.save_learning_report(context.job.project_id, report)
        return {}
