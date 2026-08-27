from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from hashlib import sha256
from html import escape

import streamlit as st

from paperaudit.audit_jobs import AuditJobManager
from paperaudit.display import LABEL_NAMES, SEVERITY_NAMES, recover_paper_title
from paperaudit.config import Settings
from paperaudit.code_parser import CodeParseError, parse_code_zip
from paperaudit.code_service import CodeLearningService
from paperaudit.hy3_client import Hy3ConfigurationError, Hy3ResponseError
from paperaudit.learning_jobs import LearningJobManager
from paperaudit.models import (
    AuditJob,
    AuditJobStatus,
    AuditRuntimeSnapshot,
    ClaimCategory,
    ParsedCodebase,
)
from paperaudit.pdf_parser import PDFParseError
from paperaudit.report_input import parse_report_file
from paperaudit.reporting import render_markdown
from paperaudit.service import AuditService
from paperaudit.storage import (
    ProjectStore,
    StorageError,
    choose_storage_directory,
    load_storage_settings,
    save_storage_settings,
    suggested_storage_root,
)
from paperaudit.ui.audit_results import render_audit_results
from paperaudit.ui.components import render_header_banner
from paperaudit.ui.learning import (
    render_learning_workspace,
    render_report_audit_dialog,
)
from paperaudit.ui.pdf_selector import get_pdf_page_count, render_selectable_pdf_page
from paperaudit.ui.styles import inject_custom_styles


