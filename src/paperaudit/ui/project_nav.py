"""Project-level top bar shared by every saved-project page.

One row: project title on the left, a 阅读 / 审计 / 评审 pill switch in the
middle and page actions on the right. Lecture vs. Q&A is switched inside the
reader's assistant card (see ``render_assistant_switch``).
"""

from __future__ import annotations

from collections.abc import Callable, MutableMapping
from html import escape
from typing import Any

import streamlit as st

NAV_TABS = ("read", "audit", "review")
PROJECT_MODES = frozenset({"learning", "audit", "audit_project", "peer_review", "lecture_empty"})


def current_tab(state: MutableMapping[str, Any]) -> str:
    mode = state.get("result_mode")
    if mode in {"audit", "audit_project"}:
        return "audit"
    if mode == "peer_review":
        return "review"
    return "read"


def route_to_tab(state: MutableMapping[str, Any], tab: str, *, assistant: str | None = None) -> None:
    """Translate a tab (and optional assistant view) into result_mode routing."""

    if tab == "read":
        if assistant is not None:
            state["lecture_empty_tab"] = assistant
        if state.get("learning_report") is None:
            state["result_mode"] = "lecture_empty"
            return
        state["result_mode"] = "learning"
        if assistant == "qa":
            state["learning_workspace_mode"] = (
                "code" if state.get("parsed_codebase") is not None else "qa"
            )
        elif assistant == "lecture":
            state["learning_workspace_mode"] = "lecture"
    elif tab == "audit":
        state["result_mode"] = "audit_project"
    elif tab == "review":
        state["result_mode"] = "peer_review"


def _on_tab_change() -> None:
    tab = st.session_state.get("project_nav_tab")
    if tab in NAV_TABS:
        route_to_tab(st.session_state, tab)


def _on_assistant_change() -> None:
    view = st.session_state.get("assistant_view")
    if view in {"lecture", "qa"}:
        route_to_tab(st.session_state, "read", assistant=view)


def render_assistant_switch() -> None:
    """讲解 / 追问 switch at the top of the reader's assistant card."""

    mode = st.session_state.get("learning_workspace_mode")
    st.session_state["assistant_view"] = "qa" if mode in {"qa", "code"} else "lecture"
    with st.container(key="assistant_switch"):
        st.segmented_control(
            "助手",
            ["lecture", "qa"],
            format_func={"lecture": "讲解", "qa": "追问"}.get,
            key="assistant_view",
            on_change=_on_assistant_change,
            required=True,
            label_visibility="collapsed",
        )


def render_project_nav(
    *,
    title: str,
    meta: str,
    tab_labels: dict[str, str],
    right: Callable[[], None] | None = None,
    full_height: bool = False,
) -> str:
    """Render the one-row project top bar; return the active tab."""

    active = current_tab(st.session_state)
    # The switch mirrors routing state; re-seed it every run (allowed because
    # the widget is not created yet in this run).
    st.session_state["project_nav_tab"] = active
    with st.container(key="project_nav"):
        title_col, tabs_col, right_col = st.columns(
            [1, 0.9, 1], vertical_alignment="center", gap="small"
        )
        title_col.markdown(
            f'<div class="pa-project-head" title="{escape(meta)}"><div class="pa-project-title">'
            f'{escape(title)}</div>'
            # Marker for the fixed-viewport reader layout CSS.
            + ('<span class="pa-learning-layout" hidden></span>' if full_height else "")
            + "</div>",
            unsafe_allow_html=True,
        )
        with tabs_col:
            st.segmented_control(
                "项目视图",
                list(NAV_TABS),
                format_func=lambda tab: tab_labels.get(tab, tab),
                key="project_nav_tab",
                on_change=_on_tab_change,
                required=True,
                label_visibility="collapsed",
            )
        if right is not None:
            with right_col:
                right()
    return active
