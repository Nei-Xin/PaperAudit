"""Paper-code consistency audits: submit, follow and read."""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from paperaudit.models import ConsistencyJob, ConsistencyReport
from paperaudit.storage import StorageError
from paperaudit.workflows import submit_consistency

from .audit_routes import require_project

router = APIRouter(prefix="/api")


class ConsistencyRequest(BaseModel):
    privacy_ack: bool = False
    max_checkpoints: int = Field(default=20, ge=1, le=40)


@router.post("/projects/{pid}/consistency-jobs", response_model=ConsistencyJob, status_code=202)
def create_consistency(request: Request, pid: str, body: ConsistencyRequest):
    state = request.app.state
    require_project(state.api, pid)
    if not body.privacy_ack:
        raise HTTPException(422, "请确认允许将论文与代码发送到模型服务。")
    with state.locks.hold(pid):
        try:
            return submit_consistency(state.api.store, state.consistency_manager, state.api.settings,
                                      pid, body.max_checkpoints)
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
                                      pid, previous.max_checkpoints, runtime=previous.runtime)
        except StorageError as exc:
            raise HTTPException(409, str(exc)) from exc


@router.get("/projects/{pid}/consistency-reports/{report_id}", response_model=ConsistencyReport)
def consistency_report(request: Request, pid: str, report_id: str):
    require_project(request.app.state.api, pid)
    try:
        return request.app.state.api.store.load_consistency_report(pid, report_id)
    except StorageError as exc:
        raise HTTPException(404, str(exc)) from exc
