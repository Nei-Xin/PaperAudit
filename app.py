from __future__ import annotations

from datetime import datetime
from html import escape
import streamlit as st
from paperaudit.audit_jobs import AuditJobManager
from paperaudit.display import LABEL_NAMES, SEVERITY_NAMES, recover_paper_title
from paperaudit.config import Settings
from paperaudit.code_service import CodeLearningService
from paperaudit.learning_jobs import LearningJobManager
from paperaudit.peer_review_jobs import PeerReviewJobManager, PeerReviewRevisionJobManager
from paperaudit.models import (
    AuditJob,
    AuditJobStatus,
    AuditRuntimeSnapshot,
    ClaimCategory,
    PeerReviewJob,
    PeerReviewVenue,
    RelatedWorkReference,
)
from paperaudit.reporting import render_markdown
from paperaudit.service import (
    AuditService,
    peer_review_rubric_metadata,
    recalculate_peer_review,
    validate_audit_report_text,
)
from paperaudit.storage import ProjectStore, StorageError, load_storage_settings
from paperaudit.ui.audit_results import render_audit_results
from paperaudit.ui.learning import render_learning_workspace, render_report_audit_dialog
from paperaudit.ui.peer_review import render_peer_review
from paperaudit.ui.styles import inject_custom_styles
from paperaudit.ui.constants import CATEGORY_LABELS, DIMENSION_NAMES
from paperaudit.ui.upload_preview import (
    render_uploaded_pdf_preview as _render_uploaded_pdf_preview,
)
from paperaudit.ui.storage_setup import render_storage_setup as _render_storage_setup
from paperaudit.ui.project_session import ProjectSession
from paperaudit.ui.sidebar import render_sidebar
from paperaudit.ui.upload import render_upload_page
from paperaudit.ui.upload_actions import process_upload


