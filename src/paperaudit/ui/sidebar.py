from __future__ import annotations

from dataclasses import replace
from html import escape
import streamlit as st
from paperaudit.config import Settings
from paperaudit.storage import ProjectStore, StorageError, StorageSettings
from .project_session import ProjectSession


@st.dialog("删除论文项目")
def _confirm_project_deletion(project_store: ProjectStore, project_session: ProjectSession, project_id: str, project_title: str) -> None:
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
                project_session.clear()
            elif st.query_params.get("project") == project_id:
                st.query_params.pop("project", None)
            st.session_state["project_delete_notice"] = f"已删除：{project_title}"
            st.rerun()


def render_sidebar(
    project_store: ProjectStore, project_session: ProjectSession,
    storage_settings: StorageSettings, env_settings: Settings,
) -> Settings:
    all_projects = project_store.list_projects()
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
                    project_session.save_conversations(project_store, str(current_project_id))
            except StorageError as exc:
                st.error(f"保存当前项目失败：{exc}")
            else:
                project_session.clear()
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
                    title_col, menu_col = st.columns([6, 1], gap="small", vertical_alignment="top")
                    if title_col.button(
                        metadata.title,
                        key=f"sidebar-open-{metadata.project_id}",
                        type="primary" if is_active else "secondary",
                        width="stretch",
                        help=metadata.original_filename,
                    ):
                        try:
                            project_session.open(project_store, metadata.project_id)
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
                        _confirm_project_deletion(project_store, project_session, metadata.project_id, metadata.title)
                    if metadata.has_code:
                        kind_badge = '<span class="pa-project-chip chip-code">论文与代码</span>'
                    elif metadata.has_peer_review:
                        kind_badge = '<span class="pa-project-chip chip-audit">投稿评审</span>'
                    elif metadata.has_learning_report:
                        kind_badge = '<span class="pa-project-chip chip-paper">论文精读</span>'
                    else:
                        kind_badge = '<span class="pa-project-chip chip-audit">论文检查</span>'

                    marker_class = " is-active" if is_active else ""
                    st.markdown(
                        f'<span class="pa-sidebar-project-marker{marker_class}"></span>'
                        f'<div class="pa-sidebar-project-meta">{kind_badge}'
                        f'<span class="pa-sidebar-filename" title="{escape(metadata.original_filename)}">{escape(metadata.original_filename)}</span></div>',
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

        if st.button(
            "清除读取缓存",
            width="stretch",
            help="清除 PDF 页面和代码解析的内存缓存，不删除项目文件或后台任务。",
        ):
            st.cache_data.clear()
            st.success("读取缓存已清除。")

        api_ready = bool(api_base.strip() and api_key.strip() and model.strip())
        if api_ready:
            st.markdown(
                # The UI branding is Hy3 while the configured backend may remain Luna.
                '<div class="pa-api-status is-ready"><span></span>Hy3</div>',
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
                <span>◇</span><div>Paper Learning Assistant<small>v1.0.0</small></div>
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

    return active_settings
