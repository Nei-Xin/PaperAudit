"""UI-independent reading workflows shared by Streamlit and the HTTP API."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

from paperaudit.config import Settings
from paperaudit.hy3_client import Hy3ConfigurationError
from paperaudit.models import AuditRuntimeSnapshot, LearningJob, PaperAnswer
from paperaudit.pdf_parser import parse_pdf
from paperaudit.storage import ProjectStore, StorageError, make_conversation


def require_model(settings: Settings) -> None:
    if not settings.is_configured:
        raise Hy3ConfigurationError("请先配置模型 API 地址、密钥和模型名称。")


def submit_learning(store: ProjectStore, manager, settings: Settings, project_id: str) -> LearningJob:
    require_model(settings)
    job = store.create_learning_job(project_id, runtime=AuditRuntimeSnapshot(
        model=settings.model, reasoning_effort=settings.reasoning_effort,
        retrieval_top_k=settings.retrieval_top_k, judge_batch_size=settings.judge_batch_size,
    ))
    manager.submit(project_id, job.job_id, settings)
    return job


def create_project_from_upload(store: ProjectStore, manager, settings: Settings,
                               pdf_bytes: bytes, filename: str):
    """Caller holds the project lock; re-upload never replaces existing data/jobs."""
    require_model(settings)
    project_id = store.project_id(pdf_bytes)
    if any(p.project_id == project_id for p in store.list_projects()):
        saved = store.load_learning_project(project_id)
        active = next((j for j in store.list_learning_jobs(project_id)
                       if j.status in {"QUEUED", "RUNNING"}), None)
        job = active if active or saved.report else submit_learning(store, manager, settings, project_id)
        return saved.metadata, job
    paper = parse_pdf(pdf_bytes)
    metadata = store.save_paper_project(pdf_bytes, filename, paper)
    return metadata, submit_learning(store, manager, settings, metadata.project_id)


def answer_paper_question(store: ProjectStore, service, project_id: str, question: str,
                          conversation_id: str | None = None, *, new_conversation: bool = False,
                          selected_text: str | None = None,
                          selected_chunk_ids: list[str] | None = None) -> PaperAnswer:
    """Serialize with other session changes using a project lock in the caller."""
    saved = store.load_learning_project(project_id)
    records = list(saved.conversations)
    if new_conversation:
        active = make_conversation()
        records.append(active)
    else:
        active = next((c for c in records if c.conversation_id == conversation_id), None)
        if conversation_id and active is None:
            raise StorageError("所选会话不存在，请刷新后重试。")
        active = active or next(c for c in records if c.conversation_id == saved.active_conversation_id)
    answer = service.answer_question(saved.paper, question, active.paper_history,
                                     selected_text=selected_text, selected_chunk_ids=selected_chunk_ids or [])
    updated = replace(active, paper_history=[*active.paper_history, answer][-10:],
                      title=question[:36] if not active.paper_history and not active.joint_history else active.title,
                      updated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    store.save_conversations(project_id, [updated if c.conversation_id == active.conversation_id else c
                                         for c in records], updated.conversation_id)
    return answer


def submit_audit(store, manager, settings, project_id, report_text, source_type,
                 source_label, source_filename, scope, audit_mode, *, runtime=None):
    """Validate before persisting; a retry can retain its original runtime snapshot."""
    from paperaudit.service import validate_audit_report_text
    require_model(settings)
    validate_audit_report_text(report_text)
    if audit_mode not in {"audit_existing", "audit_generated"}:
        raise ValueError("审计模式无效。")
    job = store.create_audit_job(
        project_id, report_text=report_text, source_type=source_type,
        source_label=source_label, source_filename=source_filename, scope=scope,
        audit_mode=audit_mode, runtime=runtime or AuditRuntimeSnapshot(
            model=settings.model, reasoning_effort=settings.reasoning_effort,
            retrieval_top_k=settings.retrieval_top_k, judge_batch_size=settings.judge_batch_size,
            deep_audit=settings.deep_audit,
        ),
    )
    manager.submit(project_id, job.job_id, settings)
    return job
