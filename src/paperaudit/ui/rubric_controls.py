from __future__ import annotations

import streamlit as st
from paperaudit.models import PeerReviewVenue
from .constants import PEER_REVIEW_VENUE_OPTIONS, PEER_REVIEW_WEIGHT_LABELS


def render_peer_review_rubric_controls() -> None:
    """Render the venue/rubric selector used before a peer-review job starts."""
    venue_value = st.session_state.get(
        "peer_review_venue", PeerReviewVenue.GENERAL.value
    )
    if venue_value not in PEER_REVIEW_VENUE_OPTIONS:
        st.session_state["peer_review_venue"] = PeerReviewVenue.GENERAL.value
    st.selectbox(
        "评审标准",
        list(PEER_REVIEW_VENUE_OPTIONS),
        format_func=PEER_REVIEW_VENUE_OPTIONS.get,
        key="peer_review_venue",
        help="选择会议标准；自定义标准可调整六个评审维度的权重。",
    )
    if st.session_state.get("peer_review_venue") == PeerReviewVenue.CUSTOM.value:
        custom_weights: dict[str, float] = {}
        with st.expander("自定义维度权重", expanded=True):
            for weight_name, weight_label in PEER_REVIEW_WEIGHT_LABELS.items():
                custom_weights[weight_name] = st.slider(
                    weight_label,
                    min_value=0.0,
                    max_value=2.0,
                    value=1.0,
                    step=0.1,
                    key=f"peer-review-weight-{weight_name}",
                )
        total_weight = sum(custom_weights.values())
        st.session_state["peer_review_rubric_weights"] = (
            {
                name: value / total_weight
                for name, value in custom_weights.items()
            }
            if total_weight > 0
            else {}
        )
    else:
        st.session_state["peer_review_rubric_weights"] = {}
