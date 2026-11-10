from __future__ import annotations

from contextlib import asynccontextmanager, contextmanager
from dataclasses import replace
import json
from pathlib import Path
from threading import Lock
from typing import Annotated, Literal
from urllib.parse import urlsplit

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response
from starlette.exceptions import HTTPException

from paperaudit.config import Settings
from paperaudit.hy3_client import Hy3ConfigurationError, Hy3ResponseError
from paperaudit.learning_jobs import LearningJobManager
from paperaudit.audit_jobs import AuditJobManager, default_audit_service
from .audit_routes import router as audit_router, report_input, DEFAULT_SCOPE
from paperaudit.models import LearningReport, LearningJob, PaperAnswer, PeerReviewVenue, ClaimCategory
from paperaudit.code_service import CodeLearningService
from paperaudit.peer_review_jobs import PeerReviewJobManager, PeerReviewRevisionJobManager
from paperaudit.peer_review_rules import normalize_peer_review_weights
from .project_routes import router as project_router, read_code_upload, selected_paper
from .review_routes import router as review_router
from paperaudit.service import AuditService
from paperaudit.storage import AuditRecordMetadata, StorageError, load_storage_settings, default_settings_dir, _atomic_write_json
from paperaudit.workflows import require_model, submit_learning, retry_learning, create_project_from_upload, answer_paper_question
from .schemas import (
    SettingsView, SettingsUpdate, ProjectSummary, ProjectDetail, ProjectCreated,
    Conversations, Question, ProjectJobs, AuditDetail, ReviewPayload, LearningRequest,
)
from .views import ReadOnlyApi, NotFound

MAX_PDF_BYTES = 200 * 1024 * 1024


class ApiProblem(Exception):
    def __init__(self, status: int, code: str, message: str):
        self.status, self.code, self.message = status, code, message


def error(status: int, code: str, message: str):
    return JSONResponse({"error": {"code": code, "message": message}}, status_code=status)


class ProjectLocks:
    """Bounded lock table: reject concurrent changes instead of queuing model calls."""
    def __init__(self):
        self.guard = Lock()
        self.active: set[str] = set()

    @contextmanager
    def hold(self, project_id: str):
        with self.guard:
            if project_id in self.active:
                raise ApiProblem(409, "project_busy", "该项目正在处理请求，请完成后再试。")
            self.active.add(project_id)
        try:
            yield
        finally:
            with self.guard:
                self.active.remove(project_id)


