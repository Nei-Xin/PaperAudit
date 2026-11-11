"""Paper-code consistency audits: submit, follow and read."""
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from paperaudit.models import ConsistencyJob, ConsistencyPlan, ConsistencyReport
from paperaudit.consistency_inputs import validate_plan_inputs
from paperaudit.storage import StorageError
from paperaudit.workflows import submit_consistency

from .audit_routes import require_project

router = APIRouter(prefix="/api")


class ConsistencyRequest(BaseModel):
    privacy_ack: bool = False
    max_checkpoints: int = Field(default=20, ge=1, le=40)
    # "plan" stops after planning so the checkpoints can be reviewed; "audit" plans and checks in one go.
    mode: Literal["plan", "audit"] = "audit"
    planning_strategy: Literal["one-shot", "agent"] = "one-shot"


class ExecuteRequest(BaseModel):
    privacy_ack: bool = False
    selected_ids: list[str] = Field(default_factory=list, max_length=40)
    extra_questions: list[str] = Field(default_factory=list, max_length=10)


@router.post("/projects/{pid}/consistency-jobs", response_model=ConsistencyJob, status_code=202)
def create_consistency(request: Request, pid: str, body: ConsistencyRequest):
    state = request.app.state
    require_project(state.api, pid)
    if not body.privacy_ack:
        raise HTTPException(422, "请确认允许将论文与代码发送到模型服务。")
    with state.locks.hold(pid):
        try:
            return submit_consistency(state.api.store, state.consistency_manager, state.api.settings,
                                      pid, body.max_checkpoints, kind=body.mode,
                                      planning_strategy=body.planning_strategy)
        except StorageError as exc:
            raise HTTPException(409, str(exc)) from exc


@router.get("/projects/{pid}/consistency-plans/{plan_id}", response_model=ConsistencyPlan)
def consistency_plan(request: Request, pid: str, plan_id: str):
    require_project(request.app.state.api, pid)
    try:
        return request.app.state.api.store.load_consistency_plan(pid, plan_id)
    except StorageError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/projects/{pid}/consistency-plans/{plan_id}/execute", response_model=ConsistencyJob, status_code=202)
def execute_plan(request: Request, pid: str, plan_id: str, body: ExecuteRequest):
    """A person approves a stored plan: check the selected checkpoints and any questions they added."""
    state = request.app.state
    require_project(state.api, pid)
    if not body.privacy_ack:
        raise HTTPException(422, "请确认允许将论文与代码发送到模型服务。")
    with state.locks.hold(pid):
        try:
            plan = state.api.store.load_consistency_plan(pid, plan_id)
            saved = state.api.store.load_learning_project(pid)
            if saved.codebase is None:
                raise StorageError("请先上传代码 ZIP。")
            try:
                validate_plan_inputs(plan, saved.paper, saved.codebase)
            except ValueError as exc:
                raise StorageError(str(exc)) from exc
            questions = [" ".join(q.split()) for q in body.extra_questions if q.strip()]
            # A lost HTTP response or double click must not pay for the same
            # approved selection again. Failed jobs use the explicit retry route.
            for previous in state.api.store.list_consistency_jobs(pid):
                if (previous.kind == "execute" and previous.plan_id == plan_id
                        and set(previous.selected_ids) == set(body.selected_ids)
                        and previous.extra_questions == questions
                        and previous.status in {"QUEUED", "RUNNING", "SUCCEEDED"}):
                    return previous
            return submit_consistency(state.api.store, state.consistency_manager, state.api.settings, pid,
                                      kind="execute", plan_id=plan_id, selected_ids=body.selected_ids,
                                      extra_questions=body.extra_questions)
        except StorageError as exc:
            raise HTTPException(409, str(exc)) from exc


@router.get("/projects/{pid}/consistency-jobs", response_model=list[ConsistencyJob])
def consistency_jobs(request: Request, pid: str):
    require_project(request.app.state.api, pid)
    return request.app.state.api.store.list_consistency_jobs(pid)


@router.post("/projects/{pid}/consistency-jobs/{job_id}/retry", response_model=ConsistencyJob, status_code=202)
def retry_consistency(request: Request, pid: str, job_id: str):
    state = request.app.state
    require_project(state.api, pid)
    with state.locks.hold(pid):
        try:
            previous = state.api.store.load_consistency_job(pid, job_id)
            if previous.status not in {"FAILED", "INTERRUPTED"}:
                raise HTTPException(409, "只有失败或中断的一致性审计可以重试。")
            return submit_consistency(state.api.store, state.consistency_manager, state.api.settings,
                                      pid, previous.max_checkpoints, runtime=previous.runtime,
                                      kind=previous.kind, plan_id=previous.plan_id,
                                      planning_strategy=previous.planning_strategy,
                                      selected_ids=previous.selected_ids, extra_questions=previous.extra_questions)
        except StorageError as exc:
            raise HTTPException(409, str(exc)) from exc


@router.get("/projects/{pid}/consistency-reports/{report_id}", response_model=ConsistencyReport)
def consistency_report(request: Request, pid: str, report_id: str):
    require_project(request.app.state.api, pid)
    try:
        return request.app.state.api.store.load_consistency_report(pid, report_id)
    except StorageError as exc:
        raise HTTPException(404, str(exc)) from exc
