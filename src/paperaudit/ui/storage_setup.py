from __future__ import annotations

import streamlit as st
from paperaudit.storage import (
    StorageError,
    choose_storage_directory,
    save_storage_settings,
    suggested_storage_root,
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


def render_storage_setup(error_message: str | None = None) -> None:
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
