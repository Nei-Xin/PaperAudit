"""Background workflow for persisted paper-code consistency audits."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from paperaudit.code_service import CodeLearningService
from paperaudit.config import Settings
from paperaudit.consistency_inputs import validate_plan_inputs
from paperaudit.job_runner import BackgroundJobManager, JobContext
from paperaudit.models import ConsistencyCategory, ConsistencyCheckpoint, ConsistencyJob, ConsistencyPlan, ConsistencyReport
from paperaudit.storage import ProjectStore, StorageError


class ConsistencyRunner(Protocol):
    def audit_consistency(self, paper: object, codebase: object, *, max_checkpoints: int,
                          progress: Callable[[str, float], None] | None = None,
                          strategy: str = "one-shot") -> ConsistencyReport: ...

    def plan_consistency(self, paper: object, codebase: object, *, max_checkpoints: int,
                         progress: Callable[[str, float], None] | None = None,
                         strategy: str = "one-shot") -> ConsistencyPlan: ...

    def check_consistency(self, paper: object, codebase: object, checkpoints: list[ConsistencyCheckpoint],
                          plan: ConsistencyPlan, *,
                          progress: Callable[[str, float], None] | None = None) -> ConsistencyReport: ...


class ConsistencyJobManager(BackgroundJobManager[ConsistencyJob]):
    start_stage = "正在准备论文与代码索引"
    success_stage = "已完成"

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
        service = self._service_factory(settings)
        if job.kind == "plan":
            # Stop here: the stored plan waits for a person to choose what gets checked.
            plan = service.plan_consistency(saved.paper, saved.codebase, max_checkpoints=job.max_checkpoints,
                                            progress=context.progress, strategy=job.planning_strategy)
            if not plan.checkpoints:
                raise StorageError("没有从论文中找到可以通过阅读代码核对的要点。")
            return {"plan_id": self._store.save_consistency_plan(job.project_id, plan).plan_id}
        map_options = ({"repo_map": self._store.load_repo_map(job.project_id),
                        "on_repo_map": lambda memory: self._store.save_repo_map(job.project_id, memory)}
                       if settings.repo_map else {})
        if job.kind == "execute":
            plan = self._store.load_consistency_plan(job.project_id, job.plan_id or "")
            validate_plan_inputs(plan, saved.paper, saved.codebase)
            chosen = [c for c in plan.checkpoints if c.checkpoint_id in set(job.selected_ids)]
            chosen += [ConsistencyCheckpoint(checkpoint_id=f"U{n:02d}", topic=question[:40],
                                             category=ConsistencyCategory.OTHER, question=question, source="user")
                       for n, question in enumerate(job.extra_questions, 1)]
            report = service.check_consistency(saved.paper, saved.codebase, chosen, plan, progress=context.progress, **map_options)
        else:
            report = service.audit_consistency(
                saved.paper, saved.codebase, max_checkpoints=job.max_checkpoints, progress=context.progress,
                strategy=job.planning_strategy, **map_options,
            )
        if not report.items:
            raise StorageError("没有找到可核对的要点，请重试规划或补充自定义问题。")
        context.progress("正在保存一致性审计结果", 0.99)
        return {"report_id": self._store.save_consistency_report(job.project_id, report).report_id}
