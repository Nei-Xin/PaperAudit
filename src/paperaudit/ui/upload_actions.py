from __future__ import annotations

from collections.abc import Callable

import streamlit as st

from paperaudit.config import Settings
from paperaudit.code_parser import CodeParseError
from paperaudit.code_service import CodeLearningService
from paperaudit.hy3_client import Hy3ConfigurationError, Hy3ResponseError
from paperaudit.models import AuditJob, PeerReviewJob
from paperaudit.pdf_parser import PDFParseError
from paperaudit.service import AuditService
from paperaudit.storage import ProjectStore, StorageError
from .upload import UploadSubmission
from .project_session import ProjectSession


def process_upload(
    submission: UploadSubmission,
    active_settings: Settings,
    project_store: ProjectStore,
    project_session: ProjectSession,
    submit_peer_review: Callable[[], PeerReviewJob],
    submit_audit: Callable[..., AuditJob],
) -> None:
    pdf_bytes = submission.pdf_bytes
    mode = submission.mode
    report_text = submission.report_text
    report_source_label = submission.report_source_label
    report_source_filename = submission.report_source_filename
    scope = submission.scope
    uploaded_codebase = submission.codebase
    status = submission.status
    progress_bar = submission.progress_bar
    assert status is not None and progress_bar is not None

    try:
        service = AuditService(active_settings)
        paper = service.parse(pdf_bytes)
        if mode == "learn":
            progress_bar.progress(0.3, text="正在调用 Hy3 生成结构化中文讲解")
            learning_report = service.generate_learning_report(paper)
            parsed_codebase = None
            code_warning = None
            if submission.code_bytes is not None:
                progress_bar.progress(0.85, text="正在建立本地代码索引")
                try:
                    parsed_codebase = uploaded_codebase or CodeLearningService(
                        active_settings
                    ).parse(submission.code_bytes, submission.code_filename)
                except (CodeParseError, ValueError) as exc:
                    code_warning = f"论文讲解已生成，但代码 ZIP 未能建立索引：{exc}"
            project_session.initialize_learning(
                paper, pdf_bytes, learning_report, parsed_codebase, code_warning,
                submission.filename,
            )
            try:
                metadata = project_store.save_learning_project(
                    pdf_bytes,
                    submission.filename,
                    paper,
                    learning_report,
                    parsed_codebase,
                )
                project_session.restore(project_store, metadata.project_id, keep_upload=True)
                st.session_state.pop("project_save_error", None)
                st.query_params["project"] = metadata.project_id
            except StorageError as exc:
                st.session_state["project_save_error"] = str(exc)
            status.update(label="论文讲解生成完成", state="complete", expanded=False)
            progress_bar.progress(1.0, text="讲解生成完成")
            st.rerun()
        elif mode == "peer_review":
            progress_bar.progress(0.3, text="正在保存论文并创建后台评审任务")
            metadata = project_store.save_paper_project(pdf_bytes, submission.filename, paper)
            project_session.restore(project_store, metadata.project_id, keep_upload=True)
            st.session_state["peer_review"] = None
            job = submit_peer_review()
            st.session_state["peer_review_job_id"] = job.job_id
            st.session_state["learning_report"] = None
            st.session_state["parsed_codebase"] = None
            st.session_state["result_mode"] = "peer_review"
            st.session_state.pop("project_save_error", None)
            st.query_params["project"] = metadata.project_id
            status.update(label="已在后台开始模拟评审", state="complete", expanded=False)
            progress_bar.progress(1.0, text="评审已提交，页面可继续使用")
            st.rerun()
        else:
            progress_bar.progress(0.25, text="正在保存论文并创建后台任务")
            metadata = project_store.save_paper_project(
                pdf_bytes,
                submission.filename,
                paper,
            )
            project_session.restore(project_store, metadata.project_id, keep_upload=True)
            job = submit_audit(
                report_text,
                "uploaded_report",
                report_source_label,
                report_source_filename,
                scope,
                mode,
            )
            st.session_state["launch_audit_job_id"] = job.job_id
            st.session_state.pop("audit_run", None)
            st.session_state.pop("active_audit_id", None)
            st.session_state.pop("audit_record_metadata", None)
            st.session_state.pop("audit_origin", None)
            st.session_state.pop("result_mode", None)
            status.update(label="已在后台开始审计", state="complete", expanded=False)
            progress_bar.progress(1.0, text="可以继续使用页面，审计不会因翻页中断")
            st.rerun()
    except (PDFParseError, Hy3ConfigurationError, Hy3ResponseError, ValueError) as exc:
        status.update(label="处理失败", state="error", expanded=True)
        st.error(f"处理错误：{exc}")
    except Exception as exc:
        status.update(label="处理失败", state="error", expanded=True)
        st.error(f"系统异常：{exc}")
