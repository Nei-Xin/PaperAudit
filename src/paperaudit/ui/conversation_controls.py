"""Small, shared controls for project-scoped conversations."""

from __future__ import annotations

from dataclasses import replace
from typing import Callable

import streamlit as st

from paperaudit.storage import ConversationRecord, make_conversation


CONVERSATIONS_KEY = "project_conversations"
ACTIVE_KEY = "active_conversation_id"


def ensure_conversation_state(
    paper_history_key: str,
    joint_history_key: str,
    conversations: list[ConversationRecord] | None = None,
) -> list[ConversationRecord]:
    records = st.session_state.get(CONVERSATIONS_KEY)
    if not isinstance(records, list) or not records:
        records = list(conversations or [make_conversation("新对话")])
        st.session_state[CONVERSATIONS_KEY] = records
    active_id = st.session_state.get(ACTIVE_KEY)
    # Empty conversations are drafts. Keep only the currently open draft so
    # repeated clicks on New do not leave a list of unusable entries.
    active_record = next(
        (item for item in records if item.conversation_id == active_id),
        None,
    )
    records[:] = [
        item
        for item in records
        if item.paper_history or item.joint_history or item is active_record
    ] or [make_conversation("新对话")]
    if isinstance(active_id, str):
        records[:] = [
            replace(
                item,
                paper_history=list(st.session_state.get(paper_history_key, item.paper_history)),
                joint_history=list(st.session_state.get(joint_history_key, item.joint_history)),
            )
            if item.conversation_id == active_id
            else item
            for item in records
        ]
    active = next((item for item in records if item.conversation_id == active_id), records[0])
    st.session_state[ACTIVE_KEY] = active.conversation_id
    st.session_state[paper_history_key] = active.paper_history
    st.session_state[joint_history_key] = active.joint_history
    return records


def active_conversation() -> ConversationRecord | None:
    records = st.session_state.get(CONVERSATIONS_KEY, [])
    active_id = st.session_state.get(ACTIVE_KEY)
    return next((item for item in records if item.conversation_id == active_id), None)


def _activate(record: ConversationRecord, paper_history_key: str, joint_history_key: str) -> None:
    st.session_state[ACTIVE_KEY] = record.conversation_id
    st.session_state[paper_history_key] = record.paper_history
    st.session_state[joint_history_key] = record.joint_history


def rename_from_question(question: str) -> None:
    record = active_conversation()
    if record is None or record.title not in {"新对话", "默认对话"}:
        return
    title = " ".join(question.strip().split())[:28] or "新对话"
    records = st.session_state.get(CONVERSATIONS_KEY, [])
    st.session_state[CONVERSATIONS_KEY] = [
        replace(item, title=title) if item.conversation_id == record.conversation_id else item
        for item in records
    ]


def render_conversation_controls(
    *,
    key_prefix: str,
    paper_history_key: str,
    joint_history_key: str,
    on_change: Callable[[], None] | None = None,
) -> None:
    records = ensure_conversation_state(paper_history_key, joint_history_key)
    active_id = st.session_state[ACTIVE_KEY]
    labels = {item.conversation_id: item.title for item in records}
    select_col, new_col, delete_col = st.columns([5, 1.15, 1.15], vertical_alignment="center")
    selected = select_col.selectbox(
        "当前对话",
        [item.conversation_id for item in records],
        index=[item.conversation_id for item in records].index(active_id),
        format_func=lambda value: labels.get(value, "新对话"),
        key=f"{key_prefix}-conversation-select-{active_id}",
        label_visibility="collapsed",
    )
    if selected != active_id:
        record = next(item for item in records if item.conversation_id == selected)
        _activate(record, paper_history_key, joint_history_key)
        if on_change:
            on_change()
        st.rerun()
    if new_col.button("＋", key=f"{key_prefix}-new-conversation", help="新建对话", width="stretch"):
        ensure_conversation_state(paper_history_key, joint_history_key)
        record = make_conversation("新对话")
        records.append(record)
        _activate(record, paper_history_key, joint_history_key)
        st.rerun()
    if delete_col.button(
        "×",
        key=f"{key_prefix}-delete-conversation",
        help="删除当前对话",
        disabled=len(records) <= 1,
        width="stretch",
    ):
        records[:] = [item for item in records if item.conversation_id != active_id]
        _activate(records[0], paper_history_key, joint_history_key)
        st.rerun()