def create_app(*, storage_root: Path | None = None, settings: Settings | None = None,
               settings_dir: Path | None = None, service_factory=AuditService,
               dist: Path | None = None, audit_service_factory=None, code_service_factory=CodeLearningService) -> FastAPI:
    """Startup (not import) loads data. Tests inject an isolated store and fake model."""
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        directory = settings_dir or default_settings_dir()
        root = storage_root
        if root is None:
            configured = load_storage_settings(directory)
            if configured is None:
                raise RuntimeError("未找到存储设置，请先配置 PAPERAUDIT_SETTINGS_DIR。")
            root = configured.storage_root
        active_settings = settings or Settings.from_env()
        model_file = directory / "model.json"
        if model_file.exists():
            update = SettingsUpdate.model_validate_json(model_file.read_text()).model_dump(exclude_none=True)
            active_settings = replace(active_settings, **update)
        api = ReadOnlyApi(root, active_settings)
        manager = LearningJobManager(api.store, service_factory=service_factory)
        app.state.api, app.state.manager = api, manager
        app.state.audit_manager = AuditJobManager(api.store, service_factory=audit_service_factory or (default_audit_service if service_factory is AuditService else service_factory))
        app.state.review_manager = PeerReviewJobManager(api.store, service_factory=service_factory)
        app.state.revision_manager = PeerReviewRevisionJobManager(api.store, service_factory=service_factory)
        app.state.service_factory = service_factory
        app.state.code_service_factory = code_service_factory
        app.state.model_file = model_file
        app.state.locks = ProjectLocks()
        app.state.settings_lock = Lock()
        try:
            yield
        finally:
            manager.shutdown(wait=True)
            app.state.audit_manager.shutdown(wait=True)
            app.state.review_manager.shutdown(wait=True)
            app.state.revision_manager.shutdown(wait=True)

    app = FastAPI(title="PaperAudit API", version="0.4.0", lifespan=lifespan)
    app.include_router(audit_router)
    app.include_router(project_router)
    app.include_router(review_router)

    @app.middleware("http")
    async def same_origin(request: Request, call_next):
        # A loopback service has no login. Reject cross-site writes (including multipart forms).
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            origin = request.headers.get("origin")
            if request.headers.get("sec-fetch-site") == "cross-site" or (
                origin and urlsplit(origin).netloc != request.headers.get("host")
            ):
                return error(403, "origin_rejected", "不允许跨站提交请求。")
        try:
            response = await call_next(request)
        except Exception:
            # Do not let model/client exceptions expose credentials in HTTP bodies or ASGI tracebacks.
            return error(500, "server_error", "请求处理失败，请稍后重试。")
        response.headers["X-Content-Type-Options"] = "nosniff"
        if request.url.path.startswith("/api/"):
            # The project id is a hash of the PDF bytes, so a project's PDF never changes.
            immutable = request.url.path.endswith("/pdf") and response.status_code == 200
            response.headers["Cache-Control"] = "private, max-age=31536000, immutable" if immutable else "no-store"
        return response

    @app.exception_handler(ApiProblem)
    async def api_problem(request, exc):
        return error(exc.status, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request, exc):
        # Never serialize validation input: it can contain api_key.
        return error(422, "invalid_request", "请求参数不正确，请检查输入内容。")

    @app.exception_handler(HTTPException)
    async def http_error(request, exc):
        return error(exc.status_code, "http_error", "未找到请求的资源。" if exc.status_code == 404 else str(exc.detail))

    @app.exception_handler(StorageError)
    async def storage_error(request, exc):
        return error(400, "storage_error", str(exc))

    @app.exception_handler(NotFound)
    async def not_found(request, exc):
        return error(404, "not_found", "未找到请求的项目或记录。")

    @app.exception_handler(Hy3ConfigurationError)
    async def missing_model(request, exc):
        return error(409, "model_not_configured", "请先配置模型 API 地址、密钥和模型名称。")

    @app.exception_handler(Hy3ResponseError)
    async def model_error(request, exc):
        return error(502, "model_error", "模型服务未能完成请求，请稍后重试。")

    @app.exception_handler(ValueError)
    async def value_error(request, exc):
        return error(422, "invalid_value", "输入内容无法处理，请检查文件和参数。")

    @app.exception_handler(Exception)
    async def unexpected(request, exc):
        return error(500, "server_error", "请求处理失败，请稍后重试。")

    def api():
        return app.state.api

    def require_project(pid):
        if not any(p.project_id == pid for p in api().store.list_projects()):
            raise NotFound(pid)

    @app.get("/api/settings", response_model=SettingsView)
    def get_settings():
        return api().settings_payload()

    @app.put("/api/settings", response_model=SettingsView)
    def put_settings(body: SettingsUpdate):
        if urlsplit(body.api_base).scheme not in {"http", "https"} or not urlsplit(body.api_base).netloc:
            raise ApiProblem(422, "invalid_api_base", "请输入完整的 http 或 https API 地址。")
        with app.state.settings_lock:
            values = body.model_dump(exclude_none=True)
            if not values.get("api_key"):
                values.pop("api_key", None)  # blank means keep the current key
            candidate = replace(api().settings, **values)
            persisted = {key: getattr(candidate, key) for key in SettingsUpdate.model_fields}
            path = app.state.model_file
            path.parent.mkdir(parents=True, exist_ok=True)
            _atomic_write_json(path, persisted)
            path.chmod(0o600)
            api().settings = candidate
        return api().settings_payload()

    @app.get("/api/storage")
    def storage():
        return {"name": api().storage_root.name, "path": str(api().storage_root)}

    @app.get("/api/projects", response_model=list[ProjectSummary])
    def projects(q: str = ""):
        return [p for p in api().projects() if q.casefold() in (p["title"] + p["original_filename"]).casefold()]

    @app.post("/api/projects", response_model=ProjectCreated, status_code=201)
    def upload(pdf: Annotated[UploadFile, File()], mode: Annotated[str, Form()] = "learn",
               privacy_ack: Annotated[bool, Form()] = False,
               code_zip: Annotated[UploadFile | None, File()] = None,
               report_text: Annotated[str | None, Form()] = None,
               report_file: Annotated[UploadFile | None, File()] = None,
               scope: Annotated[list[ClaimCategory] | None, Form()] = None,
               venue: Annotated[PeerReviewVenue, Form()] = PeerReviewVenue.GENERAL,
               rubric_weights: Annotated[str, Form()] = "{}"):
        if mode not in {"learn", "audit_existing", "peer_review"}:
            raise ApiProblem(409, "not_available", "不支持的项目创建模式。")
        if not privacy_ack:
            raise ApiProblem(422, "privacy_required", "请确认允许将论文文本发送到配置的模型服务。")
        require_model(api().settings)
        if code_zip is not None and mode != "learn":
            raise ApiProblem(422, "invalid_code_mode", "代码 ZIP 仅支持讲解模式。")
        if mode != "audit_existing" and (report_text is not None or report_file is not None):
            raise ApiProblem(422, "invalid_report_mode", "报告输入仅支持报告审计模式。")
        try:
            raw_weights = json.loads(rubric_weights)
            if not isinstance(raw_weights, dict):
                raise ValueError("Invalid weights")
            normalize_peer_review_weights(raw_weights)  # Validate before creating the project.
        except (ValueError, TypeError):
            raise ApiProblem(422, "invalid_weights", "评审权重格式无效。")
        codebase = read_code_upload(code_zip) if code_zip is not None else None
        prepared = report_input(report_text, report_file) if mode == "audit_existing" else None
        data = pdf.file.read(MAX_PDF_BYTES + 1)
        if len(data) > MAX_PDF_BYTES:
            raise ApiProblem(413, "file_too_large", "PDF 文件不能超过 200MB。")
        if not data.startswith(b"%PDF-"):
            raise ApiProblem(422, "invalid_pdf", "请选择有效的 PDF 文件。")
        filename = (pdf.filename or "paper.pdf").replace("\\", "/").split("/")[-1]
        pid = api().store.project_id(data)
        with app.state.locks.hold(pid):
            if mode == "peer_review":
                from paperaudit.pdf_parser import parse_pdf
                from paperaudit.workflows import submit_peer_review
                if not any(p.project_id == pid for p in api().store.list_projects()):
                    api().store.save_paper_project(data, filename, parse_pdf(data))
                job = submit_peer_review(api().store, app.state.review_manager, api().settings, pid, venue, raw_weights)
                metadata = api().store.load_learning_project(pid).metadata
            elif prepared is None:
                metadata, job = create_project_from_upload(api().store, app.state.manager, api().settings, data, filename)
            else:
                from paperaudit.pdf_parser import parse_pdf
                from paperaudit.workflows import submit_audit
                if not any(p.project_id == pid for p in api().store.list_projects()):
                    api().store.save_paper_project(data, filename, parse_pdf(data))
                text, report_filename, _ = prepared
                job = submit_audit(api().store, app.state.audit_manager, api().settings, pid,
                                   text, "uploaded_report", report_filename or "粘贴报告",
                                   report_filename, DEFAULT_SCOPE if scope is None else scope, "audit_existing")
                metadata = api().store.load_learning_project(pid).metadata
            if codebase is not None:
                api().store.save_codebase(pid, codebase)
        return {"project": api()._summary(metadata.project_id), "job": job}

    @app.get("/api/projects/{pid}", response_model=ProjectDetail)
    def project(pid: str):
        require_project(pid)
        return api().project(pid)

    @app.get("/api/projects/{pid}/pdf")
    def pdf(pid: str):
        require_project(pid)
        return FileResponse(api().store.projects_dir / pid / "paper.pdf", media_type="application/pdf")

    @app.get("/api/projects/{pid}/lecture", response_model=LearningReport | None)
    def lecture(pid: str):
        require_project(pid)
        return api().lecture(pid)

    @app.post("/api/projects/{pid}/lecture/jobs", response_model=LearningJob, status_code=202)
    def generate(pid: str, body: LearningRequest | None = None):
        require_project(pid)
        if body and body.regenerate and not body.privacy_ack:
            raise ApiProblem(400, "privacy_ack_required", "请确认将论文文本发送至已配置的模型服务。")
        with app.state.locks.hold(pid):
            return submit_learning(api().store, app.state.manager, api().settings, pid,
                                   regenerate=bool(body and body.regenerate))

    @app.post("/api/projects/{pid}/lecture/jobs/{job_id}/retry", response_model=LearningJob, status_code=202)
    def retry_lecture(pid: str, job_id: str):
        require_project(pid)
        with app.state.locks.hold(pid):
            return retry_learning(api().store, app.state.manager, api().settings, pid, job_id)

    @app.get("/api/projects/{pid}/conversations", response_model=Conversations)
    def conversations(pid: str):
        require_project(pid)
        return api().conversations(pid)

    @app.post("/api/projects/{pid}/qa", response_model=PaperAnswer)
    def question(pid: str, body: Question):
        require_project(pid)
        require_model(api().settings)
        with app.state.locks.hold(pid):
            saved = api().store.load_learning_project(pid)
            ids, text = selected_paper(saved, body.selection, body.page_scope,
                                       body.selected_chunk_ids, body.selected_text)
            return answer_paper_question(api().store, service_factory(api().settings), pid,
                body.question, body.conversation_id, new_conversation=body.new_conversation,
                selected_text=text, selected_chunk_ids=ids)

    @app.get("/api/projects/{pid}/jobs", response_model=ProjectJobs)
    def jobs(pid: str):
        require_project(pid)
        return api().jobs(pid)

    @app.get("/api/projects/{pid}/audits", response_model=list[AuditRecordMetadata])
    def audits(pid: str):
        require_project(pid)
        return api().audits(pid)

    @app.get("/api/projects/{pid}/audits/{audit_id}", response_model=AuditDetail)
    def audit(pid: str, audit_id: str):
        require_project(pid)
        return api().audit(pid, audit_id)

    @app.get("/api/projects/{pid}/review", response_model=ReviewPayload | None)
    def review(pid: str):
        require_project(pid)
        return api().review(pid)

    def export_response(request: Request, pid: str, format: str):
        require_project(pid)
        status, media, data = api().handle(request.url.path + "?format=" + format)
        return Response(data, status_code=status, media_type=media,
                        headers={"Content-Disposition": f'attachment; filename="report.{format}"'})

    @app.get("/api/projects/{pid}/lecture/export")
    @app.get("/api/projects/{pid}/review/export")
    def export(request: Request, pid: str, format: Literal["md", "json"] = "md"):
        return export_response(request, pid, format)

    @app.get("/api/projects/{pid}/audits/{audit_id}/export")
    def audit_export(request: Request, pid: str, audit_id: str, format: Literal["md", "json"] = "md"):
        return export_response(request, pid, format)

    @app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"], include_in_schema=False)
    def unavailable(path: str):
        raise ApiProblem(404, "not_available", "此操作尚未接入，请继续使用旧版。")

    assets = (dist or Path(__file__).resolve().parents[3] / "web" / "dist").resolve()

    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str):
        target = (assets / path).resolve()
        if assets not in target.parents or not target.is_file():
            if path.startswith("assets/"):
                raise HTTPException(404)
            target = assets / "index.html"
        if not target.is_file():
            raise HTTPException(404)
        return FileResponse(target, headers={"Cache-Control": "no-cache" if target.name == "index.html" else "public, max-age=31536000, immutable"})

    return app


app = create_app()
