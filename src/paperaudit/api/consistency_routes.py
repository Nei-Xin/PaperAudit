"""Paper-code consistency audits: submit, follow and read."""
import asyncio
import json
from time import monotonic
from typing import Literal

from fastapi import APIRouter, HTTPException, Request, Query
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool

from paperaudit.consistency_events import read_events
from pydantic import BaseModel, Field

from paperaudit.models import ConsistencyEvent, ConsistencyJob, ConsistencyPlan, ConsistencyReport
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


class EventStreamResponse(StreamingResponse):
    media_type = "text/event-stream"


@router.get("/projects/{pid}/consistency-jobs/{job_id}/events",
            response_class=EventStreamResponse,
            responses={200: {"model": ConsistencyEvent,
                             "description": "SSE: audit data is a ConsistencyEvent; end carries persisted job status.",
                             "content": {"text/event-stream": {"schema": {"type": "object"}}}}})
async def consistency_events(request: Request, pid: str, job_id: str, after: int = Query(default=0, ge=0, le=9_999_999_999)):
    """Replay durable records, then tail. Last-Event-ID takes precedence on reconnect."""
    store = request.app.state.api.store
    require_project(request.app.state.api, pid)
    try:
        path = await run_in_threadpool(store.consistency_event_path, pid, job_id)
    except StorageError as exc:
        raise HTTPException(404, str(exc)) from exc
    header = request.headers.get("last-event-id")
    if header is not None:
        if not header.isascii() or not header.isdigit() or len(header) > 10:
            raise HTTPException(422, "事件编号无效。")
        after = int(header)
    try:
        # Validate the cursor before sending headers; never silently skip future events.
        last, offset = 0, 0
        while True:
            batch, offset = await run_in_threadpool(read_events, path, offset)
            for event in batch:
                if event.event_id != last + 1 or event.job_id != job_id:
                    raise ValueError("Invalid event sequence")
                last = event.event_id
            if len(batch) < 128:
                break
        if after > last:
            raise HTTPException(409, "事件编号超出当前日志，请从头重新读取。")
    except (ValueError, OSError):
        raise HTTPException(409, "事件日志无法读取，任务状态和最终报告仍可查询。")
    return StreamingResponse(event_stream(request, store, pid, job_id, path, after),
                             media_type="text/event-stream",
                             headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})


async def event_stream(request, store, pid, job_id, path, after, *, poll_seconds=0.5, heartbeat_seconds=15):
    offset = 0
    seen = 0
    heartbeat = monotonic()
    yield "retry: 1500\n\n"
    while not await request.is_disconnected():
        try:
            # Terminal status is published after the final persisted event. Read status
            # first, then drain: a concurrent completion cannot race past the last batch.
            job = await run_in_threadpool(store.load_consistency_job, pid, job_id)
            batch, offset = await run_in_threadpool(read_events, path, offset)
            for event in batch:
                if event.job_id != job_id or event.event_id != seen + 1:
                    raise ValueError("Invalid event identity or sequence")
                seen = event.event_id
                if event.event_id > after:
                    yield f"id: {event.event_id}\nevent: audit\ndata: {event.model_dump_json()}\n\n"
                    after = event.event_id
            if len(batch) == 128:
                continue
            if job.status not in {"QUEUED", "RUNNING"}:
                yield 'event: end\ndata: ' + json.dumps({"status": job.status.value,
                    "plan_id": job.plan_id, "report_id": job.report_id}, ensure_ascii=False) + '\n\n'
                return
        except (StorageError, ValueError, OSError):
            yield 'event: stream_error\ndata: {"message":"事件日志暂不可读，请查看任务状态。"}\n\n'
            return
        if monotonic() - heartbeat >= heartbeat_seconds:
            yield ': keep-alive\n\n'
            heartbeat = monotonic()
        await asyncio.sleep(poll_seconds)
