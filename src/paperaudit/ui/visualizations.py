from __future__ import annotations

from html import escape

import streamlit as st


def render_dimension_radar_or_bar(dimensions: dict[str, float | None], labels: dict[str, str]) -> None:
    rows = []
    for key, value in dimensions.items():
        label = escape(labels.get(key, key))
        if value is None:
            rows.append(
                f'<li class="is-na"><span>{label}</span><div class="pa-dim-bar"></div>'
                f'<strong>N/A</strong></li>'
            )
            continue
        score = max(0.0, min(float(value), 100.0))
        rows.append(
            f'<li><span>{label}</span><div class="pa-dim-bar"><i style="width:{score:.1f}%"></i></div>'
            f'<strong>{float(value):.1f}</strong></li>'
        )
    st.markdown(f'<ul class="pa-dim-scores">{"".join(rows)}</ul>', unsafe_allow_html=True)


def render_status_distribution(rows: list[dict[str, object]]) -> None:
    if not rows:
        st.info("暂无论断判定数据。")
        return
    st.dataframe(rows, width="stretch", hide_index=True)
