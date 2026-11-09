"""Audit submissions, input previews and explicit retries."""
from typing import Annotated, Literal
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel

from paperaudit.models import AuditJob, ClaimCategory
from paperaudit.report_input import parse_report_file
from paperaudit.reporting import render_learning_markdown
from paperaudit.service import validate_audit_report_text
from paperaudit.workflows import submit_audit

router = APIRouter(prefix="/api")
DEFAULT_SCOPE = [category for category in ClaimCategory if category != ClaimCategory.OTHER]
MAX_REPORT_BYTES = 100 * 1024 * 1024


class ReportPreview(BaseModel):
    character_count: int
    page_count: int | None
    kind: str
    warnings: list[str]


def report_input(text: str | None, upload: UploadFile | None):
    if (text is not None) == (upload is not None):
        raise HTTPException(422, "请提供文本或报告文件其中一种。")
    filename = None
    parsed = None
    if upload is not None:
        filename = (upload.filename or "").replace("\\", "/").split("/")[-1]
        data = upload.file.read(MAX_REPORT_BYTES + 1)
        if len(data) > MAX_REPORT_BYTES:
            raise HTTPException(413, "报告文件不能超过 100MB。")
        try:
            parsed = parse_report_file(data, filename)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        text = parsed.text
    try:
        validate_audit_report_text(text or "")
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return (text or "").strip(), filename, parsed


def require_project(api, pid):
    if not any(p.project_id == pid for p in api.store.list_projects()):
        raise HTTPException(404)


@router.post("/report-files/parse", response_model=ReportPreview)
def preview(report_file: Annotated[UploadFile, File()]):
    text, _, parsed = report_input(None, report_file)
    return ReportPreview(character_count=len(text), page_count=parsed.page_count,
                         kind=parsed.kind, warnings=list(parsed.warnings))


@router.post("/projects/{pid}/audit-jobs", response_model=AuditJob, status_code=202)
def create_audit(request: Request, pid: str,
                 source: Annotated[Literal["report", "lecture"], Form()] = "report",
                 report_text: Annotated[str | None, Form()] = None,
                 report_file: Annotated[UploadFile | None, File()] = None,
                 scope: Annotated[list[ClaimCategory] | None, Form()] = None,
                 audit_mode: Annotated[Literal["audit_existing", "audit_generated"], Form()] = "audit_existing",
                 privacy_ack: Annotated[bool, Form()] = False):
    state = request.app.state
    api = state.api
    require_project(api, pid)
    if not privacy_ack:
        raise HTTPException(422, "请确认允许将论文与报告发送到模型服务。")
    with state.locks.hold(pid):
        if source == "lecture":
            if report_text is not None or report_file is not None:
                raise HTTPException(422, "审计当前讲解时不能同时提交报告。")
            report = api.lecture(pid)
            if report is None:
                raise HTTPException(409, "当前项目还没有讲解。")
            text, filename = render_learning_markdown(report), None
            source_type, label, audit_mode = "generated_learning_report", "当前论文讲解", "audit_generated"
        else:
            if audit_mode != "audit_existing":
                raise HTTPException(422, "上传报告须使用报告审计模式。")
            text, filename, _ = report_input(report_text, report_file)
            source_type, label = "uploaded_report", filename or "粘贴报告"
        return submit_audit(api.store, state.audit_manager, api.settings, pid, text,
                            source_type, label, filename,
                            DEFAULT_SCOPE if scope is None else scope, audit_mode)


@router.post("/projects/{pid}/audit-jobs/{job_id}/retry", response_model=AuditJob, status_code=202)
def retry_audit(request: Request, pid: str, job_id: str):
    state = request.app.state
    api = state.api
    require_project(api, pid)
    with state.locks.hold(pid):
        previous = api.store.load_audit_job(pid, job_id)
        if previous.status not in {"FAILED", "INTERRUPTED"}:
            raise HTTPException(409, "只有失败或中断的审计可以重试。")
        if any(j.report_hash == previous.report_hash and j.job_id != previous.job_id and j.created_at >= previous.created_at
               and j.status in {"QUEUED", "RUNNING", "SUCCEEDED"}
               for j in api.store.list_audit_jobs(pid)):
            raise HTTPException(409, "该报告已有更新的任务，请查看最新记录。")
        return submit_audit(api.store, state.audit_manager, api.settings, pid,
                            previous.report_text, previous.source_type, previous.source_label,
                            previous.source_filename, previous.scope, previous.audit_mode,
                            runtime=previous.runtime)
