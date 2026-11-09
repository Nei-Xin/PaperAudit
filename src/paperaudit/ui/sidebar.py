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
    st.warning("论文 PDF、讲解、追问、审计与评审记录将被永久删除，无法恢复。")
    cancel_col, delete_col = st.columns(2)
    if cancel_col.button("取消", width="stretch"):
        st.rerun()
    if delete_col.button(
        "永久删除", type="primary", width="stretch", key="confirm_project_delete"
    ):
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
            '<div class="pa-sidebar-brand">'
            '<svg width="28" height="28" viewBox="0 0 28 28" aria-hidden="true">'
            '<rect width="28" height="28" rx="6" fill="#1E4A7A"></rect>'
            '<path d="M9 7h7l4 4v10H9z" fill="none" stroke="#fff" stroke-width="1.6" stroke-linejoin="round"></path>'
            '<path d="m12 16 2 2 3-4" fill="none" stroke="#fff" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"></path>'
            '</svg><div><strong>PaperAudit</strong><span>论文学习与证据审计</span></div></div>',
            unsafe_allow_html=True,
        )
        if st.button(
            "新建论文",
            key="sidebar-new-project",
            type="secondary",
            icon=":material/add:",
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
            placeholder="搜索论文",
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
                # One quiet label per saved artifact (lecture / audit / review / code).
                parts = [
                    label
                    for label, present in (
                        ("讲解", metadata.has_learning_report),
                        ("审计", project_store.has_audit_runs(metadata.project_id)),
                        ("评审", metadata.has_peer_review),
                        ("代码", metadata.has_code),
                    )
                    if present
                ] or ["仅原文"]
                marker_class = " is-active" if is_active else ""
                with st.container(key=f"sidebar_project_{metadata.project_id}"):
                    # Whole row is one HTML block; the open button is stretched
                    # over it and the delete button sits on top (see CSS).
                    st.markdown(
                        f'<div class="pa-row-body">'
                        f'<span class="pa-sidebar-project-marker{marker_class}"></span>'
                        f'<div class="pa-row-title">{escape(metadata.title)}</div>'
                        f'<div class="pa-project-chips">{" · ".join(parts)}</div></div>',
                        unsafe_allow_html=True,
                    )
                    if st.button(
                        metadata.title,
                        key=f"sidebar-open-{metadata.project_id}",
                        type="tertiary",
                        width="stretch",
                    ):
                        try:
                            project_session.open(project_store, metadata.project_id)
                        except StorageError as exc:
                            st.error(f"打开项目失败：{exc}")
                        else:
                            st.rerun()
                    if st.button(
                        ":material/delete_outline:",
                        key=f"sidebar-delete-{metadata.project_id}",
                        type="tertiary",
                        help="删除论文项目",
                    ):
                        _confirm_project_deletion(project_store, project_session, metadata.project_id, metadata.title)

        st.divider()
        with st.expander("模型与检索设置", expanded=not env_settings.is_configured):
            api_base = st.text_input(
                "API 地址",
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
                "推理强度", reasoning_options, index=effort_index
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
                help="基础检索数量；首次审计再扩展至多5块，其中至多3块优先查找报告引用页，原文合计不超过18,000字符；高风险补查可另加候选。",
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
            # A navigation rerun may skip rendering this widget; keep the
            # preference outside Streamlit's disposable widget state.
            st.session_state.setdefault(
                "deep_audit_control", st.session_state.get("deep_audit_preference", env_settings.deep_audit),
            )
            deep_audit = st.toggle(
                "深度核验", key="deep_audit_control",
                help="审计时自动对证据不足的论断补查，无需逐条启动。",
            )
            st.session_state["deep_audit_preference"] = deep_audit
            if deep_audit:
                st.caption("疑难论断最多补查两轮，会增加耗时和模型调用费用。")
            if st.button(
                "清除读取缓存",
                width="stretch",
                help="清除 PDF 页面和代码解析的内存缓存，不删除项目文件或后台任务。",
            ):
                st.cache_data.clear()
                st.success("读取缓存已清除。")

        api_ready = bool(api_base.strip() and api_key.strip() and model.strip())
        # Show the model the requests actually go to, not the UI brand name. The
        # settings are only checked for completeness, so do not claim a connection.
        api_label = f"已配置 · {escape(model.strip())}" if api_ready else "API 配置不完整"
        api_class = "is-ready" if api_ready else "is-warning"
        st.markdown(
            f'<div class="pa-sidebar-status {api_class}" title="{escape(api_base.strip())}"><span></span>{api_label}'
            f'<em title="{escape(str(storage_settings.storage_root))}">'
            f'保存于 {escape(storage_settings.storage_root.name)} · v1.0.0</em></div>',
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
        deep_audit=deep_audit,
    )

    return active_settings
