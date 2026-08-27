from __future__ import annotations

import streamlit as st


def render_dimension_radar_or_bar(dimensions: dict[str, float | None], labels: dict[str, str]) -> None:
    for key, value in dimensions.items():
        label = labels.get(key, key)
        if value is None:
            st.caption(f"{label}：N/A")
        else:
            st.caption(f"{label}：{value:.1f}")
            st.progress(max(0.0, min(float(value) / 100.0, 1.0)))


def render_status_distribution(rows: list[dict[str, object]]) -> None:
    if not rows:
        st.info("暂无论断判定数据。")
        return
    st.dataframe(rows, width="stretch", hide_index=True)