st.set_page_config(
    page_title="Hy3 论文学习助手",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_custom_styles()

CATEGORY_LABELS = {
    ClaimCategory.RESEARCH_QUESTION: "研究问题",
    ClaimCategory.CONTRIBUTION: "核心贡献",
    ClaimCategory.METHOD: "方法",
    ClaimCategory.DATASET_SETUP: "数据集与实验设置",
    ClaimCategory.RESULTS: "主要结果",
    ClaimCategory.LIMITATIONS: "局限性",
}
FULL_SCOPE = list(CATEGORY_LABELS)
DIMENSION_NAMES = {
    "factual_support": "事实支持度",
    "evidence_correctness": "证据正确性",
    "evidence_completeness": "证据完整性",
    "numeric_consistency": "数字与指标一致性",
    "content_coverage": "内容覆盖度",
    "conclusion_boundary": "结论边界",
}


@st.cache_data(show_spinner=False, max_entries=4)
def _parse_uploaded_code(zip_bytes: bytes, filename: str) -> ParsedCodebase:
    return parse_code_zip(zip_bytes, filename)


@st.cache_resource(show_spinner=False)
def _get_audit_job_manager(storage_root: str) -> AuditJobManager:
    return AuditJobManager(ProjectStore(storage_root))


@st.cache_resource(show_spinner=False)
def _get_learning_job_manager(storage_root: str) -> LearningJobManager:
    return LearningJobManager(ProjectStore(storage_root))


@st.dialog("PDF 原文预览", width="large")
def _show_uploaded_pdf_dialog(
    pdf_bytes: bytes,
    page_number: int,
    preview_id: str,
) -> None:
    st.caption(f"第 {page_number} 页 · 放大阅读")
    render_selectable_pdf_page(
        pdf_bytes,
        page_number,
        [],
        key=f"upload-pdf-dialog-{preview_id}-{page_number}",
        selection_enabled=False,
        zoom_percent=120,
    )


def _render_uploaded_pdf_preview(pdf_bytes: bytes, filename: str) -> None:
    preview_id = sha256(pdf_bytes).hexdigest()[:12]
    page_count = get_pdf_page_count(pdf_bytes)
    if st.session_state.get("upload_pdf_preview_id") != preview_id:
        st.session_state["upload_pdf_preview_id"] = preview_id
        st.session_state["upload_pdf_preview_page"] = 1
        st.session_state["upload_pdf_preview_zoom"] = 100

    page_key = "upload_pdf_preview_page"
    zoom_key = "upload_pdf_preview_zoom"
    st.session_state.setdefault(page_key, 1)
    st.session_state.setdefault(zoom_key, 100)
    st.session_state[page_key] = min(
        max(int(st.session_state[page_key]), 1),
        page_count,
    )
    st.session_state[zoom_key] = min(max(int(st.session_state[zoom_key]), 100), 180)

    def change_preview_page(delta: int) -> None:
        current_page = int(st.session_state.get(page_key, 1))
        st.session_state[page_key] = min(max(current_page + delta, 1), page_count)

    def change_preview_zoom(delta: int) -> None:
        current_zoom = int(st.session_state.get(zoom_key, 100))
        st.session_state[zoom_key] = min(max(current_zoom + delta, 100), 180)

    def fit_preview_width() -> None:
        st.session_state[zoom_key] = 100

    with st.container(key="upload_pdf_preview"):
        title_col, previous_col, page_col, next_col, zoom_out_col, zoom_col, zoom_in_col, fit_col, fullscreen_col = st.columns(
            [4, 0.55, 0.9, 0.55, 0.55, 0.8, 0.55, 1.2, 0.55],
            vertical_alignment="center",
            gap="small",
        )
        title_col.markdown(
            f'<div class="pa-pdf-panel-title">PDF 原文预览 '
            f'<span>{st.session_state[page_key]} / {page_count}</span></div>',
            unsafe_allow_html=True,
        )
        previous_col.button(
            "‹",
            key="upload-preview-previous",
            disabled=st.session_state[page_key] <= 1,
            width="stretch",
            on_click=change_preview_page,
            args=(-1,),
        )
        with page_col:
            st.number_input(
                "预览页码",
                min_value=1,
                max_value=page_count,
                step=1,
                key=page_key,
                label_visibility="collapsed",
            )
        next_col.button(
            "›",
            key="upload-preview-next",
            disabled=st.session_state[page_key] >= page_count,
            width="stretch",
            on_click=change_preview_page,
            args=(1,),
        )
        zoom_out_col.button(
            "−",
            key="upload-preview-zoom-out",
            disabled=st.session_state[zoom_key] <= 100,
            width="stretch",
            on_click=change_preview_zoom,
            args=(-10,),
        )
        zoom_col.markdown(
            f'<div class="pa-pdf-zoom">{st.session_state[zoom_key]}%</div>',
            unsafe_allow_html=True,
        )
        zoom_in_col.button(
            "+",
            key="upload-preview-zoom-in",
            disabled=st.session_state[zoom_key] >= 180,
            width="stretch",
            on_click=change_preview_zoom,
            args=(10,),
        )
        fit_col.button(
            "适应宽度",
            key="upload-preview-fit-width",
            width="stretch",
            on_click=fit_preview_width,
        )
        if fullscreen_col.button("⛶", key="upload-preview-fullscreen", width="stretch"):
            _show_uploaded_pdf_dialog(
                pdf_bytes,
                int(st.session_state[page_key]),
                preview_id,
            )
        render_selectable_pdf_page(
            pdf_bytes,
            int(st.session_state[page_key]),
            [],
            key=f"upload-pdf-preview-{preview_id}",
            selection_enabled=False,
            zoom_percent=int(st.session_state[zoom_key]),
        )


def _pick_storage_path() -> None:
    try:
        selected = choose_storage_directory(
            st.session_state.get("storage_path_input") or suggested_storage_root()
        )
        if selected is not None:
            st.session_state["storage_path_input"] = str(selected)
        st.session_state.pop("storage_picker_error", None)
    except StorageError as exc:
        st.session_state["storage_picker_error"] = str(exc)


def _render_storage_setup(error_message: str | None = None) -> None:
    st.session_state.setdefault("storage_path_input", str(suggested_storage_root()))
    with st.container(key="storage_setup_shell"):
        st.markdown(
            '<div class="pa-storage-setup-icon">📁</div>'
            '<div class="pa-storage-setup-title">设置项目保存位置</div>'
            '<div class="pa-storage-setup-copy">论文、讲解报告、代码索引和追问记录将保存在此目录。'
            'API Key 不会写入项目文件。</div>',
            unsafe_allow_html=True,
        )
        path_col, browse_col = st.columns([5, 1], vertical_alignment="bottom")
        path_col.text_input(
            "保存目录",
            key="storage_path_input",
            placeholder=r"例如 D:\PaperAuditData",
        )
        browse_col.button(
            "浏览…",
            width="stretch",
            on_click=_pick_storage_path,
            help="打开 Windows 文件夹选择器；也可以直接粘贴完整路径。",
        )
        visible_error = st.session_state.get("storage_picker_error") or error_message
        if visible_error:
            st.error(str(visible_error))
        st.caption("建议选择空间充足的本地目录；程序会自动创建 projects 子目录。")
        if st.button("保存并进入项目", type="primary", width="stretch"):
            try:
                save_storage_settings(st.session_state["storage_path_input"])
            except StorageError as exc:
                st.error(str(exc))
            else:
                st.session_state.pop("storage_picker_error", None)
                st.rerun()


def _restore_learning_project(store: ProjectStore, project_id: str) -> None:
    saved = store.load_learning_project(project_id)
    restored_title = recover_paper_title(saved.paper)
    if restored_title != saved.metadata.title:
        store.update_project_title(saved.metadata.project_id, restored_title)
    restored_paper = saved.paper.model_copy(update={"title": restored_title})
    restored_report = (
        saved.report.model_copy(update={"paper_title": restored_title})
        if saved.report is not None
        else None
    )
    st.session_state["learning_report"] = restored_report
    st.session_state["learning_pdf_bytes"] = saved.pdf_bytes
    st.session_state["learning_paper"] = restored_paper
    st.session_state["parsed_codebase"] = saved.codebase
    st.session_state["paper_qa_history"] = saved.paper_history
    st.session_state["joint_qa_history"] = saved.joint_history
    st.session_state["project_original_filename"] = saved.metadata.original_filename
    st.session_state["active_project_id"] = saved.metadata.project_id
    if saved.report is not None:
        st.session_state["result_mode"] = "learning"
    else:
        records = store.list_audit_runs(saved.metadata.project_id)
        if records:
            audit_metadata, audit_run = store.load_audit_run(
                saved.metadata.project_id, records[0].audit_id
            )
            audit_run = audit_run.model_copy(update={"paper_title": restored_title})
            st.session_state["audit_run"] = audit_run
            st.session_state["active_audit_id"] = audit_metadata.audit_id
            st.session_state["audit_record_metadata"] = audit_metadata
        st.session_state["result_mode"] = "audit_project"
    st.session_state.pop("code_parse_warning", None)
    st.query_params["project"] = saved.metadata.project_id


_PROJECT_SESSION_KEYS = (
    "learning_report",
    "learning_pdf_bytes",
    "learning_paper",
    "parsed_codebase",
    "audit_run",
    "active_audit_id",
    "audit_record_metadata",
    "audit_origin",
    "audit_save_error",
    "audit_submit_notice",
    "launch_audit_job_id",
    "learning_job_id",
    "result_mode",
    "learning_selected_evidence",
    "learning_evidence_group",
    "learning_evidence_section",
    "learning_active_section",
    "learning_active_point",
    "learning_pdf_page",
    "learning_pdf_zoom",
    "learning_pdf_anchor_sync",
    "learning_focus_evidence",
    "qa_selected_evidence",
    "qa_evidence_group",
    "qa_pdf_page",
    "qa_pdf_zoom",
    "qa_pdf_anchor_sync",
    "qa_focus_evidence",
    "paper_qa_history",
    "paper_qa_pending",
    "paper_text_selection",
    "learning_workspace_mode",
    "learning_switch_to_qa",
    "learning_pdf_focus",
    "joint_qa_history",
    "joint_qa_pending",
    "joint_paper_selection",
    "joint_active_paper_citation",
    "joint_active_code_citation",
    "joint_code_selection",
    "joint_code_path",
    "joint_code_path_pending",
    "joint_code_rendered_path",
    "joint_pdf_page",
    "joint_paper_sync",
    "joint_layout_mode",
    "joint_layout_mode_pending",
    "code_parse_warning",
    "active_project_id",
    "project_original_filename",
    "project_save_error",
    "paper_pdf_upload",
    "source_code_upload",
    "workspace_audit_input_mode",
    "workspace_audit_pasted_text",
    "workspace_audit_report_file",
    "workspace_audit_scope_mode",
    "workspace_audit_scope_values",
)


def _clear_project_session() -> None:
    for state_key in _PROJECT_SESSION_KEYS:
        st.session_state.pop(state_key, None)
    st.query_params.pop("project", None)


def _open_saved_project(store: ProjectStore, project_id: str) -> None:
    current_id = st.session_state.get("active_project_id")
    if current_id and current_id != project_id:
        store.save_histories(
            str(current_id),
            st.session_state.get("paper_qa_history", []),
            st.session_state.get("joint_qa_history", []),
        )
    _clear_project_session()
    _restore_learning_project(store, project_id)


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
except StorageError as exc:
    _render_storage_setup(str(exc))
    st.stop()


@st.dialog("删除论文项目")
def _confirm_project_deletion(project_id: str, project_title: str) -> None:
    st.write(project_title)
    st.warning("论文 PDF、讲解、追问和审计记录将被永久删除，无法恢复。")
    cancel_col, delete_col = st.columns(2)
    if cancel_col.button("取消", width="stretch"):
        st.rerun()
    if delete_col.button("确认删除", type="primary", width="stretch"):
        try:
            project_store.delete_project(project_id)
        except StorageError as exc:
            st.error(str(exc))
        else:
            if st.session_state.get("active_project_id") == project_id:
                _clear_project_session()
            elif st.query_params.get("project") == project_id:
                st.query_params.pop("project", None)
            st.session_state["project_delete_notice"] = f"已删除：{project_title}"
            st.rerun()


requested_project = st.query_params.get("project")
if requested_project and st.session_state.get("active_project_id") != requested_project:
    try:
        _restore_learning_project(project_store, str(requested_project))
    except StorageError as exc:
        st.query_params.pop("project", None)
        st.session_state["project_restore_error"] = str(exc)


env_settings = Settings.from_env()
all_projects = project_store.list_projects()
if delete_notice := st.session_state.pop("project_delete_notice", None):
    st.toast(str(delete_notice), icon="🗑️")

with st.sidebar:
    st.markdown(
        '<div class="pa-sidebar-library-title">论文项目</div>',
        unsafe_allow_html=True,
    )
    if st.button(
        "＋ 新建论文",
        key="sidebar-new-project",
        type="primary",
        width="stretch",
    ):
        current_project_id = st.session_state.get("active_project_id")
        try:
            if current_project_id:
                project_store.save_histories(
                    str(current_project_id),
                    st.session_state.get("paper_qa_history", []),
                    st.session_state.get("joint_qa_history", []),
                )
        except StorageError as exc:
            st.error(f"保存当前项目失败：{exc}")
        else:
            _clear_project_session()
            st.rerun()

    project_search = st.text_input(
        "搜索论文项目",
        placeholder="搜索论文标题…",
        key="sidebar_project_search",
        label_visibility="collapsed",
    )
    search_term = project_search.strip().casefold()
    visible_projects = [
        metadata
        for metadata in all_projects
        if not search_term
        or search_term in metadata.title.casefold()
        or search_term in metadata.original_filename.casefold()
    ]
    st.markdown(
        f'<div class="pa-sidebar-section-heading"><span>我的项目</span>'
        f'<b>{len(visible_projects)}</b></div>',
        unsafe_allow_html=True,
    )
    with st.container(key="sidebar_project_list"):
        if not visible_projects:
            empty_copy = "没有匹配的论文" if search_term else "还没有保存的论文"
            st.markdown(
                f'<div class="pa-sidebar-project-empty">{empty_copy}</div>',
                unsafe_allow_html=True,
            )
        for metadata in visible_projects:
            is_active = metadata.project_id == st.session_state.get("active_project_id")
            with st.container(key=f"sidebar_project_{metadata.project_id}"):
                marker_class = " is-active" if is_active else ""
                st.markdown(
                    f'<span class="pa-sidebar-project-marker{marker_class}"></span>',
                    unsafe_allow_html=True,
                )
                title_col, menu_col = st.columns([6, 1], gap="small", vertical_alignment="center")
                if title_col.button(
                    metadata.title,
                    key=f"sidebar-open-{metadata.project_id}",
                    type="primary" if is_active else "secondary",
                    width="stretch",
                    help=metadata.original_filename,
                ):
                    try:
                        _open_saved_project(project_store, metadata.project_id)
                    except StorageError as exc:
                        st.error(f"打开项目失败：{exc}")
                    else:
                        st.rerun()
                if menu_col.button(
                    "⋮",
                    key=f"sidebar-delete-{metadata.project_id}",
                    type="tertiary",
                    width="stretch",
                    help="删除论文项目",
                ):
                    _confirm_project_deletion(metadata.project_id, metadata.title)
                project_kind = (
                    "论文与代码"
                    if metadata.has_code
                    else "论文"
                    if metadata.has_learning_report
                    else "审计"
                )
                st.markdown(
                    f'<div class="pa-sidebar-project-meta">{project_kind} · '
                    f'{escape(metadata.original_filename)}</div>',
                    unsafe_allow_html=True,
                )

    st.divider()
    with st.expander("⚙ 模型与检索", expanded=not env_settings.is_configured):
        api_base = st.text_input(
            "API Base URL",
            value=env_settings.api_base,
            key="custom_api_base",
            placeholder="https://api.example.com/v1",
        )
        api_key = st.text_input(
            "API Key",
            value=env_settings.api_key,
            key="custom_api_key",
            type="password",
            placeholder="sk-...",
        )
        model = st.text_input(
            "模型名称",
            value=env_settings.model or "hy3",
            key="custom_model",
            placeholder="hy3",
        )
        reasoning_options = ["no_think", "low", "medium", "high"]
        effort_index = (
            reasoning_options.index(env_settings.reasoning_effort)
            if env_settings.reasoning_effort in reasoning_options
            else 0
        )
        reasoning_effort = st.selectbox(
            "推理强度 (Reasoning Effort)", reasoning_options, index=effort_index
        )
        top_k_display = int(
            st.session_state.get("retrieval_top_k_control", env_settings.retrieval_top_k)
        )
        st.markdown(
            f'<div class="pa-sidebar-field"><span>候选证据 Top-K</span>'
            f'<b>{top_k_display}</b></div>',
            unsafe_allow_html=True,
        )
        retrieval_top_k = st.slider(
            "候选证据检索数量 (Top-K)",
            3,
            12,
            env_settings.retrieval_top_k,
            key="retrieval_top_k_control",
            label_visibility="collapsed",
            help="每条论断从论文中召回的最高相关正文块数量",
        )
        batch_display = int(
            st.session_state.get("judge_batch_size_control", env_settings.judge_batch_size)
        )
        st.markdown(
            f'<div class="pa-sidebar-field"><span>研判批大小</span>'
            f'<b>{batch_display}</b></div>',
            unsafe_allow_html=True,
        )
        judge_batch_size = st.slider(
            "研判并发批大小 (Batch Size)",
            2,
            10,
            env_settings.judge_batch_size,
            key="judge_batch_size_control",
            label_visibility="collapsed",
            help="每次送入模型进行事实核验的论断数量",
        )

    api_ready = bool(api_base.strip() and api_key.strip() and model.strip())
    if api_ready:
        st.markdown(
            f'<div class="pa-api-status is-ready"><span></span>{model.strip()}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="pa-api-status is-warning"><span></span>API 配置不完整</div>',
            unsafe_allow_html=True,
        )
    st.markdown(
        f'<div class="pa-storage-status"><span></span>'
        f'<div><strong>本地自动保存</strong><small title="'
        f'{escape(str(storage_settings.storage_root))}">'
        f'{escape(storage_settings.storage_root.name)}</small></div></div>',
        unsafe_allow_html=True,
    )
    st.divider()
    st.markdown(
        """
        <div class="pa-sidebar-version">
            <span>◇</span><div>Paper Learning Assistant<small>v0.3.0</small></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

active_settings = replace(
    env_settings,
    api_base=api_base.strip(),
    api_key=api_key.strip(),
    model=model.strip(),
    reasoning_effort=reasoning_effort,
    retrieval_top_k=retrieval_top_k,
    judge_batch_size=judge_batch_size,
)

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
        st.query_params["project"] = metadata.project_id
    except StorageError as exc:
        st.session_state["project_save_error"] = str(exc)

active_project_id = st.session_state.get("active_project_id")
if active_project_id and st.session_state.get("result_mode") == "learning":
    try:
        project_store.save_histories(
            str(active_project_id),
            st.session_state.get("paper_qa_history", []),
            st.session_state.get("joint_qa_history", []),
        )
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
    title_col, learning_col, action_col, history_col, export_col = st.columns(
        [2.7, 1, 1, 1, 1], vertical_alignment="center"
    )
    with title_col:
        st.markdown(f"### {escape(str(project_title))}")
        st.caption(
            f"{'论文项目' if learning_job is not None and learning_job.status == AuditJobStatus.SUCCEEDED else '仅审计项目'}"
            f" · {st.session_state.get('project_original_filename', 'paper.pdf')}"
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
            "查看论文讲解",
            type="primary",
            width="stretch",
        ):
            _restore_learning_project(project_store, str(project_id))
            st.rerun()
    elif learning_active:
        learning_col.button("正在生成讲解", disabled=True, width="stretch")
    elif learning_col.button(
        "生成论文讲解",
        type="primary",
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
        "审计另一份报告",
        type="primary",
        width="stretch",
        disabled=not api_ready or not project_id,
    ):
        render_report_audit_dialog(_submit_active_project_audit)
    with history_col.popover("审计记录", width="stretch"):
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
        "导出报告",
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
        )
        st.stop()

report_text = ""
report_source_label = "粘贴报告"
report_source_filename = None
source_code_file = None
uploaded_codebase = None
scope = FULL_SCOPE
run_clicked = False
status = None
progress_bar = None

upload_has_value = st.session_state.get("paper_pdf_upload") is not None
launch_shell_key = "launch_shell_ready" if upload_has_value else "launch_shell_empty"
with st.container(key=launch_shell_key):
    if st.session_state.get("launch_mode") not in ("生成论文讲解", "审计已有报告"):
        st.session_state["launch_mode"] = "生成论文讲解"
    launch_title_col, launch_mode_col = st.columns([1.55, 1], vertical_alignment="center")
    with launch_title_col:
        render_header_banner()
    with launch_mode_col:
        mode_label = st.segmented_control(
            "选择工作模式",
            ["生成论文讲解", "审计已有报告"],
            key="launch_mode",
            required=True,
            label_visibility="collapsed",
            width="stretch",
        )
    mode = "learn" if mode_label == "生成论文讲解" else "audit_existing"

    if not upload_has_value:
        with st.container(key="launch_pdf_upload_empty"):
            st.markdown(
                '<div class="pa-upload-title">拖拽论文 PDF 到这里</div>'
                '<div class="pa-upload-subtitle">或点击下方选择文件 · PDF · 最大 200MB</div>',
                unsafe_allow_html=True,
            )
            pdf_file = st.file_uploader(
                "上传英文论文 PDF",
                type=["pdf"],
                accept_multiple_files=False,
                help="支持带文本层的公开英文论文 PDF",
                key="paper_pdf_upload",
                label_visibility="collapsed",
            )
    else:
        current_pdf = st.session_state.get("paper_pdf_upload")
        file_bar, replace_bar = st.columns([7, 1], vertical_alignment="center")
        with file_bar:
            st.markdown(
                f'<div class="pa-ready-toolbar"><span>📄</span><strong>{current_pdf.name}</strong>'
                f'<small>{len(current_pdf.getvalue()) / 1024 / 1024:.1f} MB</small></div>',
                unsafe_allow_html=True,
            )
        with replace_bar.popover("更换文件", width="stretch"):
            pdf_file = st.file_uploader(
                "选择另一篇论文 PDF",
                type=["pdf"],
                accept_multiple_files=False,
                help="支持带文本层的公开英文论文 PDF",
                key="paper_pdf_upload",
            )

    if pdf_file is None:
        with st.expander("高级选项", expanded=False):
            if mode == "learn":
                st.markdown(
                    "标准讲解包含研究问题、核心贡献、方法、实验、结果、局限与关键术语。"
                )
                st.caption("上传论文后可继续关联开源代码 ZIP。")
            else:
                st.markdown(
                    "上传论文后，可粘贴中文报告或上传 `.txt` / `.md` / `.pptx` 文件。"
                )
                st.caption("审计会逐条检索论文原文并给出证据定位。")
        st.markdown(
            '<div class="pa-launch-hint">上传 PDF 后进入论文准备页</div>',
            unsafe_allow_html=True,
        )
    else:
        preview_col, setup_col = st.columns([1.86, 1], gap="large")
        with preview_col:
            try:
                _render_uploaded_pdf_preview(pdf_file.getvalue(), pdf_file.name)
            except (ValueError, RuntimeError) as exc:
                st.error(f"PDF 预览失败：{exc}")

        with setup_col:
            with st.container(border=True, key="launch_setup_panel"):
                st.markdown('<div class="pa-setup-heading">生成设置</div>', unsafe_allow_html=True)
                st.markdown(
                    f'<div class="pa-ready-file"><span>✓ PDF 已就绪</span>'
                    f'<strong>{pdf_file.name}</strong>'
                    f'<small>{len(pdf_file.getvalue()) / 1024 / 1024:.1f} MB</small></div>',
                    unsafe_allow_html=True,
                )
                if mode == "audit_existing":
                    st.markdown('<div class="pa-setup-title">已有报告</div>', unsafe_allow_html=True)
                    if st.session_state.get("report_source_mode") not in ("粘贴文本", "上传文件"):
                        st.session_state["report_source_mode"] = "粘贴文本"
                    report_source = st.segmented_control(
                        "报告输入方式",
                        ["粘贴文本", "上传文件"],
                        key="report_source_mode",
                        required=True,
                        label_visibility="collapsed",
                        width="stretch",
                    )
                    if report_source == "粘贴文本":
                        report_text = st.text_area(
                            "中文解读内容",
                            height=160,
                            placeholder="粘贴针对该论文的中文总结、解读或阅读笔记…",
                            label_visibility="collapsed",
                        )
                    else:
                        report_file = st.file_uploader(
                            "选择报告文件",
                            type=["txt", "md", "pptx"],
                            accept_multiple_files=False,
                            key="report_file_upload",
                            help="PowerPoint 将按幻灯片提取文字、表格、图表数据和备注。",
                        )
                        if report_file is not None:
                            report_source_label = report_file.name
                            report_source_filename = report_file.name
                            try:
                                parsed_report = parse_report_file(
                                    report_file.getvalue(), report_file.name
                                )
                                report_text = parsed_report.text
                            except ValueError as exc:
                                st.error(str(exc))
                            else:
                                if parsed_report.kind == "pptx":
                                    st.caption(
                                        f"已读取 {parsed_report.page_count} 页幻灯片 · "
                                        f"{len(report_text)} 个字符"
                                    )
                                    for warning in parsed_report.warnings:
                                        st.warning(warning)
                                else:
                                    st.caption(f"已读取 {len(report_text)} 个字符")

                    if st.session_state.get("audit_scope_mode") not in ("完整解读", "自定义重点"):
                        st.session_state["audit_scope_mode"] = "完整解读"
                    scope_mode = st.segmented_control(
                        "审计范围",
                        ["完整解读", "自定义重点"],
                        key="audit_scope_mode",
                        required=True,
                        width="stretch",
                    )
                    if scope_mode == "自定义重点":
                        selected_labels = st.multiselect(
                            "选择检查范围",
                            list(CATEGORY_LABELS.values()),
                            default=["核心贡献", "方法", "主要结果"],
                        )
                        scope = [
                            category
                            for category, label in CATEGORY_LABELS.items()
                            if label in selected_labels
                        ]
                else:
                    st.markdown(
                        '<div class="pa-setup-title">讲解模式</div>'
                        '<div class="pa-setup-mode"><strong>标准论文学习</strong>'
                        '<span>研究问题 · 主要贡献 · 方法 · 实验 · 结果 · 局限 · 关键术语</span></div>',
                        unsafe_allow_html=True,
                    )
                    st.markdown('<div class="pa-setup-title">关联开源代码</div>', unsafe_allow_html=True)
                    with st.expander("上传代码 ZIP（可选）", expanded=False):
                        source_code_file = st.file_uploader(
                            "上传论文开源代码 ZIP",
                            type=["zip"],
                            accept_multiple_files=False,
                            help="只读取文本文件，不运行代码或安装依赖。",
                            key="source_code_upload",
                        )
                        if source_code_file is not None:
                            try:
                                uploaded_codebase = _parse_uploaded_code(
                                    source_code_file.getvalue(), source_code_file.name
                                )
                                st.success(
                                    f"已解析 {len(uploaded_codebase.files)} 个文件、"
                                    f"{len(uploaded_codebase.chunks)} 个代码块"
                                )
                            except (CodeParseError, ValueError) as exc:
                                st.error(f"代码 ZIP 无法解析：{exc}")
                    if source_code_file is None:
                        st.caption("当前未关联代码，可直接生成论文讲解。")

                can_run = bool(
                    api_ready
                    and (mode == "learn" or (scope and report_text.strip()))
                )
                launch_job = None
                launch_job_id = st.session_state.get("launch_audit_job_id")
                active_launch_project_id = st.session_state.get("active_project_id")
                if mode == "audit_existing" and launch_job_id and active_launch_project_id:
                    try:
                        launch_job = project_store.load_audit_job(
                            str(active_launch_project_id), str(launch_job_id)
                        )
                    except StorageError:
                        st.session_state.pop("launch_audit_job_id", None)
                launch_job_active = bool(
                    launch_job
                    and launch_job.status
                    in {AuditJobStatus.QUEUED, AuditJobStatus.RUNNING}
                )
                if launch_job_active:
                    can_run = False
                tips = []
                if not api_ready:
                    tips.append("请先在侧栏配置 API")
                if mode == "audit_existing" and not report_text.strip():
                    tips.append("请提供中文报告")
                if tips:
                    st.caption(" · ".join(tips))
                with st.container(key="launch_setup_actions"):
                    st.divider()
                    if launch_job_active and launch_job is not None:
                        st.progress(launch_job.progress, text=launch_job.stage)
                        st.caption("审计正在后台执行，可以继续翻阅左侧论文。")
                        if st.button(
                            "刷新审计状态",
                            width="stretch",
                            key="launch_audit_refresh",
                        ):
                            st.rerun()
                    elif (
                        launch_job is not None
                        and launch_job.status == AuditJobStatus.SUCCEEDED
                        and launch_job.audit_id
                    ):
                        st.success("后台审计已完成。")
                        if st.button(
                            "查看审计结果 →",
                            type="primary",
                            width="stretch",
                            key="launch_open_audit_result",
                        ):
                            _open_active_audit(launch_job.audit_id)
                            st.session_state.pop("launch_audit_job_id", None)
                            st.rerun()
                    elif launch_job is not None and launch_job.status in {
                        AuditJobStatus.FAILED,
                        AuditJobStatus.INTERRUPTED,
                    }:
                        st.error(launch_job.error or "审计任务未能完成。")
                        if st.button(
                            "重新审计",
                            width="stretch",
                            key="launch_retry_audit",
                        ):
                            st.session_state.pop("launch_audit_job_id", None)
                            st.rerun()
                    else:
                        button_label = "生成论文讲解 →" if mode == "learn" else "开始审计 →"
                        run_clicked = st.button(
                            button_label,
                            type="primary",
                            width="stretch",
                            disabled=not can_run,
                        )
                if run_clicked:
                    status_label = (
                        "正在生成论文学习讲解" if mode == "learn" else "正在执行证据审计"
                    )
                    status = st.status(status_label, expanded=True)
                    progress_bar = st.progress(0.0, text="正在读取并解析 PDF 文本块")

if run_clicked and pdf_file is not None:
    assert status is not None and progress_bar is not None

    def update_progress(message: str, value: float) -> None:
        progress_bar.progress(value, text=message)

    try:
        service = AuditService(active_settings)
        pdf_bytes = pdf_file.getvalue()
        paper = service.parse(pdf_bytes)
        if mode == "learn":
            progress_bar.progress(0.3, text="正在调用 Hy3 生成结构化中文讲解")
            learning_report = service.generate_learning_report(paper)
            parsed_codebase = None
            code_warning = None
            if source_code_file is not None:
                progress_bar.progress(0.85, text="正在建立本地代码索引")
                try:
                    parsed_codebase = uploaded_codebase or CodeLearningService(
                        active_settings
                    ).parse(source_code_file.getvalue(), source_code_file.name)
                except (CodeParseError, ValueError) as exc:
                    code_warning = f"论文讲解已生成，但代码 ZIP 未能建立索引：{exc}"
            st.session_state["learning_report"] = learning_report
            st.session_state["learning_pdf_bytes"] = pdf_bytes
            st.session_state["learning_paper"] = paper
            st.session_state["parsed_codebase"] = parsed_codebase
            if code_warning:
                st.session_state["code_parse_warning"] = code_warning
            else:
                st.session_state.pop("code_parse_warning", None)
            st.session_state["result_mode"] = "learning"
            st.session_state.pop("learning_selected_evidence", None)
            st.session_state.pop("learning_evidence_group", None)
            st.session_state.pop("learning_evidence_section", None)
            st.session_state.pop("learning_active_section", None)
            st.session_state.pop("learning_active_point", None)
            st.session_state.pop("learning_pdf_page", None)
            st.session_state.pop("learning_pdf_zoom", None)
            st.session_state.pop("learning_pdf_anchor_sync", None)
            st.session_state.pop("learning_focus_evidence", None)
            st.session_state.pop("qa_selected_evidence", None)
            st.session_state.pop("qa_evidence_group", None)
            st.session_state.pop("qa_pdf_page", None)
            st.session_state.pop("qa_pdf_zoom", None)
            st.session_state.pop("qa_pdf_anchor_sync", None)
            st.session_state.pop("qa_focus_evidence", None)
            st.session_state["paper_qa_history"] = []
            st.session_state.pop("paper_text_selection", None)
            st.session_state.pop("learning_workspace_mode", None)
            st.session_state.pop("learning_switch_to_qa", None)
            st.session_state["joint_qa_history"] = []
            for state_key in (
                "joint_qa_pending",
                "joint_paper_selection",
                "joint_active_paper_citation",
                "joint_active_code_citation",
                "joint_code_selection",
                "joint_code_path",
                "joint_code_path_pending",
                "joint_code_rendered_path",
                "joint_pdf_page",
                "joint_paper_sync",
                "joint_layout_mode",
                "joint_layout_mode_pending",
            ):
                st.session_state.pop(state_key, None)
            try:
                metadata = project_store.save_learning_project(
                    pdf_bytes,
                    pdf_file.name,
                    paper,
                    learning_report,
                    parsed_codebase,
                )
                st.session_state["active_project_id"] = metadata.project_id
                st.session_state["project_original_filename"] = metadata.original_filename
                st.session_state.pop("project_save_error", None)
                st.query_params["project"] = metadata.project_id
            except StorageError as exc:
                st.session_state["project_save_error"] = str(exc)
            status.update(label="论文讲解生成完成", state="complete", expanded=False)
            progress_bar.progress(1.0, text="讲解生成完成")
            st.rerun()
        else:
            progress_bar.progress(0.25, text="正在保存论文并创建后台任务")
            metadata = project_store.save_paper_project(
                pdf_bytes,
                pdf_file.name,
                paper,
            )
            _restore_learning_project(project_store, metadata.project_id)
            job = _submit_active_project_audit(
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
