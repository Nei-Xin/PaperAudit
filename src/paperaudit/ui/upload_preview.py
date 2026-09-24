from __future__ import annotations

from hashlib import sha256
import streamlit as st
from paperaudit.ui.pdf_selector import get_pdf_page_count, render_selectable_pdf_page


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


def render_uploaded_pdf_preview(pdf_bytes: bytes, filename: str) -> None:
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