st.set_page_config(
    page_title="Hy3 论文学习助手",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_custom_styles()

@st.cache_resource(show_spinner=False)
def _get_audit_job_manager(storage_root: str) -> AuditJobManager:
    return AuditJobManager(ProjectStore(storage_root))


@st.cache_resource(show_spinner=False)
def _get_learning_job_manager(storage_root: str) -> LearningJobManager:
    return LearningJobManager(ProjectStore(storage_root))


@st.cache_resource(show_spinner=False)
def _get_peer_review_job_manager(storage_root: str) -> PeerReviewJobManager:
    return PeerReviewJobManager(ProjectStore(storage_root))


@st.cache_resource(show_spinner=False)
def _get_revision_job_manager(storage_root: str) -> PeerReviewRevisionJobManager:
    return PeerReviewRevisionJobManager(ProjectStore(storage_root))


project_session = ProjectSession(st.session_state, st.query_params)

storage_settings_error: str | None = None
try:
    storage_settings = load_storage_settings()
except StorageError as exc:
    storage_settings = None
    storage_settings_error = str(exc)

if storage_settings is None:
    _render_storage_setup(storage_settings_error)
    st.stop()

try:
    project_store = ProjectStore(storage_settings.storage_root)
    audit_job_manager = _get_audit_job_manager(str(storage_settings.storage_root))
    learning_job_manager = _get_learning_job_manager(str(storage_settings.storage_root))
    peer_review_job_manager = _get_peer_review_job_manager(str(storage_settings.storage_root))
    revision_job_manager = _get_revision_job_manager(str(storage_settings.storage_root))
except StorageError as exc:
    _render_storage_setup(str(exc))
    st.stop()


requested_project = st.query_params.get("project")
if requested_project and st.session_state.get("active_project_id") != requested_project:
    try:
        project_session.open(project_store, str(requested_project))
    except StorageError as exc:
        if current_project := st.session_state.get("active_project_id"):
            st.query_params["project"] = current_project
        else:
            st.query_params.pop("project", None)
        st.session_state["project_restore_error"] = str(exc)


env_settings = Settings.from_env()
if delete_notice := st.session_state.pop("project_delete_notice", None):
    st.toast(str(delete_notice), icon="🗑️")

active_settings = render_sidebar(project_store, project_session, storage_settings, env_settings)
api_ready = active_settings.is_configured

if st.session_state.get("project_restore_error"):
    st.warning(st.session_state.pop("project_restore_error"))

if (
    st.session_state.get("result_mode") == "learning"
    and not st.session_state.get("active_project_id")
    and st.session_state.get("learning_report") is not None
    and st.session_state.get("learning_pdf_bytes")
    and st.session_state.get("learning_paper") is not None
):
    current_upload = st.session_state.get("paper_pdf_upload")
    original_filename = (
        getattr(current_upload, "name", None)
        or st.session_state.get("project_original_filename")
        or "paper.pdf"
    )
    try:
        metadata = project_store.save_learning_project(
            st.session_state["learning_pdf_bytes"],
            str(original_filename),
            st.session_state["learning_paper"],
            st.session_state["learning_report"],
            st.session_state.get("parsed_codebase"),
            st.session_state.get("paper_qa_history", []),
            st.session_state.get("joint_qa_history", []),
        )
        st.session_state["active_project_id"] = metadata.project_id
        st.session_state["project_original_filename"] = metadata.original_filename
        project_session.save_conversations(project_store, metadata.project_id)
        st.query_params["project"] = metadata.project_id
    except StorageError as exc:
        st.session_state["project_save_error"] = str(exc)

active_project_id = st.session_state.get("active_project_id")
if active_project_id and st.session_state.get("result_mode") == "learning":
    try:
        project_session.save_conversations(project_store, str(active_project_id))
        st.session_state.pop("project_save_error", None)
    except StorageError as exc:
        st.session_state["project_save_error"] = str(exc)


def _submit_active_project_audit(
    report_text: str,
    source_type: str,
    source_label: str,
    source_filename: str | None,
    scope: list[ClaimCategory],
    audit_mode: str,
) -> AuditJob:
    project_id = st.session_state.get("active_project_id")
    if not project_id:
        raise StorageError("请先打开一个已保存的论文项目。")
    if not active_settings.is_configured:
        raise ValueError("请先配置并连接 Hy3 API。")
    validate_audit_report_text(report_text)
    runtime = AuditRuntimeSnapshot(
        model=active_settings.model,
        reasoning_effort=active_settings.reasoning_effort,
        retrieval_top_k=active_settings.retrieval_top_k,
        judge_batch_size=active_settings.judge_batch_size,
    )
    job = project_store.create_audit_job(
        str(project_id),
        report_text=report_text,
        source_type=source_type,
        source_label=source_label,
        source_filename=source_filename,
        scope=scope,
        audit_mode=audit_mode,
        runtime=runtime,
    )
    audit_job_manager.submit(str(project_id), job.job_id, active_settings)
    return job


def _submit_active_project_learning() -> None:
    project_id = st.session_state.get("active_project_id")
    if not project_id:
        raise StorageError("请先打开一个已保存的论文项目。")
    if not active_settings.is_configured:
        raise ValueError("请先配置并连接 Hy3 API。")
    runtime = AuditRuntimeSnapshot(
        model=active_settings.model,
        reasoning_effort=active_settings.reasoning_effort,
        retrieval_top_k=active_settings.retrieval_top_k,
        judge_batch_size=active_settings.judge_batch_size,
    )
    job = project_store.create_learning_job(str(project_id), runtime=runtime)
    learning_job_manager.submit(str(project_id), job.job_id, active_settings)
    st.session_state["learning_job_id"] = job.job_id


def _submit_active_project_peer_review() -> PeerReviewJob:
    project_id = st.session_state.get("active_project_id")
    if not project_id:
        raise StorageError("请先打开一个已保存的论文项目。")
    if not active_settings.is_configured:
        raise ValueError("请先配置并连接 Hy3 API。")
    runtime = AuditRuntimeSnapshot(
        model=active_settings.model,
        reasoning_effort=active_settings.reasoning_effort,
        retrieval_top_k=active_settings.retrieval_top_k,
        judge_batch_size=active_settings.judge_batch_size,
    )
    venue_value = st.session_state.get("peer_review_venue", PeerReviewVenue.GENERAL.value)
    try:
        venue = PeerReviewVenue(str(venue_value))
    except ValueError:
        venue = PeerReviewVenue.GENERAL
    rubric_weights = st.session_state.get("peer_review_rubric_weights", {})
    rubric_version, _, _ = peer_review_rubric_metadata(venue, rubric_weights)
    job = project_store.create_peer_review_job(
        str(project_id), runtime=runtime, venue=venue,
        rubric_version=rubric_version, rubric_weights=rubric_weights
    )
    peer_review_job_manager.submit(str(project_id), job.job_id, active_settings)
    st.session_state["peer_review_job_id"] = job.job_id
    return job


def _submit_active_project_revision(pdf_bytes: bytes, filename: str):
    project_id = st.session_state.get("active_project_id")
    if not project_id:
        raise StorageError("请先打开一个已保存的论文项目。")
    if not active_settings.is_configured:
        raise ValueError("请先配置并连接 Hy3 API。")
    job = project_store.create_peer_review_revision_job(
        str(project_id), pdf_bytes=pdf_bytes, original_filename=filename,
        runtime=AuditRuntimeSnapshot(
            model=active_settings.model, reasoning_effort=active_settings.reasoning_effort,
            retrieval_top_k=active_settings.retrieval_top_k,
            judge_batch_size=active_settings.judge_batch_size,
        ),
    )
    revision_job_manager.submit(str(project_id), job.job_id, active_settings)
    return job


def _load_active_revision_jobs():
    project_id = st.session_state.get("active_project_id")
    return project_store.list_peer_review_revision_jobs(str(project_id)) if project_id else []


def _load_active_project_revisions():
    project_id = st.session_state.get("active_project_id")
    return project_store.list_peer_review_revisions(str(project_id)) if project_id else []


def _save_active_peer_review(report):
    project_id = st.session_state.get("active_project_id")
    if not project_id:
        raise StorageError("请先打开一个已保存的论文项目。")
    # Human concern edits must update the system-computed score and decision.
    report = recalculate_peer_review(report)
    project_store.save_peer_review(str(project_id), report)
    st.session_state["peer_review"] = report


def _compare_active_related_work(references: list[RelatedWorkReference]):
    paper = st.session_state.get("learning_paper")
    if paper is None:
        raise StorageError("当前没有已加载的论文。")
    if not active_settings.is_configured:
        raise ValueError("请先配置并连接 Hy3 API。")
    comparison = AuditService(active_settings).compare_related_work(paper, references)
    report = project_store.load_peer_review(str(st.session_state.get("active_project_id")))
    if report is None:
        raise StorageError("当前项目没有基准评审记录。")
    updated = report.model_copy(update={"related_work_comparison": comparison})
    _save_active_peer_review(updated)
    return comparison


def _load_active_project_revision_pdf(revision_id: str) -> bytes:
    project_id = st.session_state.get("active_project_id")
    if not project_id:
        raise StorageError("请先打开一个已保存的论文项目。")
    return project_store.load_peer_review_revision_pdf(str(project_id), revision_id)


def _save_active_project_revision(revision):
    project_id = st.session_state.get("active_project_id")
    if not project_id:
        raise StorageError("当前没有已打开的论文项目。")
    project_store.update_peer_review_revision(str(project_id), revision)


def _load_active_audit_jobs() -> list[AuditJob]:
    project_id = st.session_state.get("active_project_id")
    return project_store.list_audit_jobs(str(project_id)) if project_id else []


def _load_active_audit_records():
    project_id = st.session_state.get("active_project_id")
    return project_store.list_audit_runs(str(project_id)) if project_id else []


def _open_active_audit(audit_id: str) -> None:
    project_id = st.session_state.get("active_project_id")
    if not project_id:
        raise StorageError("当前没有已打开的论文项目。")
    metadata, run = project_store.load_audit_run(str(project_id), audit_id)
    paper = st.session_state.get("learning_paper")
    if paper is not None:
        run = run.model_copy(update={"paper_title": recover_paper_title(paper)})
    st.session_state["audit_run"] = run
    st.session_state["active_audit_id"] = audit_id
    st.session_state["audit_record_metadata"] = metadata
    if st.session_state.get("learning_report") is None:
        st.session_state.pop("audit_origin", None)
        st.session_state["result_mode"] = "audit_project"
    else:
        st.session_state["audit_origin"] = "history"
        st.session_state["result_mode"] = "audit"


if st.session_state.get("result_mode") == "audit_project":
    project_id = st.session_state.get("active_project_id")
    project_title = getattr(st.session_state.get("learning_paper"), "title", "论文审计项目")
    jobs = _load_active_audit_jobs() if project_id else []
    launch_job_id = st.session_state.get("launch_audit_job_id")
    launch_job = next((job for job in jobs if job.job_id == launch_job_id), None)
    if (
        launch_job is not None
        and launch_job.status == AuditJobStatus.SUCCEEDED
        and launch_job.audit_id
        and st.session_state.get("active_audit_id") != launch_job.audit_id
    ):
        _open_active_audit(launch_job.audit_id)
        st.session_state.pop("launch_audit_job_id", None)
    elif launch_job is not None and launch_job.status in {
        AuditJobStatus.FAILED,
        AuditJobStatus.INTERRUPTED,
    }:
        st.session_state.pop("launch_audit_job_id", None)
    learning_jobs = project_store.list_learning_jobs(str(project_id)) if project_id else []
    learning_job_id = st.session_state.get("learning_job_id")
    learning_job = next(
        (job for job in learning_jobs if job.job_id == learning_job_id),
        None,
    )
    if learning_job is None and learning_jobs:
        learning_job = next(
            (
                job
                for job in learning_jobs
                if job.status in {AuditJobStatus.QUEUED, AuditJobStatus.RUNNING}
            ),
            learning_jobs[0],
        )
        st.session_state["learning_job_id"] = learning_job.job_id
    audit_header = st.container(key="audit_project_header")
    title_col, learning_col, action_col, history_col, export_col = audit_header.columns(
        [3.3, 1.15, 1.15, 1.05, 1.05], vertical_alignment="center"
    )
    with title_col:
        project_kind = (
            "论文项目"
            if learning_job is not None
            and learning_job.status == AuditJobStatus.SUCCEEDED
            else "仅审计项目"
        )
        project_filename = st.session_state.get(
            "project_original_filename", "paper.pdf"
        )
        st.markdown(
            f'<div class="pa-audit-project-heading" title="{escape(str(project_title))}">'
            f'<strong>{escape(str(project_title))}</strong>'
            f'<span>{project_kind} · {escape(str(project_filename))}</span></div>',
            unsafe_allow_html=True,
        )
    learning_active = bool(
        learning_job
        and learning_job.status in {AuditJobStatus.QUEUED, AuditJobStatus.RUNNING}
    )
    learning_succeeded = bool(
        learning_job and learning_job.status == AuditJobStatus.SUCCEEDED
    )
    if learning_succeeded:
        if learning_col.button(
            "查看讲解",
            type="secondary",
            width="stretch",
        ):
            project_session.restore(project_store, str(project_id))
            st.rerun()
    elif learning_active:
        learning_col.button("讲解生成中", disabled=True, width="stretch")
    elif learning_col.button(
        "生成讲解",
        type="secondary",
        width="stretch",
        disabled=not api_ready or not project_id,
    ):
        try:
            _submit_active_project_learning()
        except (StorageError, ValueError) as exc:
            st.error(str(exc))
        else:
            st.rerun()
    if action_col.button(
        "审计报告",
        type="primary",
        width="stretch",
        disabled=not api_ready or not project_id,
    ):
        render_report_audit_dialog(_submit_active_project_audit)
    with history_col.popover("记录", width="stretch"):
        records = _load_active_audit_records() if project_id else []
        active_jobs = [
            job
            for job in jobs
            if job.status in {AuditJobStatus.QUEUED, AuditJobStatus.RUNNING}
        ]
        if active_jobs:
            st.caption(f"进行中 · {len(active_jobs)}")
            for job in active_jobs:
                st.progress(job.progress, text=f"{job.source_label} · {job.stage}")
        if st.button("刷新状态", width="stretch", key="audit_project_refresh"):
            st.rerun()
        st.divider()
        st.caption(f"历史记录 · {len(records)}")
        if not records:
            st.caption("还没有已完成的审计记录。")
        for record in records:
            created_label = datetime.fromisoformat(record.created_at).astimezone().strftime(
                "%m-%d %H:%M"
            )
            active_marker = " · 当前" if record.audit_id == st.session_state.get("active_audit_id") else ""
            if st.button(
                f"{record.source_label} · {created_label}{active_marker}",
                width="stretch",
                key=f"open-audit-only-{record.audit_id}",
            ):
                _open_active_audit(record.audit_id)
                st.rerun()
    current_export_run = st.session_state.get("audit_run")
    export_col.download_button(
        "导出",
        render_markdown(current_export_run) if current_export_run is not None else "",
        file_name="paperaudit-report.md",
        mime="text/markdown",
        disabled=current_export_run is None,
        width="stretch",
    )

    active_jobs = [
        job
        for job in jobs
        if job.status in {AuditJobStatus.QUEUED, AuditJobStatus.RUNNING}
    ]
    if learning_active and learning_job is not None:
        with st.container(border=True):
            status_col, refresh_col = st.columns([5, 1], vertical_alignment="center")
            with status_col:
                st.markdown("**论文讲解正在后台生成**")
                st.progress(learning_job.progress, text=learning_job.stage)
                st.caption("可以继续查看当前审计结果，页面切换不会取消生成任务。")
            if refresh_col.button(
                "刷新状态", width="stretch", key="learning_job_inline_refresh"
            ):
                st.rerun()
    elif learning_job is not None and learning_job.status in {
        AuditJobStatus.FAILED,
        AuditJobStatus.INTERRUPTED,
    }:
        st.error(learning_job.error or "论文讲解任务未能完成，可以重新生成。")
    if active_jobs:
        current_job = active_jobs[0]
        with st.container(border=True):
            status_col, refresh_col = st.columns([5, 1], vertical_alignment="center")
            with status_col:
                st.markdown(f"**{escape(current_job.source_label)} 正在后台审计**")
                st.progress(current_job.progress, text=current_job.stage)
                st.caption("可以继续浏览、切换页面或稍后返回，任务不会被取消。")
            if refresh_col.button("刷新状态", width="stretch", key="audit_job_inline_refresh"):
                st.rerun()
    elif launch_job is not None and launch_job.status in {
        AuditJobStatus.FAILED,
        AuditJobStatus.INTERRUPTED,
    }:
        st.error(launch_job.error or "审计任务未能完成。")

    audit_record_metadata = st.session_state.get("audit_record_metadata")
    if audit_record_metadata is not None:
        created_label = datetime.fromisoformat(
            audit_record_metadata.created_at
        ).astimezone().strftime("%Y-%m-%d %H:%M")
        st.caption(
            f"当前审计 · {audit_record_metadata.source_label} · {created_label}"
        )
    audit_run = st.session_state.get("audit_run")
    if audit_run is None:
        if not active_jobs:
            empty_pdf = st.session_state.get("learning_pdf_bytes")
            empty_paper = st.session_state.get("learning_paper")
            if empty_pdf and empty_paper:
                preview_col, empty_col = st.columns([1.65, 1], gap="large")
                with preview_col:
                    st.markdown("### 论文原文")
                    _render_uploaded_pdf_preview(empty_pdf, st.session_state.get("project_original_filename") or "paper.pdf")
                with empty_col:
                    st.markdown("### 开始论文检查")
                    st.info("该论文还没有审计记录。上传一份解读报告后，系统会逐条核验其中的事实、数字与结论。")
                    if st.button("上传第一份报告", type="primary", width="stretch", key="empty_start_audit"):
                        render_report_audit_dialog(_submit_active_project_audit)
            else:
                st.info("该论文尚无已完成的审计记录，可以上传第一份报告开始审计。")
    else:
        render_audit_results(
            audit_run,
            CATEGORY_LABELS,
            LABEL_NAMES,
            SEVERITY_NAMES,
            DIMENSION_NAMES,
            paper=st.session_state.get("learning_paper"),
            pdf_bytes=st.session_state.get("learning_pdf_bytes"),
        )
    st.stop()

if (
    st.session_state.get("result_mode") == "audit"
    and st.session_state.get("audit_run") is not None
):
    audit_record_metadata = st.session_state.get("audit_record_metadata")
    if audit_record_metadata is not None:
        try:
            created_label = datetime.fromisoformat(
                audit_record_metadata.created_at
            ).astimezone().strftime("%Y-%m-%d %H:%M")
            source_label = audit_record_metadata.source_label
        except AttributeError:
            created_label = ""
            source_label = "历史审计"
        st.caption(f"历史审计 · {source_label} · {created_label}")
    return_to_learning = render_audit_results(
        st.session_state["audit_run"],
        CATEGORY_LABELS,
        LABEL_NAMES,
        SEVERITY_NAMES,
        DIMENSION_NAMES,
        show_return_to_learning=(
            st.session_state.get("audit_origin") in {"learning", "history"}
        ),
        paper=st.session_state.get("learning_paper"),
        pdf_bytes=st.session_state.get("learning_pdf_bytes"),
    )
    if return_to_learning:
        st.session_state["result_mode"] = "learning"
        st.session_state.pop("audit_origin", None)
        st.session_state.pop("audit_record_metadata", None)
        st.session_state.pop("active_audit_id", None)
        st.rerun()
    st.stop()

if st.session_state.get("result_mode") == "learning":
    learning_report = st.session_state.get("learning_report")
    learning_pdf_bytes = st.session_state.get("learning_pdf_bytes")
    learning_paper = st.session_state.get("learning_paper")
    parsed_codebase = st.session_state.get("parsed_codebase")
    if learning_report is not None and learning_pdf_bytes:
        if st.session_state.get("project_save_error"):
            st.warning(f"自动保存失败：{st.session_state['project_save_error']}")
        qa_service = AuditService(active_settings) if api_ready else None
        code_service = CodeLearningService(active_settings) if api_ready else None
        if st.session_state.get("code_parse_warning"):
            st.warning(st.session_state["code_parse_warning"])
        render_learning_workspace(
            learning_report,
            learning_pdf_bytes,
            paper=learning_paper,
            qa_service=qa_service,
            codebase=parsed_codebase,
            code_service=code_service,
            submit_audit_job=(
                _submit_active_project_audit
                if api_ready and active_project_id
                else None
            ),
            load_audit_jobs=(
                _load_active_audit_jobs if active_project_id else None
            ),
            load_audit_records=(
                _load_active_audit_records if active_project_id else None
            ),
            on_open_audit=(
                _open_active_audit if active_project_id else None
            ),
            submit_peer_review=(
                _submit_active_project_peer_review
                if api_ready and active_project_id
                else None
            ),
        )
        st.stop()

if st.session_state.get("result_mode") == "peer_review":
    project_id = st.session_state.get("active_project_id")
    peer_review = st.session_state.get("peer_review")
    review_pdf_bytes = st.session_state.get("learning_pdf_bytes")
    peer_job = None
    if project_id:
        peer_jobs = project_store.list_peer_review_jobs(str(project_id))
        peer_job_id = st.session_state.get("peer_review_job_id")
        peer_job = next((job for job in peer_jobs if job.job_id == peer_job_id), None)
        if peer_job is None and peer_jobs:
            peer_job = peer_jobs[0]
            st.session_state["peer_review_job_id"] = peer_job.job_id
        if peer_review is None:
            peer_review = project_store.load_peer_review(str(project_id))
            st.session_state["peer_review"] = peer_review
    if peer_review is not None:
        st.markdown("<div style='height:1.2rem'></div>", unsafe_allow_html=True)
        render_peer_review(
            peer_review,
            review_pdf_bytes,
            on_submit_revision=_submit_active_project_revision if api_ready else None,
            load_revision_jobs=_load_active_revision_jobs,
            on_update_report=_save_active_peer_review,
            on_compare_related_work=_compare_active_related_work,
            load_revisions=_load_active_project_revisions,
            load_revision_pdf=_load_active_project_revision_pdf,
            on_update_revision=_save_active_project_revision,
        )
    elif peer_job is not None and peer_job.status in {AuditJobStatus.QUEUED, AuditJobStatus.RUNNING}:
        st.markdown("## 模拟投稿评审")
        st.info("评审正在后台进行，完成后会自动保存到左侧论文项目。")
        st.progress(peer_job.progress, text=peer_job.stage)
        if st.button("刷新评审状态", type="primary", key="peer_review_refresh"):
            st.rerun()
    elif peer_job is not None and peer_job.status in {AuditJobStatus.FAILED, AuditJobStatus.INTERRUPTED}:
        st.error(peer_job.error or "模拟评审任务未能完成。")
        if st.button("重新开始评审", type="primary", key="peer_review_retry"):
            try:
                # Retry with the exact rubric snapshot used by the failed job;
                # changing the sidebar controls must not silently change the
                # meaning of a retry.
                st.session_state["peer_review_venue"] = peer_job.venue.value
                st.session_state["peer_review_rubric_weights"] = dict(peer_job.rubric_weights)
                _submit_active_project_peer_review()
            except (StorageError, ValueError) as exc:
                st.error(str(exc))
            else:
                st.rerun()
    else:
        st.info("当前项目还没有模拟评审记录。")
    st.stop()

submission = render_upload_page(project_store, api_ready, _open_active_audit)
if submission is not None:
    process_upload(
        submission, active_settings, project_store, project_session,
        _submit_active_project_peer_review, _submit_active_project_audit,
    )

result_mode = st.session_state.get("result_mode")
if result_mode == "learning":
    learning_report = st.session_state.get("learning_report")
    learning_pdf_bytes = st.session_state.get("learning_pdf_bytes")
    learning_paper = st.session_state.get("learning_paper")
    parsed_codebase = st.session_state.get("parsed_codebase")
    if learning_report is not None and learning_pdf_bytes:
        st.markdown("<div style='height:1.2rem'></div>", unsafe_allow_html=True)
        qa_service = AuditService(active_settings) if api_ready else None
        code_service = CodeLearningService(active_settings) if api_ready else None
        if st.session_state.get("code_parse_warning"):
            st.warning(st.session_state["code_parse_warning"])
        render_learning_workspace(
            learning_report,
            learning_pdf_bytes,
            paper=learning_paper,
            qa_service=qa_service,
            codebase=parsed_codebase,
            code_service=code_service,
            submit_peer_review=(
                _submit_active_project_peer_review
                if api_ready and active_project_id
                else None
            ),
        )

if result_mode == "audit":
    run = st.session_state.get("audit_run")
    if run is not None:
        render_audit_results(
            run,
            CATEGORY_LABELS,
            LABEL_NAMES,
            SEVERITY_NAMES,
            DIMENSION_NAMES,
            show_return_to_learning=(
                st.session_state.get("audit_origin") in {"learning", "history"}
            ),
            paper=st.session_state.get("learning_paper"),
            pdf_bytes=st.session_state.get("learning_pdf_bytes"),
        )
