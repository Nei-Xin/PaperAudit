from __future__ import annotations

import streamlit as st


def inject_custom_styles() -> None:
    st.markdown(
        """
        <style>
        /* ── Design Tokens ─────────────────────────────────── */
        :root {
          /* Brand / Accent */
          --pa-primary: #2563eb;
          --pa-primary-hover: #1d4ed8;
          --pa-primary-surface: #eff6ff;
          --pa-primary-light: #dbeafe;
          --pa-primary-border: #bfdbfe;
          --pa-primary-dark: #1e40af;
          --pa-primary-action: #1677ff;

          /* Semantic – Success */
          --pa-success: #22c55e;
          --pa-success-dark: #047857;
          --pa-success-surface: #ecfdf5;
          --pa-success-light: #dcfce7;
          --pa-success-text: #065f46;
          --pa-success-muted: #087443;

          /* Semantic – Warning */
          --pa-warning: #f59e0b;
          --pa-warning-dark: #b45309;
          --pa-warning-surface: #fef3c7;
          --pa-warning-text: #92400e;

          /* Semantic – Danger */
          --pa-danger: #ef4444;
          --pa-danger-dark: #b91c1c;
          --pa-danger-surface: #fee2e2;
          --pa-danger-text: #991b1b;

          /* Neutral – Text */
          --pa-text-primary: #0f172a;
          --pa-text-heading: #172033;
          --pa-text-body: #334155;
          --pa-text-secondary: #475569;
          --pa-text-muted: #64748b;
          --pa-text-faint: #94a3b8;
          --pa-text-placeholder: #8a96a8;

          /* Neutral – Surfaces */
          --pa-bg: #ffffff;
          --pa-bg-page: #fbfcfe;
          --pa-surface: #f8fafc;
          --pa-surface-alt: #f1f5f9;
          --pa-surface-raised: #fff;
          --pa-surface-code: #0f172a;

          /* Neutral – Borders */
          --pa-border: #e2e8f0;
          --pa-border-light: #eef2f7;
          --pa-border-medium: #dbe4ee;
          --pa-border-strong: #cbd5e1;
          --pa-border-panel: #dee5ed;
          --pa-border-divider: #e5e7eb;
          --pa-border-sidebar: #e5eaf0;
          --pa-border-item: #edf1f5;

          /* Cyan / Evidence accent */
          --pa-cyan: #0ea5e9;
          --pa-cyan-light: #38bdf8;
          --pa-cyan-surface: #f7fbff;
          --pa-cyan-border: #93c5fd;

          /* Spacing */
          --pa-space-2xs: 0.12rem;
          --pa-space-xs: 0.25rem;
          --pa-space-sm: 0.5rem;
          --pa-space-md: 0.75rem;
          --pa-space-lg: 1rem;
          --pa-space-xl: 1.5rem;
          --pa-space-2xl: 2rem;

          /* Radius */
          --pa-radius-xs: 4px;
          --pa-radius-sm: 6px;
          --pa-radius-md: 8px;
          --pa-radius-lg: 10px;
          --pa-radius-xl: 12px;
          --pa-radius-pill: 999px;

          /* Shadows */
          --pa-shadow-xs: 0 1px 2px rgba(15,23,42,.04);
          --pa-shadow-sm: 0 2px 8px rgba(15,23,42,.035);
          --pa-shadow-md: 0 4px 12px rgba(15,23,42,.06);
          --pa-shadow-lg: 0 18px 50px rgba(15,23,42,.08);
          --pa-shadow-up: 0 -6px 18px rgba(15,23,42,.06);

          /* Transitions */
          --pa-transition-fast: 0.12s ease;
          --pa-transition-normal: 0.18s ease;
          --pa-transition-slow: 0.28s ease;

          /* Font stacks */
          --pa-font-mono: ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
        }

        /* ── Global Transitions ─────────────────────────────── */
        .pa-sidebar-project-marker,
        .pa-evidence-chip,
        .pa-point-card,
        .pa-badge,
        .pa-learning-nav-link,
        .pa-learning-key,
        .pa-context-chips span,
        .pa-learning-concepts span,
        .pa-answer-support,
        [data-testid="stBaseButton-primary"],
        [data-testid="stBaseButton-tertiary"] {
            transition: background var(--pa-transition-fast),
                        color var(--pa-transition-fast),
                        border-color var(--pa-transition-fast),
                        box-shadow var(--pa-transition-fast),
                        transform var(--pa-transition-fast);
        }
        div[class*="st-key-sidebar_project_"] [data-testid="stButton"] button,
        .st-key-joint_code_file_tree [data-testid="stButton"] button,
        .st-key-joint_code_file_tree [data-testid="stExpander"] details summary,
        div[class*="st-key-joint_paper_refs_"] [data-testid="stButton"] button,
        div[class*="st-key-joint_code_refs_"] [data-testid="stButton"] button,
        div[class*="st-key-learning_point_"] [data-testid="stBaseButton-tertiary"],
        .st-key-learning_section_support [data-testid="stBaseButton-tertiary"] {
            transition: background var(--pa-transition-fast),
                        color var(--pa-transition-fast),
                        border-color var(--pa-transition-fast);
        }

        /* ── Status indicator pulse ─────────────────────────── */
        @keyframes pa-pulse {
            0%, 100% { box-shadow: 0 0 0 3px var(--pa-success-light); }
            50% { box-shadow: 0 0 0 5px rgba(34,197,94,0); }
        }

        /* ── Skeleton shimmer for loading states ────────────── */
        @keyframes pa-shimmer {
            0% { background-position: 200% 0; }
            100% { background-position: -200% 0; }
        }

        .block-container {
            max-width:1900px;padding:3.1rem 1.25rem 2rem;
        }
        .block-container:has(.st-key-learning_primary_nav) {
            max-width:none !important;width:100% !important;height:100vh;max-height:100vh;
            margin:0 !important;padding:0 .5rem !important;overflow:hidden;
        }
        /* Keep Streamlit's native header available so a collapsed project sidebar
           can always be reopened. The learning header remains the visual header. */
        body:has(.st-key-learning_primary_nav) header[data-testid="stHeader"] {
            height:2.35rem;background:transparent;z-index:1;
        }
        body:has(.st-key-learning_primary_nav) header[data-testid="stHeader"] button {
            opacity:.72;
        }
        [data-testid="stFileUploaderDropzone"] {border-radius: 9px;}
        [data-testid="stMetric"] {
            border: 1px solid var(--pa-border); border-radius: var(--pa-radius-lg); padding: 12px 14px;
            background: var(--pa-bg);
        }
        section[data-testid="stSidebar"]:not([aria-expanded="false"]) {
            width:clamp(160px,12vw,220px) !important;
            min-width:clamp(160px,12vw,220px) !important;
        }
        section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
            height:100vh;max-height:100vh;overflow-y:auto;
            padding:1rem .625rem .75rem;background:var(--pa-bg-page);border-right:1px solid var(--pa-border-sidebar);
        }
        .pa-sidebar-library-title {
            margin:.08rem 0 .72rem;color:var(--pa-text-heading);font-size:1rem;font-weight:780;
            letter-spacing:.01em;
        }
        .pa-sidebar-section-heading {
            display:flex;align-items:center;justify-content:space-between;
            margin:1rem .12rem .42rem;color:var(--pa-text-body);font-size:.72rem;font-weight:760;
        }
        .pa-sidebar-section-heading b {
            display:inline-flex;align-items:center;justify-content:center;min-width:1.25rem;height:1.25rem;
            padding:0 .3rem;border-radius:.42rem;background:var(--pa-surface-alt);color:var(--pa-text-muted);
            font-size:.63rem;font-weight:700;
        }
        .st-key-sidebar_project_list {
            max-height:calc(100vh - 22rem);min-height:8rem;margin-top:.4rem;padding:0;
            overflow-y:auto;scrollbar-gutter:stable;border:0;border-radius:0;background:transparent;
            box-shadow:none;
        }
        div[class*="st-key-sidebar_project_"] {
            position:relative;margin:0 0 .35rem 0;padding:.45rem .55rem .45rem .6rem;
            border-radius:var(--pa-radius-md);border:1px solid var(--pa-border);
            background:var(--pa-bg);overflow:hidden;
            box-shadow:0 1px 3px rgba(15,23,42,.03);
            transition:transform var(--pa-transition-fast), box-shadow var(--pa-transition-fast), border-color var(--pa-transition-fast);
        }
        div[class*="st-key-sidebar_project_"] > [data-testid="stVerticalBlock"] {
            gap: 0.1rem !important;
        }
        div[class*="st-key-sidebar_project_"] [data-testid="stHorizontalBlock"] {
            min-height: 0 !important;
            height: auto !important;
            margin: 0 !important;
            padding: 0 !important;
            align-items: flex-start !important;
        }
        div[class*="st-key-sidebar_project_"] [data-testid="stColumn"] {
            min-height: 0 !important;
            height: auto !important;
            align-self: flex-start !important;
        }
        div[class*="st-key-sidebar_project_"] [data-testid="stButton"],
        div[class*="st-key-sidebar_project_"] [data-testid="stElementContainer"] {
            min-height: 0 !important;
            height: auto !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        div[class*="st-key-sidebar_project_"] button,
        div[class*="st-key-sidebar_project_"] button[data-testid*="stBaseButton"],
        div[class*="st-key-sidebar_project_"] [data-testid="stButton"] button {
            justify-content: flex-start;
            min-height: 0 !important;
            height: auto !important;
            max-height: none !important;
            padding: 0 !important;
            margin: 0 !important;
            border: 0 !important;
            background: transparent !important;
            box-shadow: none !important;
            text-align: left;
        }
        div[class*="st-key-sidebar_project_"] button:hover,
        div[class*="st-key-sidebar_project_"] [data-testid="stButton"] button:hover {
            background: transparent !important;
            color: var(--pa-primary-action) !important;
        }
        div[class*="st-key-sidebar_project_"] button p,
        div[class*="st-key-sidebar_project_"] [data-testid="stButton"] button p {
            display: -webkit-box;
            max-width: 100%;
            overflow: hidden;
            -webkit-box-orient: vertical;
            -webkit-line-clamp: 2;
            white-space: normal;
            line-height: 1.25 !important;
            color: var(--pa-text-heading);
            font-size: 0.74rem;
            font-weight: 650;
            margin: 0 !important;
            padding: 0 !important;
        }
        div[class*="st-key-sidebar_project_"]:has(.pa-sidebar-project-marker.is-active) button p {
            color: var(--pa-primary-dark);
            font-weight: 750;
        }
        div[class*="st-key-sidebar_project_"]:last-child {
            margin-bottom:0;
        }
        div[class*="st-key-sidebar_project_"]:hover {
            border-color:var(--pa-primary-border);
            box-shadow:var(--pa-shadow-sm);
            transform:translateY(-1px);
        }
        div[class*="st-key-sidebar_project_"]:has(.pa-sidebar-project-marker.is-active) {
            background:var(--pa-primary-surface);
            border-color:var(--pa-primary-border);
            border-left:4px solid var(--pa-primary-action);
            box-shadow:0 2px 8px rgba(37,99,235,.08);
        }
        /* The project list key also matches the generic project-card selector
           above; reset card-only decoration on the outer scroll container. */
        .st-key-sidebar_project_list,
        .st-key-sidebar_project_list:hover,
        .st-key-sidebar_project_list:has(.pa-sidebar-project-marker.is-active) {
            margin-top:.4rem !important;padding:0 !important;overflow-y:auto !important;overflow-x:hidden !important;
            background:transparent !important;border:0 !important;border-left:0 !important;
            border-radius:0 !important;box-shadow:none !important;transform:none !important;
        }
        .pa-sidebar-project-marker {display:none;}
        div[class*="st-key-sidebar_project_"] div[class*="st-key-sidebar-delete-"]
        [data-testid="stButton"] button {
            justify-content:center;min-height:0 !important;height:auto !important;padding:0;color:var(--pa-text-placeholder);
            opacity:0.3;transition:all var(--pa-transition-fast);
        }
        div[class*="st-key-sidebar_project_"]:hover div[class*="st-key-sidebar-delete-"]
        [data-testid="stButton"] button {
            opacity:1.0;color:var(--pa-danger);
        }
        div[class*="st-key-sidebar_project_"] div[class*="st-key-sidebar-delete-"]
        [data-testid="stButton"] button p {
            display:block;overflow:visible;color:inherit;font-size:.85rem;line-height:1;
        }
        .pa-sidebar-project-meta {
            display:flex;align-items:center;justify-content:space-between;gap:.35rem;
            flex-wrap:nowrap;margin-top:.15rem;width:100%;min-width:0;
            overflow:hidden;line-height:1.2;
        }
        .pa-project-chip {
            display:inline-flex;align-items:center;gap:3px;padding:2px 6px;
            border-radius:var(--pa-radius-pill);font-size:.58rem;font-weight:700;
            white-space:nowrap;flex-shrink:0;letter-spacing:.01em;
        }
        .chip-paper {
            background:var(--pa-primary-surface);color:var(--pa-primary);
            border:1px solid var(--pa-primary-border);
        }
        .chip-code {
            background:var(--pa-success-surface);color:var(--pa-success-dark);
            border:1px solid var(--pa-success-light);
        }
        .chip-audit {
            background:var(--pa-warning-surface);color:var(--pa-warning-dark);
            border:1px solid var(--pa-warning-surface);
        }
        .pa-sidebar-filename {
            color:var(--pa-text-muted);font-size:.58rem;font-weight:500;
            white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
            min-width:0;flex:0 1 auto;text-align:right;
        }
        .pa-sidebar-project-empty {
            padding:.8rem .4rem;color:var(--pa-text-faint);font-size:.68rem;text-align:center;
        }
        .st-key-joint_code_file_tree {
            min-width:0;padding:.42rem .4rem;border:1px solid var(--pa-border);border-radius:9px;
            background:var(--pa-bg);scrollbar-gutter:stable;
        }
        .st-key-joint_code_file_tree_list {
            height:calc(100vh - 260px);max-height:720px;min-height:320px;overflow-y:auto;
            overflow-x:hidden;scrollbar-gutter:stable;padding-right:.12rem;
        }
        .st-key-joint_code_file_tree_list::-webkit-scrollbar {width:6px;}
        .st-key-joint_code_file_tree_list::-webkit-scrollbar-thumb {
            background:transparent;border-radius:6px;
        }
        .st-key-joint_code_file_tree_list:hover::-webkit-scrollbar-thumb {background:var(--pa-border-strong);}
        .pa-code-tree-title {
            padding:.08rem .35rem .42rem;color:var(--pa-text-heading);font-size:.75rem;font-weight:760;
        }
        .st-key-joint_code_file_tree > [data-testid="stVerticalBlock"] {gap:.12rem;}
        .st-key-joint_code_file_tree [data-testid="stTextInput"] {margin-bottom:.22rem;}
        .st-key-joint_code_file_tree [data-testid="stTextInput"] input {
            min-height:2rem;padding:.35rem .55rem;border-color:var(--pa-border-sidebar);border-radius:6px;
            background:var(--pa-surface);font-size:.68rem;
        }
        .st-key-joint_code_file_tree [data-testid="stExpander"] {
            margin:0;border:0 !important;border-radius:5px;background:transparent !important;
        }
        .st-key-joint_code_file_tree [data-testid="stExpander"] details {
            border:0 !important;background:transparent !important;
        }
        .st-key-joint_code_file_tree [data-testid="stExpander"] details summary {
            min-height:30px;height:30px;padding:0 7px;border-radius:5px;
            color:var(--pa-text-body);font-size:13px;font-weight:600;
        }
        .st-key-joint_code_file_tree [data-testid="stExpander"] details summary:hover {
            background:var(--pa-surface-alt);
        }
        .st-key-joint_code_file_tree [data-testid="stExpanderDetails"] {
            margin-left:14px;padding:0 0 0 1px;border-left:1px solid var(--pa-border-light);
        }
        .st-key-joint_code_file_tree button[kind],
        .st-key-joint_code_file_tree [data-testid="stButton"] button {
            min-height:28px;height:28px;padding:0 7px;border:0 !important;border-radius:5px;
            justify-content:flex-start !important;box-shadow:none !important;
            background:transparent;color:var(--pa-text-secondary);font-size:13px;text-align:left;
        }
        .st-key-joint_code_file_tree button[kind]:hover,
        .st-key-joint_code_file_tree [data-testid="stButton"] button:hover {
            background:var(--pa-surface-alt);color:var(--pa-text-heading);
        }
        .st-key-joint_code_file_tree [data-testid="stBaseButton-primary"] {
            background:var(--pa-primary-surface) !important;color:var(--pa-primary-action) !important;font-weight:650;
            box-shadow:none !important;
        }
        .st-key-joint_code_file_tree [data-testid="stBaseButton-primary"] span,
        .st-key-joint_code_file_tree [data-testid="stBaseButton-primary"] p {
            color:var(--pa-primary-action) !important;
        }
        .st-key-joint_code_file_tree button p {
            width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;text-align:left;
        }
        .st-key-joint_code_file_tree button [data-testid="stIconMaterial"] {
            flex:0 0 15px;width:15px;font-size:15px;color:var(--pa-text-muted);
        }
        .pa-code-breadcrumb {
            margin:.12rem 0 .5rem;padding:.42rem .55rem;border-bottom:1px solid var(--pa-border-sidebar);
            color:var(--pa-text-faint);font-size:.67rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
        }
        .pa-code-breadcrumb strong {color:var(--pa-text-secondary);font-weight:700;}
        .pa-sidebar-title {font-size:.82rem;font-weight:750;color:var(--pa-text-body);margin:.2rem 0 .45rem;}
        .pa-api-status {
            display:flex;align-items:center;gap:.52rem;padding:.58rem .62rem;margin-top:.5rem;
            border:1px solid var(--pa-border-sidebar);border-radius:7px 7px 0 0;background:var(--pa-bg);
            color:var(--pa-text-body);font-size:.7rem;font-weight:650;
            white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
        }
        .pa-api-status span {width:.42rem;height:.42rem;border-radius:50%;flex:0 0 auto;}
        .pa-api-status.is-ready span {background:var(--pa-success);box-shadow:0 0 0 3px var(--pa-success-light);animation:pa-pulse 2.5s ease-in-out infinite;}
        .pa-api-status.is-warning span {background:var(--pa-warning);box-shadow:0 0 0 3px var(--pa-warning-surface);}
        .pa-sidebar-field {
            display:flex;align-items:center;justify-content:space-between;gap:.5rem;
            margin:.45rem 0 .05rem;color:var(--pa-text-muted);font-size:.7rem;
        }
        .pa-sidebar-field b {color:var(--pa-primary);font-size:.72rem;}
        .pa-sidebar-version {
            display:flex;align-items:flex-start;gap:.52rem;padding:.75rem .28rem .1rem;
            color:var(--pa-text-placeholder);font-size:.63rem;line-height:1.45;
        }
        .pa-sidebar-version > span {font-size:.85rem;color:var(--pa-text-placeholder);}
        .pa-sidebar-version small {display:block;margin-top:.12rem;color:var(--pa-text-faint);font-size:.59rem;}
        .pa-audit-empty-note {
            display:flex;flex-direction:column;gap:.12rem;margin:.55rem 0 .2rem;padding:.65rem .72rem;
            border-radius:7px;background:var(--pa-surface);color:var(--pa-text-muted);
        }
        .pa-audit-empty-note strong {color:var(--pa-text-secondary);font-size:.7rem;font-weight:700;}
        .pa-audit-empty-note span {font-size:.64rem;line-height:1.45;}
        .pa-storage-status {
            display:flex;align-items:flex-start;gap:.52rem;padding:.58rem .62rem;
            border:1px solid var(--pa-border-sidebar);border-top:0;border-radius:0 0 7px 7px;background:var(--pa-bg);min-width:0;
        }
        .pa-storage-status > span {
            width:.42rem;height:.42rem;margin-top:.18rem;border-radius:50%;background:var(--pa-success);
            box-shadow:0 0 0 3px var(--pa-success-light);animation:pa-pulse 2.5s ease-in-out infinite;flex:0 0 auto;
        }
        .pa-storage-status div {min-width:0;}
        .pa-storage-status strong {display:block;color:var(--pa-text-body);font-size:.69rem;}
        .pa-storage-status small {
            display:block;margin-top:.12rem;color:var(--pa-text-faint);font-size:.61rem;
            white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
        }
        .pa-header {
            display:flex; justify-content:space-between; align-items:center; gap:1rem;
            min-height:3.5rem;padding:.35rem 0;margin:0;border:0;border-radius:0;background:transparent;
        }
        .pa-header-title {font-size:1.05rem; font-weight:750; color:var(--pa-text-heading);}
        .pa-header-subtitle {margin-top:.12rem; color:var(--pa-text-muted); font-size:.72rem;white-space:nowrap;}
        .pa-header-badge {color:var(--pa-text-muted); font-size:.65rem; white-space:nowrap;}
        .st-key-launch_shell_empty {max-width:1120px;margin:0 auto;}
        .st-key-launch_shell_ready {max-width:1440px;margin:0 auto;}
        .st-key-launch_shell_empty > div:first-child,
        .st-key-launch_shell_ready > div:first-child {gap:.7rem;}
        .st-key-launch_pdf_upload_empty {
            margin:1.2rem 0 .7rem;padding:1.25rem 1.5rem 1.35rem;
            border:2px dashed var(--pa-primary-border);border-radius:14px;background:var(--pa-cyan-surface);text-align:center;
        }
        .st-key-launch_pdf_upload_empty [data-testid="stFileUploaderDropzone"] {
            min-height:5rem;border:0;background:transparent;justify-content:center;
        }
        .st-key-launch_pdf_upload_empty [data-testid="stFileUploaderDropzoneInstructions"] {
            display:none;
        }
        .pa-upload-title {color:var(--pa-text-heading);font-size:1.08rem;font-weight:750;margin:.1rem 0 .25rem;}
        .pa-upload-subtitle {color:var(--pa-text-muted);font-size:.76rem;margin-bottom:.35rem;}
        .pa-launch-hint {color:var(--pa-text-faint);font-size:.72rem;text-align:center;margin:.35rem 0;}
        .st-key-storage_setup_shell {
            max-width:720px;margin:clamp(2.5rem,10vh,7rem) auto 0;padding:2rem 2.1rem 1.8rem;
            border:1px solid var(--pa-border-medium);border-radius:16px;background:var(--pa-bg);
            box-shadow:0 18px 50px rgba(15,23,42,.08);
        }
        .pa-storage-setup-icon {font-size:1.7rem;margin-bottom:.55rem;}
        .pa-storage-setup-title {color:var(--pa-text-heading);font-size:1.35rem;font-weight:750;}
        .pa-storage-setup-copy {color:var(--pa-text-muted);font-size:.82rem;line-height:1.65;margin:.35rem 0 1rem;}
        .pa-recent-title {color:var(--pa-text-body);font-size:.78rem;font-weight:750;margin:1.15rem 0 .45rem;}
        div[class*="st-key-recent_project_"] {border-color:var(--pa-border) !important;background:var(--pa-bg);}
        .pa-recent-project-title {
            color:var(--pa-text-heading);font-size:.8rem;font-weight:700;white-space:nowrap;
            overflow:hidden;text-overflow:ellipsis;
        }
        .pa-recent-project-meta {color:var(--pa-text-faint);font-size:.67rem;margin-top:.16rem;}
        .pa-ready-toolbar {
            display:flex;align-items:center;gap:.5rem;min-width:0;padding:.42rem .18rem;
            border-bottom:1px solid var(--pa-border);color:var(--pa-text-secondary);
        }
        .pa-ready-toolbar strong {
            min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
            color:var(--pa-text-heading);font-size:.8rem;
        }
        .pa-ready-toolbar small {margin-left:auto;color:var(--pa-text-faint);font-size:.68rem;white-space:nowrap;}
        .st-key-launch_setup_panel {
            position:sticky;top:3.5rem;min-height:min(73vh,760px);padding:.2rem;
            border-color:var(--pa-border-medium) !important;border-radius:11px;background:var(--pa-bg);
        }
        .st-key-launch_setup_panel > div[data-testid="stVerticalBlock"] {
            min-height:inherit;
        }
        .pa-setup-heading {color:var(--pa-text-heading);font-size:1rem;font-weight:750;margin:.08rem 0 .65rem;}
        .pa-ready-file {
            display:grid;grid-template-columns:1fr auto;gap:.2rem .6rem;padding:.75rem .8rem;
            margin-bottom:.8rem;border-left:3px solid var(--pa-primary);background:var(--pa-surface);
        }
        .pa-ready-file span {grid-column:1 / -1;color:var(--pa-primary);font-size:.68rem;font-weight:700;}
        .pa-ready-file strong {
            min-width:0;color:var(--pa-text-heading);font-size:.82rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
        }
        .pa-ready-file small {color:var(--pa-text-faint);font-size:.68rem;white-space:nowrap;}
        .pa-setup-title {color:var(--pa-text-heading);font-size:.88rem;font-weight:750;margin:.35rem 0 .28rem;}
        .pa-setup-mode {
            padding:.68rem .75rem;margin-bottom:.7rem;border:1px solid var(--pa-border);
            border-radius:8px;background:var(--pa-surface);
        }
        .pa-setup-mode strong {display:block;color:var(--pa-text-heading);font-size:.8rem;margin-bottom:.24rem;}
        .pa-setup-mode span {display:block;color:var(--pa-text-muted);font-size:.7rem;line-height:1.5;}
        .st-key-launch_setup_actions {margin-top:1rem;}
        .pa-setup-copy {
            color:var(--pa-text-muted);font-size:.74rem;line-height:1.55;padding:0 0 .75rem;
            margin-bottom:.55rem;border-bottom:1px solid var(--pa-border);
        }
        .st-key-upload_pdf_preview {
            padding:.4rem;background:var(--pa-surface-alt);border-radius:8px;
        }
        .st-key-upload_pdf_preview > div:first-child {
            padding:.25rem .35rem;background:var(--pa-bg);border-bottom:1px solid var(--pa-border);
        }
        .pa-grade {
            padding:1rem 1.2rem; margin-bottom:1rem; border-radius:10px;
            background:var(--pa-surface); border-left:5px solid var(--pa-text-muted);
        }
        .pa-grade-trusted {border-left-color:var(--pa-success);}
        .pa-grade-review {border-left-color:var(--pa-warning);}
        .pa-grade-untrusted {border-left-color:var(--pa-danger);}
        .pa-grade-title {font-size:1.1rem; font-weight:700; color:var(--pa-text-heading);}
        .pa-grade-detail {margin-top:.2rem; color:var(--pa-text-muted); font-size:.86rem;}
        .pa-audit-card {
            border:1px solid var(--pa-border); border-radius:11px; padding:1rem 1.1rem;
            margin-bottom:.75rem; background:var(--pa-bg);
        }
        .pa-audit-meta {color:var(--pa-text-muted); font-size:.78rem; margin-bottom:.45rem;}
        .pa-audit-claim {font-weight:650; line-height:1.55; color:var(--pa-text-heading);}
        .pa-audit-explanation {margin-top:.55rem; color:var(--pa-text-secondary); line-height:1.55;}
        .pa-audit-head {display:flex;justify-content:space-between;align-items:center;gap:.6rem;flex-wrap:wrap;}
        .pa-audit-tags {display:flex;align-items:center;gap:.35rem;flex-wrap:wrap;}
        .pa-badge {display:inline-flex;padding:.18rem .48rem;border-radius:5px;font-size:.74rem;font-weight:650;}
        .badge-supported {background:var(--pa-success-light);color:var(--pa-success-text);border:1px solid var(--pa-success-light);}
        .badge-partially {background:var(--pa-warning-surface);color:var(--pa-warning-text);border:1px solid var(--pa-warning-surface);}
        .badge-contradicted {background:var(--pa-danger-surface);color:var(--pa-danger-text);border:1px solid var(--pa-danger-surface);}
        .badge-no-support,.badge-abstain,.badge-sev-none {background:var(--pa-surface-alt);color:var(--pa-text-secondary);border:1px solid var(--pa-border-strong);}
        .badge-sev-low {background:#e0f2fe;color:var(--pa-primary-hover);border:1px solid #bae6fd;}
        .badge-sev-medium {background:var(--pa-warning-surface);color:var(--pa-warning-dark);border:1px solid var(--pa-warning-surface);}
        .badge-sev-high {background:var(--pa-warning-surface);color:var(--pa-danger-dark);border:1px solid var(--pa-warning-surface);}
        .badge-sev-critical {background:var(--pa-danger-surface);color:var(--pa-danger-dark);border:1px solid var(--pa-danger-surface);}
        .pa-mark {background:var(--pa-warning-surface);color:inherit;padding:0 .12rem;border-radius:3px;}
        .pa-evidence {
            margin-top:.55rem; padding:.7rem .8rem; border-left:3px solid var(--pa-cyan);
            border-radius:0 8px 8px 0; background:var(--pa-cyan-surface); color:var(--pa-text-body);
            font-size:.84rem; line-height:1.55; white-space:pre-wrap; overflow-wrap:anywhere;
        }
        .pa-audit-summary {
            display:flex;align-items:stretch;gap:0;flex-wrap:nowrap;
            padding:0;margin:0 0 .55rem;border:1px solid var(--pa-border-medium);
            border-radius:8px;background:var(--pa-bg);overflow:hidden;
        }
        .pa-audit-summary-grade {
            display:flex;flex-direction:column;align-items:flex-start;justify-content:center;
            gap:.12rem;min-width:8.5rem;padding:.72rem 1rem;border-right:1px solid var(--pa-border);
        }
        .pa-audit-summary-grade span {
            color:var(--pa-text-muted);font-size:.7rem;font-weight:700;text-transform:uppercase;
            letter-spacing:.04em;
        }
        .pa-audit-summary-grade strong {
            font-size:1rem;color:var(--pa-text-body);white-space:nowrap;
        }
        .pa-audit-summary-grade.is-trusted strong {color:var(--pa-success-dark);}
        .pa-audit-summary-grade.is-review strong {color:var(--pa-warning-dark);}
        .pa-audit-summary-grade.is-untrusted strong {color:var(--pa-danger-dark);}
        .pa-audit-summary-score {
            display:flex;align-items:center;min-width:5rem;padding:.72rem 1rem;
            border-right:1px solid var(--pa-border);color:var(--pa-primary-hover);font-size:1.65rem;
            font-weight:750;line-height:1;
        }
        .pa-audit-summary-score small {
            color:var(--pa-text-muted);font-size:.72rem;font-weight:600;margin-left:.18rem;
        }
        .pa-audit-summary-metrics {
            display:grid;grid-template-columns:repeat(5,minmax(7.5rem,1fr));
            align-items:stretch;gap:0;flex:1 1 auto;
        }
        .pa-audit-summary-metric {
            display:flex;flex-direction:column;align-items:center;justify-content:center;
            gap:.2rem;padding:.62rem .55rem;border-right:1px solid var(--pa-border-light);
            border-radius:0;background:var(--pa-bg);color:var(--pa-text-muted);
        }
        .pa-audit-summary-metric span {font-size:.68rem;white-space:nowrap;}
        .pa-audit-summary-metric strong {font-size:1rem;color:var(--pa-text-heading);}
        .pa-audit-summary-metric.is-danger {background:var(--pa-danger-surface);}
        .pa-audit-summary-metric.is-danger strong {color:var(--pa-danger-dark);}
        .pa-audit-summary-metric.is-warning {background:var(--pa-warning-surface);}
        .pa-audit-summary-metric.is-warning strong {color:var(--pa-danger-dark);}
        .st-key-audit_quick_filters {margin:.15rem 0 .45rem;}
        .st-key-audit_quick_filters div[data-testid="stButtonGroup"] {flex-wrap:wrap;}
        .st-key-audit_advanced_filters {margin-bottom:.15rem;}
        .st-key-audit_advanced_filters [data-testid="stHorizontalBlock"] {gap:.5rem;}
        .st-key-audit_advanced_filters [data-baseweb="select"] > div,
        .st-key-audit_advanced_filters input {min-height:2.15rem;font-size:.78rem;}
        .st-key-peer_review_pdf_panel {
            min-height:0;padding:.45rem !important;border:1px solid var(--pa-border-medium) !important;
            border-radius:10px !important;background:var(--pa-surface-alt);overflow:hidden;
        }
        .st-key-peer_review_pdf_panel [data-testid="stImage"] img {max-height:none;object-fit:contain;}
        .st-key-peer_review_pdf_panel [data-testid="stCaptionContainer"] {font-size:.68rem;}
        .st-key-peer_review_pdf_panel + div {min-width:0;}
        .pa-peer-section-card {
            margin:.35rem 0 .65rem;padding:.7rem .78rem;border:1px solid var(--pa-border-medium);
            border-radius:9px;background:var(--pa-bg);box-shadow:0 1px 3px rgba(15,23,42,.03);
        }
        .st-key-peer_review_header {margin-bottom:.42rem;padding-bottom:.25rem;border-bottom:1px solid var(--pa-border-light);}
        .st-key-peer_review_header .pa-workspace-title {font-size:1.05rem;}
        .st-key-peer_review_header .pa-workspace-summary {max-width:34rem;}
        .pa-peer-header-stat {display:flex;flex-direction:column;gap:.12rem;min-width:7rem;}
        .pa-peer-header-stat span {color:var(--pa-text-muted);font-size:.67rem;font-weight:650;}
        .pa-peer-header-stat strong {color:var(--pa-primary-dark);font-size:1rem;line-height:1.15;}
        .pa-peer-readonly-result {
            display:flex;align-items:center;justify-content:flex-end;gap:.7rem;min-height:2.5rem;
            color:var(--pa-text-muted);white-space:nowrap;
        }
        .pa-peer-readonly-result > span {font-size:.68rem;font-weight:700;color:var(--pa-text-muted);}
        .pa-peer-readonly-result > strong {font-size:1rem;}
        .pa-peer-readonly-result > b {font-size:.9rem;color:var(--pa-text-heading);}
        .pa-peer-readonly-result > small {font-size:.67rem;color:var(--pa-text-muted);}
        .pa-peer-decision-strong-accept strong {color:#18794e;}
        .pa-peer-decision-weak-accept strong {color:#147d78;}
        .pa-peer-decision-borderline strong {color:#9a6700;}
        .pa-peer-decision-weak-reject strong {color:#b54708;}
        .pa-peer-decision-strong-reject strong {color:#b42318;}
        .pa-peer-decision-scale {
            display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:.35rem;margin:.15rem 0 .55rem;
        }
        .pa-peer-scale-step {
            display:flex;flex-direction:column;gap:.1rem;padding:.35rem .42rem;border:1px solid var(--pa-border);
            border-radius:6px;background:var(--pa-surface);color:var(--pa-text-muted);font-size:.62rem;line-height:1.25;
        }
        .pa-peer-scale-step strong {font-size:.65rem;color:var(--pa-text-secondary);white-space:nowrap;}
        .pa-peer-scale-step.is-active {border-color:currentColor;box-shadow:0 0 0 1px currentColor;background:var(--pa-bg);}
        .pa-peer-scale-step.pa-peer-decision-strong-accept {color:#18794e;}
        .pa-peer-scale-step.pa-peer-decision-weak-accept {color:#147d78;}
        .pa-peer-scale-step.pa-peer-decision-borderline {color:#9a6700;}
        .pa-peer-scale-step.pa-peer-decision-weak-reject {color:#b54708;}
        .pa-peer-scale-step.pa-peer-decision-strong-reject {color:#b42318;}
        .st-key-peer_review_source_panel {
            height:calc(100vh - 17rem) !important;max-height:calc(100vh - 17rem) !important;
            min-height:32rem !important;overflow-y:auto;overflow-x:hidden;
            padding:.35rem .5rem .6rem;border:1px solid var(--pa-border-medium);background:var(--pa-surface);
            border-radius:var(--pa-radius-lg);box-shadow:var(--pa-shadow-xs);scrollbar-gutter:stable;
        }
        .st-key-peer_review_side_panel {
            height:calc(100vh - 17rem) !important;max-height:calc(100vh - 17rem) !important;
            min-height:32rem !important;overflow-y:auto;overflow-x:hidden;
            padding:0 .35rem .75rem 0;scrollbar-gutter:stable;
        }
        .st-key-peer_review_side_panel [data-testid="stTabs"] > div:first-child {
            position:sticky;top:0;z-index:5;background:var(--pa-bg);padding-top:.1rem;
        }
        .st-key-peer_review_side_panel h3 {margin:.8rem 0 .4rem;font-size:.95rem;}
        .st-key-peer_review_side_panel [data-testid="stVerticalBlock"] {gap:.35rem;}
        .st-key-peer_review_pdf_toolbar {
            padding:.35rem .5rem;min-height:42px;border-bottom:1px solid var(--pa-border);
            background:var(--pa-bg);border-radius:var(--pa-radius-md) var(--pa-radius-md) 0 0;
        }
        .st-key-peer_review_pdf_toolbar [data-testid="stHorizontalBlock"] {
            gap:.5rem !important;align-items:center;flex-wrap:nowrap !important;
        }
        .st-key-peer_review_pdf_toolbar [data-testid="stColumn"] {min-width:0 !important;}
        .st-key-peer_review_pdf_toolbar button {
            min-height:1.85rem;height:1.85rem;padding:0 .4rem !important;white-space:nowrap;
            border-radius:var(--pa-radius-sm) !important;border:1px solid var(--pa-border) !important;
            background:var(--pa-surface) !important;color:var(--pa-text-primary) !important;box-shadow:none !important;
        }
        .st-key-peer_review_pdf_toolbar button p {font-size:.73rem;font-weight:600;white-space:nowrap;}
        .pa-peer-page-label {text-align:center;color:var(--pa-text-body);font-size:.74rem;font-weight:650;line-height:1.8rem;white-space:nowrap;}
        .pa-peer-page-label span {color:var(--pa-text-muted);font-weight:500;}
        .pa-peer-summary-strip {
            display:flex;align-items:flex-start;gap:.55rem;margin:.05rem 0 .55rem;padding:.62rem .8rem;
            border:1px solid #fed7aa;border-radius:8px;background:#fffaf5;color:var(--pa-text-body);
            font-size:.76rem;line-height:1.55;
        }
        .pa-peer-summary-strip strong {flex:0 0 auto;color:#b54708;font-size:.72rem;}
        .pa-peer-summary-strip span {min-width:0;}
        .pa-peer-point-card {
            margin:.42rem 0;padding:.62rem .72rem;border-left:3px solid var(--pa-primary-action);
            border-radius:0 8px 8px 0;background:var(--pa-primary-surface);color:var(--pa-text-body);
            font-size:.8rem;line-height:1.58;
        }
        .pa-peer-point-card strong {display:block;margin-bottom:.22rem;color:var(--pa-text-heading);font-size:.78rem;}
        .pa-peer-concern-head {
            display:flex;align-items:center;gap:.42rem;margin:0 0 .4rem;padding:0 0 .58rem;
            border-bottom:1px solid var(--pa-border-light);
            white-space:nowrap;overflow:hidden;
        }
        .pa-peer-concern-head strong {flex:1;min-width:0;margin:0;color:var(--pa-text-heading);font-size:.82rem;line-height:1.4;}
        .pa-peer-severity-badge,.pa-peer-status-badge {
            display:inline-flex;align-items:center;white-space:nowrap;border-radius:999px;padding:.16rem .42rem;
            font-size:.62rem;font-weight:750;line-height:1.2;
        }
        .pa-peer-severity-badge {background:#fff1f2;color:#be123c;}
        .severity-p0 .pa-peer-severity-badge {background:#fee2e2;color:#b91c1c;}
        .severity-p1 .pa-peer-severity-badge {background:#ffedd5;color:#c2410c;}
        .severity-p2 .pa-peer-severity-badge {background:#fef3c7;color:#a16207;}
        .severity-p3 .pa-peer-severity-badge {background:#f1f5f9;color:#475569;}
        .pa-peer-status-badge {background:var(--pa-surface-alt);color:var(--pa-text-muted);font-weight:650;}
        .pa-peer-category-inline,.pa-peer-title-separator {color:var(--pa-text-muted);font-size:.69rem;font-weight:600;}
        .pa-peer-concern-head + [data-testid="stCaptionContainer"] {margin:0 0 .95rem;color:var(--pa-text-faint);font-size:.65rem;line-height:1.4;}
        .pa-peer-metadata {display:flex;align-items:center;gap:.48rem;flex-wrap:wrap;margin:.52rem 0 .92rem;color:var(--pa-text-faint);font-size:.66rem;line-height:1.4;}
        .pa-peer-metadata span {padding-left:.45rem;border-left:1px solid var(--pa-border-light);}
        .pa-peer-metadata em {padding:.14rem .38rem;border-radius:999px;background:#fff7ed;color:#c2410c;font-size:.63rem;font-style:normal;font-weight:650;}
        .pa-peer-subsection-label {margin:0 0 .32rem;color:var(--pa-text-heading);font-size:.69rem;font-weight:750;letter-spacing:.01em;}
        .pa-peer-subsection-muted {margin-top:.12rem;color:var(--pa-text-muted);font-weight:650;}
        .pa-peer-why-text {max-width:48rem;margin:.22rem 0 .1rem;color:var(--pa-text-muted);font-size:.71rem;line-height:1.65;}
        .pa-peer-action-callout {
            margin:1rem 0 .78rem;padding:.78rem .9rem .82rem;border:1px solid #d6e5f1;
            border-radius:8px;background:#f5f9fc;color:var(--pa-text-body);font-size:.74rem;line-height:1.55;
        }
        .pa-peer-action-callout strong {display:block;margin-bottom:.55rem;color:var(--pa-primary-dark);font-size:.72rem;font-weight:750;}
        .pa-peer-action-callout ul {display:grid;gap:.4rem;margin:0;padding:0;list-style:none;}
        .pa-peer-action-callout li {padding-left:.05rem;color:var(--pa-text-body);font-size:.72rem;line-height:1.5;}
        div[class*="st-key-peer-major-card-"],div[class*="st-key-peer-minor-card-"] {
            margin-bottom:.8rem;padding:1rem 1.05rem .88rem !important;border-color:var(--pa-border-medium) !important;
            border-radius:9px !important;background:var(--pa-bg);box-shadow:0 1px 2px rgba(15,23,42,.025);
        }
        div[class*="st-key-peer-major-card-"] > [data-testid="stVerticalBlock"],
        div[class*="st-key-peer-minor-card-"] > [data-testid="stVerticalBlock"] {gap:.12rem !important;}
        div[class*="st-key-peer-major-card-"] [data-testid="stMarkdownContainer"] > p,
        div[class*="st-key-peer-minor-card-"] [data-testid="stMarkdownContainer"] > p {
            max-width:48rem;margin:.08rem 0;color:var(--pa-text-body);font-size:.78rem;line-height:1.72;
        }
        div[class*="st-key-peer-major-card-"] .pa-peer-metadata,
        div[class*="st-key-peer-minor-card-"] .pa-peer-metadata,
        div[class*="st-key-peer-major-card-"] .pa-peer-why-text,
        div[class*="st-key-peer-minor-card-"] .pa-peer-why-text {
            color:var(--pa-text-muted);font-size:.68rem;
        }
        div[class*="st-key-peer-major-card-"] [data-testid="stButton"] button,
        div[class*="st-key-peer-minor-card-"] [data-testid="stButton"] button {
            min-height:2rem;padding:.28rem .68rem;border-radius:7px;
        }
        div[class*="st-key-peer-major-card-"] [data-testid="stExpander"],
        div[class*="st-key-peer-minor-card-"] [data-testid="stExpander"] {margin-top:.28rem;}
        div[class*="st-key-peer-major-card-"] [data-testid="stExpander"] summary,
        div[class*="st-key-peer-minor-card-"] [data-testid="stExpander"] summary {
            min-height:2.25rem;padding:.35rem .68rem;color:var(--pa-text-muted);font-size:.72rem;
        }
        .pa-peer-decision-card {border-left-color:var(--pa-warning);background:var(--pa-warning-surface);}
        .pa-peer-priority-card {border-left-color:var(--pa-cyan);background:var(--pa-cyan-surface);}
        .pa-peer-blocker-card {border-left-color:#d97706;background:#fff7ed;}
        .pa-peer-fatal-card {border-left-color:#dc2626;background:#fef2f2;}
        .pa-peer-contribution-card {border-left-color:#7c3aed;background:#f5f3ff;}
        .pa-peer-required-card {border-left-color:#ea580c;background:#fff7ed;}
        .pa-peer-suggested-card {border-left-color:#64748b;background:#f8fafc;}
        .pa-peer-evidence-quote {margin:.35rem 0 .5rem;padding:.45rem .58rem;border-radius:7px;background:var(--pa-surface-alt);color:var(--pa-text-muted);font-size:.7rem;line-height:1.5;}
        .pa-peer-risk-card {
            margin:0;padding:0;border:0;border-left:0;border-radius:0;background:transparent;
        }
        .pa-peer-risk-card.pa-peer-risk-high {border-left-color:#dc2626;}
        .pa-peer-risk-card > div {display:flex;justify-content:space-between;gap:.6rem;align-items:center;}
        .pa-peer-risk-card strong {color:var(--pa-text-heading);font-size:.79rem;}
        .pa-peer-risk-card span {font-size:.65rem;font-weight:750;color:#b54708;}
        .pa-peer-risk-card p {margin:.3rem 0;color:var(--pa-text-body);font-size:.75rem;line-height:1.5;}
        .pa-peer-risk-card small {color:var(--pa-text-muted);font-size:.65rem;}
        /* Keep the risk card and evidence action in one stable bordered block. */
        div[class*="st-key-peer-risk-card-"] {
            margin:.45rem 0 .85rem !important;padding:.68rem .72rem .72rem !important;
            border:1px solid var(--pa-border) !important;border-left:3px solid #f59e0b !important;
            border-radius:8px !important;background:var(--pa-bg) !important;position:relative;z-index:1;
        }
        div[class*="st-key-peer-risk-card-"]:has(.pa-peer-risk-high) {
            border-left-color:#dc2626 !important;
        }
        div[class*="st-key-peer-risk-card-"] > [data-testid="stVerticalBlock"] {
            gap:.2rem !important;
        }
        div[class*="st-key-peer-risk-card-"] [data-testid="stButton"] {
            margin:.28rem 0 0 !important;
        }
        div[class*="st-key-peer-risk-card-"] [data-testid="stButton"] button {
            min-height:1.72rem !important;margin:0 !important;padding:.18rem .52rem;border-radius:6px;
            font-size:.69rem !important;line-height:1.2 !important;
        }
        div[class*="st-key-peer-risk-card-"] [data-testid="stButton"] button p {
            font-size:.69rem !important;line-height:1.2 !important;
        }
        .pa-peer-action-card {
            margin:0;padding:.65rem .75rem;border:1px solid var(--pa-border);
            border-radius:8px;background:var(--pa-bg);
        }
        .pa-peer-action-title {display:flex;align-items:center;gap:.38rem;}
        .pa-peer-action-title strong {font-size:.73rem;color:var(--pa-text-heading);font-weight:700;}
        .pa-peer-action-priority {display:inline-flex;align-items:center;justify-content:center;min-width:1.65rem;padding:.15rem .32rem;border-radius:999px;font-size:.61rem;font-weight:800;line-height:1.2;}
        .pa-peer-action-priority.priority-p0 {background:#fff1ed;color:#c2410c;}
        .pa-peer-action-priority.priority-p1 {background:#fff7ed;color:#a16207;}
        .pa-peer-action-card p {margin:.32rem 0 0;color:var(--pa-text-body);font-size:.74rem;line-height:1.55;}
        .pa-peer-plan-progress {float:right;color:var(--pa-text-faint);font-size:.66rem;font-weight:550;line-height:1.5;}
        div[class*="st-key-peer-action-item-"] {margin:.45rem 0;padding:0 !important;overflow:visible;}
        div[class*="st-key-peer-action-item-"] > [data-testid="stVerticalBlock"] {gap:0 !important;}
        div[class*="st-key-peer-action-item-"] [data-testid="stCheckbox"] {display:flex;justify-content:flex-end;align-items:center;min-height:2.8rem;}
        div[class*="st-key-peer-action-item-"] [data-testid="stCheckbox"] label {gap:.28rem;color:var(--pa-text-muted);font-size:.68rem;white-space:nowrap;}
        .pa-peer-conclusion {margin:.35rem 0 .55rem;padding:.68rem;border:1px solid var(--pa-border);border-radius:8px;background:var(--pa-bg);}
        .pa-peer-conclusion > div {display:flex;align-items:center;justify-content:space-between;gap:.6rem;}
        .pa-peer-conclusion strong {font-size:.76rem;color:var(--pa-text-heading);}
        .pa-peer-conclusion span {font-size:.74rem;font-weight:750;}
        .pa-peer-conclusion p {margin:.38rem 0 0;color:var(--pa-text-body);font-size:.76rem;line-height:1.55;}
        .pa-peer-strength-row {padding:.55rem .1rem;border-bottom:1px solid var(--pa-border-light);}
        .pa-peer-strength-row:last-child {border-bottom:0;}
        .pa-peer-strength-row strong {font-size:.75rem;color:#18794e;}
        .pa-peer-strength-row p {margin:.18rem 0 0;color:var(--pa-text-body);font-size:.74rem;line-height:1.5;}
        .pa-peer-pdf-focus {
            display:flex;justify-content:space-between;gap:.5rem;padding:.38rem .55rem;
            border-bottom:1px solid var(--pa-primary-border);background:var(--pa-primary-surface);
            color:var(--pa-primary-dark);font-size:.68rem;font-weight:700;
        }
        .pa-peer-pdf-focus span {color:var(--pa-text-muted);font-weight:500;}
        .st-key-peer_review_pdf_panel [data-testid="stVerticalBlock"] {gap:.35rem;}
        .pa-audit-list-head {
            display:flex;align-items:center;gap:.4rem;min-width:0;margin-bottom:.08rem;
        }
        .pa-audit-list-head > strong {
            padding:.12rem .32rem;border-radius:4px;background:var(--pa-primary-surface);color:var(--pa-primary-hover);
            font-size:.72rem;font-family:ui-monospace,SFMono-Regular,Consolas,monospace;
        }
        .pa-audit-list-head > span {font-size:.83rem;font-weight:700;color:var(--pa-text-primary);}
        .pa-audit-list-head > div {display:flex;gap:.25rem;margin-left:auto;}
        [class*="st-key-audit_claim_item_"] {
            padding:.55rem .62rem !important;margin-bottom:.35rem;border-color:var(--pa-border-medium) !important;
            border-radius:7px !important;background:var(--pa-bg);box-shadow:none;
        }
        [class*="st-key-audit_claim_item_active_"] {
            border-color:var(--pa-primary-action) !important;background:var(--pa-cyan-surface);
            box-shadow:0 0 0 1px rgba(22,119,255,.08);
        }
        [class*="st-key-audit_claim_item_"] .stButton {margin:.12rem 0 .05rem;}
        [class*="st-key-audit_claim_item_"] .stButton > button {
            min-height:0 !important;padding:.08rem 0 !important;border:0 !important;
            justify-content:flex-start;text-align:left;color:var(--pa-text-secondary);background:transparent !important;
            box-shadow:none !important;font-size:.76rem;line-height:1.4;
        }
        [class*="st-key-audit_claim_item_"] [data-testid="stCaptionContainer"] {
            font-size:.68rem;color:#7c8799;
        }
        .pa-audit-page-label {padding:.42rem 0;text-align:center;color:var(--pa-text-muted);font-size:.75rem;}
        .st-key-audit_selected_detail {
            min-height:39rem;padding:.8rem 1.05rem !important;border-color:var(--pa-border-medium) !important;
            border-radius:7px !important;background:var(--pa-bg);
        }
        .st-key-audit_selected_detail .pa-audit-detail-head {
            margin:-.1rem 0 .25rem;padding:0 0 .7rem;border-bottom:1px solid var(--pa-border);
        }
        .st-key-audit_selected_detail .pa-audit-detail-section {
            padding:.8rem 0;border-top:0;border-bottom:1px solid var(--pa-border-light);
        }
        div[data-testid="stExpander"]:has(.pa-audit-detail) {
            border:1px solid var(--pa-border);border-radius:9px;background:var(--pa-bg);
            margin-bottom:.45rem;box-shadow:none;
        }
        div[data-testid="stExpander"]:has(.pa-audit-detail) summary {
            padding:.65rem .8rem;color:var(--pa-text-body);font-size:.8rem;font-weight:650;
            line-height:1.45;
        }
        .pa-audit-detail {padding:.05rem .15rem .3rem;color:var(--pa-text-body);}
        .pa-audit-detail-head {
            display:flex;justify-content:space-between;align-items:center;
            gap:.6rem;flex-wrap:wrap;padding-bottom:.5rem;
        }
        .pa-audit-detail-section {
            width:100%;padding:.62rem 0;border-top:1px solid var(--pa-border-light);
        }
        .pa-audit-detail-label {
            margin-bottom:.28rem;color:var(--pa-text-muted);font-size:.68rem;font-weight:750;
            text-transform:uppercase;letter-spacing:.035em;
        }
        .pa-audit-detail-copy,.pa-audit-claim {max-width:100ch;}
        .pa-audit-detail-copy {color:var(--pa-text-secondary);font-size:.84rem;line-height:1.65;}
        .pa-audit-evidence-list {display:grid;gap:.5rem;width:100%;}
        .pa-audit-evidence-item {
            padding:.62rem .72rem;border-left:3px solid var(--pa-cyan-light);
            border-radius:0 7px 7px 0;background:var(--pa-cyan-surface);
        }
        .pa-audit-evidence-meta {
            color:var(--pa-primary-hover);font-size:.68rem;font-weight:750;margin-bottom:.28rem;
        }
        .pa-audit-evidence-text {
            color:var(--pa-text-body);font-size:.8rem;line-height:1.62;white-space:normal;
            overflow-wrap:anywhere;
        }
        .pa-audit-empty-inline {
            display:inline-block;padding:.42rem .58rem;border-radius:6px;
            background:var(--pa-surface);color:var(--pa-text-muted);font-size:.78rem;
        }
        .pa-audit-empty {
            display:flex;flex-direction:column;gap:.2rem;align-items:flex-start;
            padding:1.15rem;border:1px dashed var(--pa-border-strong);border-radius:9px;
            background:var(--pa-surface);color:var(--pa-text-muted);margin:.4rem 0 .55rem;
        }
        .pa-audit-empty strong {color:var(--pa-text-body);font-size:.88rem;}
        .pa-audit-empty span {font-size:.76rem;}
        .pa-learning-hero {
            padding:.7rem .95rem; border:1px solid var(--pa-primary-light); border-left:4px solid var(--pa-primary);
            border-radius:0 12px 12px 0; background:linear-gradient(135deg,var(--pa-primary-surface),var(--pa-surface));
            margin-bottom:.25rem;
        }
        .pa-learning-eyebrow {color:var(--pa-primary); font-size:.75rem; font-weight:700; margin-bottom:.25rem;}
        .pa-learning-title {color:var(--pa-text-heading); font-size:1.25rem; font-weight:700; line-height:1.4;}
        .pa-learning-summary {color:var(--pa-text-secondary); margin-top:.5rem; line-height:1.6;}
        .st-key-learning_primary_nav {
            position:relative;top:auto;z-index:999991;height:46px;min-height:46px;
            padding:0;
            box-sizing:border-box;width:min(100%,1580px);margin:0 auto;
            border-bottom:1px solid var(--pa-border-divider);background:rgba(255,255,255,.98);
            backdrop-filter:blur(10px);overflow:visible;
        }
        .st-key-learning_primary_nav [data-testid="stHorizontalBlock"] {overflow:visible;}
        .st-key-learning_primary_nav {gap:0 !important;}
        .st-key-learning_primary_nav > [data-testid="stLayoutWrapper"]
        > [data-testid="stHorizontalBlock"] {
            display:flex !important;justify-content:space-between !important;
            width:100% !important;gap:.75rem !important;align-items:center !important;height:100% !important;
        }
        .st-key-learning_primary_nav > [data-testid="stLayoutWrapper"]
        > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child {
            flex:1 1 auto !important;min-width:0 !important;
        }
        .st-key-learning_primary_nav > [data-testid="stLayoutWrapper"]
        > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2) {
            flex:0 0 auto !important;width:auto !important;min-width:200px !important;
        }
        .st-key-learning_primary_nav > [data-testid="stLayoutWrapper"]
        > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:last-child {
            flex:0 0 auto !important;width:auto !important;margin-left:auto !important;
        }
        .st-key-learning_primary_nav [role="radiogroup"] {
            display:inline-flex !important;align-items:center !important;
            min-height:34px !important;height:34px !important;padding:2px !important;
            border:1px solid var(--pa-border-medium) !important;border-radius:var(--pa-radius-md) !important;
            background:var(--pa-surface) !important;box-shadow:none !important;
        }
        .st-key-learning_primary_nav [role="radio"] {
            display:inline-flex !important;align-items:center !important;justify-content:center !important;
            min-height:28px !important;height:28px !important;padding:0 .75rem !important;
            border-radius:var(--pa-radius-sm) !important;border:0 !important;
            background:transparent !important;color:var(--pa-text-secondary) !important;
            font-size:.76rem !important;font-weight:600 !important;box-shadow:none !important;
            transition:all var(--pa-transition-fast) !important;
        }
        .st-key-learning_primary_nav [role="radio"]:hover {
            color:var(--pa-text-primary) !important;background:rgba(15,23,42,.03) !important;
        }
        .st-key-learning_primary_nav [role="radio"][aria-checked="true"] {
            background:var(--pa-bg) !important;color:var(--pa-success-dark) !important;
            font-weight:750 !important;border:0 !important;
            box-shadow:0 1px 3px rgba(15,23,42,.08) !important;
        }
        .st-key-learning_primary_nav [data-testid="stPopover"] {
            display:inline-block !important;margin-left:auto !important;
        }
        .st-key-learning_primary_nav [data-testid="stPopover"] button {
            min-height:32px;height:32px;border-radius:8px;font-size:.75rem;font-weight:650;
            border:1px solid var(--pa-border);background:var(--pa-bg);
            box-shadow:var(--pa-shadow-xs);
        }
        .st-key-learning_primary_nav [data-testid="stProgress"] {margin:0;}
        .st-key-learning_primary_nav [data-testid="stCaptionContainer"] {
            margin:0;font-size:.68rem;line-height:1.25;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
        }
        .st-key-learning_primary_nav [data-testid="stButton"] button {
            min-height:28px;height:28px;padding:0 .45rem;font-size:.68rem;border-radius:var(--pa-radius-sm);
        }
        .st-key-learning_primary_nav [data-testid="stButton"] button p {white-space:nowrap;}
        .st-key-learning_primary_nav [data-testid="stHorizontalBlock"]:has(.pa-workspace-header) {
            flex-wrap:nowrap !important;
        }
        .pa-workspace-header {
            display:flex;align-items:center;gap:.7rem;min-width:0;padding:.06rem 0;
        }
        .pa-workspace-brand-icon {
            display:grid;place-items:center;flex:0 0 22px;width:22px;height:22px;
            border:0;border-radius:4px;background:var(--pa-success-surface);color:var(--pa-success-muted);
            font-size:.8rem;font-weight:800;line-height:1;
        }
        .pa-workspace-copy {flex:1 1 auto;min-width:0;}
        .pa-workspace-title-row {min-width:0;display:flex;align-items:baseline;gap:.7rem;}
        .pa-workspace-title {
            color:var(--pa-text-primary);font-size:1rem;font-weight:760;line-height:1.35;
            flex:0 1 auto;max-width:48%;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
        }
        .pa-workspace-summary {
            flex:1 1 auto;min-width:0;max-width:360px;margin:0;color:var(--pa-text-muted);font-size:.75rem;line-height:1.25;
            white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
        }
        .pa-panel-title {
            color:var(--pa-text-primary);font-size:.88rem;font-weight:750;line-height:2.2rem;
            white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
        }
        .pa-panel-title span {color:var(--pa-text-faint);font-size:.7rem;font-weight:500;margin-left:.28rem;}
        .pa-workspace-status {
            display:flex;align-items:center;gap:.42rem;color:var(--pa-text-muted);font-size:.72rem;
            min-height:2rem;white-space:nowrap;overflow:hidden;
        }
        .pa-workspace-status span {
            width:.45rem;height:.45rem;border-radius:50%;background:var(--pa-success);
            box-shadow:0 0 0 3px var(--pa-success-light);animation:pa-pulse 2.5s ease-in-out infinite;flex:0 0 auto;
        }
        .pa-workspace-status strong {
            color:var(--pa-text-secondary);font-size:.72rem;font-weight:700;flex:0 0 auto;
        }
        .pa-workspace-status em {
            color:var(--pa-text-faint);font-size:.68rem;font-style:normal;overflow:hidden;
            text-overflow:ellipsis;
        }
        .st-key-joint_workspace_nav {
            box-sizing:border-box;width:100%;margin:.35rem 0 .5rem;padding:.22rem .45rem;
            border:1px solid var(--pa-border-divider);border-radius:10px;background:var(--pa-surface);
        }
        .st-key-joint_workspace_nav > [data-testid="stLayoutWrapper"]
        > [data-testid="stHorizontalBlock"] {
            align-items:center !important;gap:.65rem !important;
        }
        .st-key-joint_workspace_nav [data-testid="stColumn"] {min-width:0 !important;}
        .st-key-joint_workspace_nav [role="radiogroup"] {
            width:360px !important;max-width:100% !important;margin-left:auto !important;
            min-height:30px !important;height:30px !important;padding:2px !important;
            border:1px solid var(--pa-border-medium) !important;border-radius:8px !important;
            background:var(--pa-bg) !important;box-shadow:none !important;
        }
        .st-key-joint_workspace_nav [role="radio"] {
            min-height:24px !important;height:24px !important;padding:0 .8rem !important;
            border-radius:6px !important;font-size:.72rem !important;font-weight:600 !important;
        }
        .st-key-joint_workspace_nav [role="radio"][aria-checked="true"] {
            background:var(--pa-primary-surface) !important;color:var(--pa-primary) !important;
            box-shadow:0 1px 2px rgba(15,23,42,.08) !important;
        }
        .st-key-audit_activity_strip {
            box-sizing:border-box;width:min(100%,1580px);margin:0 auto;padding:.2rem .5rem;
            border:1px solid var(--pa-primary-border);border-radius:var(--pa-radius-md);
            background:var(--pa-primary-surface);min-height:0;
        }
        [data-testid="stElementContainer"]:has(.st-key-audit_activity_strip) {
            margin:0 !important;padding:0 !important;min-height:0 !important;
        }
        .st-key-audit_activity_strip [data-testid="stProgress"] {margin:0;}
        .st-key-audit_activity_strip [data-testid="stCaptionContainer"] {margin:0;font-size:.74rem;}
        .pa-audit-compact-message {
            position:relative;top:.38rem;min-width:0;overflow:hidden;text-overflow:ellipsis;
            white-space:nowrap;color:var(--pa-text-muted);font-size:.68rem;line-height:1.2;
        }
        .st-key-audit_activity_compact [data-testid="stHorizontalBlock"]:has(.pa-audit-compact-message) {
            justify-content:flex-start !important;gap:.45rem !important;
        }
        .st-key-audit_activity_compact [data-testid="stHorizontalBlock"]:has(.pa-audit-compact-message)
        > [data-testid="stColumn"]:first-child {
            flex:0 1 auto !important;width:auto !important;min-width:0 !important;
        }
        .st-key-audit_activity_compact [data-testid="stHorizontalBlock"]:has(.pa-audit-compact-message)
        > [data-testid="stColumn"]:last-child {
            flex:0 0 auto !important;width:auto !important;min-width:max-content !important;
        }
        .pa-learning-nav-marker,.pa-learning-source-marker,.pa-learning-point-marker {display:none;}
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.pa-learning-nav-marker) {
            position:sticky; top:3.2rem;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.pa-learning-nav-marker),
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.pa-learning-source-marker) {
            border-radius:12px; border-color:var(--pa-border-medium); background:var(--pa-bg);
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.pa-learning-point-marker) {
            border-color:var(--pa-border); border-radius:11px; background:var(--pa-bg); margin-bottom:.6rem;
        }
        .pa-learning-nav-link {
            display:block; padding:.45rem .55rem; margin:.12rem 0; border-radius:6px;
            color:var(--pa-text-secondary) !important; text-decoration:none !important; font-size:.84rem;
        }
        .pa-learning-nav-link:hover {color:var(--pa-primary-hover) !important; background:var(--pa-primary-surface);}
        .pa-learning-section-anchor {scroll-margin-top:4rem;}
        .st-key-learning_section_bar {
            height:40px;padding:0 .25rem;margin:0;border:0;border-bottom:1px solid var(--pa-border-divider);
            border-radius:10px 10px 0 0;background:var(--pa-bg);position:relative;top:auto;z-index:11;
            box-shadow:none;
        }
        .st-key-learning_section_bar [role="radiogroup"] {
            height:40px;gap:0 !important;border:0 !important;border-radius:0 !important;
            flex-wrap:nowrap !important;
            background:transparent !important;overflow-x:auto;scrollbar-width:none;
        }
        .st-key-learning_section_bar [role="radiogroup"]::-webkit-scrollbar {display:none;}
        .st-key-learning_section_bar [role="radio"],
        .st-key-learning_section_bar button {
            height:40px;min-height:40px;min-width:0 !important;flex:1 1 0 !important;
            padding:.1rem 0 !important;
            border:0 !important;border-radius:0 !important;background:transparent !important;
            box-shadow:none !important;color:var(--pa-text-secondary) !important;font-weight:560;
            font-size:.72rem !important;white-space:nowrap !important;overflow:hidden !important;
        }
        .st-key-learning_section_bar [role="radio"] p,
        .st-key-learning_section_bar button p {
            margin:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
            font-size:.72rem !important;
        }
        .st-key-learning_section_bar [role="radio"][aria-checked="true"],
        .st-key-learning_section_bar button[aria-checked="true"] {
            color:var(--pa-success-muted) !important;font-weight:700 !important;
            box-shadow:inset 0 -2px 0 var(--pa-success-muted) !important;
        }
        .st-key-learning_section_bar [data-testid="stCaptionContainer"] {display:none;}
        .st-key-learning_explanation_header {
            min-height:42px;padding:.22rem .9rem;margin:0;border-bottom:1px solid var(--pa-border-divider);
            background:var(--pa-bg);box-sizing:border-box;
        }
        .st-key-learning_explanation_header > [data-testid="stVerticalBlock"] {gap:0;}
        .pa-explanation-panel-title {
            color:var(--pa-text-heading);font-size:.8rem;font-weight:700;line-height:2rem;white-space:nowrap;
        }
        .st-key-learning_explanation_header [role="radiogroup"] {
            min-height:32px;border-color:var(--pa-border);background:var(--pa-surface);
        }
        .pa-learning-topic-card {
            background:var(--pa-bg);border:1px solid var(--pa-border-medium);
            border-radius:var(--pa-radius-lg);padding:.85rem 1rem .65rem;margin-bottom:.85rem;
            box-shadow:var(--pa-shadow-xs);
        }
        .pa-learning-topic-title {
            color:var(--pa-text-heading);font-size:.95rem;font-weight:750;line-height:1.4;margin:0 0 .3rem 0;
        }
        .pa-learning-bullet-item {
            position:relative;padding-left:.85rem;margin-bottom:.8rem;
            border-left:2px solid var(--pa-primary-light);
        }
        .pa-learning-bullet-item.is-active {
            border-left-color:var(--pa-primary);
        }
        .pa-learning-bullet-title {
            color:var(--pa-text-heading);font-size:.84rem;font-weight:700;line-height:1.4;
            display:flex;align-items:center;gap:.35rem;margin-bottom:.2rem;
        }
        .pa-learning-bullet-title.is-active {
            color:var(--pa-primary-hover);
        }
        .pa-bullet-dot {
            color:var(--pa-primary);font-size:.9rem;line-height:1;
        }
        .pa-learning-bullet-text {
            color:var(--pa-text-secondary);font-size:.8rem;line-height:1.58;margin-bottom:.4rem;
        }
        .pa-learning-section-kicker {
            color:var(--pa-primary);font-size:.7rem;font-weight:700;letter-spacing:.04em;margin-bottom:.18rem;
        }
        .pa-learning-section-title {
            color:var(--pa-text-heading);font-size:1.18rem;line-height:1.4;margin:.04rem 0 .32rem;
        }
        .pa-learning-section-overview {
            color:var(--pa-text-secondary);font-size:.8rem;line-height:1.6;margin-bottom:.2rem;
        }
        .pa-learning-block-heading {
            color:var(--pa-text-muted);font-size:.7rem;font-weight:750;letter-spacing:.05em;
            text-transform:uppercase;margin:.8rem 0 .1rem;
        }
        .pa-learning-key {
            display:inline-flex;align-items:center;gap:4px;
            padding:2px 8px;margin-bottom:0.4rem;
            border:1px solid var(--pa-primary-border); border-radius:var(--pa-radius-pill);
            background:linear-gradient(135deg, var(--pa-primary-surface), #e0e7ff);
            color:var(--pa-primary);font-size:.66rem;font-weight:700;
            letter-spacing:.02em;
        }
        div[class*="st-key-learning_point_"] {
            position:relative;margin-bottom:0.75rem;padding:0.75rem 0.85rem;
            border:1px solid var(--pa-border);border-left:3px solid var(--pa-primary-light);
            border-radius:var(--pa-radius-md);background:var(--pa-bg);
            box-shadow:var(--pa-shadow-xs);
            transition:transform var(--pa-transition-fast), box-shadow var(--pa-transition-fast), border-color var(--pa-transition-fast);
        }
        div[class*="st-key-learning_point_"]:hover {
            transform:translateY(-1px);
            box-shadow:var(--pa-shadow-md);
            border-color:var(--pa-primary-border);
        }
        .pa-learning-point-marker {display:none;}
        .pa-learning-point-marker.is-active {
            display:block;position:absolute;left:-3px;top:0;bottom:0;width:3px;
            border-radius:3px 0 0 3px;background:var(--pa-primary-hover);
        }
        .pa-learning-point-title {
            margin:0.15rem 0 0.35rem;color:var(--pa-text-heading);font-size:.93rem;font-weight:700;line-height:1.4;
        }
        .pa-learning-point-title.is-active {color:var(--pa-primary-hover);}
        div[class*="st-key-learning_point_"] p {
            color:var(--pa-text-secondary);font-size:.82rem;line-height:1.62;margin-bottom:.4rem;
        }
        div[class*="st-key-learning_point_"] [data-testid="stBaseButton-tertiary"] {
            min-height:1.85rem;padding:0.2rem 0.6rem;color:var(--pa-primary);font-size:.71rem;
            font-weight:600;
            background:var(--pa-primary-surface);border:1px solid var(--pa-primary-border);
            border-radius:var(--pa-radius-pill);
            transition:all var(--pa-transition-fast);
        }
        div[class*="st-key-learning_point_"] [data-testid="stBaseButton-tertiary"]:hover {
            color:var(--pa-primary-hover);background:var(--pa-primary-light);
            border-color:var(--pa-primary);transform:translateY(-1px);
            box-shadow:0 2px 6px rgba(37,99,235,0.15);
        }
        .st-key-learning_section_support {padding:.15rem .2rem .55rem;}
        .pa-learning-guide {
            display:flex;flex-direction:column;gap:.22rem;padding:.65rem .72rem;
            border-radius:var(--pa-radius-md);background:var(--pa-surface);color:var(--pa-text-secondary);
            border:1px solid var(--pa-border-light);
        }
        .pa-learning-guide strong {color:var(--pa-text-body);font-size:.72rem;}
        .pa-learning-guide span {font-size:.78rem;line-height:1.55;}
        .pa-learning-concepts-label,.pa-learning-recommend-label {
            color:var(--pa-text-muted);font-size:.7rem;font-weight:700;margin:.72rem 0 .35rem;
        }
        .pa-learning-concepts {display:flex;gap:.35rem;flex-wrap:wrap;}
        .pa-learning-concepts span {
            display:inline-flex;max-width:100%;padding:.2rem .55rem;border:1px solid var(--pa-border);
            border-radius:var(--pa-radius-pill);background:var(--pa-bg);color:var(--pa-text-secondary);font-size:.68rem;
            font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
            transition:all var(--pa-transition-fast);
        }
        .pa-learning-concepts span:hover {
            border-color:var(--pa-primary-border);color:var(--pa-primary);
        }
        .st-key-learning_section_support [data-testid="stBaseButton-tertiary"] {
            justify-content:flex-start;min-height:1.85rem;padding:.18rem .4rem;
            color:var(--pa-text-secondary);font-size:.73rem;text-align:left;
            border-radius:var(--pa-radius-sm);
        }
        .st-key-learning_section_support [data-testid="stBaseButton-tertiary"]:hover {
            color:var(--pa-primary-hover);background:var(--pa-primary-surface);
        }
        .st-key-learning_section_followup {
            position:relative;z-index:6;flex:0 0 auto;padding:.35rem .75rem .55rem;
            background:linear-gradient(to bottom,rgba(255,255,255,.72),var(--pa-bg) 28%);
        }
        div[data-testid="stForm"]:has(.pa-learning-followup-form-marker) {
            border:1px solid var(--pa-border-medium);padding:.45rem;background:var(--pa-bg);border-radius:var(--pa-radius-lg);
            box-shadow:var(--pa-shadow-up);
        }
        .pa-learning-source-text {
            padding:.85rem; margin-bottom:.75rem; border-left:3px solid var(--pa-cyan);
            border-radius:0 var(--pa-radius-md) var(--pa-radius-md) 0; background:var(--pa-cyan-surface); color:var(--pa-text-body);
            font-size:.84rem; line-height:1.6; white-space:pre-wrap; overflow-wrap:anywhere;
        }
        .pa-learning-context-text {
            color:var(--pa-text-secondary); font-size:.8rem; line-height:1.55;
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
            position:relative;min-height:0;border:1px solid var(--pa-border-medium);border-radius:10px;
            background:var(--pa-bg);overflow:hidden;
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

        /* The optimized lecture workspace uses a fixed-width detail rail and
           lets the PDF reader fill the remaining main-column width.  The
           keyed containers below are Streamlit's wrappers around the two
           columns; constraining both levels keeps long reports from expanding
           the whole page. */
        body:has(.st-key-learning_primary_nav) .stApp,
        body:has(.st-key-learning_primary_nav) [data-testid="stAppViewContainer"],
        body:has(.st-key-learning_primary_nav) [data-testid="stMain"] {
            height:100vh !important;max-height:100vh !important;
            overflow:hidden !important;
        }
        .block-container:has(.st-key-learning_primary_nav) > [data-testid="stVerticalBlock"] {
            height:100%;min-height:0;display:flex;flex-direction:column;
            gap:8px !important;overflow:hidden;
        }
        .block-container:has(.st-key-learning_primary_nav) > [data-testid="stVerticalBlock"]
        > [data-testid="stLayoutWrapper"]:has(.st-key-learning_primary_nav),
        .block-container:has(.st-key-learning_primary_nav) > [data-testid="stVerticalBlock"]
        > [data-testid="stLayoutWrapper"]:has(.st-key-audit_activity_strip) {
            flex:0 0 auto !important;min-height:0 !important;
        }
        .block-container:has(.st-key-learning_primary_nav) > [data-testid="stVerticalBlock"]
        > [data-testid="stLayoutWrapper"]:has(.st-key-learning_source_panel) {
            flex:1 1 0 !important;min-height:0 !important;overflow:hidden;
        }
        [data-testid="stHorizontalBlock"]:has(.st-key-learning_source_panel) {
            align-items:stretch !important;min-height:0 !important;height:100% !important;
            max-height:none !important;gap:1rem !important;
            width:min(100%, 1580px) !important;margin-inline:auto;
        }
        [data-testid="stHorizontalBlock"]:has(.st-key-learning_source_panel)
        > [data-testid="stColumn"]:has(.st-key-learning_source_panel) {
            flex:1 1 0 !important;width:auto !important;min-width:0 !important;
            min-height:0 !important;height:100% !important;max-height:none !important;
            align-self:stretch !important;
        }
        [data-testid="stHorizontalBlock"]:has(.st-key-learning_source_panel)
        > [data-testid="stColumn"]:has([class*="st-key-learning_report_scroll_"]),
        [data-testid="stHorizontalBlock"]:has(.st-key-learning_source_panel)
        > [data-testid="stColumn"]:has([class*="st-key-learning_page_context_scroll_"]) {
            flex:0 1 clamp(360px,22vw,420px) !important;
            width:clamp(360px,22vw,420px) !important;
            max-width:420px !important;min-width:360px !important;
            min-height:0 !important;height:100% !important;max-height:none !important;
            align-self:stretch !important;
            display:flex !important;flex-direction:column;overflow:hidden;
        }
        [data-testid="stHorizontalBlock"]:has(.st-key-learning_source_panel)
        > [data-testid="stColumn"]:has([class*="st-key-learning_report_scroll_"]) > [data-testid="stVerticalBlock"],
        [data-testid="stHorizontalBlock"]:has(.st-key-learning_source_panel)
        > [data-testid="stColumn"]:has([class*="st-key-learning_page_context_scroll_"]) > [data-testid="stVerticalBlock"] {
            display:flex !important;flex-direction:column;min-height:0 !important;
            height:100% !important;overflow:hidden;
        }
        [data-testid="stHorizontalBlock"]:has(.st-key-learning_source_panel)
        [class*="st-key-learning_report_scroll_"],
        [data-testid="stHorizontalBlock"]:has(.st-key-learning_source_panel)
        [class*="st-key-learning_page_context_scroll_"] {
            flex:1 1 0 !important;height:auto !important;min-height:0 !important;
            overflow-y:auto !important;overflow-x:hidden;
        }
        [data-testid="stHorizontalBlock"]:has(.st-key-learning_source_panel)
        .st-key-learning_section_followup {
            flex:0 0 auto !important;position:sticky;bottom:0;z-index:6;
            margin-top:auto;padding-bottom:.7rem;
        }
        [data-testid="stHorizontalBlock"]:has(.st-key-learning_source_panel)
        > [data-testid="stColumn"]:has(.st-key-learning_source_panel) > [data-testid="stVerticalBlock"] {
            min-height:0 !important;height:100% !important;display:flex !important;
            flex-direction:column;
        }
        [data-testid="stHorizontalBlock"]:has(.st-key-learning_source_panel)
        > [data-testid="stColumn"]:has(.st-key-learning_source_panel)
        > [data-testid="stVerticalBlock"] > [data-testid="stLayoutWrapper"]:has(.st-key-learning_section_bar) {
            flex:0 0 auto !important;min-height:0 !important;
        }
        [data-testid="stHorizontalBlock"]:has(.st-key-learning_source_panel)
        > [data-testid="stColumn"]:has(.st-key-learning_source_panel)
        > [data-testid="stVerticalBlock"] > [data-testid="stLayoutWrapper"]:has(.st-key-learning_source_panel) {
            flex:1 1 0 !important;min-height:0 !important;overflow:hidden;
        }
        [data-testid="stHorizontalBlock"]:has(.st-key-learning_source_panel)
        .st-key-learning_source_panel {min-height:0;}
        .pa-page-relation {
            display:flex;flex-direction:column;gap:.28rem;padding:.72rem .8rem;margin:.3rem 0 .7rem;
            border-left:3px solid var(--pa-primary);border-radius:0 8px 8px 0;background:var(--pa-surface);
            color:var(--pa-text-secondary);font-size:.78rem;line-height:1.58;
        }
        .pa-page-relation strong {color:var(--pa-text-primary);font-size:.72rem;}
        .pa-page-point-section {
            color:var(--pa-primary);font-size:.66rem;font-weight:700;margin:0 0 .18rem;
        }
        div[class*="st-key-learning_page_point_"] {
            padding:.72rem .15rem .82rem;border-bottom:1px solid var(--pa-border);
        }
        .pa-logic-node {
            position:relative;margin:0.4rem 0 0.6rem;padding:0.6rem 0.8rem;
            border-left:3px solid var(--pa-cyan);border-radius:0 var(--pa-radius-md) var(--pa-radius-md) 0;
            background:var(--pa-cyan-surface);border-top:1px solid var(--pa-border-light);
            border-right:1px solid var(--pa-border-light);border-bottom:1px solid var(--pa-border-light);
            transition:transform var(--pa-transition-fast);
        }
        .pa-logic-node:hover {
            transform:translateX(2px);
        }
        .pa-logic-node span {
            display:inline-block;padding:1px 6px;margin-bottom:0.25rem;
            background:var(--pa-primary-surface);color:var(--pa-primary);
            border-radius:var(--pa-radius-xs);font-size:.64rem;font-weight:700;
        }
        .pa-logic-node strong {display:block;color:var(--pa-text-heading);font-size:.82rem;line-height:1.4;}
        .pa-logic-node p {color:var(--pa-text-secondary);font-size:.76rem;line-height:1.52;margin:.25rem 0 0;}
        div[class*="st-key-learning_page_point_"] [data-testid="stBaseButton-tertiary"],
        [class*="st-key-learning_page_context_scroll_"] [data-testid="stBaseButton-tertiary"] {
            min-height:1.8rem;padding:.16rem .38rem;border:1px solid var(--pa-primary-light);
            border-radius:999px;background:var(--pa-cyan-surface);color:var(--pa-primary);font-size:.68rem;
        }
        .st-key-learning_nav_panel {
            position:sticky;top:4rem;align-self:flex-start;
        }
        .st-key-learning_source_panel,.st-key-qa_source_panel {
            position:relative;top:auto;align-self:flex-start;
        }
        .st-key-learning_source_panel {
            padding:.35rem .5rem .6rem;border:1px solid var(--pa-border-medium);background:var(--pa-surface);
            border-radius:var(--pa-radius-lg);
            height:100% !important;min-height:0 !important;overflow:hidden;
            gap:.4rem !important;box-shadow:var(--pa-shadow-xs);
        }
        .st-key-learning_pdf_toolbar,.st-key-qa_pdf_toolbar {
            position:sticky;top:0;z-index:8;padding:.35rem .5rem;
            min-height:42px;flex:0 0 auto;
            border-bottom:1px solid var(--pa-border);background:var(--pa-bg);
            border-radius:var(--pa-radius-md) var(--pa-radius-md) 0 0;
        }
        .st-key-learning_pdf_toolbar [data-testid="stHorizontalBlock"],
        .st-key-qa_pdf_toolbar [data-testid="stHorizontalBlock"] {
            gap:.5rem !important;align-items:center;justify-content:flex-start;
            flex-wrap:nowrap !important;overflow:visible;
        }
        .st-key-learning_pdf_toolbar [data-testid="stHorizontalBlock"] > [data-testid="stColumn"],
        .st-key-qa_pdf_toolbar [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
            flex:0 0 auto !important;width:auto !important;min-width:0 !important;
        }
        .st-key-learning_pdf_toolbar [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child,
        .st-key-qa_pdf_toolbar [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child {
            flex:0 1 clamp(9rem, 16vw, 14rem) !important;
            min-width:9rem !important;
        }
        .st-key-learning_pdf_toolbar [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2),
        .st-key-learning_pdf_toolbar [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(4),
        .st-key-learning_pdf_toolbar [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(5),
        .st-key-learning_pdf_toolbar [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(7),
        .st-key-qa_pdf_toolbar [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2),
        .st-key-qa_pdf_toolbar [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(4),
        .st-key-qa_pdf_toolbar [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(5),
        .st-key-qa_pdf_toolbar [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(7) {
            flex-basis:2.5rem !important;width:2.5rem !important;
        }
        .st-key-learning_pdf_toolbar [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(3),
        .st-key-qa_pdf_toolbar [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(3) {
            flex-basis:7rem !important;width:7rem !important;
        }
        .st-key-learning_pdf_toolbar [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(6),
        .st-key-qa_pdf_toolbar [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(6) {
            flex-basis:3.5rem !important;width:3.5rem !important;
        }
        .st-key-learning_pdf_toolbar [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:last-child,
        .st-key-qa_pdf_toolbar [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:last-child {
            flex-basis:7.5rem !important;width:7.5rem !important;
        }
        .st-key-learning_pdf_toolbar [data-testid="stHorizontalBlock"] [data-testid="stHorizontalBlock"],
        .st-key-qa_pdf_toolbar [data-testid="stHorizontalBlock"] [data-testid="stHorizontalBlock"] {
            display:flex !important;gap:.25rem !important;align-items:center;
            width:100% !important;min-width:0 !important;
        }
        .st-key-learning_pdf_toolbar [data-testid="stHorizontalBlock"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"],
        .st-key-qa_pdf_toolbar [data-testid="stHorizontalBlock"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
            flex:0 0 auto !important;width:auto !important;min-width:0 !important;
        }
        .st-key-learning_pdf_toolbar [data-testid="stHorizontalBlock"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child,
        .st-key-qa_pdf_toolbar [data-testid="stHorizontalBlock"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child {
            flex:1 1 0 !important;min-width:0 !important;
        }
        .st-key-learning_pdf_toolbar [data-testid="stHorizontalBlock"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:last-child,
        .st-key-qa_pdf_toolbar [data-testid="stHorizontalBlock"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:last-child {
            flex:0 0 2.5rem !important;width:2.5rem !important;
        }
        .st-key-learning_pdf_toolbar [data-testid="stColumn"],
        .st-key-qa_pdf_toolbar [data-testid="stColumn"] {min-width:0 !important;}
        .st-key-learning_pdf_toolbar button,
        .st-key-qa_pdf_toolbar button {
            min-height:1.85rem;height:1.85rem;padding:0 .4rem !important;white-space:nowrap;
            border-radius:var(--pa-radius-sm) !important;
            border:1px solid var(--pa-border) !important;
            background:var(--pa-surface) !important;
            color:var(--pa-text-primary) !important;
            box-shadow:none !important;
            transition:all var(--pa-transition-fast);
        }
        .st-key-learning_pdf_toolbar button:hover,
        .st-key-qa_pdf_toolbar button:hover {
            background:var(--pa-bg) !important;
            border-color:var(--pa-primary-border) !important;
            color:var(--pa-primary) !important;
        }
        .st-key-learning_pdf_toolbar button p,
        .st-key-qa_pdf_toolbar button p {font-size:.73rem;font-weight:600;white-space:nowrap;}
        .pa-pdf-panel-title {
            display:flex;align-items:center;gap:.3rem;font-weight:750;color:var(--pa-text-heading);
            font-size:.82rem;margin:0;line-height:1.8rem;
        }
        .pa-pdf-panel-title span {font-size:.7rem;font-weight:500;color:var(--pa-text-muted);}
        .pa-pdf-page-total {
            color:var(--pa-text-muted);font-size:.72rem;line-height:1.8rem;white-space:nowrap;font-weight:600;
        }
        .pa-pdf-zoom {color:var(--pa-text-body);font-size:.74rem;font-weight:650;text-align:center;line-height:1.8rem;white-space:nowrap;}
        .st-key-learning_source_panel [data-testid="stImage"] img,
        .st-key-qa_source_panel [data-testid="stImage"] img {
            width:100%;max-height:min(72vh,900px);object-fit:contain;
            border:1px solid var(--pa-border);border-radius:7px;background:var(--pa-bg);
        }
        .st-key-learning_source_panel > .st-key-learning-selectable-pdf {
            flex:1 1 0 !important;min-height:0 !important;overflow:hidden;
            display:flex;flex-direction:column;
        }
        .st-key-learning_source_panel .st-key-learning-selectable-pdf,
        .st-key-learning_source_panel .st-key-learning-selectable-pdf [data-testid="stBidiComponent"],
        .st-key-learning_source_panel .st-key-learning-selectable-pdf [data-testid="stBidiComponentRegular"] {
            flex:1 1 0 !important;height:100% !important;min-height:0 !important;
            max-height:none !important;overflow:hidden;
        }
        .st-key-learning_source_panel .st-key-learning-selectable-pdf
        [data-testid="stBidiComponentRegular"] > div,
        .st-key-learning_source_panel .st-key-learning-selectable-pdf
        [data-testid="stBidiComponentRegular"] > div > div {
            height:100% !important;min-height:0 !important;overflow:hidden;
        }
        .st-key-learning_source_panel .pa-selectable-pdf {
            height:100% !important;min-height:0 !important;max-height:none !important;
            overflow-y:auto !important;overflow-x:auto;
        }
        .block-container:has(.st-key-learning_primary_nav) > [data-testid="stVerticalBlock"]
        > [data-testid="stLayoutWrapper"]:has(.st-key-qa_source_panel) {
            flex:1 1 0 !important;min-height:0 !important;overflow:hidden;
        }
        [data-testid="stHorizontalBlock"]:has(.st-key-qa_source_panel) {
            align-items:stretch !important;min-height:0 !important;height:100% !important;
            width:min(100%,1580px) !important;margin-inline:auto;gap:1rem !important;
        }
        [data-testid="stHorizontalBlock"]:has(.st-key-qa_source_panel)
        > [data-testid="stColumn"] {
            min-width:0 !important;min-height:0 !important;height:100% !important;
            display:flex !important;flex-direction:column;
        }
        [data-testid="stHorizontalBlock"]:has(.st-key-qa_source_panel)
        > [data-testid="stColumn"]:has(.st-key-qa_source_panel) {
            flex:1 1 0 !important;width:auto !important;
        }
        [data-testid="stHorizontalBlock"]:has(.st-key-qa_source_panel)
        > [data-testid="stColumn"]:has(.st-key-qa_conversation_panel) {
            flex:0 1 clamp(420px,26vw,520px) !important;
            width:clamp(420px,26vw,520px) !important;
            min-width:420px !important;max-width:520px !important;
        }
        .st-key-qa_source_panel {
            display:flex !important;flex-direction:column;flex:1 1 0 !important;
            height:100% !important;min-height:0 !important;overflow:hidden;
        }
        .st-key-qa_source_panel > .st-key-qa-selectable-pdf {
            display:flex !important;flex:1 1 0 !important;min-height:0 !important;
            overflow:hidden;
        }
        .st-key-qa_source_panel .st-key-qa-selectable-pdf,
        .st-key-qa_source_panel .st-key-qa-selectable-pdf [data-testid="stBidiComponent"],
        .st-key-qa_source_panel .st-key-qa-selectable-pdf [data-testid="stBidiComponentRegular"] {
            flex:1 1 0 !important;height:100% !important;min-height:0 !important;
            max-height:none !important;overflow:hidden;
        }
        .st-key-qa_source_panel .st-key-qa-selectable-pdf
        [data-testid="stBidiComponentRegular"] > div,
        .st-key-qa_source_panel .st-key-qa-selectable-pdf
        [data-testid="stBidiComponentRegular"] > div > div {
            height:100% !important;min-height:0 !important;overflow:hidden;
        }
        .st-key-qa_source_panel .pa-selectable-pdf {
            height:100% !important;min-height:0 !important;max-height:none !important;
            overflow-y:auto !important;overflow-x:auto;
        }
        [data-testid="stLayoutWrapper"]:has(> .st-key-qa_source_panel),
        [data-testid="stLayoutWrapper"]:has(> .st-key-qa_conversation_panel) {
            flex:1 1 0 !important;height:100% !important;min-height:0 !important;
            display:flex !important;flex-direction:column;
        }
        .st-key-qa_conversation_panel > [data-testid="stLayoutWrapper"]:has(.st-key-qa_history_scroll) {
            flex:1 1 0 !important;height:100% !important;min-height:0 !important;
            overflow:hidden;display:flex;flex-direction:column;
        }
        .st-key-qa_conversation_panel {
            display:flex !important;flex-direction:column;height:100% !important;
            min-height:0 !important;overflow:hidden;
        }
        .st-key-qa_conversation_panel .st-key-qa_history_scroll {
            flex:1 1 0 !important;height:auto !important;max-height:none !important;
            min-height:0 !important;overflow-y:auto !important;overflow-x:hidden;
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
            border:1px solid var(--pa-primary-light);border-radius:9px;background:var(--pa-cyan-surface);color:var(--pa-text-secondary);font-size:.84rem;
        }
        .pa-qa-question {
            padding:.65rem .8rem;border-radius:9px;background:var(--pa-surface-alt);color:var(--pa-text-primary);
            font-weight:600;line-height:1.5;margin-bottom:.65rem;
        }
        .pa-qa-answer-head {display:flex;align-items:center;gap:.5rem;margin-bottom:.45rem;}
        .pa-qa-answer-label {font-size:.76rem;font-weight:700;color:var(--pa-success-dark);}
        .pa-qa-answer {color:var(--pa-text-body);line-height:1.7;margin-bottom:.55rem;}
        .pa-qa-citation-count {color:var(--pa-text-muted);font-size:.76rem;margin:.25rem 0 .45rem;}
        .pa-answer-conclusion {
            margin-top:.72rem;padding-top:.72rem;border-top:1px solid var(--pa-border);
        }
        .pa-answer-support {
            display:inline-flex;padding:.14rem .42rem;border-radius:999px;
            font-size:.67rem;font-weight:720;line-height:1.35;
        }
        .pa-answer-support.is-direct {background:var(--pa-success-surface);color:var(--pa-success-dark);}
        .pa-answer-support.is-inference {background:var(--pa-warning-surface);color:var(--pa-danger-dark);}
        .pa-answer-conclusion-text {
            margin:.38rem 0 .45rem;color:var(--pa-text-heading);font-size:.88rem;font-weight:650;line-height:1.65;
        }
        .pa-answer-evidence {
            margin:.16rem 0;padding:.48rem .58rem;border-left:2px solid var(--pa-cyan-border);
            border-radius:0 6px 6px 0;background:var(--pa-surface);color:var(--pa-text-secondary);
            font-size:.73rem;line-height:1.55;
        }
        .pa-answer-evidence span {
            display:block;margin-bottom:.12rem;color:var(--pa-primary);font-size:.63rem;font-weight:700;
        }
        .st-key-qa_selected_quote {
            border-color:var(--pa-primary-border) !important;background:var(--pa-cyan-surface);margin-bottom:.7rem;
        }
        .pa-selected-quote-label {
            color:var(--pa-primary);font-size:.73rem;font-weight:700;margin-bottom:.25rem;
        }
        .pa-selected-quote {
            color:var(--pa-text-body);font-size:.84rem;line-height:1.55;
            display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden;
        }
        div[data-testid="stForm"]:has(.pa-qa-form-marker) {
            position:sticky;bottom:0;z-index:5;margin-top:.65rem;
            border:1px solid var(--pa-border-medium);padding:.55rem;background:var(--pa-bg);
            border-radius:10px;box-shadow:0 -6px 18px rgba(15,23,42,.06);
        }
        /* Paper + code is a viewport-sized workspace. The outer row stretches,
           while each panel owns its own scroll position. */
        /* Streamlit inserts a layout wrapper between keyed containers and
           their children. Constrain both layers so the workspace is truly
           viewport-sized instead of being expanded by the longest panel. */
        section.main:has(.st-key-joint_workspace) {height:auto;min-height:100vh;overflow:visible;}
        .block-container:has(.st-key-joint_workspace) {
            height:auto;min-height:calc(100vh + 2.5rem);overflow:visible;
        }
        /* Keep a page-level vertical scroll available as a fallback when the
           pointer is outside an individual panel.  The PDF, code, file-tree,
           and Assistant regions still keep their own scroll positions. */
        body:has(.st-key-joint_workspace) .stApp,
        body:has(.st-key-joint_workspace) [data-testid="stAppViewContainer"] {
            overflow-y:auto !important;overflow-x:hidden !important;
        }
        body:has(.st-key-joint_workspace) [data-testid="stMain"],
        body:has(.st-key-joint_workspace) .stMain {
            overflow:visible !important;
        }
        .st-key-joint_workspace {
            box-sizing:border-box;height:calc(100vh - 7.5rem) !important;
            min-height:540px !important;max-height:calc(100vh - 7.5rem) !important;
            width:100% !important;max-width:100% !important;margin:.4rem 0 0;padding:0 .25rem;
            flex:0 0 auto !important;overflow:hidden;
        }
        .st-key-joint_workspace > [data-testid="stLayoutWrapper"] {
            height:100%;min-height:0;display:flex;flex:1 1 auto;
        }
        .st-key-joint_workspace > [data-testid="stLayoutWrapper"]
        > [data-testid="stVerticalBlock"] {
            height:100%;min-height:0;display:flex;flex:1 1 auto;flex-direction:column;
        }
        [data-testid="stHorizontalBlock"]:has(.st-key-joint_pdf_panel) {
            align-items:stretch !important;min-height:0 !important;height:100%;
            gap:1rem !important;width:100%;margin:0;
        }
        .st-key-joint_workspace [data-testid="stHorizontalBlock"]:has(.st-key-joint_pdf_panel),
        .st-key-joint_workspace [data-testid="stHorizontalBlock"]:has(.st-key-joint_code_panel) {
            min-height:100% !important;height:100% !important;align-items:stretch !important;
        }
        [data-testid="stHorizontalBlock"]:has(.st-key-joint_pdf_panel)
        > [data-testid="stColumn"] {
            min-width:0 !important;min-height:0 !important;height:100%;
            display:flex;flex-direction:column;overflow:hidden !important;
        }
        /* 3-column balanced mode column allocation: PDF gets 40%, Code 35%, Assistant 25% */
        [data-testid="stHorizontalBlock"]:has(.st-key-joint_pdf_panel):has(.st-key-joint_code_panel)
        > [data-testid="stColumn"]:nth-child(1) {
            flex:40 1 0% !important;width:40% !important;min-width:340px !important;
        }
        [data-testid="stHorizontalBlock"]:has(.st-key-joint_pdf_panel):has(.st-key-joint_code_panel)
        > [data-testid="stColumn"]:nth-child(2) {
            flex:35 1 0% !important;width:35% !important;min-width:280px !important;
        }
        [data-testid="stHorizontalBlock"]:has(.st-key-joint_pdf_panel):has(.st-key-joint_code_panel)
        > [data-testid="stColumn"]:nth-child(3) {
            flex:25 1 0% !important;width:25% !important;min-width:260px !important;
        }
        [data-testid="stHorizontalBlock"]:has(.st-key-joint_pdf_panel)
        > [data-testid="stColumn"] > [data-testid="stVerticalBlock"]
        > [data-testid="stLayoutWrapper"] {
            flex:1 1 0 !important;min-height:0 !important;height:100%;
            display:flex;flex-direction:column;
        }
        .st-key-joint_pdf_panel,.st-key-joint_code_panel,.st-key-joint_conversation_panel {
            align-self:stretch;padding:.1rem .45rem .35rem;min-width:0;min-height:0;
            height:auto !important;max-height:none;overflow:hidden;overscroll-behavior:contain;
            scrollbar-gutter:stable;
            display:flex !important;flex:1 1 0 !important;flex-direction:column;
        }
        .st-key-joint_pdf_panel > [data-testid="stLayoutWrapper"],
        .st-key-joint_code_panel > [data-testid="stLayoutWrapper"],
        .st-key-joint_conversation_panel > [data-testid="stLayoutWrapper"] {
            min-height:0;display:flex;flex:0 0 auto;flex-direction:column;
        }
        /* In the paper-only and code-only layouts Streamlit adds one more
           wrapper around each keyed panel.  Stretch that parent as well;
           otherwise the keyed panel falls back to its intrinsic height
           (roughly one line) while its viewer overflows outside the workspace
           and gets clipped by the viewport-sized shell. */
        [data-testid="stLayoutWrapper"]:has(> .st-key-joint_pdf_panel),
        [data-testid="stLayoutWrapper"]:has(> .st-key-joint_code_panel),
        [data-testid="stLayoutWrapper"]:has(> .st-key-joint_conversation_panel) {
            flex:1 1 0 !important;height:100% !important;min-height:0 !important;
            display:flex;flex-direction:column;
        }
        .st-key-joint_pdf_panel > [data-testid="stLayoutWrapper"]:has(.pa-selectable-pdf),
        .st-key-joint_code_panel > [data-testid="stLayoutWrapper"]:has(.pa-selectable-code) {
            flex:1 1 0;min-height:0;overflow:hidden;
        }
        .st-key-joint_code_panel > [data-testid="stLayoutWrapper"]:has(.pa-selectable-code)
        > [data-testid="stVerticalBlock"] {
            height:100%;min-height:0;overflow:hidden;display:flex;flex-direction:column;
        }
        /* The code-focus layout nests a second horizontal row for the file
           tree and editor.  Without an explicit height on that nested row,
           the tree's long list determines the row height and the workspace
           cannot receive the mouse wheel outside the editor. */
        .st-key-joint_code_panel [data-testid="stHorizontalBlock"]:has(.st-key-joint_code_file_tree) {
            height:100% !important;min-height:0 !important;align-items:stretch !important;
            overflow:hidden;
        }
        .st-key-joint_code_panel [data-testid="stHorizontalBlock"]:has(.st-key-joint_code_file_tree)
        > [data-testid="stColumn"] {
            height:100% !important;min-height:0 !important;display:flex;flex-direction:column;
            overflow:hidden;
        }
        .st-key-joint_code_panel [data-testid="stHorizontalBlock"]:has(.st-key-joint_code_file_tree)
        > [data-testid="stColumn"] > [data-testid="stVerticalBlock"]
        > [data-testid="stLayoutWrapper"] {
            height:100% !important;min-height:0 !important;display:flex;flex-direction:column;
        }
        .st-key-joint_code_file_tree {
            height:100% !important;min-height:0 !important;max-height:none !important;
            overflow-y:auto !important;overflow-x:hidden !important;overscroll-behavior:contain;
            scrollbar-gutter:stable;background:var(--pa-surface) !important;
            border-right:1px solid var(--pa-border) !important;padding:.4rem !important;
        }
        .pa-tree-header {
            display:flex;align-items:center;justify-content:space-between;
            padding:.3rem .4rem .45rem;border-bottom:1px solid var(--pa-border-medium);
            margin-bottom:.45rem;font-size:.78rem;font-weight:700;color:var(--pa-text-primary);
        }
        .pa-tree-count {
            font-size:.68rem;color:var(--pa-text-muted);font-weight:600;
            background:var(--pa-surface-alt);padding:1px 6px;border-radius:4px;
        }
        div[class*="-file-"] button {
            text-align:left !important;justify-content:flex-start !important;
            padding:.22rem .5rem !important;min-height:1.8rem !important;height:1.8rem !important;
            font-size:.76rem !important;border-radius:6px !important;margin-bottom:2px !important;
        }
        div[class*="-file-"] button[kind="tertiary"] {
            border:0 !important;background:transparent !important;color:var(--pa-text-body) !important;
        }
        div[class*="-file-"] button[kind="tertiary"]:hover {
            background:var(--pa-primary-surface) !important;color:var(--pa-primary) !important;
        }
        div[class*="-file-"] button[kind="primary"] {
            background:var(--pa-primary-surface) !important;color:var(--pa-primary-dark) !important;
            border-left:3px solid var(--pa-primary) !important;font-weight:700 !important;
            box-shadow:none !important;
        }
        .st-key-joint_code_panel [class*="st-key-joint-selectable-code-"] {
            flex:1 1 0 !important;height:auto !important;min-height:0 !important;overflow:hidden;
        }
        .st-key-joint_code_panel [class*="st-key-joint-selectable-code-"]
        [data-testid="stBidiComponent"],
        .st-key-joint_code_panel [class*="st-key-joint-selectable-code-"]
        [data-testid="stBidiComponentRegular"] {
            height:100% !important;min-height:0 !important;overflow:hidden;
        }
        .st-key-joint_pdf_panel .st-key-joint-selectable-pdf,
        .st-key-joint_pdf_panel [data-testid="stBidiComponent"],
        .st-key-joint_pdf_panel [data-testid="stBidiComponentRegular"],
        .st-key-joint_pdf_panel iframe {
            height:auto !important;min-height:0 !important;width:100% !important;
        }
        .st-key-joint_code_panel [class*="st-key-joint-selectable-code-"]
        [data-testid="stBidiComponentRegular"] > div,
        .st-key-joint_code_panel [class*="st-key-joint-selectable-code-"]
        [data-testid="stBidiComponentRegular"] > div > div {
            height:100% !important;min-height:0 !important;overflow:visible;
        }
        .st-key-joint_pdf_panel .pa-selectable-pdf,
        .st-key-joint_code_panel .pa-selectable-code {
            height:100% !important;min-height:0 !important;max-height:none !important;
        }
        .st-key-joint_pdf_panel [data-testid="stImage"] img {
            width:100% !important;height:auto !important;max-height:calc(100vh - 11.5rem) !important;
            object-fit:contain !important;border-radius:8px;border:1px solid var(--pa-border-medium);
            background:var(--pa-bg);box-shadow:var(--pa-shadow-xs);
        }
        .st-key-joint_pdf_panel,.st-key-joint_conversation_panel {overflow-y:auto;}
        .st-key-joint_code_panel {overflow:hidden;border-left:1px solid var(--pa-border);}
        .st-key-joint_conversation_panel {border-left:1px solid var(--pa-border);padding-bottom:.3rem;}
        .st-key-joint_assistant_scroll {
            flex:0 1 auto !important;height:auto !important;min-height:0;max-height:100%;
            overflow-y:auto;overflow-x:hidden;
            overscroll-behavior:contain;scrollbar-gutter:stable;padding-right:.35rem;
        }
        .st-key-joint_conversation_panel > [data-testid="stLayoutWrapper"]:has(.st-key-joint_assistant_scroll) {
            flex:0 1 auto;min-height:0;max-height:100%;overflow:hidden;
        }
        .st-key-joint_assistant_scroll > [data-testid="stLayoutWrapper"] {
            min-height:0;display:flex;flex-direction:column;
        }
        /* Streamlit gives keyed vertical containers a flex-grow default when
           they sit inside the Assistant stack. Keep each message/context card
           in normal document flow so its content cannot overlap the next row;
           the outer Assistant container remains the only scroll owner. */
        .st-key-joint_assistant_scroll div[class*="st-key-joint_message_"],
        .st-key-joint_assistant_scroll div[class*="st-key-joint_pending_message"],
        .st-key-joint_assistant_scroll div[class*="st-key-joint_answer_body_"],
        .st-key-joint_assistant_scroll .st-key-joint_current_context,
        .st-key-joint_assistant_scroll .st-key-joint_selected_context,
        .st-key-joint_assistant_scroll .st-key-joint_context_actions {
            flex:0 0 auto !important;height:auto !important;min-height:0 !important;
        }
        /* The composer context is a compact two-line reminder, not a second
           copy of the selected code. Keep it immediately above the input. */
        .st-key-joint_composer_context,
        .st-key-joint_composer_context > [data-testid="stLayoutWrapper"],
        .st-key-joint_composer_context > [data-testid="stLayoutWrapper"] > [data-testid="stVerticalBlock"] {
            flex:0 0 auto !important;height:auto !important;min-height:0 !important;
        }
        .st-key-joint_composer_context .st-key-joint_current_context {
            margin:.25rem 0 .35rem;padding:.3rem .45rem .35rem;
            border-radius:7px;background:var(--pa-surface-alt);
        }
        .st-key-joint_composer_context .st-key-joint_current_context [data-testid="stCaptionContainer"] {
            margin:0 0 .15rem;font-size:.64rem;line-height:1.25;
        }
        .pa-compact-code-preview,
        .pa-compact-paper-preview {
            display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:2;
            overflow:hidden;max-height:2.65rem;margin:.1rem 0 .15rem;
            color:var(--pa-text-secondary);font-size:.67rem;line-height:1.35;
        }
        .pa-compact-code-preview code {
            color:var(--pa-success-dark);font-size:.66rem;white-space:normal;
            overflow-wrap:anywhere;
        }
        .st-key-joint_composer_context .st-key-joint_current_context [data-testid="stHorizontalBlock"] {
            margin-top:.1rem;
        }
        .st-key-joint_composer_context .st-key-joint_selected_context {
            padding:.3rem .45rem;margin:.25rem 0 .35rem;border-radius:7px;
        }
        .st-key-joint_context_actions > [data-testid="stLayoutWrapper"],
        .st-key-joint_context_actions > [data-testid="stLayoutWrapper"] > [data-testid="stVerticalBlock"] {
            flex:0 0 auto !important;height:auto !important;min-height:0 !important;
        }
        .st-key-joint_pdf_toolbar {
            flex:0 0 auto;min-height:40px;padding:.2rem .3rem;
            border-bottom:1px solid var(--pa-border);background:var(--pa-bg);
            border-radius:var(--pa-radius-md) var(--pa-radius-md) 0 0;
        }
        .st-key-joint_pdf_toolbar [data-testid="stHorizontalBlock"] {
            gap:.3rem !important;align-items:center;
        }
        .st-key-joint_pdf_toolbar [data-testid="stColumn"] {min-width:0 !important;}
        .st-key-joint_pdf_toolbar button {
            min-height:1.85rem;height:1.85rem;padding:.1rem .3rem;white-space:nowrap;
            border-radius:var(--pa-radius-sm) !important;
            border:1px solid var(--pa-border) !important;
            background:var(--pa-surface) !important;
        }
        .st-key-joint_pdf_toolbar button p {font-size:.72rem;font-weight:600;white-space:nowrap;}
        .pa-pdf-footer-note {
            font-size:.7rem !important;color:var(--pa-text-muted) !important;
            text-align:center !important;margin-top:.15rem !important;margin-bottom:0 !important;
            line-height:1.2 !important;
        }
        .st-key-joint_pdf_toolbar [data-testid="stNumberInput"] input {
            min-height:1.85rem;height:1.85rem;padding:.1rem .2rem;text-align:center;
        }
        .pa-code-breadcrumb {
            background:#0f172a !important;color:#94a3b8 !important;
            padding:.55rem .8rem !important;border-radius:8px 8px 0 0 !important;
            font-size:.78rem !important;font-weight:600 !important;
            border-bottom:1px solid #1e293b !important;
            display:flex !important;align-items:center !important;justify-content:space-between !important;
        }
        .pa-code-breadcrumb strong {color:#f8fafc !important;font-weight:700 !important;}
        .pa-code-viewer {
            height:calc(100vh - 12rem) !important;max-height:none !important;
            overflow:auto;overscroll-behavior:contain;
            border:1px solid #1e293b;border-radius:0 0 8px 8px;background:#0f172a;
            padding:.6rem 0;font:12px/1.62 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
            scrollbar-gutter:stable;
        }
        .pa-code-line {display:flex;min-width:max-content;color:var(--pa-primary-light);padding:0 .8rem;}
        .pa-code-line:hover {background:#172554;}
        .pa-code-line.is-active {background:rgba(250,204,21,.22);box-shadow:inset 3px 0 #facc15;}
        .pa-code-number {
            width:3.2rem;flex:0 0 3.2rem;text-align:right;margin-right:1rem;
            color:var(--pa-text-muted);user-select:none;
        }
        .pa-code-line code {color:inherit;background:transparent;padding:0;white-space:pre;}
        .pa-assistant-meta-badge {
            display:inline-flex;align-items:center;gap:.35rem;
            padding:.22rem .65rem;margin-bottom:.5rem;
            border:1px solid var(--pa-success-border);border-radius:var(--pa-radius-pill);
            background:var(--pa-success-surface);color:var(--pa-success-dark);
            font-size:.72rem;font-weight:650;box-shadow:var(--pa-shadow-2xs);
        }
        .pa-assistant-subhead {
            font-size:.75rem;color:var(--pa-text-muted);font-weight:600;margin:.2rem 0 .3rem;
        }
        .pa-composer-disclaimer {
            font-size:.68rem;color:var(--pa-text-muted);text-align:center;margin-top:.3rem;margin-bottom:.1rem;
        }
        .st-key-joint_assistant_top_tab [role="radiogroup"] {
            display:flex !important;gap:2px !important;padding:2px !important;
            background:var(--pa-surface-alt) !important;border:1px solid var(--pa-border-medium) !important;
            border-radius:8px !important;margin-bottom:.4rem !important;
        }
        .st-key-joint_assistant_top_tab [role="radio"] {
            flex:1 !important;justify-content:center !important;border:0 !important;
            background:transparent !important;border-radius:6px !important;padding:.2rem 0 !important;
        }
        .st-key-joint_assistant_top_tab [role="radio"][aria-checked="true"] {
            background:var(--pa-surface) !important;color:var(--pa-primary) !important;
            font-weight:700 !important;box-shadow:0 1px 3px rgba(15,23,42,.08) !important;
        }
        .pa-code-snapshot-card {
            border:1px solid var(--pa-border-medium);border-radius:8px 8px 0 0;
            background:var(--pa-surface-alt);padding:.4rem .65rem;margin-top:.2rem;
        }
        .pa-code-snapshot-tag {
            background:var(--pa-primary-surface);color:var(--pa-primary);
            font-size:.65rem;font-weight:700;padding:1px 6px;border-radius:4px;
        }
        div[data-testid="stForm"]:has(.pa-joint-form-marker) {
            position:sticky;bottom:.15rem;z-index:5;margin:.55rem 0 .2rem;
            border:1px solid var(--pa-primary-border);padding:.45rem;background:rgba(255,255,255,.97);
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
            border:1px solid var(--pa-border-medium);border-top:2px solid var(--pa-primary-light);
            border-radius:10px;background:var(--pa-bg);box-shadow:0 2px 8px rgba(15,23,42,.035);
        }
        div[class*="st-key-joint_message_selection_"],
        .st-key-joint_pending_selection {
            margin:0 0 .55rem;padding:0 0 .55rem;border-bottom:1px solid var(--pa-border);
        }
        .pa-message-selection-title {
            display:flex;align-items:center;justify-content:space-between;gap:.55rem;
            margin:0 0 .32rem;color:var(--pa-text-secondary);font-size:.67rem;
        }
        .pa-message-selection-title span {
            min-width:0;color:var(--pa-text-muted);font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
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
            background:var(--pa-surface-alt);color:var(--pa-text-heading);font-size:.82rem;font-weight:680;line-height:1.5;
        }
        .pa-assistant-user span {
            display:inline-flex;margin-right:.38rem;padding:.08rem .3rem;border-radius:4px;
            background:var(--pa-primary-light);color:var(--pa-primary-hover);font-size:.6rem;font-weight:750;vertical-align:.08rem;
        }
        .pa-assistant-meta {
            display:inline-flex;margin:.12rem 0 .48rem;padding:.13rem .4rem;
            border-radius:999px;background:var(--pa-success-surface);color:var(--pa-success-dark);
            font-size:.64rem;font-weight:700;
        }
        div[class*="st-key-joint_answer_body_"] {
            color:var(--pa-text-body);font-size:.83rem;line-height:1.78;
        }
        div[class*="st-key-joint_answer_body_"] p {margin:.15rem 0 .55rem;}
        div[class*="st-key-joint_answer_body_"] ul,
        div[class*="st-key-joint_answer_body_"] ol {
            margin:.28rem 0 .58rem;padding-left:1.25rem;
        }
        div[class*="st-key-joint_answer_body_"] li {margin:.2rem 0;padding-left:.12rem;}
        div[class*="st-key-joint_answer_body_"] li::marker {
            color:var(--pa-primary);font-weight:750;
        }
        div[class*="st-key-joint_answer_body_"] code {
            padding:0 .05rem;border:0;background:transparent;color:var(--pa-success-dark);
            font-size:.75rem;font-weight:560;overflow-wrap:anywhere;
        }
        div[class*="st-key-joint_answer_body_"] pre {
            margin:.42rem 0 .68rem;padding:.68rem .75rem;overflow-x:hidden;
            border:1px solid var(--pa-text-primary);border-radius:7px;background:var(--pa-text-primary);
            box-shadow:inset 3px 0 var(--pa-primary);font-size:.71rem;line-height:1.62;
        }
        div[class*="st-key-joint_answer_body_"] pre code {
            padding:0;border:0;background:transparent;color:var(--pa-primary-light);
            white-space:pre-wrap;overflow-wrap:anywhere;word-break:break-word;
        }
        .pa-reference-heading {
            display:flex;align-items:center;gap:.38rem;margin:.58rem 0 .32rem;
            color:var(--pa-text-secondary);font-size:.67rem;font-weight:720;
        }
        .pa-reference-heading span {color:var(--pa-text-faint);font-weight:500;}
        .pa-reference-heading::after {
            content:"";height:1px;flex:1;background:var(--pa-border);
        }
        div[class*="st-key-joint_paper_refs_"] [data-testid="stButton"] button,
        div[class*="st-key-joint_code_refs_"] [data-testid="stButton"] button {
            justify-content:flex-start;min-height:2rem;padding:.3rem .48rem;
            border:1px solid var(--pa-border-medium);border-radius:6px;background:var(--pa-surface);color:var(--pa-text-body);
            box-shadow:none;text-align:left;
        }
        div[class*="st-key-joint_paper_refs_"] [data-testid="stButton"] button:hover,
        div[class*="st-key-joint_code_refs_"] [data-testid="stButton"] button:hover {
            border-color:var(--pa-cyan-border);background:var(--pa-primary-surface);color:var(--pa-primary-hover);
        }
        div[class*="st-key-joint_paper_refs_"] [data-testid="stButton"] button p,
        div[class*="st-key-joint_code_refs_"] [data-testid="stButton"] button p {
            overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:.67rem;
        }
        div[class*="st-key-joint_code_refs_"] [data-testid="stButton"] button p {
            font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
        }
        .pa-context-title {color:var(--pa-text-muted);font-size:.7rem;font-weight:700;text-transform:uppercase;letter-spacing:.04em;}
        .pa-context-chips {display:flex;gap:.35rem;flex-wrap:wrap;margin:.2rem 0 .45rem;}
        .pa-context-chips span {
            display:inline-flex;max-width:100%;padding:.22rem .48rem;border:1px solid var(--pa-primary-border);
            border-radius:999px;background:var(--pa-primary-surface);color:var(--pa-primary-hover);font-size:.68rem;
            white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
        }
        .st-key-joint_current_context {
            margin:.35rem 0 .7rem;padding:.58rem .65rem .65rem;
            border:1px solid var(--pa-border-medium);border-radius:9px;background:var(--pa-surface);
            flex:0 0 auto !important;height:auto !important;min-height:0 !important;
            overflow:visible !important;
        }
        .st-key-joint_current_context > [data-testid="stLayoutWrapper"],
        .st-key-joint_current_context > [data-testid="stLayoutWrapper"] > [data-testid="stVerticalBlock"] {
            flex:0 0 auto !important;height:auto !important;min-height:0 !important;
        }
        .st-key-joint_current_context [data-testid="stCode"] {
            flex:0 0 auto !important;height:auto !important;min-height:0 !important;
            max-height:none !important;overflow:visible !important;
        }
        .st-key-joint_current_context [data-testid="stCode"] pre {
            height:auto !important;min-height:0 !important;max-height:none !important;
            overflow:visible !important;white-space:pre-wrap !important;overflow-wrap:anywhere;
        }
        .st-key-joint_current_context [data-testid="stCaptionContainer"] {
            margin:.05rem 0 .3rem;color:var(--pa-text-muted);
        }
        .st-key-joint_current_context [data-testid="stCode"] {
            margin:0;
        }
        .st-key-joint_current_context [data-testid="stCode"] pre {
            font-size:.71rem;line-height:1.58;
        }
        .st-key-joint_selected_context {
            padding:.55rem .65rem;margin:.35rem 0;border:1px solid var(--pa-primary-border);
            border-radius:9px;background:var(--pa-cyan-surface);
        }
        .st-key-joint_conversation_panel [data-testid="stPills"] {margin:.25rem 0;}
        [data-testid="stBaseButton-primary"] {
            background:var(--pa-primary);border-color:var(--pa-primary);color:var(--pa-bg);
        }
        [data-testid="stBaseButton-primary"]:hover {
            background:var(--pa-primary-hover);border-color:var(--pa-primary-hover);color:var(--pa-bg);
        }
        @media (prefers-color-scheme: dark) {
            /* ── Dark mode: override design tokens ──────────── */
            :root {
                --pa-text-primary: #f8fafc;
                --pa-text-heading: #f8fafc;
                --pa-text-body: #e2e8f0;
                --pa-text-secondary: #cbd5e1;
                --pa-text-muted: #94a3b8;
                --pa-text-faint: #64748b;
                --pa-text-placeholder: #64748b;
                --pa-bg: #0f172a;
                --pa-bg-page: #0f172a;
                --pa-surface: #1e293b;
                --pa-surface-alt: #1e293b;
                --pa-surface-raised: #1e293b;
                --pa-border: #334155;
                --pa-border-light: #1e293b;
                --pa-border-medium: #334155;
                --pa-border-strong: #475569;
                --pa-border-panel: #334155;
                --pa-border-divider: #334155;
                --pa-border-sidebar: #334155;
                --pa-border-item: #334155;
                --pa-primary: #60a5fa;
                --pa-primary-hover: #93c5fd;
                --pa-primary-surface: #172554;
                --pa-primary-light: #1e3a5f;
                --pa-primary-border: #1e40af;
                --pa-primary-action: #60a5fa;
                --pa-cyan-surface: #0f172a;
                --pa-success-surface: #052e16;
                --pa-success-light: #052e16;
                --pa-shadow-sm: 0 2px 8px rgba(0,0,0,.2);
                --pa-shadow-md: 0 4px 12px rgba(0,0,0,.25);
                --pa-shadow-lg: 0 18px 50px rgba(0,0,0,.3);
                --pa-shadow-up: 0 -6px 18px rgba(0,0,0,.2);
            }
            /* ── Component-specific dark overrides ──────────── */
            .pa-learning-hero {background:linear-gradient(135deg,#172554,#1e293b); border-color:#334155;}
            .pa-audit-summary,
            div[data-testid="stExpander"]:has(.pa-audit-detail) {
                background:#111827;border-color:#334155;
            }
            .pa-audit-evidence-item {background:#0f172a;border-color:#38bdf8;}
            .st-key-learning_primary_nav,
            .st-key-learning_section_bar {background:rgba(15,23,42,.97);border-color:#334155;}
            .st-key-learning_explanation_header {background:#111827;border-color:#334155;}
            .st-key-learning_source_panel {background:#111827;}
            .st-key-learning_pdf_toolbar,.st-key-qa_pdf_toolbar {
                background:rgba(30,41,59,.96);border-color:#334155;
            }
            div[class*="st-key-sidebar_project_"]:has(.pa-sidebar-project-marker.is-active) {
                background:#172554;
            }
            .st-key-storage_setup_shell {background:#1e293b;border-color:#334155;}
            .st-key-launch_pdf_upload_empty {background:#172554;border-color:#1e40af;}
            .st-key-launch_setup_panel {background:#1e293b;border-color:#334155 !important;}
            .st-key-upload_pdf_preview {background:#111827;}
            .pa-qa-question {background:#0f172a;}
            .st-key-qa_selected_quote {background:#172554;border-color:#334155 !important;}
            .pa-assistant-user span {background:#172554;color:#93c5fd;}
            .pa-assistant-meta {background:#052e16;color:#6ee7b7;}
            div[class*="st-key-joint_answer_body_"] code {
                background:transparent;color:#86efac;border:0;
            }
            div[class*="st-key-joint_answer_body_"] pre {background:#020617;border-color:#334155;}
            div[class*="st-key-joint_answer_body_"] pre code {
                background:transparent;color:#dbeafe;border:0;
            }
            .pa-context-chips span {background:#172554;border-color:#1e40af;color:#bfdbfe;}
            .st-key-joint_selected_context {background:#172554;border-color:#334155;}
            .pa-qa-intro {background:#172554;border-color:#334155;}
            .st-key-learning_section_followup {
                background:linear-gradient(to bottom,rgba(30,41,59,.72),#1e293b 28%);
            }
            div[class*="st-key-recent_project_"] {background:#1e293b;border-color:#334155 !important;}
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
                /* Keep the native Streamlit toolbar clear on compact screens. */
                flex:0 0 360px !important;width:360px !important;min-width:0 !important;
            }
            .st-key-learning_primary_nav > [data-testid="stLayoutWrapper"]
            > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:last-child {
                flex:0 0 120px !important;width:120px !important;min-width:0 !important;
            }
            .st-key-joint_workspace {height:calc(100vh - 13.8rem);min-height:480px;}
            [data-testid="stHorizontalBlock"]:has(.st-key-joint_pdf_panel) {
                gap:.25rem !important;
            }
            .st-key-joint_pdf_panel,.st-key-joint_code_panel,
            .st-key-joint_conversation_panel {padding-left:.25rem;padding-right:.25rem;}
            .st-key-joint_pdf_toolbar button {font-size:.68rem;}
        }
        @media (max-width:1100px) and (min-width:701px) {
            .st-key-joint_workspace {height:calc(100vh - 13.2rem);min-height:440px;}
            [data-testid="stHorizontalBlock"]:has(.st-key-joint_pdf_panel)
            > [data-testid="stColumn"]:nth-child(1),
            [data-testid="stHorizontalBlock"]:has(.st-key-joint_pdf_panel)
            > [data-testid="stColumn"]:nth-child(2) {flex:1 1 0 !important;min-width:0 !important;}
            [data-testid="stHorizontalBlock"]:has(.st-key-joint_pdf_panel)
            > [data-testid="stColumn"]:nth-child(3) {flex:0 0 320px !important;width:320px !important;}
            .st-key-joint_conversation_panel {font-size:.88rem;}
        }
        @media (max-width:700px) {
            /* The desktop workspace is viewport-locked; release that lock on
               phones so the natural single-column flow remains scrollable. */
            section.main:has(.st-key-joint_workspace) {height:auto;overflow:visible;}
            .block-container:has(.st-key-joint_workspace) {height:auto;min-height:0;overflow:visible;}
            .st-key-joint_workspace {
                height:auto !important;max-height:none !important;min-height:0 !important;
                overflow:visible;
            }
            .pa-audit-summary {align-items:flex-start;gap:.6rem;padding:.65rem;}
            .pa-audit-summary-grade {
                flex:1 1 100%;min-width:0;padding:0 0 .5rem;border-right:0;
                border-bottom:1px solid var(--pa-border);
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
            > [data-testid="stColumn"]:has(.st-key-learning_source_panel),
            [data-testid="stHorizontalBlock"]:has(.st-key-learning_source_panel)
            > [data-testid="stColumn"]:has([class*="st-key-learning_report_scroll_"]),
            [data-testid="stHorizontalBlock"]:has(.st-key-learning_source_panel)
            > [data-testid="stColumn"]:has([class*="st-key-learning_page_context_scroll_"]) {
                height:auto !important;max-height:none !important;min-height:0 !important;
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
                height:auto;max-height:none;overflow:visible;
            }
            .st-key-joint_pdf_panel,.st-key-joint_code_panel,.st-key-joint_conversation_panel {
                border-left:0;padding:.15rem 0 .45rem;
            }
            /* Short selections should not inherit the desktop flex scroller's
               viewport height on narrow screens. Let the Assistant follow its
               content so the selection actions and composer stay together. */
            .st-key-joint_assistant_scroll {
                flex:0 0 auto !important;height:auto !important;min-height:0 !important;
                max-height:none !important;overflow:visible !important;
            }
            .st-key-joint_assistant_scroll > [data-testid="stLayoutWrapper"] {
                height:auto !important;min-height:0 !important;display:block !important;
            }
            .st-key-joint_pdf_panel [data-testid="stHorizontalBlock"] {
                flex-wrap:nowrap !important;gap:.35rem !important;
            }
            .st-key-joint_pdf_panel [data-testid="stColumn"] {
                min-width:0 !important;
            }
            .pa-workspace-title,.pa-workspace-summary {white-space:normal;}
            .st-key-learning_primary_nav {padding-right:0;}
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

            /* Release the desktop-centered shell on narrow screens. The
               learning workspace then flows from the viewport edge instead
               of centering a wide desktop row off-screen. */
            body:has(.st-key-learning_primary_nav) .stApp,
            body:has(.st-key-learning_primary_nav) [data-testid="stAppViewContainer"],
            body:has(.st-key-learning_primary_nav) [data-testid="stMain"] {
                height:auto !important;max-height:none !important;overflow:visible !important;
            }
            .block-container:has(.st-key-learning_primary_nav) {
                width:100% !important;max-width:none !important;height:auto !important;
                min-height:0 !important;padding:0 .75rem !important;overflow:visible !important;
            }
            .block-container:has(.st-key-learning_primary_nav) > [data-testid="stVerticalBlock"] {
                height:auto !important;min-height:0 !important;overflow:visible !important;
            }
            .st-key-learning_primary_nav,.st-key-audit_activity_strip {
                width:100% !important;max-width:none !important;margin:0 !important;
            }
            [data-testid="stHorizontalBlock"]:has(.st-key-learning_source_panel) {
                width:100% !important;max-width:none !important;margin:0 !important;
                height:auto !important;min-height:0 !important;flex-wrap:wrap !important;
            }
            [data-testid="stHorizontalBlock"]:has(.st-key-learning_source_panel)
            > [data-testid="stColumn"]:has(.st-key-learning_source_panel),
            [data-testid="stHorizontalBlock"]:has(.st-key-learning_source_panel)
            > [data-testid="stColumn"]:has([class*="st-key-learning_report_scroll_"]) {
                flex:1 1 100% !important;width:100% !important;min-width:0 !important;
                height:auto !important;max-height:none !important;
            }
            .st-key-learning_source_panel {
                height:auto !important;max-height:none !important;overflow:visible !important;
            }
            .st-key-learning_source_panel .st-key-learning-selectable-pdf,
            .st-key-learning_source_panel .st-key-learning-selectable-pdf [data-testid="stBidiComponent"],
            .st-key-learning_source_panel .st-key-learning-selectable-pdf [data-testid="stBidiComponentRegular"] {
                height:auto !important;min-height:0 !important;max-height:none !important;
            }
            .st-key-learning_source_panel .pa-selectable-pdf {
                height:62vh !important;min-height:360px !important;max-height:none !important;
            }
            .st-key-joint_workspace {
                width:100% !important;max-width:none !important;height:auto !important;
                min-height:0 !important;max-height:none !important;overflow:visible !important;
            }
            [data-testid="stHorizontalBlock"]:has(.st-key-joint_pdf_panel) {
                width:100% !important;max-width:none !important;height:auto !important;
                min-height:0 !important;flex-wrap:wrap !important;gap:.75rem !important;
            }
            [data-testid="stHorizontalBlock"]:has(.st-key-joint_pdf_panel)
            > [data-testid="stColumn"]:has(.st-key-joint_pdf_panel),
            [data-testid="stHorizontalBlock"]:has(.st-key-joint_pdf_panel)
            > [data-testid="stColumn"]:has(.st-key-joint_conversation_panel) {
                flex:1 1 100% !important;width:100% !important;min-width:0 !important;
                max-width:none !important;height:auto !important;max-height:none !important;
            }
            .st-key-joint_pdf_panel,.st-key-joint_conversation_panel {
                height:auto !important;max-height:none !important;overflow:visible !important;
            }
            [data-testid="stHorizontalBlock"]:has(.st-key-qa_source_panel) {
                width:100% !important;max-width:none !important;height:auto !important;
                min-height:0 !important;flex-wrap:wrap !important;gap:.75rem !important;
            }
            [data-testid="stHorizontalBlock"]:has(.st-key-qa_source_panel)
            > [data-testid="stColumn"]:has(.st-key-qa_source_panel),
            [data-testid="stHorizontalBlock"]:has(.st-key-qa_source_panel)
            > [data-testid="stColumn"]:has(.st-key-qa_conversation_panel) {
                flex:1 1 100% !important;width:100% !important;min-width:0 !important;
                max-width:none !important;height:auto !important;max-height:none !important;
            }
            .st-key-qa_source_panel,.st-key-qa_conversation_panel {
                height:auto !important;max-height:none !important;overflow:visible !important;
            }
        }
        @media (max-height:760px) {
            .st-key-qa_history_scroll {height:auto;max-height:none;overflow:visible;}
            .st-key-qa_conversation_panel {position:static;}
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
