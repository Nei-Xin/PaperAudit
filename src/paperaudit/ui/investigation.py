"""User-facing trace of read actions; no model private reasoning."""

import streamlit as st

from paperaudit.agents.models import STOP_LABELS, TOOL_LABELS
from paperaudit.display import LABEL_NAMES
from paperaudit.models import ClaimAudit


def render_investigation(audit: ClaimAudit) -> None:
    trace = audit.investigation
    if trace is None:
        return
    with st.expander("深度核验 · 调查记录"):
        st.write(STOP_LABELS[trace.stop_reason])
        if audit.judgment_before_investigation:
            st.caption(f"调查前：{LABEL_NAMES[audit.judgment_before_investigation.label]} → "
                       f"最终：{LABEL_NAMES[audit.judgment.label]}")
        st.caption(f"额外模型请求 {trace.requests} 次 · 用时 {trace.elapsed_seconds:.1f} 秒"
                   f" · 已报告用量 {trace.tokens} tokens")
        candidates = {c.evidence_id: c for c in audit.candidates}
        for index, step in enumerate(trace.steps, 1):
            st.write(f"{index}. {TOOL_LABELS[step.action.tool]}：{step.action.reason}")
            if step.action.query:
                st.text(f"查询：{step.action.query}")
            elif step.action.page:
                st.text(f"第 {step.action.page} 页")
            elif step.action.chunk_id:
                st.text(f"原文片段：{step.action.chunk_id}")
            st.caption(step.outcome)
            for evidence_id in step.added_evidence_ids:
                item = candidates.get(evidence_id)
                if item:
                    st.text(f"第 {item.page} 页 · {item.chunk_id}\n{item.text}")
        if trace.missing_aspects:
            st.write("仍需核对：" + "；".join(trace.missing_aspects))
