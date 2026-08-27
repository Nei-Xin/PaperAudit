from __future__ import annotations

import streamlit as st


def inject_custom_styles() -> None:
    st.markdown(
        """
        <style>
        .block-container {
            max-width:1900px;padding:3.1rem 1.25rem 2rem;
        }
        .block-container:has(.st-key-learning_primary_nav) {
            padding-top:.85rem;
        }
        /* Keep Streamlit's native header available so a collapsed project sidebar
           can always be reopened. The learning header remains the visual header. */
        body:has(.st-key-learning_primary_nav) header[data-testid="stHeader"] {
            height:2.35rem;background:transparent;
        }
        body:has(.st-key-learning_primary_nav) header[data-testid="stHeader"] button {
            opacity:.72;
        }
        [data-testid="stFileUploaderDropzone"] {border-radius: 9px;}
        [data-testid="stMetric"] {
            border: 1px solid #e2e8f0; border-radius: 10px; padding: 12px 14px;
            background: #ffffff;
        }
        section[data-testid="stSidebar"]:not([aria-expanded="false"]) {
            width:260px !important;min-width:260px !important;
        }
        section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
            padding:.9rem .82rem 1rem;background:#fbfcfe;border-right:1px solid #e5eaf0;
        }
        .pa-sidebar-library-title {
            margin:.08rem 0 .72rem;color:#172033;font-size:1rem;font-weight:780;
            letter-spacing:.01em;
        }
        .pa-sidebar-section-heading {
            display:flex;align-items:center;justify-content:space-between;
            margin:1rem .12rem .42rem;color:#334155;font-size:.72rem;font-weight:760;
        }
        .pa-sidebar-section-heading b {
            display:inline-flex;align-items:center;justify-content:center;min-width:1.25rem;height:1.25rem;
            padding:0 .3rem;border-radius:.42rem;background:#eef2f6;color:#64748b;
            font-size:.63rem;font-weight:700;
        }
        .st-key-sidebar_project_list {
            max-height:38vh;min-height:4.5rem;margin-top:.12rem;padding:0;
            overflow-y:auto;scrollbar-gutter:stable;border:1px solid #e4e9ef;
            border-radius:8px;background:#fff;box-shadow:0 2px 8px rgba(15,23,42,.035);
        }
        div[class*="st-key-sidebar_project_"] {
            position:relative;margin:0;padding:.34rem .45rem .46rem .68rem;
            border-radius:0;border-bottom:1px solid #edf1f5;
        }
        div[class*="st-key-sidebar_project_"]:last-child {
            border-bottom:0;
        }
        div[class*="st-key-sidebar_project_"]:has(.pa-sidebar-project-marker.is-active) {
            background:#eef6ff;
        }
        .pa-sidebar-project-marker {display:none;}
        .pa-sidebar-project-marker.is-active {
            display:block;position:absolute;left:0;top:0;bottom:0;width:3px;background:#1683f8;
        }
        div[class*="st-key-sidebar_project_"] [data-testid="stButton"] button {
            justify-content:flex-start;min-height:1.75rem;padding:.18rem .22rem;
            border:0;background:transparent;box-shadow:none;text-align:left;
        }
        div[class*="st-key-sidebar_project_"] [data-testid="stButton"] button:hover {
            background:#f1f5f9;color:#172033;
        }
        div[class*="st-key-sidebar_project_"] [data-testid="stButton"] button p {
            display:-webkit-box;max-width:100%;overflow:hidden;-webkit-box-orient:vertical;
            -webkit-line-clamp:2;white-space:normal;line-height:1.36;
            color:#263449;font-size:.72rem;font-weight:700;
        }
        div[class*="st-key-sidebar_project_"] div[class*="st-key-sidebar-delete-"]
        [data-testid="stButton"] button {
            justify-content:center;min-height:1.75rem;padding:0;color:#7c899b;
        }
        div[class*="st-key-sidebar_project_"] div[class*="st-key-sidebar-delete-"]
        [data-testid="stButton"] button p {
            display:block;overflow:visible;color:inherit;font-size:.9rem;line-height:1;
        }
        div[class*="st-key-sidebar_project_"]:has(.pa-sidebar-project-marker.is-active)
        [data-testid="stButton"] button p {color:#1d4ed8;}
        .pa-sidebar-project-meta {
            margin:-.02rem .24rem 0;color:#8a96a8;font-size:.59rem;
            overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
        }
        .pa-sidebar-project-empty {
            padding:.8rem .4rem;color:#94a3b8;font-size:.68rem;text-align:center;
        }
        .st-key-joint_code_file_tree {
            min-width:0;padding:.42rem .4rem;border:1px solid #e3e8ef;border-radius:9px;
            background:#fff;scrollbar-gutter:stable;
        }
        .st-key-joint_code_file_tree_list {
            height:calc(100vh - 260px);max-height:720px;min-height:320px;overflow-y:auto;
            overflow-x:hidden;scrollbar-gutter:stable;padding-right:.12rem;
        }
        .st-key-joint_code_file_tree_list::-webkit-scrollbar {width:6px;}
        .st-key-joint_code_file_tree_list::-webkit-scrollbar-thumb {
            background:transparent;border-radius:6px;
        }
        .st-key-joint_code_file_tree_list:hover::-webkit-scrollbar-thumb {background:#cbd5e1;}
        .pa-code-tree-title {
            padding:.08rem .35rem .42rem;color:#172033;font-size:.75rem;font-weight:760;
        }
        .st-key-joint_code_file_tree > [data-testid="stVerticalBlock"] {gap:.12rem;}
        .st-key-joint_code_file_tree [data-testid="stTextInput"] {margin-bottom:.22rem;}
        .st-key-joint_code_file_tree [data-testid="stTextInput"] input {
            min-height:2rem;padding:.35rem .55rem;border-color:#e5eaf0;border-radius:6px;
            background:#f8fafc;font-size:.68rem;
        }
        .st-key-joint_code_file_tree [data-testid="stExpander"] {
            margin:0;border:0 !important;border-radius:5px;background:transparent !important;
        }
        .st-key-joint_code_file_tree [data-testid="stExpander"] details {
            border:0 !important;background:transparent !important;
        }
        .st-key-joint_code_file_tree [data-testid="stExpander"] details summary {
            min-height:30px;height:30px;padding:0 7px;border-radius:5px;
            color:#334155;font-size:13px;font-weight:600;
        }
        .st-key-joint_code_file_tree [data-testid="stExpander"] details summary:hover {
            background:#f1f5f9;
        }
        .st-key-joint_code_file_tree [data-testid="stExpanderDetails"] {
            margin-left:14px;padding:0 0 0 1px;border-left:1px solid #f0f2f5;
        }
        .st-key-joint_code_file_tree button[kind],
        .st-key-joint_code_file_tree [data-testid="stButton"] button {
            min-height:28px;height:28px;padding:0 7px;border:0 !important;border-radius:5px;
            justify-content:flex-start !important;box-shadow:none !important;
            background:transparent;color:#475569;font-size:13px;text-align:left;
        }
        .st-key-joint_code_file_tree button[kind]:hover,
        .st-key-joint_code_file_tree [data-testid="stButton"] button:hover {
            background:#f1f5f9;color:#172033;
        }
        .st-key-joint_code_file_tree [data-testid="stBaseButton-primary"] {
            background:#eaf3ff !important;color:#1677ff !important;font-weight:650;
            box-shadow:none !important;
        }
        .st-key-joint_code_file_tree [data-testid="stBaseButton-primary"] span,
        .st-key-joint_code_file_tree [data-testid="stBaseButton-primary"] p {
            color:#1677ff !important;
        }
        .st-key-joint_code_file_tree button p {
            width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;text-align:left;
        }
        .st-key-joint_code_file_tree button [data-testid="stIconMaterial"] {
            flex:0 0 15px;width:15px;font-size:15px;color:#64748b;
        }
        .pa-code-breadcrumb {
            margin:.12rem 0 .5rem;padding:.42rem .55rem;border-bottom:1px solid #e5eaf0;
            color:#94a3b8;font-size:.67rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
        }
        .pa-code-breadcrumb strong {color:#475569;font-weight:700;}
        .pa-sidebar-title {font-size:.82rem;font-weight:750;color:#334155;margin:.2rem 0 .45rem;}
        .pa-api-status {
            display:flex;align-items:center;gap:.52rem;padding:.58rem .62rem;margin-top:.5rem;
            border:1px solid #e5eaf0;border-radius:7px 7px 0 0;background:#fff;
            color:#334155;font-size:.7rem;font-weight:650;
            white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
        }
        .pa-api-status span {width:.42rem;height:.42rem;border-radius:50%;flex:0 0 auto;}
        .pa-api-status.is-ready span {background:#22c55e;box-shadow:0 0 0 3px #dcfce7;}
        .pa-api-status.is-warning span {background:#f59e0b;box-shadow:0 0 0 3px #fef3c7;}
        .pa-sidebar-field {
            display:flex;align-items:center;justify-content:space-between;gap:.5rem;
            margin:.45rem 0 .05rem;color:#64748b;font-size:.7rem;
        }
        .pa-sidebar-field b {color:#2563eb;font-size:.72rem;}
        .pa-sidebar-version {
            display:flex;align-items:flex-start;gap:.52rem;padding:.75rem .28rem .1rem;
            color:#8b96a7;font-size:.63rem;line-height:1.45;
        }
        .pa-sidebar-version > span {font-size:.85rem;color:#7c899b;}
        .pa-sidebar-version small {display:block;margin-top:.12rem;color:#a0a9b7;font-size:.59rem;}
        .pa-audit-empty-note {
            display:flex;flex-direction:column;gap:.12rem;margin:.55rem 0 .2rem;padding:.65rem .72rem;
            border-radius:7px;background:#f8fafc;color:#64748b;
        }
        .pa-audit-empty-note strong {color:#475569;font-size:.7rem;font-weight:700;}
        .pa-audit-empty-note span {font-size:.64rem;line-height:1.45;}
        .pa-storage-status {
            display:flex;align-items:flex-start;gap:.52rem;padding:.58rem .62rem;
            border:1px solid #e5eaf0;border-top:0;border-radius:0 0 7px 7px;background:#fff;min-width:0;
        }
        .pa-storage-status > span {
            width:.42rem;height:.42rem;margin-top:.18rem;border-radius:50%;background:#22c55e;
            box-shadow:0 0 0 3px #dcfce7;flex:0 0 auto;
        }
        .pa-storage-status div {min-width:0;}
        .pa-storage-status strong {display:block;color:#334155;font-size:.69rem;}
        .pa-storage-status small {
            display:block;margin-top:.12rem;color:#94a3b8;font-size:.61rem;
            white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
        }
        .pa-header {
            display:flex; justify-content:space-between; align-items:center; gap:1rem;
            min-height:3.5rem;padding:.35rem 0;margin:0;border:0;border-radius:0;background:transparent;
        }
        .pa-header-title {font-size:1.05rem; font-weight:750; color:#172033;}
        .pa-header-subtitle {margin-top:.12rem; color:#64748b; font-size:.72rem;white-space:nowrap;}
        .pa-header-badge {color:#64748b; font-size:.65rem; white-space:nowrap;}
        .st-key-launch_shell_empty {max-width:1120px;margin:0 auto;}
        .st-key-launch_shell_ready {max-width:1440px;margin:0 auto;}
        .st-key-launch_shell_empty > div:first-child,
        .st-key-launch_shell_ready > div:first-child {gap:.7rem;}
        .st-key-launch_pdf_upload_empty {
            margin:1.2rem 0 .7rem;padding:1.25rem 1.5rem 1.35rem;
            border:2px dashed #bfdbfe;border-radius:14px;background:#f8fbff;text-align:center;
        }
        .st-key-launch_pdf_upload_empty [data-testid="stFileUploaderDropzone"] {
            min-height:5rem;border:0;background:transparent;justify-content:center;
        }
        .st-key-launch_pdf_upload_empty [data-testid="stFileUploaderDropzoneInstructions"] {
            display:none;
        }
        .pa-upload-title {color:#172033;font-size:1.08rem;font-weight:750;margin:.1rem 0 .25rem;}
        .pa-upload-subtitle {color:#64748b;font-size:.76rem;margin-bottom:.35rem;}
        .pa-launch-hint {color:#94a3b8;font-size:.72rem;text-align:center;margin:.35rem 0;}
        .st-key-storage_setup_shell {
            max-width:720px;margin:clamp(2.5rem,10vh,7rem) auto 0;padding:2rem 2.1rem 1.8rem;
            border:1px solid #dbe4ee;border-radius:16px;background:#fff;
            box-shadow:0 18px 50px rgba(15,23,42,.08);
        }
        .pa-storage-setup-icon {font-size:1.7rem;margin-bottom:.55rem;}
        .pa-storage-setup-title {color:#172033;font-size:1.35rem;font-weight:750;}
        .pa-storage-setup-copy {color:#64748b;font-size:.82rem;line-height:1.65;margin:.35rem 0 1rem;}
        .pa-recent-title {color:#334155;font-size:.78rem;font-weight:750;margin:1.15rem 0 .45rem;}
        div[class*="st-key-recent_project_"] {border-color:#e2e8f0 !important;background:#fff;}
        .pa-recent-project-title {
            color:#172033;font-size:.8rem;font-weight:700;white-space:nowrap;
            overflow:hidden;text-overflow:ellipsis;
        }
        .pa-recent-project-meta {color:#94a3b8;font-size:.67rem;margin-top:.16rem;}
        .pa-ready-toolbar {
            display:flex;align-items:center;gap:.5rem;min-width:0;padding:.42rem .18rem;
            border-bottom:1px solid #e2e8f0;color:#475569;
        }
        .pa-ready-toolbar strong {
            min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
            color:#172033;font-size:.8rem;
        }
        .pa-ready-toolbar small {margin-left:auto;color:#94a3b8;font-size:.68rem;white-space:nowrap;}
        .st-key-launch_setup_panel {
            position:sticky;top:3.5rem;min-height:min(73vh,760px);padding:.2rem;
            border-color:#dbe4ee !important;border-radius:11px;background:#fff;
        }
        .st-key-launch_setup_panel > div[data-testid="stVerticalBlock"] {
            min-height:inherit;
        }
        .pa-setup-heading {color:#172033;font-size:1rem;font-weight:750;margin:.08rem 0 .65rem;}
        .pa-ready-file {
            display:grid;grid-template-columns:1fr auto;gap:.2rem .6rem;padding:.75rem .8rem;
            margin-bottom:.8rem;border-left:3px solid #2563eb;background:#f8fafc;
        }
        .pa-ready-file span {grid-column:1 / -1;color:#2563eb;font-size:.68rem;font-weight:700;}
        .pa-ready-file strong {
            min-width:0;color:#172033;font-size:.82rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
        }
        .pa-ready-file small {color:#94a3b8;font-size:.68rem;white-space:nowrap;}
        .pa-setup-title {color:#172033;font-size:.88rem;font-weight:750;margin:.35rem 0 .28rem;}
        .pa-setup-mode {
            padding:.68rem .75rem;margin-bottom:.7rem;border:1px solid #e2e8f0;
            border-radius:8px;background:#f8fafc;
        }
        .pa-setup-mode strong {display:block;color:#172033;font-size:.8rem;margin-bottom:.24rem;}
        .pa-setup-mode span {display:block;color:#64748b;font-size:.7rem;line-height:1.5;}
        .st-key-launch_setup_actions {margin-top:1rem;}
        .pa-setup-copy {
            color:#64748b;font-size:.74rem;line-height:1.55;padding:0 0 .75rem;
            margin-bottom:.55rem;border-bottom:1px solid #e2e8f0;
        }
        .st-key-upload_pdf_preview {
            padding:.4rem;background:#eef1f5;border-radius:8px;
        }
        .st-key-upload_pdf_preview > div:first-child {
            padding:.25rem .35rem;background:#fff;border-bottom:1px solid #e2e8f0;
        }
        .pa-grade {
            padding:1rem 1.2rem; margin-bottom:1rem; border-radius:10px;
            background:#f8fafc; border-left:5px solid #64748b;
        }
        .pa-grade-trusted {border-left-color:#10b981;}
        .pa-grade-review {border-left-color:#f59e0b;}
        .pa-grade-untrusted {border-left-color:#ef4444;}
        .pa-grade-title {font-size:1.1rem; font-weight:700; color:#172033;}
        .pa-grade-detail {margin-top:.2rem; color:#64748b; font-size:.86rem;}
        .pa-audit-card {
            border:1px solid #e2e8f0; border-radius:11px; padding:1rem 1.1rem;
            margin-bottom:.75rem; background:#fff;
        }
        .pa-audit-meta {color:#64748b; font-size:.78rem; margin-bottom:.45rem;}
        .pa-audit-claim {font-weight:650; line-height:1.55; color:#172033;}
        .pa-audit-explanation {margin-top:.55rem; color:#475569; line-height:1.55;}
        .pa-audit-head {display:flex;justify-content:space-between;align-items:center;gap:.6rem;flex-wrap:wrap;}
        .pa-audit-tags {display:flex;align-items:center;gap:.35rem;flex-wrap:wrap;}
        .pa-badge {display:inline-flex;padding:.18rem .48rem;border-radius:5px;font-size:.74rem;font-weight:650;}
        .badge-supported {background:#d1fae5;color:#065f46;border:1px solid #a7f3d0;}
        .badge-partially {background:#fef3c7;color:#92400e;border:1px solid #fde68a;}
        .badge-contradicted {background:#fee2e2;color:#991b1b;border:1px solid #fecaca;}
        .badge-no-support,.badge-abstain,.badge-sev-none {background:#f1f5f9;color:#475569;border:1px solid #cbd5e1;}
        .badge-sev-low {background:#e0f2fe;color:#0369a1;border:1px solid #bae6fd;}
        .badge-sev-medium {background:#fef9c3;color:#a16207;border:1px solid #fef08a;}
        .badge-sev-high {background:#ffedd5;color:#c2410c;border:1px solid #fed7aa;}
        .badge-sev-critical {background:#ffe4e6;color:#be123c;border:1px solid #fecdd3;}
        .pa-mark {background:#fef3c7;color:inherit;padding:0 .12rem;border-radius:3px;}
        .pa-evidence {
            margin-top:.55rem; padding:.7rem .8rem; border-left:3px solid #0ea5e9;
            border-radius:0 8px 8px 0; background:#f7fbff; color:#334155;
            font-size:.84rem; line-height:1.55; white-space:pre-wrap; overflow-wrap:anywhere;
        }
        .pa-audit-summary {
            display:flex;align-items:stretch;gap:0;flex-wrap:nowrap;
            padding:0;margin:0 0 .55rem;border:1px solid #dbe2ea;
            border-radius:8px;background:#fff;overflow:hidden;
        }
        .pa-audit-summary-grade {
            display:flex;flex-direction:column;align-items:flex-start;justify-content:center;
            gap:.12rem;min-width:8.5rem;padding:.72rem 1rem;border-right:1px solid #e2e8f0;
        }
        .pa-audit-summary-grade span {
            color:#64748b;font-size:.7rem;font-weight:700;text-transform:uppercase;
            letter-spacing:.04em;
        }
        .pa-audit-summary-grade strong {
            font-size:1rem;color:#334155;white-space:nowrap;
        }
        .pa-audit-summary-grade.is-trusted strong {color:#047857;}
        .pa-audit-summary-grade.is-review strong {color:#b45309;}
        .pa-audit-summary-grade.is-untrusted strong {color:#b91c1c;}
        .pa-audit-summary-score {
            display:flex;align-items:center;min-width:5rem;padding:.72rem 1rem;
            border-right:1px solid #e2e8f0;color:#1565d8;font-size:1.65rem;
            font-weight:750;line-height:1;
        }
        .pa-audit-summary-score small {
            color:#64748b;font-size:.72rem;font-weight:600;margin-left:.18rem;
        }
        .pa-audit-summary-metrics {
            display:grid;grid-template-columns:repeat(5,minmax(7.5rem,1fr));
            align-items:stretch;gap:0;flex:1 1 auto;
        }
        .pa-audit-summary-metric {
            display:flex;flex-direction:column;align-items:center;justify-content:center;
            gap:.2rem;padding:.62rem .55rem;border-right:1px solid #eef2f7;
            border-radius:0;background:#fff;color:#64748b;
        }
        .pa-audit-summary-metric span {font-size:.68rem;white-space:nowrap;}
        .pa-audit-summary-metric strong {font-size:1rem;color:#172033;}
        .pa-audit-summary-metric.is-danger {background:#fff1f2;}
        .pa-audit-summary-metric.is-danger strong {color:#be123c;}
        .pa-audit-summary-metric.is-warning {background:#fff7ed;}
        .pa-audit-summary-metric.is-warning strong {color:#c2410c;}
        .st-key-audit_quick_filters {margin:.15rem 0 .45rem;}
        .st-key-audit_quick_filters div[data-testid="stButtonGroup"] {flex-wrap:wrap;}
        .st-key-audit_advanced_filters {margin-bottom:.15rem;}
        .st-key-audit_advanced_filters [data-testid="stHorizontalBlock"] {gap:.5rem;}
        .st-key-audit_advanced_filters [data-baseweb="select"] > div,
        .st-key-audit_advanced_filters input {min-height:2.15rem;font-size:.78rem;}
        .pa-audit-list-head {
            display:flex;align-items:center;gap:.4rem;min-width:0;margin-bottom:.08rem;
        }
        .pa-audit-list-head > strong {
            padding:.12rem .32rem;border-radius:4px;background:#e8f1ff;color:#1565d8;
            font-size:.72rem;font-family:ui-monospace,SFMono-Regular,Consolas,monospace;
        }
        .pa-audit-list-head > span {font-size:.83rem;font-weight:700;color:#25324a;}
        .pa-audit-list-head > div {display:flex;gap:.25rem;margin-left:auto;}
        [class*="st-key-audit_claim_item_"] {
            padding:.55rem .62rem !important;margin-bottom:.35rem;border-color:#dfe5ed !important;
            border-radius:7px !important;background:#fff;box-shadow:none;
        }
        [class*="st-key-audit_claim_item_active_"] {
            border-color:#1677ff !important;background:#f8fbff;
            box-shadow:0 0 0 1px rgba(22,119,255,.08);
        }
        [class*="st-key-audit_claim_item_"] .stButton {margin:.12rem 0 .05rem;}
        [class*="st-key-audit_claim_item_"] .stButton > button {
            min-height:0 !important;padding:.08rem 0 !important;border:0 !important;
            justify-content:flex-start;text-align:left;color:#475569;background:transparent !important;
            box-shadow:none !important;font-size:.76rem;line-height:1.4;
        }
        [class*="st-key-audit_claim_item_"] [data-testid="stCaptionContainer"] {
            font-size:.68rem;color:#7c8799;
        }
        .pa-audit-page-label {padding:.42rem 0;text-align:center;color:#64748b;font-size:.75rem;}
        .st-key-audit_selected_detail {
            min-height:39rem;padding:.8rem 1.05rem !important;border-color:#dfe5ed !important;
            border-radius:7px !important;background:#fff;
        }
        .st-key-audit_selected_detail .pa-audit-detail-head {
            margin:-.1rem 0 .25rem;padding:0 0 .7rem;border-bottom:1px solid #e8edf3;
        }
        .st-key-audit_selected_detail .pa-audit-detail-section {
            padding:.8rem 0;border-top:0;border-bottom:1px solid #eef2f7;
        }
        div[data-testid="stExpander"]:has(.pa-audit-detail) {
            border:1px solid #e2e8f0;border-radius:9px;background:#fff;
            margin-bottom:.45rem;box-shadow:none;
        }
        div[data-testid="stExpander"]:has(.pa-audit-detail) summary {
            padding:.65rem .8rem;color:#334155;font-size:.8rem;font-weight:650;
            line-height:1.45;
        }
        .pa-audit-detail {padding:.05rem .15rem .3rem;color:#334155;}
        .pa-audit-detail-head {
            display:flex;justify-content:space-between;align-items:center;
            gap:.6rem;flex-wrap:wrap;padding-bottom:.5rem;
        }
        .pa-audit-detail-section {
            width:100%;padding:.62rem 0;border-top:1px solid #eef2f7;
        }
        .pa-audit-detail-label {
            margin-bottom:.28rem;color:#64748b;font-size:.68rem;font-weight:750;
            text-transform:uppercase;letter-spacing:.035em;
        }
        .pa-audit-detail-copy,.pa-audit-claim {max-width:100ch;}
        .pa-audit-detail-copy {color:#475569;font-size:.84rem;line-height:1.65;}
        .pa-audit-evidence-list {display:grid;gap:.5rem;width:100%;}
        .pa-audit-evidence-item {
            padding:.62rem .72rem;border-left:3px solid #38bdf8;
            border-radius:0 7px 7px 0;background:#f7fbff;
        }
        .pa-audit-evidence-meta {
            color:#0369a1;font-size:.68rem;font-weight:750;margin-bottom:.28rem;
        }
        .pa-audit-evidence-text {
            color:#334155;font-size:.8rem;line-height:1.62;white-space:normal;
            overflow-wrap:anywhere;
        }
        .pa-audit-empty-inline {
            display:inline-block;padding:.42rem .58rem;border-radius:6px;
            background:#f8fafc;color:#64748b;font-size:.78rem;
        }
        .pa-audit-empty {
            display:flex;flex-direction:column;gap:.2rem;align-items:flex-start;
            padding:1.15rem;border:1px dashed #cbd5e1;border-radius:9px;
            background:#f8fafc;color:#64748b;margin:.4rem 0 .55rem;
        }
        .pa-audit-empty strong {color:#334155;font-size:.88rem;}
        .pa-audit-empty span {font-size:.76rem;}
        .pa-learning-hero {
            padding:.7rem .95rem; border:1px solid #dbeafe; border-left:4px solid #2563eb;
            border-radius:0 12px 12px 0; background:linear-gradient(135deg,#eff6ff,#f8fafc);
            margin-bottom:.25rem;
        }
        .pa-learning-eyebrow {color:#2563eb; font-size:.75rem; font-weight:700; margin-bottom:.25rem;}
        .pa-learning-title {color:#172033; font-size:1.25rem; font-weight:700; line-height:1.4;}
        .pa-learning-summary {color:#475569; margin-top:.5rem; line-height:1.6;}
        .st-key-learning_primary_nav {
            position:relative;top:auto;z-index:12;min-height:56px;padding:.2rem 0;
            margin:0;border-bottom:1px solid #e5e7eb;background:rgba(255,255,255,.97);
            backdrop-filter:blur(10px);overflow:visible;
        }
        .st-key-learning_primary_nav [data-testid="stHorizontalBlock"] {overflow:visible;}
        .st-key-learning_primary_nav {gap:0 !important;}
        .st-key-learning_primary_nav > [data-testid="stLayoutWrapper"]
        > [data-testid="stHorizontalBlock"] {gap:1rem;align-items:center;}
        .st-key-learning_primary_nav > [data-testid="stLayoutWrapper"]
        > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child {
            flex:1 1 420px !important;min-width:0 !important;
        }
        .st-key-learning_primary_nav > [data-testid="stLayoutWrapper"]
        > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2) {
            flex:0 1 460px !important;width:460px !important;max-width:460px;
        }
        .st-key-learning_primary_nav > [data-testid="stLayoutWrapper"]
        > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:last-child {
            flex:0 0 140px !important;width:140px !important;max-width:140px;
        }
        .st-key-learning_primary_nav [role="radiogroup"] {
            min-height:40px;border-color:#dbe4ee;border-radius:8px;background:#fff;
        }
        .st-key-learning_primary_nav [role="radio"] {
            min-height:40px;border-radius:0;color:#334155;font-size:.8rem;
        }
        .st-key-learning_primary_nav [data-testid="stPopover"] button {
            min-height:40px;border-radius:8px;font-size:.8rem;
        }
        .st-key-learning_primary_nav [role="radio"][aria-checked="true"] {
            background:#178b55 !important;color:#fff !important;border-color:#178b55 !important;
        }
        .pa-workspace-header {
            display:flex;align-items:center;gap:.7rem;min-width:0;padding:.06rem 0;
        }
        .pa-workspace-brand-icon {
            display:grid;place-items:center;flex:0 0 34px;width:34px;height:38px;
            border:2px solid #15803d;border-radius:4px;color:#15803d;
            font-size:1.12rem;font-weight:800;line-height:1;
        }
        .pa-workspace-copy {flex:1 1 auto;min-width:0;}
        .pa-workspace-title-row {min-width:0;}
        .pa-workspace-title-row {display:flex;align-items:baseline;gap:.7rem;}
        .pa-workspace-title {
            color:#0f172a;font-size:1rem;font-weight:760;line-height:1.35;
            flex:0 1 auto;max-width:48%;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
        }
        .pa-workspace-summary {
            flex:1 1 auto;min-width:0;margin:0;color:#64748b;font-size:.75rem;line-height:1.25;
            white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
        }
        .pa-panel-title {
            color:#0f172a;font-size:.88rem;font-weight:750;line-height:2.2rem;
            white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
        }
        .pa-panel-title span {color:#94a3b8;font-size:.7rem;font-weight:500;margin-left:.28rem;}
        .pa-workspace-status {
            display:flex;align-items:center;gap:.42rem;color:#64748b;font-size:.72rem;
            min-height:2rem;
        }
        .pa-workspace-status span {
            width:.45rem;height:.45rem;border-radius:50%;background:#22c55e;
            box-shadow:0 0 0 3px #dcfce7;flex:0 0 auto;
        }
        .st-key-audit_activity_strip {
            margin:.35rem 0 .2rem;padding:.35rem .65rem;border:1px solid #dbeafe;
            border-radius:8px;background:#f8fbff;
        }
        .st-key-audit_activity_strip [data-testid="stProgress"] {margin:0;}
        .st-key-audit_activity_strip [data-testid="stCaptionContainer"] {margin:0;}
        .pa-learning-nav-marker,.pa-learning-source-marker,.pa-learning-point-marker {display:none;}
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.pa-learning-nav-marker) {
            position:sticky; top:3.2rem;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.pa-learning-nav-marker),
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.pa-learning-source-marker) {
            border-radius:12px; border-color:#dbe4ee; background:#fff;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.pa-learning-point-marker) {
            border-color:#e2e8f0; border-radius:11px; background:#fff; margin-bottom:.6rem;
        }
        .pa-learning-nav-link {
            display:block; padding:.45rem .55rem; margin:.12rem 0; border-radius:6px;
            color:#475569 !important; text-decoration:none !important; font-size:.84rem;
        }
        .pa-learning-nav-link:hover {color:#1d4ed8 !important; background:#eff6ff;}
        .pa-learning-section-anchor {scroll-margin-top:4rem;}
        .st-key-learning_section_bar {
            height:42px;padding:0;margin:0 0 .45rem;border:0;border-bottom:1px solid #e5e7eb;
            border-radius:0;background:rgba(255,255,255,.97);position:relative;top:auto;z-index:11;
            box-shadow:none;backdrop-filter:blur(10px);
        }
        .st-key-learning_section_bar [role="radiogroup"] {
            height:42px;gap:0 !important;border:0 !important;border-radius:0 !important;
            background:transparent !important;
        }
        .st-key-learning_section_bar [role="radio"],
        .st-key-learning_section_bar button {
            height:42px;min-height:42px;padding:.15rem .75rem !important;
            border:0 !important;border-radius:0 !important;background:transparent !important;
            box-shadow:none !important;color:#475569 !important;font-weight:560;
        }
        .st-key-learning_section_bar [role="radio"][aria-checked="true"],
        .st-key-learning_section_bar button[aria-checked="true"] {
            color:#18794e !important;box-shadow:inset 0 -2px 0 #1f7a54 !important;
        }
        .st-key-learning_section_bar [data-testid="stCaptionContainer"] {display:none;}
        .st-key-learning_explanation_header {
            min-height:42px;padding:.22rem 1rem;margin:0;border-bottom:1px solid #e5e7eb;
            background:#fff;box-sizing:border-box;
        }
        .st-key-learning_explanation_header > [data-testid="stVerticalBlock"] {gap:0;}
        .pa-explanation-panel-title {
            color:#172033;font-size:.8rem;font-weight:700;line-height:2rem;white-space:nowrap;
        }
        .st-key-learning_explanation_header [role="radiogroup"] {
            min-height:32px;border-color:#e2e8f0;background:#f8fafc;
        }
        .pa-learning-section-kicker {
            color:#2563eb;font-size:.7rem;font-weight:700;letter-spacing:.04em;margin-bottom:.18rem;
        }
        .pa-learning-section-title {
            color:#172033;font-size:1.18rem;line-height:1.4;margin:.04rem 0 .32rem;
        }
        .pa-learning-section-overview {
            color:#475569;font-size:.84rem;line-height:1.65;padding-bottom:.75rem;margin-bottom:.2rem;
            border-bottom:1px solid #eef2f7;
        }
        .pa-learning-block-heading {
            color:#64748b;font-size:.7rem;font-weight:750;letter-spacing:.05em;
            text-transform:uppercase;margin:.8rem 0 .1rem;
        }
        .pa-learning-key {
            display:inline-flex;padding:.1rem .35rem;margin-bottom:.34rem;
            border:1px solid #c7d2fe; border-radius:5px; background:#eef2ff;
            color:#4338ca;font-size:.64rem;font-weight:650;
        }
        div[class*="st-key-learning_point_"] {
            position:relative;padding:.72rem .25rem .78rem .72rem;
            border-bottom:1px solid #e8edf3;
        }
        .pa-learning-point-marker {display:none;}
        .pa-learning-point-marker.is-active {
            display:block;position:absolute;left:0;top:.7rem;bottom:.7rem;width:3px;
            border-radius:2px;background:#2563eb;
        }
        .pa-learning-point-title {
            margin:.04rem 0 .3rem;color:#172033;font-size:.92rem;font-weight:650;line-height:1.45;
        }
        .pa-learning-point-title.is-active {color:#1d4ed8;}
        div[class*="st-key-learning_point_"] p {
            color:#475569;font-size:.82rem;line-height:1.62;margin-bottom:.3rem;
        }
        div[class*="st-key-learning_point_"] [data-testid="stBaseButton-tertiary"] {
            min-height:1.8rem;padding:.15rem .35rem;color:#2563eb;font-size:.7rem;
            background:#f8fbff;border:1px solid #dbeafe;border-radius:999px;
        }
        div[class*="st-key-learning_point_"] [data-testid="stBaseButton-tertiary"]:hover {
            color:#1d4ed8;background:#eff6ff;border-color:#bfdbfe;
        }
        .st-key-learning_section_support {padding:.15rem .2rem .55rem;}
        .pa-learning-guide {
            display:flex;flex-direction:column;gap:.22rem;padding:.65rem .72rem;
            border-radius:8px;background:#f8fafc;color:#475569;
        }
        .pa-learning-guide strong {color:#334155;font-size:.72rem;}
        .pa-learning-guide span {font-size:.78rem;line-height:1.55;}
        .pa-learning-concepts-label,.pa-learning-recommend-label {
            color:#64748b;font-size:.7rem;font-weight:700;margin:.72rem 0 .35rem;
        }
        .pa-learning-concepts {display:flex;gap:.35rem;flex-wrap:wrap;}
        .pa-learning-concepts span {
            display:inline-flex;max-width:100%;padding:.2rem .45rem;border:1px solid #e2e8f0;
            border-radius:999px;background:#fff;color:#475569;font-size:.68rem;
            white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
        }
        .st-key-learning_section_support [data-testid="stBaseButton-tertiary"] {
            justify-content:flex-start;min-height:1.85rem;padding:.18rem .2rem;
            color:#475569;font-size:.73rem;text-align:left;
        }
        .st-key-learning_section_support [data-testid="stBaseButton-tertiary"]:hover {
            color:#1d4ed8;background:#f8fafc;
        }
        .st-key-learning_section_followup {
            position:relative;z-index:6;flex:0 0 auto;padding:.45rem 1rem .7rem;
            background:linear-gradient(to bottom,rgba(255,255,255,.72),#fff 28%);
        }
        div[data-testid="stForm"]:has(.pa-learning-followup-form-marker) {
            border:1px solid #dbe4ee;padding:.45rem;background:#fff;border-radius:10px;
            box-shadow:0 -5px 16px rgba(15,23,42,.06);
        }
        .pa-learning-source-text {
            padding:.85rem; margin-bottom:.75rem; border-left:3px solid #0ea5e9;
            border-radius:0 8px 8px 0; background:#f7fbff; color:#334155;
            font-size:.84rem; line-height:1.6; white-space:pre-wrap; overflow-wrap:anywhere;
        }
        .pa-learning-context-text {
            color:#475569; font-size:.8rem; line-height:1.55;
            white-space:pre-wrap; overflow-wrap:anywhere;
        }
        [class*="st-key-learning_report_scroll_"],
        [class*="st-key-learning_page_context_scroll_"] {
            min-width:0;padding:.78rem 1rem 1rem;box-sizing:border-box;
            overscroll-behavior-y:auto;
        }
        [data-testid="stHorizontalBlock"]:has(.st-key-learning_source_panel)
        > [data-testid="stColumn"]:has([class*="st-key-learning_report_scroll_"]),
        [data-testid="stHorizontalBlock"]:has(.st-key-learning_source_panel)
        > [data-testid="stColumn"]:has([class*="st-key-learning_page_context_scroll_"]) {
            position:relative;min-height:0;border:1px solid #dbe4ee;border-radius:10px;
            background:#fff;overflow:hidden;
        }
        [data-testid="stHorizontalBlock"]:has(.st-key-learning_source_panel)
        > [data-testid="stColumn"]:has([class*="st-key-learning_report_scroll_"])
        > [data-testid="stVerticalBlock"],
        [data-testid="stHorizontalBlock"]:has(.st-key-learning_source_panel)
        > [data-testid="stColumn"]:has([class*="st-key-learning_page_context_scroll_"])
        > [data-testid="stVerticalBlock"] {
            position:absolute;inset:0;min-height:0;
        }
        [data-testid="stLayoutWrapper"]:has(> [class*="st-key-learning_report_scroll_"]),
        [data-testid="stLayoutWrapper"]:has(> [class*="st-key-learning_page_context_scroll_"]) {
            flex:1 1 0 !important;min-height:0 !important;
        }
        [class*="st-key-learning_report_scroll_"],
        [class*="st-key-learning_page_context_scroll_"] {
            height:100% !important;min-height:0 !important;overflow-y:auto !important;
        }
        [class*="st-key-learning_report_scroll_"] p,
        [class*="st-key-learning_page_context_scroll_"] p {line-height:1.65;}
        .pa-page-relation {
            display:flex;flex-direction:column;gap:.28rem;padding:.72rem .8rem;margin:.3rem 0 .7rem;
            border-left:3px solid #2563eb;border-radius:0 8px 8px 0;background:#f8fafc;
            color:#475569;font-size:.78rem;line-height:1.58;
        }
        .pa-page-relation strong {color:#1e293b;font-size:.72rem;}
        .pa-page-point-section {
            color:#2563eb;font-size:.66rem;font-weight:700;margin:0 0 .18rem;
        }
        div[class*="st-key-learning_page_point_"] {
            padding:.72rem .15rem .82rem;border-bottom:1px solid #e8edf3;
        }
        .pa-logic-node {
            position:relative;padding:.5rem .25rem .15rem .85rem;border-left:2px solid #dbeafe;
        }
        .pa-logic-node span {
            display:block;color:#2563eb;font-size:.64rem;font-weight:750;margin-bottom:.12rem;
        }
        .pa-logic-node strong {color:#172033;font-size:.8rem;line-height:1.4;}
        .pa-logic-node p {color:#64748b;font-size:.74rem;line-height:1.5;margin:.2rem 0 0;}
        div[class*="st-key-learning_page_point_"] [data-testid="stBaseButton-tertiary"],
        [class*="st-key-learning_page_context_scroll_"] [data-testid="stBaseButton-tertiary"] {
            min-height:1.8rem;padding:.16rem .38rem;border:1px solid #dbeafe;
            border-radius:999px;background:#f8fbff;color:#2563eb;font-size:.68rem;
        }
        .st-key-learning_nav_panel {
            position:sticky;top:4rem;align-self:flex-start;
        }
        .st-key-learning_source_panel,.st-key-qa_source_panel {
            position:relative;top:auto;align-self:flex-start;
        }
        .st-key-learning_source_panel {
            padding:.45rem;border:1px solid #dbe4ee;background:#eef1f5;border-radius:10px;
        }
        .st-key-learning_pdf_toolbar,.st-key-qa_pdf_toolbar {
            position:sticky;top:6.7rem;z-index:8;padding:.28rem .35rem;
            border-bottom:1px solid #e2e8f0;background:rgba(255,255,255,.96);
            backdrop-filter:blur(8px);
        }
        .st-key-learning_pdf_toolbar button,
        .st-key-qa_pdf_toolbar button {
            min-height:2rem;padding:.18rem .3rem;white-space:nowrap;
        }
        .st-key-learning_pdf_toolbar button p,
        .st-key-qa_pdf_toolbar button p {font-size:.7rem;white-space:nowrap;}
        .pa-pdf-panel-title {
            display:flex;align-items:baseline;gap:.2rem;font-weight:700;color:#172033;
            margin:0;line-height:2.25rem;
        }
        .pa-pdf-panel-title span {font-size:.78rem;font-weight:400;color:#64748b;}
        .pa-pdf-page-total {
            color:#64748b;font-size:.7rem;line-height:2rem;white-space:nowrap;
        }
        .pa-pdf-zoom {color:#64748b;font-size:.72rem;text-align:center;line-height:2.25rem;white-space:nowrap;}
        .st-key-learning_source_panel [data-testid="stImage"] img,
        .st-key-qa_source_panel [data-testid="stImage"] img {
            width:100%;max-height:min(72vh,900px);object-fit:contain;
            border:1px solid #e2e8f0;border-radius:7px;background:#fff;
        }
        .st-key-qa_history_scroll {
            max-height:calc(100vh - 25rem);min-height:14rem;
            overflow-y:auto;overscroll-behavior:contain;
            padding-right:.5rem;scrollbar-gutter:stable;
        }
        .st-key-qa_conversation_panel {
            position:sticky;top:6.75rem;align-self:flex-start;
            padding:.1rem 0 .35rem;
        }
        .pa-qa-intro {
            display:flex;align-items:center;gap:.55rem;padding:.72rem .9rem;margin:.35rem 0 1rem;
            border:1px solid #dbeafe;border-radius:9px;background:#f8fbff;color:#475569;font-size:.84rem;
        }
        .pa-qa-question {
            padding:.65rem .8rem;border-radius:9px;background:#f1f5f9;color:#1e293b;
            font-weight:600;line-height:1.5;margin-bottom:.65rem;
        }
        .pa-qa-answer-head {display:flex;align-items:center;gap:.5rem;margin-bottom:.45rem;}
        .pa-qa-answer-label {font-size:.76rem;font-weight:700;color:#047857;}
        .pa-qa-answer {color:#334155;line-height:1.7;margin-bottom:.55rem;}
        .pa-qa-citation-count {color:#64748b;font-size:.76rem;margin:.25rem 0 .45rem;}
        .pa-answer-conclusion {
            margin-top:.72rem;padding-top:.72rem;border-top:1px solid #e2e8f0;
        }
        .pa-answer-support {
            display:inline-flex;padding:.14rem .42rem;border-radius:999px;
            font-size:.67rem;font-weight:720;line-height:1.35;
        }
        .pa-answer-support.is-direct {background:#ecfdf5;color:#047857;}
        .pa-answer-support.is-inference {background:#fff7ed;color:#c2410c;}
        .pa-answer-conclusion-text {
            margin:.38rem 0 .45rem;color:#172033;font-size:.88rem;font-weight:650;line-height:1.65;
        }
        .pa-answer-evidence {
            margin:.16rem 0;padding:.48rem .58rem;border-left:2px solid #93c5fd;
            border-radius:0 6px 6px 0;background:#f8fafc;color:#475569;
            font-size:.73rem;line-height:1.55;
        }
        .pa-answer-evidence span {
            display:block;margin-bottom:.12rem;color:#2563eb;font-size:.63rem;font-weight:700;
        }
        .st-key-qa_selected_quote {
            border-color:#bfdbfe !important;background:#f8fbff;margin-bottom:.7rem;
        }
        .pa-selected-quote-label {
            color:#2563eb;font-size:.73rem;font-weight:700;margin-bottom:.25rem;
        }
        .pa-selected-quote {
            color:#334155;font-size:.84rem;line-height:1.55;
            display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden;
        }
        div[data-testid="stForm"]:has(.pa-qa-form-marker) {
            position:sticky;bottom:0;z-index:5;margin-top:.65rem;
            border:1px solid #dbe4ee;padding:.55rem;background:#fff;
            border-radius:10px;box-shadow:0 -6px 18px rgba(15,23,42,.06);
        }
        .st-key-joint_pdf_panel,.st-key-joint_code_panel,.st-key-joint_conversation_panel {
            align-self:flex-start;padding:.1rem .65rem .45rem;min-width:0;
        }
        .st-key-joint_code_panel,.st-key-joint_conversation_panel {border-left:1px solid #e2e8f0;}
        .st-key-joint_pdf_panel,.st-key-joint_conversation_panel {
            max-height:min(80vh,1020px);overflow-y:auto;overscroll-behavior:contain;
            scrollbar-gutter:stable;
        }
        .st-key-joint_conversation_panel {
            padding-bottom:.3rem;
        }
        .pa-code-viewer {
            height:clamp(360px,calc(78vh - 9.5rem),780px);
            overflow:auto;overscroll-behavior:contain;
            border:1px solid #dbe4ee;border-radius:8px;background:#0f172a;
            padding:.6rem 0;font:12px/1.62 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
            scrollbar-gutter:stable;
        }
        .pa-code-line {display:flex;min-width:max-content;color:#dbeafe;padding:0 .8rem;}
        .pa-code-line:hover {background:#172554;}
        .pa-code-line.is-active {background:rgba(250,204,21,.22);box-shadow:inset 3px 0 #facc15;}
        .pa-code-number {
            width:3.2rem;flex:0 0 3.2rem;text-align:right;margin-right:1rem;
            color:#64748b;user-select:none;
        }
        .pa-code-line code {color:inherit;background:transparent;padding:0;white-space:pre;}
        div[data-testid="stForm"]:has(.pa-joint-form-marker) {
            position:sticky;bottom:.15rem;z-index:5;margin:.55rem 0 .2rem;
            border:1px solid #bfdbfe;padding:.45rem;background:rgba(255,255,255,.97);
            border-radius:10px;box-shadow:0 -6px 18px rgba(15,23,42,.06);
        }
        .st-key-joint_conversation_panel:has(.pa-joint-pending-marker)
        div[data-testid="stForm"]:has(.pa-joint-form-marker) {
            display:block !important;
            opacity:.58;
            pointer-events:none;
            filter:saturate(.55);
        }
        .st-key-joint_conversation_panel:has(.pa-joint-pending-marker)
        .st-key-joint_current_context,
        .st-key-joint_conversation_panel:has(.pa-joint-pending-marker)
        .st-key-explain-current-code-selection,
        .st-key-joint_conversation_panel:has(.pa-joint-pending-marker)
        .st-key-relate-current-code-selection {
            display:none !important;
        }
        div[data-testid="stForm"]:has(.pa-joint-form-marker) textarea {
            min-height:3rem !important;border:0 !important;box-shadow:none !important;
        }
        div[class*="st-key-joint_message_"] {
            margin:.35rem 0 .75rem;padding:.72rem .78rem .68rem;
            border:1px solid #dbe4ee;border-top:2px solid #dbeafe;
            border-radius:10px;background:#fff;box-shadow:0 2px 8px rgba(15,23,42,.035);
        }
        div[class*="st-key-joint_message_selection_"],
        .st-key-joint_pending_selection {
            margin:0 0 .55rem;padding:0 0 .55rem;border-bottom:1px solid #e2e8f0;
        }
        .pa-message-selection-title {
            display:flex;align-items:center;justify-content:space-between;gap:.55rem;
            margin:0 0 .32rem;color:#475569;font-size:.67rem;
        }
        .pa-message-selection-title span {
            min-width:0;color:#64748b;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
            overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
        }
        div[class*="st-key-joint_message_selection_"] [data-testid="stCode"],
        .st-key-joint_pending_selection [data-testid="stCode"] {margin:0;}
        div[class*="st-key-joint_message_selection_"] [data-testid="stCode"] pre,
        .st-key-joint_pending_selection [data-testid="stCode"] pre {
            font-size:.69rem;line-height:1.52;
        }
        .pa-assistant-user {
            margin:0 0 .45rem;padding:.48rem .58rem;border-radius:7px;
            background:#f1f5f9;color:#172033;font-size:.82rem;font-weight:680;line-height:1.5;
        }
        .pa-assistant-user span {
            display:inline-flex;margin-right:.38rem;padding:.08rem .3rem;border-radius:4px;
            background:#dbeafe;color:#1d4ed8;font-size:.6rem;font-weight:750;vertical-align:.08rem;
        }
        .pa-assistant-meta {
            display:inline-flex;margin:.12rem 0 .48rem;padding:.13rem .4rem;
            border-radius:999px;background:#ecfdf5;color:#047857;
            font-size:.64rem;font-weight:700;
        }
        div[class*="st-key-joint_answer_body_"] {
            color:#334155;font-size:.83rem;line-height:1.78;
        }
        div[class*="st-key-joint_answer_body_"] p {margin:.15rem 0 .55rem;}
        div[class*="st-key-joint_answer_body_"] ul,
        div[class*="st-key-joint_answer_body_"] ol {
            margin:.28rem 0 .58rem;padding-left:1.25rem;
        }
        div[class*="st-key-joint_answer_body_"] li {margin:.2rem 0;padding-left:.12rem;}
        div[class*="st-key-joint_answer_body_"] li::marker {
            color:#2563eb;font-weight:750;
        }
        div[class*="st-key-joint_answer_body_"] code {
            padding:0 .05rem;border:0;background:transparent;color:#0f766e;
            font-size:.75rem;font-weight:560;overflow-wrap:anywhere;
        }
        div[class*="st-key-joint_answer_body_"] pre {
            margin:.42rem 0 .68rem;padding:.68rem .75rem;overflow-x:hidden;
            border:1px solid #1e293b;border-radius:7px;background:#0f172a;
            box-shadow:inset 3px 0 #2563eb;font-size:.71rem;line-height:1.62;
        }
        div[class*="st-key-joint_answer_body_"] pre code {
            padding:0;border:0;background:transparent;color:#dbeafe;
            white-space:pre-wrap;overflow-wrap:anywhere;word-break:break-word;
        }
        .pa-reference-heading {
            display:flex;align-items:center;gap:.38rem;margin:.58rem 0 .32rem;
            color:#475569;font-size:.67rem;font-weight:720;
        }
        .pa-reference-heading span {color:#94a3b8;font-weight:500;}
        .pa-reference-heading::after {
            content:"";height:1px;flex:1;background:#e2e8f0;
        }
        div[class*="st-key-joint_paper_refs_"] [data-testid="stButton"] button,
        div[class*="st-key-joint_code_refs_"] [data-testid="stButton"] button {
            justify-content:flex-start;min-height:2rem;padding:.3rem .48rem;
            border:1px solid #dbe4ee;border-radius:6px;background:#f8fafc;color:#334155;
            box-shadow:none;text-align:left;
        }
        div[class*="st-key-joint_paper_refs_"] [data-testid="stButton"] button:hover,
        div[class*="st-key-joint_code_refs_"] [data-testid="stButton"] button:hover {
            border-color:#93c5fd;background:#eff6ff;color:#1d4ed8;
        }
        div[class*="st-key-joint_paper_refs_"] [data-testid="stButton"] button p,
        div[class*="st-key-joint_code_refs_"] [data-testid="stButton"] button p {
            overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:.67rem;
        }
        div[class*="st-key-joint_code_refs_"] [data-testid="stButton"] button p {
            font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
        }
        .pa-context-title {color:#64748b;font-size:.7rem;font-weight:700;text-transform:uppercase;letter-spacing:.04em;}
        .pa-context-chips {display:flex;gap:.35rem;flex-wrap:wrap;margin:.2rem 0 .45rem;}
        .pa-context-chips span {
            display:inline-flex;max-width:100%;padding:.22rem .48rem;border:1px solid #bfdbfe;
            border-radius:999px;background:#eff6ff;color:#1d4ed8;font-size:.68rem;
            white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
        }
        .st-key-joint_current_context {
            margin:.35rem 0 .7rem;padding:.58rem .65rem .65rem;
            border:1px solid #dbe4ee;border-radius:9px;background:#f8fafc;
        }
        .st-key-joint_current_context [data-testid="stCaptionContainer"] {
            margin:.05rem 0 .3rem;color:#64748b;
        }
        .st-key-joint_current_context [data-testid="stCode"] {
            margin:0;
        }
        .st-key-joint_current_context [data-testid="stCode"] pre {
            font-size:.71rem;line-height:1.58;
        }
        .st-key-joint_selected_context {
            padding:.55rem .65rem;margin:.35rem 0;border:1px solid #bfdbfe;
            border-radius:9px;background:#f8fbff;
        }
        .st-key-joint_conversation_panel [data-testid="stPills"] {margin:.25rem 0;}
        [data-testid="stBaseButton-primary"] {
            background:#2563eb;border-color:#2563eb;color:#fff;
        }
        [data-testid="stBaseButton-primary"]:hover {
            background:#1d4ed8;border-color:#1d4ed8;color:#fff;
        }
        @media (prefers-color-scheme: dark) {
            [data-testid="stMetric"],.pa-audit-card,
            div[data-testid="stVerticalBlockBorderWrapper"]:has(.pa-learning-nav-marker),
            div[data-testid="stVerticalBlockBorderWrapper"]:has(.pa-learning-source-marker),
            div[data-testid="stVerticalBlockBorderWrapper"]:has(.pa-learning-point-marker) {
                background:#1e293b; border-color:#334155;
            }
            .pa-learning-hero {background:linear-gradient(135deg,#172554,#1e293b); border-color:#334155;}
            .pa-header-title,.pa-learning-title,.pa-workspace-title,.pa-panel-title,
            .pa-grade-title,.pa-audit-claim {color:#f8fafc;}
            .pa-learning-summary,.pa-audit-explanation,.pa-learning-context-text {color:#cbd5e1;}
            .pa-audit-summary,
            div[data-testid="stExpander"]:has(.pa-audit-detail) {
                background:#111827;border-color:#334155;
            }
            .pa-audit-summary-grade {border-color:#334155;}
            .pa-audit-summary-score,.pa-audit-summary-metric strong,
            .pa-audit-empty strong {color:#f8fafc;}
            .pa-audit-summary-metric,.pa-audit-empty-inline,.pa-audit-empty {
                background:#1e293b;color:#cbd5e1;border-color:#475569;
            }
            div[data-testid="stExpander"]:has(.pa-audit-detail) summary,
            .pa-audit-detail,.pa-audit-evidence-text {color:#e2e8f0;}
            .pa-audit-detail-section {border-color:#334155;}
            .pa-audit-detail-copy {color:#cbd5e1;}
            .pa-audit-evidence-item {background:#0f172a;border-color:#38bdf8;}
            .pa-pdf-panel-title {color:#f8fafc;}
            .st-key-learning_primary_nav,
            .st-key-learning_section_bar {background:rgba(15,23,42,.97);border-color:#334155;}
            .st-key-learning_explanation_header {background:#111827;border-color:#334155;}
            .pa-explanation-panel-title {color:#f8fafc;}
            .pa-learning-section-title {color:#f8fafc;}
            .pa-learning-section-overview {color:#cbd5e1;border-color:#334155;}
            .pa-learning-point-title {color:#f8fafc;}
            .pa-learning-point-title.is-active {color:#93c5fd;}
            div[class*="st-key-learning_point_"] {border-color:#334155;}
            div[class*="st-key-learning_point_"] p {color:#cbd5e1;}
            .pa-learning-guide {background:#0f172a;color:#cbd5e1;}
            .pa-learning-guide strong {color:#e2e8f0;}
            .pa-page-relation {background:#0f172a;color:#cbd5e1;border-color:#3b82f6;}
            .pa-page-relation strong,.pa-logic-node strong {color:#e2e8f0;}
            .pa-logic-node {border-color:#334155;}
            .pa-logic-node p {color:#94a3b8;}
            .pa-learning-concepts span {background:#1e293b;border-color:#334155;color:#cbd5e1;}
            .st-key-learning_section_followup {
                background:linear-gradient(to bottom,rgba(30,41,59,.72),#1e293b 28%);
            }
            div[data-testid="stForm"]:has(.pa-learning-followup-form-marker) {
                background:#1e293b;border-color:#334155;
            }
            .st-key-learning_source_panel {background:#111827;}
            .st-key-learning_pdf_toolbar,.st-key-qa_pdf_toolbar {
                background:rgba(30,41,59,.96);border-color:#334155;
            }
            .pa-sidebar-title {color:#e2e8f0;}
            .pa-sidebar-library-title {color:#f8fafc;}
            div[class*="st-key-sidebar_project_"]:has(.pa-sidebar-project-marker.is-active) {
                background:#172554;
            }
            div[class*="st-key-sidebar_project_"] [data-testid="stButton"] button:hover {
                background:#1e293b;color:#f8fafc;
            }
            div[class*="st-key-sidebar_project_"] [data-testid="stButton"] button p {
                color:#cbd5e1;
            }
            div[class*="st-key-sidebar_project_"]:has(.pa-sidebar-project-marker.is-active)
            [data-testid="stButton"] button p {color:#93c5fd;}
            .pa-api-status {background:#1e293b;color:#cbd5e1;}
            .pa-storage-status {background:#1e293b;}
            .pa-storage-status strong {color:#e2e8f0;}
            .st-key-storage_setup_shell {background:#1e293b;border-color:#334155;}
            .pa-storage-setup-title,.pa-recent-project-title {color:#f8fafc;}
            div[class*="st-key-recent_project_"] {background:#1e293b;border-color:#334155 !important;}
            .st-key-launch_pdf_upload_empty {background:#172554;border-color:#1e40af;}
            .pa-ready-file,.pa-setup-mode {background:#1e293b;border-color:#334155;}
            .st-key-launch_setup_panel {background:#1e293b;border-color:#334155 !important;}
            .pa-ready-toolbar {border-color:#334155;}
            .pa-upload-title,.pa-ready-file strong,.pa-ready-toolbar strong,
            .pa-setup-heading,.pa-setup-title,.pa-setup-mode strong {color:#f8fafc;}
            .st-key-upload_pdf_preview {background:#111827;}
            .pa-qa-question {background:#0f172a;color:#e2e8f0;}
            .pa-qa-answer,.pa-qa-intro {color:#cbd5e1;}
            .pa-answer-conclusion {border-color:#334155;}
            .pa-answer-conclusion-text {color:#f8fafc;}
            .pa-answer-evidence {background:#0f172a;color:#cbd5e1;border-color:#3b82f6;}
            .pa-selected-quote {color:#cbd5e1;}
            .st-key-qa_selected_quote {background:#172554;border-color:#334155 !important;}
            div[data-testid="stForm"]:has(.pa-qa-form-marker) {
                background:#1e293b;border-color:#334155;
            }
            div[data-testid="stForm"]:has(.pa-joint-form-marker) {
                background:#1e293b;border-color:#334155;
            }
            div[class*="st-key-joint_message_"] {background:#1e293b;border-color:#334155;}
            .pa-assistant-user {background:#0f172a;color:#e2e8f0;}
            .pa-assistant-user span {background:#172554;color:#93c5fd;}
            .pa-assistant-meta {background:#052e16;color:#6ee7b7;}
            div[class*="st-key-joint_answer_body_"] {color:#cbd5e1;}
            div[class*="st-key-joint_answer_body_"] code {
                background:transparent;color:#86efac;border:0;
            }
            div[class*="st-key-joint_answer_body_"] pre {background:#020617;border-color:#334155;}
            div[class*="st-key-joint_answer_body_"] pre code {
                background:transparent;color:#dbeafe;border:0;
            }
            .pa-reference-heading {color:#cbd5e1;}
            .pa-reference-heading::after {background:#334155;}
            div[class*="st-key-joint_paper_refs_"] [data-testid="stButton"] button,
            div[class*="st-key-joint_code_refs_"] [data-testid="stButton"] button {
                background:#0f172a;border-color:#334155;color:#cbd5e1;
            }
            .pa-context-chips span {background:#172554;border-color:#1e40af;color:#bfdbfe;}
            .st-key-joint_selected_context {background:#172554;border-color:#334155;}
            .st-key-joint_code_panel,.st-key-joint_conversation_panel {border-color:#334155;}
            .pa-qa-intro {background:#172554;border-color:#334155;}
            .pa-learning-source-text,.pa-evidence {background:#0f172a; color:#cbd5e1;}
        }
        @media (max-width:1350px) {
            .pa-workspace-summary {display:none;}
            .pa-workspace-title {max-width:100%;}
            .st-key-learning_primary_nav > [data-testid="stLayoutWrapper"]
            > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child {
                flex:1 1 250px !important;
            }
            .st-key-learning_primary_nav > [data-testid="stLayoutWrapper"]
            > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2) {
                flex:0 1 360px !important;width:360px !important;
            }
            .st-key-learning_primary_nav > [data-testid="stLayoutWrapper"]
            > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:last-child {
                flex:0 0 120px !important;width:120px !important;
            }
        }
        @media (max-width:700px) {
            .pa-audit-summary {align-items:flex-start;gap:.6rem;padding:.65rem;}
            .pa-audit-summary-grade {
                flex:1 1 100%;min-width:0;padding:0 0 .5rem;border-right:0;
                border-bottom:1px solid #e2e8f0;
            }
            .pa-audit-summary-score {min-width:4rem;font-size:1.25rem;}
            .pa-audit-summary-metrics {flex:1 1 100%;gap:.3rem;}
            .pa-audit-summary-metric {flex:1 1 calc(50% - .3rem);}
            .st-key-audit_advanced_filters > [data-testid="stLayoutWrapper"]
            > [data-testid="stHorizontalBlock"] {flex-wrap:wrap !important;}
            .st-key-audit_advanced_filters > [data-testid="stLayoutWrapper"]
            > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
                flex:1 1 100% !important;width:100% !important;min-width:0 !important;
            }
            div[data-testid="stExpander"]:has(.pa-audit-detail) summary {
                white-space:normal;overflow-wrap:anywhere;
            }
            .pa-audit-evidence-text,.pa-audit-detail-copy,.pa-audit-claim {
                overflow-wrap:anywhere;
            }
            .pa-header {align-items:flex-start; flex-direction:column;}
            .pa-header-badge {display:none;}
            .pa-header-subtitle {white-space:normal;}
            .st-key-storage_setup_shell {margin:1rem auto 0;padding:1.25rem 1rem;}
            .st-key-launch_shell_ready {max-width:100%;}
            .st-key-launch_pdf_upload_empty {padding:1rem .75rem;}
            .st-key-launch_setup_panel {position:static;min-height:auto;}
            .st-key-upload_pdf_preview [data-testid="stHorizontalBlock"] {
                flex-wrap:nowrap !important;gap:.2rem !important;overflow-x:auto;
            }
            .st-key-upload_pdf_preview [data-testid="stColumn"] {
                flex:0 0 2.2rem !important;width:2.2rem !important;min-width:2.2rem !important;
            }
            .st-key-upload_pdf_preview [data-testid="stColumn"]:first-child {
                flex-basis:7rem !important;width:7rem !important;min-width:7rem !important;
            }
            .st-key-upload_pdf_preview [data-testid="stColumn"]:nth-child(3),
            .st-key-upload_pdf_preview [data-testid="stColumn"]:nth-child(6) {
                flex-basis:3rem !important;width:3rem !important;min-width:3rem !important;
            }
            .st-key-upload_pdf_preview [data-testid="stColumn"]:nth-child(8) {
                flex-basis:5rem !important;width:5rem !important;min-width:5rem !important;
            }
            div[data-testid="stVerticalBlockBorderWrapper"]:has(.pa-learning-nav-marker),
            div[data-testid="stVerticalBlockBorderWrapper"]:has(.pa-learning-source-marker) {position:static;}
            .st-key-qa_history_scroll {
                height:auto;max-height:none;overflow:visible;padding-right:0;
            }
            .st-key-learning_nav_panel,.st-key-learning_source_panel,.st-key-qa_source_panel,
            .st-key-qa_conversation_panel {
                position:static;
            }
            [data-testid="stHorizontalBlock"]:has(.st-key-learning_source_panel)
            > [data-testid="stColumn"]:has([class*="st-key-learning_report_scroll_"]),
            [data-testid="stHorizontalBlock"]:has(.st-key-learning_source_panel)
            > [data-testid="stColumn"]:has([class*="st-key-learning_page_context_scroll_"]) {
                position:static;
            }
            [data-testid="stHorizontalBlock"]:has(.st-key-learning_source_panel)
            > [data-testid="stColumn"]:has([class*="st-key-learning_report_scroll_"])
            > [data-testid="stVerticalBlock"],
            [data-testid="stHorizontalBlock"]:has(.st-key-learning_source_panel)
            > [data-testid="stColumn"]:has([class*="st-key-learning_page_context_scroll_"])
            > [data-testid="stVerticalBlock"] {
                position:static;
            }
            [class*="st-key-learning_report_scroll_"],
            [class*="st-key-learning_page_context_scroll_"] {
                height:auto !important;overflow:visible !important;
            }
            .pa-code-viewer {height:62vh;}
            .st-key-joint_pdf_panel,.st-key-joint_conversation_panel {
                max-height:none;overflow:visible;
            }
            .st-key-joint_pdf_panel,.st-key-joint_code_panel,.st-key-joint_conversation_panel {
                border-left:0;padding:.15rem 0 .45rem;
            }
            .st-key-joint_pdf_panel [data-testid="stHorizontalBlock"] {
                flex-wrap:nowrap !important;gap:.35rem !important;
            }
            .st-key-joint_pdf_panel [data-testid="stColumn"] {
                min-width:0 !important;
            }
            .pa-workspace-title,.pa-workspace-summary {white-space:normal;}
            section[data-testid="stSidebar"]:not([aria-expanded="false"]) {
                width:260px !important;min-width:260px !important;
            }
            .st-key-learning_pdf_toolbar [data-testid="stHorizontalBlock"],
            .st-key-qa_pdf_toolbar [data-testid="stHorizontalBlock"] {
                flex-wrap:nowrap !important;gap:.2rem !important;overflow-x:auto;
            }
            .st-key-learning_pdf_toolbar [data-testid="stColumn"],
            .st-key-qa_pdf_toolbar [data-testid="stColumn"] {
                flex:0 0 2.2rem !important;width:2.2rem !important;min-width:2.2rem !important;
            }
            .st-key-learning_pdf_toolbar [data-testid="stColumn"]:first-child,
            .st-key-qa_pdf_toolbar [data-testid="stColumn"]:first-child {
                flex-basis:5.2rem !important;width:5.2rem !important;min-width:5.2rem !important;
            }
            .st-key-learning_pdf_toolbar [data-testid="stColumn"]:nth-child(3),
            .st-key-qa_pdf_toolbar [data-testid="stColumn"]:nth-child(3),
            .st-key-learning_pdf_toolbar [data-testid="stColumn"]:nth-child(6),
            .st-key-qa_pdf_toolbar [data-testid="stColumn"]:nth-child(6) {
                flex-basis:3rem !important;width:3rem !important;min-width:3rem !important;
            }
            .st-key-learning_pdf_toolbar [data-testid="stColumn"]:last-child,
            .st-key-qa_pdf_toolbar [data-testid="stColumn"]:last-child {
                flex-basis:4.8rem !important;width:4.8rem !important;min-width:4.8rem !important;
            }
            .st-key-learning_section_bar [role="radiogroup"] {
                flex-wrap:nowrap !important;overflow-x:auto;justify-content:flex-start !important;
            }
            .st-key-learning_section_bar [role="radio"] {flex:0 0 auto !important;}
        }
        @media (max-height:760px) {
            .st-key-qa_history_scroll {height:auto;max-height:none;overflow:visible;}
            .st-key-qa_conversation_panel {position:static;}
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
