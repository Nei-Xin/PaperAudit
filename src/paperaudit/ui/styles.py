from __future__ import annotations

import streamlit as st


def inject_custom_styles() -> None:
    st.markdown(
        """
        <style>
        /* ── Design Tokens ─────────────────────────────────── */
        :root {
          /* Academic paper palette: warm paper surfaces, ink text, ink-blue accent. */
          /* Brand / Accent */
          --pa-primary: #1e4a7a;
          --pa-primary-hover: #163a61;
          --pa-primary-surface: #eef3f8;
          --pa-primary-light: #dfe6ee;
          --pa-primary-border: #bcc9d8;
          --pa-primary-dark: #13304f;
          --pa-primary-action: #1e4a7a;

          /* Semantic – Success */
          --pa-success: #3f8a5a;
          --pa-success-dark: #24553a;
          --pa-success-surface: #edf3ec;
          --pa-success-light: #dce8d8;
          --pa-success-text: #24553a;
          --pa-success-muted: #2f6b45;

          /* Semantic – Warning */
          --pa-warning: #b7791f;
          --pa-warning-dark: #8a5a12;
          --pa-warning-surface: #f8efd9;
          --pa-warning-text: #7a4e0e;

          /* Semantic – Danger */
          --pa-danger: #a63d31;
          --pa-danger-dark: #8c2f25;
          --pa-danger-surface: #f6e4df;
          --pa-danger-text: #7e2a21;

          /* Neutral – Text (ink) */
          --pa-text-primary: #1a1a19;
          --pa-text-heading: #1a1a19;
          --pa-text-body: #3a3835;
          --pa-text-secondary: #57534e;
          --pa-text-muted: #6b6661;
          --pa-text-faint: #6b6661;
          --pa-text-placeholder: #807a74;

          /* Neutral – Surfaces (paper) */
          --pa-bg: #ffffff;
          --pa-bg-page: #f4f4f2;
          --pa-surface: #fafaf9;
          --pa-surface-alt: #f0efec;
          --pa-surface-raised: #ffffff;
          --pa-surface-code: #24211d;

          /* Neutral – Borders */
          --pa-border: #e7e5e1;
          --pa-border-light: #f0efec;
          --pa-border-medium: #e4e2de;
          --pa-border-strong: #d6d3cd;
          --pa-border-panel: #e7e5e1;
          --pa-border-divider: #e7e5e1;
          --pa-border-sidebar: #e7e5e1;
          --pa-border-item: #f0efec;

          /* Evidence accent (teal ink) */
          --pa-cyan: #2f6f8f;
          --pa-cyan-light: #5b93ad;
          --pa-cyan-surface: #f3f6f6;
          --pa-cyan-border: #a9c3cf;

          /* Highlighter for quoted evidence */
          --pa-highlight: rgba(232, 196, 92, .38);
          --pa-highlight-strong: #d9a93a;

          /* Spacing */
          --pa-space-2xs: 0.12rem;
          --pa-space-xs: 0.25rem;
          --pa-space-sm: 0.5rem;
          --pa-space-md: 0.75rem;
          --pa-space-lg: 1rem;
          --pa-space-xl: 1.5rem;
          --pa-space-2xl: 2rem;

          /* Radius */
          --pa-radius-xs: 3px;
          --pa-radius-sm: 6px;
          --pa-radius-md: 6px;
          --pa-radius-lg: 10px;
          --pa-radius-xl: 10px;
          --pa-radius-pill: 999px;

          /* Shadows */
          --pa-shadow-xs: 0 1px 2px rgba(26,26,25,.05);
          --pa-shadow-sm: 0 1px 2px rgba(26,26,25,.06), 0 2px 8px rgba(26,26,25,.04);
          --pa-shadow-md: 0 3px 10px rgba(26,26,25,.07);
          --pa-shadow-lg: 0 14px 40px rgba(26,26,25,.10);
          --pa-shadow-up: 0 -4px 14px rgba(26,26,25,.06);

          /* Transitions */
          --pa-transition-fast: 0.12s ease;
          --pa-transition-normal: 0.18s ease;
          --pa-transition-slow: 0.28s ease;

          /* Font stacks */
          --pa-font-mono: "JetBrains Mono",ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
          --pa-font-serif: "Source Serif 4","Songti SC","STSong","SimSun",Georgia,serif;
          --pa-font-sans: "Inter","PingFang SC","Hiragino Sans GB","Microsoft YaHei","Noto Sans SC",-apple-system,"Segoe UI",sans-serif;
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
            50% { box-shadow: 0 0 0 5px rgba(63,138,90,0); }
        }

        /* ── Skeleton shimmer for loading states ────────────── */
        @keyframes pa-shimmer {
            0% { background-position: 200% 0; }
            100% { background-position: -200% 0; }
        }

        .block-container {
            max-width:1900px;padding:3.1rem 1.25rem 2rem;
        }
        .block-container:has(.pa-learning-layout) {
            max-width:none !important;width:100% !important;height:100vh;max-height:100vh;
            margin:0 !important;padding:0 .5rem !important;overflow:hidden;
        }
        /* Keep Streamlit's native header available so a collapsed project sidebar
           can always be reopened. The learning header remains the visual header. */
        body:has(.pa-learning-layout) header[data-testid="stHeader"] {
            height:2.35rem;background:transparent;z-index:1;
        }
        body:has(.pa-learning-layout) header[data-testid="stHeader"] button {
            opacity:.72;
        }
        [data-testid="stFileUploaderDropzone"] {border-radius: 9px;}
        [data-testid="stMetric"] {
            border: 1px solid var(--pa-border); border-radius: var(--pa-radius-lg); padding: 12px 14px;
            background: var(--pa-bg);
        }
        [data-testid^="stBaseButton-"] {
            min-height:2rem;border-radius:var(--pa-radius-sm) !important;
            font-size:.78rem;font-weight:650;box-shadow:none !important;
        }
        [data-testid="stBaseButton-secondary"] {
            border-color:var(--pa-border-strong);background:var(--pa-bg);color:var(--pa-text-body);
        }
        [data-testid="stBaseButton-secondary"]:hover {
            border-color:var(--pa-primary-border);background:var(--pa-primary-surface);color:var(--pa-primary-dark);
        }
        [data-testid="stButtonGroup"] button {
            min-height:2rem;border-radius:var(--pa-radius-sm) !important;
        }
        [data-baseweb="input"] > div,
        [data-baseweb="select"] > div,
        [data-testid="stTextInputRootElement"] {
            min-height:2rem;border-radius:var(--pa-radius-sm) !important;
        }
        section[data-testid="stSidebar"]:not([aria-expanded="false"]) {
            width:clamp(200px,15vw,232px) !important;
            min-width:clamp(200px,15vw,232px) !important;
        }
        section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
            height:100vh;max-height:100vh;overflow-y:auto;
            padding:.9rem .75rem .75rem;background:var(--pa-bg-page);border-right:1px solid var(--pa-border-sidebar);
        }
        .pa-sidebar-library-title {
            margin:.08rem 0 .72rem;color:var(--pa-text-heading);font-size:1rem;font-weight:780;
            letter-spacing:.01em;
        }
        .pa-sidebar-section-heading {
            display:flex;align-items:center;justify-content:space-between;
            margin:1rem .12rem .42rem;color:var(--pa-text-body);font-size:.75rem;font-weight:760;
        }
        .pa-sidebar-section-heading b {
            display:inline-flex;align-items:center;justify-content:center;min-width:1.25rem;height:1.25rem;
            padding:0 .3rem;border-radius:.42rem;background:var(--pa-surface-alt);color:var(--pa-text-muted);
            font-size:.75rem;font-weight:700;
        }
        .st-key-sidebar_project_list {
            max-height:calc(100vh - 22rem);min-height:8rem;margin-top:.4rem;padding:0;
            overflow-y:auto;scrollbar-gutter:stable;border:0;border-radius:0;background:transparent;
            box-shadow:none;
        }
        div[class*="st-key-sidebar_project_"] {
            position:relative;margin:0 0 .4rem 0;padding:.5rem .6rem .5rem .65rem;
            border-radius:var(--pa-radius-md);border:1px solid var(--pa-border);
            background:var(--pa-bg);overflow:hidden;
            box-shadow:0 1px 3px rgba(26,26,25,.03);
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
            font-size: 0.76rem;
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
            box-shadow:0 2px 8px rgba(30,74,122,.08);
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
            border-radius:var(--pa-radius-pill);font-size:.75rem;font-weight:700;
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
            color:var(--pa-text-muted);font-size:.75rem;font-weight:500;
            white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
            min-width:0;flex:0 1 auto;text-align:right;
        }
        .pa-sidebar-project-empty {
            padding:.8rem .4rem;color:var(--pa-text-faint);font-size:.75rem;text-align:center;
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
            background:var(--pa-surface);font-size:.75rem;
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
            color:var(--pa-text-faint);font-size:.75rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
        }
        .pa-code-breadcrumb strong {color:var(--pa-text-secondary);font-weight:700;}
        .pa-sidebar-title {font-size:.82rem;font-weight:750;color:var(--pa-text-body);margin:.2rem 0 .45rem;}
        .pa-api-status {
            display:flex;align-items:center;gap:.52rem;padding:.58rem .62rem;margin-top:.5rem;
            border:1px solid var(--pa-border-sidebar);border-radius:7px 7px 0 0;background:var(--pa-bg);
            color:var(--pa-text-body);font-size:.75rem;font-weight:650;
            white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
        }
        .pa-api-status span {width:.42rem;height:.42rem;border-radius:50%;flex:0 0 auto;}
        .pa-api-status.is-ready span {background:var(--pa-success);box-shadow:0 0 0 3px var(--pa-success-light);animation:pa-pulse 2.5s ease-in-out infinite;}
        .pa-api-status.is-warning span {background:var(--pa-warning);box-shadow:0 0 0 3px var(--pa-warning-surface);}
        .pa-sidebar-field {
            display:flex;align-items:center;justify-content:space-between;gap:.5rem;
            margin:.45rem 0 .05rem;color:var(--pa-text-muted);font-size:.75rem;
        }
        .pa-sidebar-field b {color:var(--pa-primary);font-size:.75rem;}
        .pa-sidebar-version {
            display:flex;align-items:flex-start;gap:.52rem;padding:.75rem .28rem .1rem;
            color:var(--pa-text-placeholder);font-size:.75rem;line-height:1.45;
        }
        .pa-sidebar-version > span {font-size:.85rem;color:var(--pa-text-placeholder);}
        .pa-sidebar-version small {display:block;margin-top:.12rem;color:var(--pa-text-faint);font-size:.75rem;}
        .pa-audit-empty-note {
            display:flex;flex-direction:column;gap:.12rem;margin:.55rem 0 .2rem;padding:.65rem .72rem;
            border-radius:7px;background:var(--pa-surface);color:var(--pa-text-muted);
        }
        .pa-audit-empty-note strong {color:var(--pa-text-secondary);font-size:.75rem;font-weight:700;}
        .pa-audit-empty-note span {font-size:.75rem;line-height:1.45;}
        .pa-storage-status {
            display:flex;align-items:flex-start;gap:.52rem;padding:.58rem .62rem;
            border:1px solid var(--pa-border-sidebar);border-top:0;border-radius:0 0 7px 7px;background:var(--pa-bg);min-width:0;
        }
        .pa-storage-status > span {
            width:.42rem;height:.42rem;margin-top:.18rem;border-radius:50%;background:var(--pa-success);
            box-shadow:0 0 0 3px var(--pa-success-light);animation:pa-pulse 2.5s ease-in-out infinite;flex:0 0 auto;
        }
        .pa-storage-status div {min-width:0;}
        .pa-storage-status strong {display:block;color:var(--pa-text-body);font-size:.75rem;}
        .pa-storage-status small {
            display:block;margin-top:.12rem;color:var(--pa-text-faint);font-size:.75rem;
            white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
        }
        .pa-header {
            display:flex; justify-content:space-between; align-items:center; gap:1rem;
            min-height:3.5rem;padding:.35rem 0;margin:0;border:0;border-radius:0;background:transparent;
        }
        .pa-header-title {font-size:1.05rem; font-weight:750; color:var(--pa-text-heading);}
        .pa-header-subtitle {margin-top:.12rem; color:var(--pa-text-muted); font-size:.75rem;white-space:nowrap;}
        .pa-header-badge {color:var(--pa-text-muted); font-size:.75rem; white-space:nowrap;}
        .st-key-launch_shell_empty {max-width:960px;margin:0 auto;}
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
        .pa-launch-hint {color:var(--pa-text-faint);font-size:.75rem;text-align:center;margin:.35rem 0;}
        .st-key-storage_setup_shell {
            max-width:720px;margin:clamp(2.5rem,10vh,7rem) auto 0;padding:2rem 2.1rem 1.8rem;
            border:1px solid var(--pa-border-medium);border-radius:16px;background:var(--pa-bg);
            box-shadow:0 18px 50px rgba(26,26,25,.08);
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
        .pa-recent-project-meta {color:var(--pa-text-faint);font-size:.75rem;margin-top:.16rem;}
        .pa-ready-toolbar {
            display:flex;align-items:center;gap:.5rem;min-width:0;padding:.42rem .18rem;
            border-bottom:1px solid var(--pa-border);color:var(--pa-text-secondary);
        }
        .pa-ready-toolbar strong {
            min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
            color:var(--pa-text-heading);font-size:.8rem;
        }
        .pa-ready-toolbar small {margin-left:auto;color:var(--pa-text-faint);font-size:.75rem;white-space:nowrap;}
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
        .pa-ready-file span {grid-column:1 / -1;color:var(--pa-primary);font-size:.75rem;font-weight:700;}
        .pa-ready-file strong {
            min-width:0;color:var(--pa-text-heading);font-size:.82rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
        }
        .pa-ready-file small {color:var(--pa-text-faint);font-size:.75rem;white-space:nowrap;}
        .pa-setup-title {color:var(--pa-text-heading);font-size:.88rem;font-weight:750;margin:.35rem 0 .28rem;}
        .pa-setup-mode {
            padding:.68rem .75rem;margin-bottom:.7rem;border:1px solid var(--pa-border);
            border-radius:8px;background:var(--pa-surface);
        }
        .pa-setup-mode strong {display:block;color:var(--pa-text-heading);font-size:.8rem;margin-bottom:.24rem;}
        .pa-setup-mode span {display:block;color:var(--pa-text-muted);font-size:.75rem;line-height:1.5;}
        .st-key-launch_setup_actions {margin-top:1rem;}
        .pa-setup-copy {
            color:var(--pa-text-muted);font-size:.75rem;line-height:1.55;padding:0 0 .75rem;
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
        .pa-badge {display:inline-flex;padding:.18rem .48rem;border-radius:5px;font-size:.75rem;font-weight:650;}
        .badge-supported {background:var(--pa-success-light);color:var(--pa-success-text);border:1px solid var(--pa-success-light);}
        .badge-partially {background:var(--pa-warning-surface);color:var(--pa-warning-text);border:1px solid var(--pa-warning-surface);}
        .badge-contradicted {background:var(--pa-danger-surface);color:var(--pa-danger-text);border:1px solid var(--pa-danger-surface);}
        .badge-no-support,.badge-abstain,.badge-sev-none {background:var(--pa-surface-alt);color:var(--pa-text-secondary);border:1px solid var(--pa-border-strong);}
        .badge-sev-low {background:var(--pa-primary-surface);color:var(--pa-primary-hover);border:1px solid var(--pa-primary-border);}
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
            padding:0;margin:0 0 .3rem;border:1px solid var(--pa-border-medium);
            border-radius:9px;background:var(--pa-bg);overflow:hidden;
            box-shadow:0 1px 3px rgba(26,26,25,.03);
        }
        .pa-audit-summary-grade {
            display:flex;flex-direction:column;align-items:flex-start;justify-content:center;
            gap:.06rem;min-width:7.5rem;padding:.35rem .65rem;border-right:1px solid var(--pa-border);
            background:var(--pa-surface-alt);
        }
        .pa-audit-summary-grade span {
            color:var(--pa-text-muted);font-size:.75rem;font-weight:700;text-transform:uppercase;
            letter-spacing:.04em;line-height:1.2;
        }
        .pa-audit-summary-grade strong {
            font-size:1rem;line-height:1.15;color:var(--pa-text-body);white-space:nowrap;
        }
        .pa-audit-summary-grade.is-trusted strong {color:var(--pa-success-dark);}
        .pa-audit-summary-grade.is-review strong {color:var(--pa-warning-dark);}
        .pa-audit-summary-grade.is-untrusted strong {color:var(--pa-danger-dark);}
        .pa-audit-summary-score {
            display:flex;align-items:center;min-width:4.5rem;padding:.35rem .65rem;
            border-right:1px solid var(--pa-border);color:var(--pa-primary-hover);font-size:1.4rem;
            font-weight:750;line-height:1;background:var(--pa-surface-alt);
        }
        .pa-audit-summary-score small {
            color:var(--pa-text-muted);font-size:.75rem;font-weight:600;margin-left:.18rem;
        }
        .pa-audit-summary-metrics {
            display:grid;grid-template-columns:repeat(5,minmax(7.5rem,1fr));
            align-items:stretch;gap:0;flex:1 1 auto;
        }
        .pa-audit-summary-metric {
            display:flex;flex-direction:column;align-items:center;justify-content:center;
            gap:.08rem;padding:.35rem .45rem;border-right:1px solid var(--pa-border-light);
            border-radius:0;background:var(--pa-bg);color:var(--pa-text-muted);
        }
        .pa-audit-summary-metric span {font-size:.75rem;line-height:1.2;white-space:nowrap;}
        .pa-audit-summary-metric strong {font-size:1rem;line-height:1.15;color:var(--pa-text-heading);}
        .pa-audit-summary-metric.is-danger {background:var(--pa-bg);}
        .pa-audit-summary-metric.is-danger strong {color:var(--pa-danger-dark);}
        .pa-audit-summary-metric.is-warning {background:var(--pa-bg);}
        .pa-audit-summary-metric.is-warning strong {color:var(--pa-warning-dark);}
        .pa-audit-summary-meta {
            display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;
            gap:.12rem .8rem;margin:0 0 .35rem;padding:0 .05rem;
            color:var(--pa-text-muted);font-size:.75rem;line-height:1.4;
        }
        .pa-audit-summary-meta small {color:var(--pa-text-faint);font-size:.75rem;}
        [data-testid="stMarkdown"]:has(.pa-audit-summary)
        [data-testid="stMarkdownContainer"] {margin-bottom:-.3rem !important;}
        [data-testid="stMarkdown"]:has(.pa-audit-summary-meta)
        [data-testid="stMarkdownContainer"] {margin-bottom:-.35rem !important;}
        body:has(.st-key-audit_project_header) header[data-testid="stHeader"] {
            height:2.35rem;background:transparent;
        }
        .block-container:has(.st-key-audit_project_header) {
            max-width:none;padding:1rem 1.25rem .75rem !important;
        }
        .block-container:has(.st-key-audit_project_header) > [data-testid="stVerticalBlock"] {
            width:100%;max-width:1760px;margin:0 auto;gap:8px !important;
        }
        .st-key-audit_project_header {
            padding:0 7.5rem .45rem 0;border-bottom:1px solid var(--pa-border-light);
        }
        .st-key-audit_project_header [data-testid="stHorizontalBlock"] {
            gap:.65rem !important;align-items:center !important;
        }
        .st-key-audit_project_header [data-testid="stColumn"] {min-width:0 !important;}
        .st-key-audit_project_header [data-testid^="stBaseButton-"],
        .st-key-audit_project_header [data-testid="stDownloadButton"] button {
            min-height:2.1rem;height:2.1rem;white-space:nowrap;
        }
        .pa-audit-project-heading {display:flex;flex-direction:column;min-width:0;gap:.15rem;}
        .pa-audit-project-heading strong {
            min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
            color:var(--pa-text-heading);font-size:1.1rem;line-height:1.3;
        }
        .pa-audit-project-heading span {color:var(--pa-text-muted);font-size:.75rem;}
        .st-key-audit_quick_filters {margin:.15rem 0 .45rem;}
        .st-key-audit_quick_filters div[data-testid="stButtonGroup"] {flex-wrap:wrap;}
        .st-key-audit_advanced_filters {
            width:min(100%,1040px);margin-bottom:.18rem;padding:.42rem .48rem;
            border:1px solid var(--pa-border-light);border-radius:9px;background:var(--pa-surface);
        }
        .st-key-audit_advanced_filters [data-testid="stHorizontalBlock"] {
            display:grid !important;grid-template-columns:minmax(260px,360px) repeat(4,minmax(128px,150px));
            justify-content:start;gap:.45rem !important;
        }
        .st-key-audit_advanced_filters [data-testid="stColumn"] {
            width:auto !important;min-width:0 !important;
        }
        .st-key-audit_advanced_filters [data-baseweb="select"] > div,
        .st-key-audit_advanced_filters input {min-height:2.05rem;font-size:.78rem;}
        .st-key-peer_review_pdf_panel {
            min-height:0;padding:.45rem !important;border:1px solid var(--pa-border-medium) !important;
            border-radius:10px !important;background:var(--pa-surface-alt);overflow:hidden;
        }
        .st-key-peer_review_pdf_panel [data-testid="stImage"] img {max-height:none;object-fit:contain;}
        .st-key-peer_review_pdf_panel [data-testid="stCaptionContainer"] {font-size:.75rem;}
        .st-key-peer_review_pdf_panel + div {min-width:0;}
        .pa-peer-section-card {
            margin:.35rem 0 .65rem;padding:.7rem .78rem;border:1px solid var(--pa-border-medium);
            border-radius:9px;background:var(--pa-bg);box-shadow:0 1px 3px rgba(26,26,25,.03);
        }
        .st-key-peer_review_overview {
            flex:0 0 auto !important;height:auto !important;min-height:73px !important;
            gap:3px !important;overflow:visible;
        }
        .st-key-peer_review_overview:has(.pa-peer-summary-strip) {min-height:109px !important;}
        .st-key-peer_review_overview > [data-testid="stLayoutWrapper"],
        .st-key-peer_review_overview > [data-testid="stElementContainer"] {
            flex:0 0 auto !important;height:auto !important;
        }
        .st-key-peer_review_overview > [data-testid="stElementContainer"]:has(.pa-peer-meta-line) {
            min-height:30px !important;
        }
        .st-key-peer_review_overview > [data-testid="stElementContainer"]:has(.pa-peer-summary-strip) {
            min-height:33px !important;
        }
        .st-key-peer_review_header {
            flex:0 0 auto !important;height:auto !important;min-height:40px !important;
            margin:0;padding-bottom:.18rem;
            border-bottom:1px solid var(--pa-border-light);
        }
        .st-key-peer_review_header .pa-workspace-title {font-size:1.05rem;}
        .st-key-peer_review_header .pa-workspace-summary {max-width:34rem;}
        .pa-peer-header-stat {display:flex;flex-direction:column;gap:.12rem;min-width:7rem;}
        .pa-peer-header-stat span {color:var(--pa-text-muted);font-size:.75rem;font-weight:650;}
        .pa-peer-header-stat strong {color:var(--pa-primary-dark);font-size:1rem;line-height:1.15;}
        .pa-peer-readonly-result {
            display:flex;align-items:center;justify-content:flex-end;gap:.7rem;min-height:2.5rem;
            color:var(--pa-text-muted);white-space:nowrap;
        }
        .pa-peer-readonly-result > span {font-size:.75rem;font-weight:700;color:var(--pa-text-muted);}
        .pa-peer-readonly-result > strong {font-size:1rem;}
        .pa-peer-readonly-result > b {font-size:.9rem;color:var(--pa-text-heading);}
        .pa-peer-readonly-result > small {font-size:.75rem;color:var(--pa-text-muted);}
        .pa-peer-meta-line {
            display:flex;align-items:center;flex-wrap:wrap;min-height:30px;gap:.1rem .9rem;padding:0 .1rem;
            color:var(--pa-text-muted);font-size:.75rem;line-height:1.35;
        }
        .pa-peer-meta-line span,.pa-peer-meta-line small {min-width:0;}
        .pa-peer-meta-line small {color:var(--pa-text-faint);font-size:.75rem;}
        .pa-peer-decision-strong-accept strong {color:var(--pa-success-dark);}
        .pa-peer-decision-weak-accept strong {color:#2a6b66;}
        .pa-peer-decision-borderline strong {color:var(--pa-warning-dark);}
        .pa-peer-decision-weak-reject strong {color:#a4521c;}
        .pa-peer-decision-strong-reject strong {color:var(--pa-danger-dark);}
        section.main:has(.st-key-peer_review_workspace),
        .block-container:has(.st-key-peer_review_workspace) {
            height:100vh !important;max-height:100vh !important;min-height:0 !important;overflow:hidden !important;
        }
        body:has(.st-key-peer_review_workspace) header[data-testid="stHeader"] {
            height:2.35rem;background:transparent;
        }
        .block-container:has(.st-key-peer_review_workspace) {
            padding:1rem 1.25rem .5rem !important;
        }
        .block-container:has(.st-key-peer_review_workspace) > [data-testid="stVerticalBlock"] {
            height:100%;min-height:0;display:flex;flex-direction:column;
            gap:6px !important;
        }
        .block-container:has(.st-key-peer_review_workspace) > [data-testid="stVerticalBlock"]
        > [data-testid="stLayoutWrapper"] {flex:0 0 auto !important;min-height:0 !important;}
        .block-container:has(.st-key-peer_review_workspace) > [data-testid="stVerticalBlock"]
        > [data-testid="stLayoutWrapper"]:has(.st-key-peer_review_workspace) {
            flex:1 1 0 !important;min-height:0 !important;overflow:hidden;
        }
        .st-key-peer_review_workspace,
        .st-key-peer_review_workspace > [data-testid="stLayoutWrapper"],
        .st-key-peer_review_workspace > [data-testid="stLayoutWrapper"] > [data-testid="stVerticalBlock"] {
            height:100% !important;min-height:0 !important;display:flex;flex-direction:column;overflow:hidden;
        }
        .st-key-peer_review_workspace [data-testid="stHorizontalBlock"]:has(.st-key-peer_review_source_panel) {
            flex:1 1 0 !important;height:100% !important;min-height:0 !important;align-items:stretch !important;
        }
        .st-key-peer_review_workspace [data-testid="stHorizontalBlock"]:has(.st-key-peer_review_source_panel)
        > [data-testid="stColumn"] {
            height:100% !important;min-height:0 !important;display:flex;flex-direction:column;overflow:hidden;
        }
        .st-key-peer_review_workspace [data-testid="stLayoutWrapper"]:has(>
        .st-key-peer_review_source_panel),
        .st-key-peer_review_workspace [data-testid="stLayoutWrapper"]:has(>
        .st-key-peer_review_side_panel) {
            flex:1 1 0 !important;height:100% !important;min-height:0 !important;overflow:hidden;
        }
        .st-key-peer_review_source_panel {
            flex:1 1 0 !important;height:100% !important;max-height:none !important;
            min-height:0 !important;overflow-y:auto;overflow-x:hidden;
            padding:.35rem .5rem .6rem;border:1px solid var(--pa-border-medium);background:var(--pa-surface);
            border-radius:var(--pa-radius-lg);box-shadow:var(--pa-shadow-xs);scrollbar-gutter:stable;
        }
        .st-key-peer_review_side_panel {
            flex:1 1 0 !important;height:100% !important;max-height:none !important;
            min-height:0 !important;overflow-y:auto;overflow-x:hidden;
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
        .st-key-peer_review_pdf_toolbar button p {font-size:.75rem;font-weight:600;white-space:nowrap;}
        .pa-peer-page-label {text-align:center;color:var(--pa-text-body);font-size:.75rem;font-weight:650;line-height:1.8rem;white-space:nowrap;}
        .pa-peer-page-label span {color:var(--pa-text-muted);font-weight:500;}
        .pa-peer-summary-strip {
            display:flex;align-items:center;min-height:33px;gap:.55rem;margin:0;padding:.45rem .7rem;
            border:1px solid #ecd9b4;border-radius:var(--pa-radius-md);background:#fbf4e6;color:var(--pa-text-body);
            font-size:.75rem;line-height:1.4;
        }
        .pa-peer-summary-strip strong {flex:0 0 auto;color:#a4521c;font-size:.75rem;}
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
            font-size:.75rem;font-weight:750;line-height:1.2;
        }
        .pa-peer-severity-badge {background:var(--pa-danger-surface);color:var(--pa-danger-dark);}
        .severity-p0 .pa-peer-severity-badge {background:var(--pa-danger-surface);color:var(--pa-danger-dark);}
        .severity-p1 .pa-peer-severity-badge {background:#f6e6d6;color:#9a4a1c;}
        .severity-p2 .pa-peer-severity-badge {background:var(--pa-warning-surface);color:var(--pa-warning-text);}
        .severity-p3 .pa-peer-severity-badge {background:var(--pa-surface-alt);color:var(--pa-text-secondary);}
        .pa-peer-status-badge {background:var(--pa-surface-alt);color:var(--pa-text-muted);font-weight:650;}
        .pa-peer-category-inline,.pa-peer-title-separator {color:var(--pa-text-muted);font-size:.75rem;font-weight:600;}
        .pa-peer-concern-head + [data-testid="stCaptionContainer"] {margin:0 0 .95rem;color:var(--pa-text-faint);font-size:.75rem;line-height:1.4;}
        .pa-peer-metadata {display:flex;align-items:center;gap:.48rem;flex-wrap:wrap;margin:.52rem 0 .92rem;color:var(--pa-text-faint);font-size:.75rem;line-height:1.4;}
        .pa-peer-metadata span {padding-left:.45rem;border-left:1px solid var(--pa-border-light);}
        .pa-peer-metadata em {padding:.14rem .38rem;border-radius:999px;background:#f6e6d6;color:#9a4a1c;font-size:.75rem;font-style:normal;font-weight:650;}
        .pa-peer-subsection-label {margin:0 0 .32rem;color:var(--pa-text-heading);font-size:.75rem;font-weight:750;letter-spacing:.01em;}
        .pa-peer-subsection-muted {margin-top:.12rem;color:var(--pa-text-muted);font-weight:650;}
        .pa-peer-why-text {max-width:48rem;margin:.22rem 0 .1rem;color:var(--pa-text-muted);font-size:.75rem;line-height:1.65;}
        .pa-peer-action-callout {
            margin:1rem 0 .78rem;padding:.78rem .9rem .82rem;border:1px solid var(--pa-primary-border);
            border-radius:8px;background:var(--pa-primary-surface);color:var(--pa-text-body);font-size:.75rem;line-height:1.55;
        }
        .pa-peer-action-callout strong {display:block;margin-bottom:.55rem;color:var(--pa-primary-dark);font-size:.75rem;font-weight:750;}
        .pa-peer-action-callout ul {display:grid;gap:.4rem;margin:0;padding:0;list-style:none;}
        .pa-peer-action-callout li {padding-left:.05rem;color:var(--pa-text-body);font-size:.75rem;line-height:1.5;}
        div[class*="st-key-peer-major-card-"],div[class*="st-key-peer-minor-card-"] {
            margin-bottom:.8rem;padding:1rem 1.05rem .88rem !important;border-color:var(--pa-border-medium) !important;
            border-radius:9px !important;background:var(--pa-bg);box-shadow:0 1px 2px rgba(26,26,25,.025);
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
            color:var(--pa-text-muted);font-size:.75rem;
        }
        div[class*="st-key-peer-major-card-"] [data-testid="stButton"] button,
        div[class*="st-key-peer-minor-card-"] [data-testid="stButton"] button {
            min-height:2rem;padding:.28rem .68rem;border-radius:7px;
        }
        div[class*="st-key-peer-major-card-"] [data-testid="stExpander"],
        div[class*="st-key-peer-minor-card-"] [data-testid="stExpander"] {margin-top:.28rem;}
        div[class*="st-key-peer-major-card-"] [data-testid="stExpander"] summary,
        div[class*="st-key-peer-minor-card-"] [data-testid="stExpander"] summary {
            min-height:2.25rem;padding:.35rem .68rem;color:var(--pa-text-muted);font-size:.75rem;
        }
        .pa-peer-decision-card {border-left-color:var(--pa-warning);background:var(--pa-warning-surface);}
        .pa-peer-priority-card {border-left-color:var(--pa-cyan);background:var(--pa-cyan-surface);}
        .pa-peer-blocker-card {border-left-color:var(--pa-warning);background:#fbf4e6;}
        .pa-peer-fatal-card {border-left-color:var(--pa-danger);background:#fdf3f0;}
        .pa-peer-contribution-card {border-left-color:#6b4f8a;background:#f4f0f6;}
        .pa-peer-required-card {border-left-color:#b8632a;background:#fbf4e6;}
        .pa-peer-suggested-card {border-left-color:var(--pa-text-muted);background:var(--pa-surface);}
        .pa-peer-evidence-quote {margin:.35rem 0 .5rem;padding:.45rem .58rem;border-radius:7px;background:var(--pa-surface-alt);color:var(--pa-text-muted);font-size:.75rem;line-height:1.5;}
        .pa-peer-risk-card {
            margin:0;padding:0;border:0;border-left:0;border-radius:0;background:transparent;
        }
        .pa-peer-risk-card.pa-peer-risk-high {border-left-color:var(--pa-danger);}
        .pa-peer-risk-card > div {display:flex;justify-content:space-between;gap:.6rem;align-items:center;}
        .pa-peer-risk-card strong {color:var(--pa-text-heading);font-size:.79rem;}
        .pa-peer-risk-card span {font-size:.75rem;font-weight:750;color:#a4521c;}
        .pa-peer-risk-card p {margin:.3rem 0;color:var(--pa-text-body);font-size:.75rem;line-height:1.5;}
        .pa-peer-risk-card small {color:var(--pa-text-muted);font-size:.75rem;}
        /* Keep the risk card and evidence action in one stable bordered block. */
        div[class*="st-key-peer-risk-card-"] {
            margin:.45rem 0 .85rem !important;padding:.68rem .72rem .72rem !important;
            border:1px solid var(--pa-border) !important;border-left:3px solid var(--pa-warning) !important;
            border-radius:8px !important;background:var(--pa-bg) !important;position:relative;z-index:1;
        }
        div[class*="st-key-peer-risk-card-"]:has(.pa-peer-risk-high) {
            border-left-color:var(--pa-danger) !important;
        }
        div[class*="st-key-peer-risk-card-"] > [data-testid="stVerticalBlock"] {
            gap:.2rem !important;
        }
        div[class*="st-key-peer-risk-card-"] [data-testid="stButton"] {
            margin:.28rem 0 0 !important;
        }
        div[class*="st-key-peer-risk-card-"] [data-testid="stButton"] button {
            min-height:1.72rem !important;margin:0 !important;padding:.18rem .52rem;border-radius:6px;
            font-size:.75rem !important;line-height:1.2 !important;
        }
        div[class*="st-key-peer-risk-card-"] [data-testid="stButton"] button p {
            font-size:.75rem !important;line-height:1.2 !important;
        }
        .pa-peer-action-card {
            margin:0;padding:.65rem .75rem;border:1px solid var(--pa-border);
            border-radius:8px;background:var(--pa-bg);
        }
        .pa-peer-action-title {display:flex;align-items:center;gap:.38rem;}
        .pa-peer-action-title strong {font-size:.75rem;color:var(--pa-text-heading);font-weight:700;}
        .pa-peer-action-priority {display:inline-flex;align-items:center;justify-content:center;min-width:1.65rem;padding:.15rem .32rem;border-radius:999px;font-size:.75rem;font-weight:800;line-height:1.2;}
        .pa-peer-action-priority.priority-p0 {background:var(--pa-danger-surface);color:var(--pa-danger-dark);}
        .pa-peer-action-priority.priority-p1 {background:var(--pa-warning-surface);color:var(--pa-warning-text);}
        .pa-peer-action-card p {margin:.32rem 0 0;color:var(--pa-text-body);font-size:.75rem;line-height:1.55;}
        .pa-peer-plan-progress {float:right;color:var(--pa-text-faint);font-size:.75rem;font-weight:550;line-height:1.5;}
        div[class*="st-key-peer-action-item-"] {margin:.45rem 0;padding:0 !important;overflow:visible;}
        div[class*="st-key-peer-action-item-"] > [data-testid="stVerticalBlock"] {gap:0 !important;}
        div[class*="st-key-peer-action-item-"] [data-testid="stCheckbox"] {display:flex;justify-content:flex-end;align-items:center;min-height:2.8rem;}
        div[class*="st-key-peer-action-item-"] [data-testid="stCheckbox"] label {gap:.28rem;color:var(--pa-text-muted);font-size:.75rem;white-space:nowrap;}
        .pa-peer-conclusion {margin:.35rem 0 .55rem;padding:.68rem;border:1px solid var(--pa-border);border-radius:8px;background:var(--pa-bg);}
        .pa-peer-conclusion > div {display:flex;align-items:center;justify-content:space-between;gap:.6rem;}
        .pa-peer-conclusion strong {font-size:.76rem;color:var(--pa-text-heading);}
        .pa-peer-conclusion span {font-size:.75rem;font-weight:750;}
        .pa-peer-conclusion p {margin:.38rem 0 0;color:var(--pa-text-body);font-size:.76rem;line-height:1.55;}
        .pa-peer-strength-row {padding:.55rem .1rem;border-bottom:1px solid var(--pa-border-light);}
        .pa-peer-strength-row:last-child {border-bottom:0;}
        .pa-peer-strength-row strong {font-size:.75rem;color:var(--pa-success-dark);}
        .pa-peer-strength-row p {margin:.18rem 0 0;color:var(--pa-text-body);font-size:.75rem;line-height:1.5;}
        .pa-peer-pdf-focus {
            display:flex;justify-content:space-between;gap:.5rem;padding:.38rem .55rem;
            border-bottom:1px solid var(--pa-primary-border);background:var(--pa-primary-surface);
            color:var(--pa-primary-dark);font-size:.75rem;font-weight:700;
        }
        .pa-peer-pdf-focus span {color:var(--pa-text-muted);font-weight:500;}
        .st-key-peer_review_pdf_panel [data-testid="stVerticalBlock"] {gap:.35rem;}
        .pa-audit-list-head {
            display:flex;align-items:center;gap:.4rem;min-width:0;margin-bottom:.08rem;
        }
        .pa-audit-panel-heading {
            display:flex;align-items:center;justify-content:space-between;gap:.65rem;
            min-height:2.05rem;padding:0 .08rem;color:var(--pa-text-muted);line-height:1.25;
        }
        .pa-audit-panel-heading strong {color:var(--pa-text-heading);font-size:.84rem;}
        .pa-audit-panel-heading span {font-size:.75rem;white-space:nowrap;}
        .st-key-audit_detail_navigation {margin:0 0 .1rem;}
        .st-key-audit_detail_navigation [data-testid="stHorizontalBlock"] {
            align-items:center !important;gap:.4rem !important;
        }
        .st-key-audit_detail_navigation [data-testid^="stBaseButton-"] {
            min-height:1.95rem;height:1.95rem;font-size:.75rem;
        }
        [data-testid="stHorizontalBlock"]:has(.st-key-audit_selected_detail) {
            display:grid !important;grid-template-columns:clamp(400px,26vw,460px) minmax(0,1fr);
            align-items:start !important;gap:1rem !important;
        }
        [data-testid="stHorizontalBlock"]:has(.st-key-audit_selected_detail)
        > [data-testid="stColumn"] {
            width:auto !important;min-width:0 !important;
        }
        [data-testid="stHorizontalBlock"]:has(.st-key-audit_selected_detail)
        > [data-testid="stColumn"]:nth-child(2) > [data-testid="stVerticalBlock"] {
            gap:0 !important;
        }
        .pa-audit-list-head > strong {
            padding:.12rem .32rem;border-radius:4px;background:var(--pa-primary-surface);color:var(--pa-primary-hover);
            font-size:.75rem;font-family:ui-monospace,SFMono-Regular,Consolas,monospace;
        }
        .pa-audit-list-head > span {
            min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
            font-size:.83rem;font-weight:700;color:var(--pa-text-primary);
        }
        .pa-audit-list-head > div {display:flex;flex:0 0 auto;gap:.25rem;margin-left:auto;}
        .pa-audit-list-head .pa-badge,.pa-audit-list-foot .pa-badge {
            flex:0 0 auto;padding:.1rem .38rem;border-radius:999px;
            font-size:.75rem;line-height:1.25;white-space:nowrap;
        }
        [class*="st-key-audit_claim_item_"] {
            gap:.18rem !important;padding:.48rem .58rem !important;margin-bottom:.42rem;
            border-color:var(--pa-border-medium) !important;
            border-radius:8px !important;background:var(--pa-bg);box-shadow:0 1px 2px rgba(26,26,25,.025);
        }
        [class*="st-key-audit_claim_item_active_"] {
            border-color:var(--pa-primary-border) !important;
            border-left:3px solid var(--pa-primary-action) !important;background:var(--pa-primary-surface);
            box-shadow:0 1px 3px rgba(30,74,122,.08);
        }
        [class*="st-key-audit_claim_item_"] .stButton {margin:.5rem 0 .05rem;}
        [class*="st-key-audit_claim_item_"] .stButton > button {
            min-height:0 !important;padding:.08rem 0 !important;border:0 !important;
            justify-content:flex-start !important;text-align:left;color:var(--pa-text-secondary);background:transparent !important;
            box-shadow:none !important;font-size:.76rem;line-height:1.35;
        }
        [class*="st-key-audit_claim_item_"] .stButton > button p {width:100%;text-align:left !important;}
        [class*="st-key-audit_claim_item_"] .stButton > button > div,
        [class*="st-key-audit_claim_item_"] .stButton > button > div > span,
        [class*="st-key-audit_claim_item_"] .stButton [data-testid="stMarkdownContainer"] {
            width:100%;justify-content:flex-start !important;
        }
        [class*="st-key-audit_claim_item_"] .stButton > button p {
            display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:2;
            overflow:hidden;white-space:normal;
        }
        .pa-audit-list-foot {
            display:flex;align-items:center;justify-content:space-between;gap:.5rem;
            min-height:1.25rem;color:var(--pa-text-faint);font-size:.75rem;line-height:1.2;
        }
        .pa-audit-list-foot > span {
            min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
        }
        .pa-audit-list-foot > div {display:flex;flex:0 0 auto;align-items:center;}
        [class*="st-key-audit_claim_item_"] [data-testid="stElementContainer"]:has(.pa-audit-list-foot) {
            min-height:1.4rem;flex:0 0 1.4rem !important;
        }
        .pa-audit-page-label {padding:.32rem 0;text-align:center;color:var(--pa-text-muted);font-size:.75rem;}
        .st-key-audit_selected_detail {
            gap:.45rem !important;padding:.72rem .8rem !important;border-color:var(--pa-border-medium) !important;
            border-radius:9px !important;background:var(--pa-bg);box-shadow:0 1px 3px rgba(26,26,25,.03);
        }
        .st-key-audit_selected_detail .pa-audit-detail-head {
            margin:0 0 .15rem;padding:0 0 .52rem;border-bottom:1px solid var(--pa-border-light);
        }
        .st-key-audit_selected_detail .pa-audit-detail-section {
            padding:.62rem .68rem;border:1px solid var(--pa-border-light);border-radius:8px;
            background:var(--pa-surface-alt);
        }
        div[data-testid="stExpander"]:has(.pa-audit-detail) {
            border:1px solid var(--pa-border);border-radius:9px;background:var(--pa-bg);
            margin-bottom:.45rem;box-shadow:none;
        }
        div[data-testid="stExpander"]:has(.pa-audit-detail) summary {
            padding:.65rem .8rem;color:var(--pa-text-body);font-size:.8rem;font-weight:650;
            line-height:1.45;
        }
        .pa-audit-detail {display:grid;gap:.55rem;padding:.05rem .05rem .15rem;color:var(--pa-text-body);}
        .pa-audit-detail-head {
            display:flex;justify-content:space-between;align-items:center;
            gap:.6rem;flex-wrap:wrap;padding-bottom:.5rem;
        }
        .pa-audit-detail-section {
            width:100%;padding:.55rem 0;border-top:1px solid var(--pa-border-light);
        }
        .pa-audit-claim-panel {
            border-color:var(--pa-primary-border) !important;background:var(--pa-primary-surface) !important;
        }
        .pa-audit-assessment-grid {
            display:grid;grid-template-columns:minmax(0,1.35fr) minmax(240px,.65fr);gap:.55rem;
        }
        .pa-audit-suggestion-panel {
            border-color:#ecd9b4 !important;background:var(--pa-warning-surface) !important;
        }
        .pa-audit-evidence-section {
            padding:.58rem 0 0 !important;border:0 !important;background:transparent !important;
        }
        .pa-audit-detail-label {
            margin-bottom:.3rem;color:var(--pa-text-muted);font-size:.75rem;font-weight:750;
        }
        .pa-audit-detail-copy,.pa-audit-claim,.pa-audit-evidence-text {max-width:96ch;}
        .pa-audit-detail-copy {color:var(--pa-text-secondary);font-size:.82rem;line-height:1.58;}
        .pa-audit-evidence-list {
            display:grid;grid-template-columns:repeat(auto-fit,minmax(31rem,1fr));
            align-items:stretch;gap:.4rem;width:100%;
        }
        .pa-audit-evidence-item {
            height:100%;
            padding:.58rem .68rem;border:1px solid var(--pa-border-light);border-left:3px solid var(--pa-cyan-light);
            border-radius:7px;background:var(--pa-surface-alt);
        }
        .pa-audit-evidence-meta {
            color:var(--pa-primary-hover);font-size:.75rem;font-weight:750;margin-bottom:.28rem;
        }
        .pa-audit-evidence-text {
            color:var(--pa-text-body);font-size:.78rem;line-height:1.55;white-space:normal;
            overflow-wrap:anywhere;
        }
        .pa-audit-evidence-item:only-child .pa-audit-evidence-text {
            max-width:none;
        }
        .st-key-audit_evidence_actions {margin-top:-.15rem;}
        .st-key-audit_evidence_actions [data-testid="stHorizontalBlock"] {gap:.4rem !important;}
        .st-key-audit_evidence_actions [data-testid^="stBaseButton-"] {
            min-height:1.8rem;height:1.8rem;padding:.18rem .55rem;
            border:1px solid var(--pa-border-light) !important;border-radius:6px;
            background:var(--pa-bg) !important;color:var(--pa-text-muted) !important;
            font-size:.75rem;box-shadow:none !important;
        }
        .st-key-audit_evidence_actions [data-testid^="stBaseButton-"]:hover {
            border-color:var(--pa-primary-border) !important;
            background:var(--pa-primary-surface) !important;color:var(--pa-primary-hover) !important;
        }
        .st-key-audit_evidence_actions [data-testid^="stBaseButton-"] p {
            display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
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
        .pa-panel-title span {color:var(--pa-text-faint);font-size:.75rem;font-weight:500;margin-left:.28rem;}
        .pa-workspace-status {
            display:flex;align-items:center;gap:.42rem;color:var(--pa-text-muted);font-size:.75rem;
            min-height:2rem;white-space:nowrap;overflow:hidden;
        }
        .pa-workspace-status span {
            width:.45rem;height:.45rem;border-radius:50%;background:var(--pa-success);
            box-shadow:0 0 0 3px var(--pa-success-light);animation:pa-pulse 2.5s ease-in-out infinite;flex:0 0 auto;
        }
        .pa-workspace-status strong {
            color:var(--pa-text-secondary);font-size:.75rem;font-weight:700;flex:0 0 auto;
        }
        .pa-workspace-status em {
            color:var(--pa-text-faint);font-size:.75rem;font-style:normal;overflow:hidden;
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
            border-radius:6px !important;font-size:.75rem !important;font-weight:600 !important;
        }
        .st-key-joint_workspace_nav [role="radio"][aria-checked="true"] {
            background:var(--pa-primary-surface) !important;color:var(--pa-primary) !important;
            box-shadow:0 1px 2px rgba(26,26,25,.08) !important;
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
        .st-key-audit_activity_strip [data-testid="stCaptionContainer"] {margin:0;font-size:.75rem;}
        .pa-audit-compact-message {
            position:relative;top:.38rem;min-width:0;overflow:hidden;text-overflow:ellipsis;
            white-space:nowrap;color:var(--pa-text-muted);font-size:.75rem;line-height:1.2;
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
            height:44px;padding:0 .25rem;margin:0;border:0;border-bottom:1px solid var(--pa-border-divider);
            border-radius:10px 10px 0 0;background:var(--pa-bg);position:relative;top:auto;z-index:11;
            box-shadow:none;
        }
        .st-key-learning_section_bar [role="radiogroup"] {
            height:44px;gap:.15rem !important;border:0 !important;border-radius:0 !important;
            flex-wrap:nowrap !important;
            background:transparent !important;overflow-x:auto;overflow-y:hidden;
            scrollbar-width:thin;scrollbar-color:var(--pa-border-medium) transparent;
        }
        .st-key-learning_section_bar [role="radiogroup"]::-webkit-scrollbar {height:3px;}
        .st-key-learning_section_bar [role="radiogroup"]::-webkit-scrollbar-thumb {
            background:var(--pa-border-medium);border-radius:999px;
        }
        .st-key-learning_section_bar [role="radio"],
        .st-key-learning_section_bar button {
            height:41px;min-height:41px;min-width:4.6rem !important;flex:0 0 auto !important;
            padding:.1rem .55rem !important;
            border:0 !important;border-radius:0 !important;background:transparent !important;
            box-shadow:none !important;color:var(--pa-text-secondary) !important;font-weight:560;
            font-size:.75rem !important;white-space:nowrap !important;overflow:visible !important;
        }
        .st-key-learning_section_bar [role="radio"] p,
        .st-key-learning_section_bar button p {
            margin:0;overflow:visible;white-space:nowrap;font-size:.75rem !important;
        }
        .st-key-learning_section_bar [role="radio"][aria-checked="true"],
        .st-key-learning_section_bar button[aria-checked="true"] {
            color:var(--pa-primary) !important;font-weight:700 !important;
            box-shadow:inset 0 -2px 0 var(--pa-primary) !important;
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
            color:var(--pa-primary);font-size:.75rem;font-weight:700;letter-spacing:.04em;margin-bottom:.18rem;
        }
        .pa-learning-section-title {
            color:var(--pa-text-heading);font-size:1.18rem;line-height:1.4;margin:.04rem 0 .32rem;
        }
        .pa-learning-section-overview {
            color:var(--pa-text-secondary);font-size:.8rem;line-height:1.6;margin-bottom:.2rem;
        }
        .pa-learning-block-heading {
            color:var(--pa-text-muted);font-size:.75rem;font-weight:750;letter-spacing:.05em;
            text-transform:uppercase;margin:.8rem 0 .1rem;
        }
        .pa-learning-key {
            display:inline-flex;align-items:center;gap:4px;
            padding:2px 8px;margin-bottom:0.4rem;
            border:1px solid var(--pa-primary-border); border-radius:var(--pa-radius-pill);
            background:linear-gradient(135deg, var(--pa-bg), var(--pa-surface));
            color:var(--pa-primary);font-size:.75rem;font-weight:700;
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
            min-height:1.85rem;padding:0.2rem 0.6rem;color:var(--pa-primary);font-size:.75rem;
            font-weight:600;
            background:var(--pa-primary-surface);border:1px solid var(--pa-primary-border);
            border-radius:var(--pa-radius-pill);
            transition:all var(--pa-transition-fast);
        }
        div[class*="st-key-learning_point_"] [data-testid="stBaseButton-tertiary"]:hover {
            color:var(--pa-primary-hover);background:var(--pa-primary-light);
            border-color:var(--pa-primary);transform:translateY(-1px);
            box-shadow:0 2px 6px rgba(30,74,122,0.15);
        }
        .st-key-learning_section_support {padding:.15rem .2rem .55rem;}
        .pa-learning-guide {
            display:flex;flex-direction:column;gap:.22rem;padding:.65rem .72rem;
            border-radius:var(--pa-radius-md);background:var(--pa-surface);color:var(--pa-text-secondary);
            border:1px solid var(--pa-border-light);
        }
        .pa-learning-guide strong {color:var(--pa-text-body);font-size:.75rem;}
        .pa-learning-guide span {font-size:.78rem;line-height:1.55;}
        .pa-learning-concepts-label,.pa-learning-recommend-label {
            color:var(--pa-text-muted);font-size:.75rem;font-weight:700;margin:.72rem 0 .35rem;
        }
        .pa-learning-concepts {display:flex;gap:.35rem;flex-wrap:wrap;}
        .pa-learning-concepts span {
            display:inline-flex;max-width:100%;padding:.2rem .55rem;border:1px solid var(--pa-border);
            border-radius:var(--pa-radius-pill);background:var(--pa-bg);color:var(--pa-text-secondary);font-size:.75rem;
            font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
            transition:all var(--pa-transition-fast);
        }
        .pa-learning-concepts span:hover {
            border-color:var(--pa-primary-border);color:var(--pa-primary);
        }
        .st-key-learning_section_support [data-testid="stBaseButton-tertiary"] {
            justify-content:flex-start;min-height:1.85rem;padding:.18rem .4rem;
            color:var(--pa-text-secondary);font-size:.75rem;text-align:left;
            border-radius:var(--pa-radius-sm);
        }
        .st-key-learning_section_support [data-testid="stBaseButton-tertiary"]:hover {
            color:var(--pa-primary-hover);background:var(--pa-primary-surface);
        }
        .st-key-learning_section_followup {
            position:relative;z-index:6;flex:0 0 auto;padding:.35rem .75rem .55rem;
            background:linear-gradient(to bottom,rgba(255,254,251,.72),var(--pa-bg) 28%);
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
        body:has(.pa-learning-layout) .stApp,
        body:has(.pa-learning-layout) [data-testid="stAppViewContainer"],
        body:has(.pa-learning-layout) [data-testid="stMain"] {
            height:100vh !important;max-height:100vh !important;
            overflow:hidden !important;
        }
        .block-container:has(.pa-learning-layout) > [data-testid="stVerticalBlock"] {
            height:100%;min-height:0;display:flex;flex-direction:column;
            gap:8px !important;overflow:hidden;
        }
        .block-container:has(.pa-learning-layout) > [data-testid="stVerticalBlock"]
        > [data-testid="stLayoutWrapper"]:has(.st-key-project_nav),
        .block-container:has(.pa-learning-layout) > [data-testid="stVerticalBlock"]
        > [data-testid="stLayoutWrapper"]:has(.st-key-audit_activity_strip) {
            flex:0 0 auto !important;min-height:0 !important;
        }
        .block-container:has(.pa-learning-layout) > [data-testid="stVerticalBlock"]
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
            /* Wide enough for ~30 CJK characters per line at reading size. */
            flex:0 1 clamp(420px,34vw,560px) !important;
            width:clamp(420px,34vw,560px) !important;
            max-width:560px !important;min-width:420px !important;
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
        .pa-page-relation strong {color:var(--pa-text-primary);font-size:.75rem;}
        .pa-page-point-section {
            color:var(--pa-primary);font-size:.75rem;font-weight:700;margin:0 0 .18rem;
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
            border-radius:var(--pa-radius-xs);font-size:.75rem;font-weight:700;
        }
        .pa-logic-node strong {display:block;color:var(--pa-text-heading);font-size:.82rem;line-height:1.4;}
        .pa-logic-node p {color:var(--pa-text-secondary);font-size:.76rem;line-height:1.52;margin:.25rem 0 0;}
        div[class*="st-key-learning_page_point_"] [data-testid="stBaseButton-tertiary"],
        [class*="st-key-learning_page_context_scroll_"] [data-testid="stBaseButton-tertiary"] {
            min-height:1.8rem;padding:.16rem .38rem;border:1px solid var(--pa-primary-light);
            border-radius:999px;background:var(--pa-cyan-surface);color:var(--pa-primary);font-size:.75rem;
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
        .st-key-qa_pdf_toolbar button p {font-size:.75rem;font-weight:600;white-space:nowrap;}
        .pa-pdf-panel-title {
            display:flex;align-items:center;gap:.3rem;font-weight:750;color:var(--pa-text-heading);
            font-size:.82rem;margin:0;line-height:1.8rem;
        }
        .pa-pdf-panel-title span {font-size:.75rem;font-weight:500;color:var(--pa-text-muted);}
        .pa-pdf-page-total {
            color:var(--pa-text-muted);font-size:.75rem;line-height:1.8rem;white-space:nowrap;font-weight:600;
        }
        .pa-pdf-zoom {color:var(--pa-text-body);font-size:.75rem;font-weight:650;text-align:center;line-height:1.8rem;white-space:nowrap;}
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
        .block-container:has(.pa-learning-layout) > [data-testid="stVerticalBlock"]
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
            font-size:.75rem;font-weight:720;line-height:1.35;
        }
        .pa-answer-support.is-direct {background:var(--pa-success-surface);color:var(--pa-success-dark);}
        .pa-answer-support.is-inference {background:var(--pa-warning-surface);color:var(--pa-danger-dark);}
        .pa-answer-conclusion-text {
            margin:.38rem 0 .45rem;color:var(--pa-text-heading);font-size:.88rem;font-weight:650;line-height:1.65;
        }
        .pa-answer-evidence {
            margin:.16rem 0;padding:.48rem .58rem;border-left:2px solid var(--pa-cyan-border);
            border-radius:0 6px 6px 0;background:var(--pa-surface);color:var(--pa-text-secondary);
            font-size:.75rem;line-height:1.55;
        }
        .pa-answer-evidence span {
            display:block;margin-bottom:.12rem;color:var(--pa-primary);font-size:.75rem;font-weight:700;
        }
        .st-key-qa_selected_quote {
            border-color:var(--pa-primary-border) !important;background:var(--pa-cyan-surface);margin-bottom:.7rem;
        }
        .pa-selected-quote-label {
            color:var(--pa-primary);font-size:.75rem;font-weight:700;margin-bottom:.25rem;
        }
        .pa-selected-quote {
            color:var(--pa-text-body);font-size:.84rem;line-height:1.55;
            display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden;
        }
        div[data-testid="stForm"]:has(.pa-qa-form-marker) {
            position:sticky;bottom:0;z-index:5;margin-top:.65rem;
            border:1px solid var(--pa-border-medium);padding:.55rem;background:var(--pa-bg);
            border-radius:10px;box-shadow:0 -6px 18px rgba(26,26,25,.06);
        }
        /* Paper + code is a viewport-sized workspace. The outer row stretches,
           while each panel owns its own scroll position. */
        /* Streamlit inserts a layout wrapper between keyed containers and
           their children. Constrain both layers so the workspace is truly
           viewport-sized instead of being expanded by the longest panel. */
        section.main:has(.st-key-joint_workspace) {height:100vh;min-height:0;overflow:hidden;}
        .block-container:has(.st-key-joint_workspace) {
            height:100vh;max-height:100vh;min-height:0;overflow:hidden;
        }
        /* Keep the desktop shell fixed. PDF, code, file tree, and Assistant
           history each own one explicit scroll position. */
        body:has(.st-key-joint_workspace) .stApp,
        body:has(.st-key-joint_workspace) [data-testid="stAppViewContainer"] {
            height:100vh !important;max-height:100vh !important;overflow:hidden !important;
        }
        body:has(.st-key-joint_workspace) [data-testid="stMain"],
        body:has(.st-key-joint_workspace) .stMain {
            height:100vh !important;max-height:100vh !important;overflow:hidden !important;
        }
        .st-key-joint_workspace {
            box-sizing:border-box;height:calc(100vh - 8.1rem) !important;
            min-height:540px !important;max-height:calc(100vh - 8.1rem) !important;
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
            font-size:.75rem;color:var(--pa-text-muted);font-weight:600;
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
        .st-key-joint_pdf_panel {overflow-y:auto;}
        .st-key-joint_code_panel {overflow:hidden;border-left:1px solid var(--pa-border);}
        .st-key-joint_conversation_panel {
            overflow:hidden;border-left:1px solid var(--pa-border);padding-bottom:.3rem;
        }
        .st-key-joint_assistant_scroll {
            flex:1 1 0 !important;height:auto !important;min-height:0;max-height:none;
            overflow-y:auto;overflow-x:hidden;
            overscroll-behavior:contain;scrollbar-gutter:stable;padding-right:.35rem;
        }
        .st-key-joint_conversation_panel > [data-testid="stLayoutWrapper"]:has(.st-key-joint_assistant_scroll) {
            flex:1 1 0;min-height:0;max-height:none;overflow:hidden;
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
            margin:0 0 .15rem;font-size:.75rem;line-height:1.25;
        }
        .pa-compact-code-preview,
        .pa-compact-paper-preview {
            display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:2;
            overflow:hidden;max-height:2.65rem;margin:.1rem 0 .15rem;
            color:var(--pa-text-secondary);font-size:.75rem;line-height:1.35;
        }
        .pa-compact-code-preview code {
            color:var(--pa-success-dark);font-size:.75rem;white-space:normal;
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
        .st-key-joint_pdf_toolbar button p {font-size:.75rem;font-weight:600;white-space:nowrap;}
        .pa-pdf-footer-note {
            font-size:.75rem !important;color:var(--pa-text-muted) !important;
            text-align:center !important;margin-top:.15rem !important;margin-bottom:0 !important;
            line-height:1.2 !important;
        }
        .st-key-joint_pdf_toolbar [data-testid="stNumberInput"] input {
            min-height:1.85rem;height:1.85rem;padding:.1rem .2rem;text-align:center;
        }
        .pa-code-breadcrumb {
            background:var(--pa-surface-code) !important;color:#a39a8a !important;
            padding:.55rem .8rem !important;border-radius:8px 8px 0 0 !important;
            font-size:.78rem !important;font-weight:600 !important;
            border-bottom:1px solid #35312b !important;
            display:flex !important;align-items:center !important;justify-content:space-between !important;
        }
        .pa-code-breadcrumb strong {color:#f4efe4 !important;font-weight:700 !important;}
        .pa-code-viewer {
            height:calc(100vh - 12rem) !important;max-height:none !important;
            overflow:auto;overscroll-behavior:contain;
            border:1px solid #35312b;border-radius:0 0 var(--pa-radius-md) var(--pa-radius-md);background:var(--pa-surface-code);
            padding:.6rem 0;font:12px/1.62 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
            scrollbar-gutter:stable;
        }
        .pa-code-line {display:flex;min-width:max-content;color:var(--pa-primary-light);padding:0 .8rem;}
        .pa-code-line:hover {background:#322e28;}
        .pa-code-line.is-active {background:rgba(217,169,58,.20);box-shadow:inset 3px 0 var(--pa-highlight-strong);}
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
            font-size:.75rem;font-weight:650;box-shadow:var(--pa-shadow-2xs);
        }
        .pa-assistant-subhead {
            font-size:.75rem;color:var(--pa-text-muted);font-weight:600;margin:.2rem 0 .3rem;
        }
        .pa-composer-disclaimer {
            font-size:.75rem;color:var(--pa-text-muted);text-align:center;margin-top:.3rem;margin-bottom:.1rem;
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
            font-weight:700 !important;box-shadow:0 1px 3px rgba(26,26,25,.08) !important;
        }
        .pa-code-snapshot-card {
            border:1px solid var(--pa-border-medium);border-radius:8px 8px 0 0;
            background:var(--pa-surface-alt);padding:.4rem .65rem;margin-top:.2rem;
        }
        .pa-code-snapshot-tag {
            background:var(--pa-primary-surface);color:var(--pa-primary);
            font-size:.75rem;font-weight:700;padding:1px 6px;border-radius:4px;
        }
        div[data-testid="stForm"]:has(.pa-joint-form-marker) {
            position:sticky;bottom:.15rem;z-index:5;margin:.55rem 0 .2rem;
            border:1px solid var(--pa-primary-border);padding:.45rem;background:rgba(255,254,251,.97);
            border-radius:10px;box-shadow:0 -6px 18px rgba(26,26,25,.06);
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
            border-radius:10px;background:var(--pa-bg);box-shadow:0 2px 8px rgba(26,26,25,.035);
        }
        div[class*="st-key-joint_message_selection_"],
        .st-key-joint_pending_selection {
            margin:0 0 .55rem;padding:0 0 .55rem;border-bottom:1px solid var(--pa-border);
        }
        .pa-message-selection-title {
            display:flex;align-items:center;justify-content:space-between;gap:.55rem;
            margin:0 0 .32rem;color:var(--pa-text-secondary);font-size:.75rem;
        }
        .pa-message-selection-title span {
            min-width:0;color:var(--pa-text-muted);font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
            overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
        }
        div[class*="st-key-joint_message_selection_"] [data-testid="stCode"],
        .st-key-joint_pending_selection [data-testid="stCode"] {margin:0;}
        div[class*="st-key-joint_message_selection_"] [data-testid="stCode"] pre,
        .st-key-joint_pending_selection [data-testid="stCode"] pre {
            font-size:.75rem;line-height:1.52;
        }
        .pa-assistant-user {
            margin:0 0 .45rem;padding:.48rem .58rem;border-radius:7px;
            background:var(--pa-surface-alt);color:var(--pa-text-heading);font-size:.82rem;font-weight:680;line-height:1.5;
        }
        .pa-assistant-user span {
            display:inline-flex;margin-right:.38rem;padding:.08rem .3rem;border-radius:4px;
            background:var(--pa-primary-light);color:var(--pa-primary-hover);font-size:.75rem;font-weight:750;vertical-align:.08rem;
        }
        .pa-assistant-meta {
            display:inline-flex;margin:.12rem 0 .48rem;padding:.13rem .4rem;
            border-radius:999px;background:var(--pa-success-surface);color:var(--pa-success-dark);
            font-size:.75rem;font-weight:700;
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
            box-shadow:inset 3px 0 var(--pa-primary);font-size:.75rem;line-height:1.62;
        }
        div[class*="st-key-joint_answer_body_"] pre code {
            padding:0;border:0;background:transparent;color:var(--pa-primary-light);
            white-space:pre-wrap;overflow-wrap:anywhere;word-break:break-word;
        }
        .pa-reference-heading {
            display:flex;align-items:center;gap:.38rem;margin:.58rem 0 .32rem;
            color:var(--pa-text-secondary);font-size:.75rem;font-weight:720;
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
            overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:.75rem;
        }
        div[class*="st-key-joint_code_refs_"] [data-testid="stButton"] button p {
            font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
        }
        .pa-context-title {color:var(--pa-text-muted);font-size:.75rem;font-weight:700;text-transform:uppercase;letter-spacing:.04em;}
        .pa-context-chips {display:flex;gap:.35rem;flex-wrap:wrap;margin:.2rem 0 .45rem;}
        .pa-context-chips span {
            display:inline-flex;max-width:100%;padding:.22rem .48rem;border:1px solid var(--pa-primary-border);
            border-radius:999px;background:var(--pa-primary-surface);color:var(--pa-primary-hover);font-size:.75rem;
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
            font-size:.75rem;line-height:1.58;
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
        @media (min-width:1451px) {
            .st-key-audit_project_header [data-testid="stHorizontalBlock"] {
                display:grid !important;
                grid-template-columns:minmax(320px,1fr) repeat(4,minmax(112px,160px));
            }
            .st-key-audit_project_header [data-testid="stColumn"] {
                width:auto !important;min-width:0 !important;
            }
        }
        @media (max-width:1100px) {
            [data-testid="stHorizontalBlock"]:has(.st-key-audit_selected_detail) {
                grid-template-columns:minmax(300px,38%) minmax(0,1fr);
            }
            .st-key-audit_advanced_filters [data-testid="stHorizontalBlock"] {
                grid-template-columns:minmax(220px,1.5fr) repeat(4,minmax(100px,1fr));
            }
        }
        @media (max-width:800px) {
            [data-testid="stHorizontalBlock"]:has(.st-key-audit_selected_detail) {
                grid-template-columns:minmax(0,1fr);
            }
            .st-key-audit_advanced_filters {width:100%;}
            .st-key-audit_advanced_filters [data-testid="stHorizontalBlock"] {
                grid-template-columns:minmax(0,1fr) minmax(0,1fr);
            }
            .st-key-audit_advanced_filters [data-testid="stColumn"]:first-child {
                grid-column:1 / -1;
            }
        }
        @media (max-width:1350px) {
            .pa-audit-assessment-grid {grid-template-columns:minmax(0,1fr);}
            .pa-workspace-summary {display:none;}
            .pa-workspace-title {max-width:100%;}
            .st-key-joint_workspace {height:calc(100vh - 13.8rem);min-height:480px;}
            [data-testid="stHorizontalBlock"]:has(.st-key-joint_pdf_panel) {
                gap:.25rem !important;
            }
            .st-key-joint_pdf_panel,.st-key-joint_code_panel,
            .st-key-joint_conversation_panel {padding-left:.25rem;padding-right:.25rem;}
            .st-key-joint_pdf_toolbar button {font-size:.75rem;}
        }
        @media (max-width:1350px) and (min-width:1101px) {
            /* Balanced mode keeps readable content widths by stacking paper
               and code on the left, with Assistant spanning the right rail. */
            .st-key-joint_workspace [data-testid="stHorizontalBlock"]:has(.st-key-joint_pdf_panel):has(.st-key-joint_code_panel) {
                display:grid !important;
                grid-template-columns:minmax(0,1fr) minmax(330px,34%);
                grid-template-rows:minmax(0,1fr) minmax(0,1fr);
                gap:.45rem !important;
            }
            .st-key-joint_workspace [data-testid="stHorizontalBlock"]:has(.st-key-joint_pdf_panel):has(.st-key-joint_code_panel)
            > [data-testid="stColumn"] {
                width:auto !important;min-width:0 !important;height:auto !important;min-height:0 !important;
            }
            .st-key-joint_workspace [data-testid="stHorizontalBlock"]:has(.st-key-joint_pdf_panel):has(.st-key-joint_code_panel)
            > [data-testid="stColumn"]:nth-child(1) {grid-column:1;grid-row:1;}
            .st-key-joint_workspace [data-testid="stHorizontalBlock"]:has(.st-key-joint_pdf_panel):has(.st-key-joint_code_panel)
            > [data-testid="stColumn"]:nth-child(2) {grid-column:1;grid-row:2;}
            .st-key-joint_workspace [data-testid="stHorizontalBlock"]:has(.st-key-joint_pdf_panel):has(.st-key-joint_code_panel)
            > [data-testid="stColumn"]:nth-child(3) {grid-column:2;grid-row:1 / span 2;}
        }
        @media (max-width:1100px) and (min-width:701px) {
            section.main:has(.st-key-joint_workspace),
            .block-container:has(.st-key-joint_workspace) {
                height:auto !important;max-height:none !important;min-height:100vh !important;overflow:visible !important;
            }
            body:has(.st-key-joint_workspace) .stApp,
            body:has(.st-key-joint_workspace) [data-testid="stAppViewContainer"],
            body:has(.st-key-joint_workspace) [data-testid="stMain"] {
                height:auto !important;max-height:none !important;overflow-y:auto !important;overflow-x:hidden !important;
            }
            .st-key-joint_workspace {
                height:auto !important;max-height:none !important;min-height:0 !important;overflow:visible;
            }
            .st-key-joint_workspace [data-testid="stHorizontalBlock"]:has(.st-key-joint_pdf_panel):has(.st-key-joint_code_panel) {
                display:grid !important;grid-template-columns:minmax(0,1fr) !important;
                grid-template-rows:repeat(3,minmax(440px,68vh));gap:.75rem !important;height:auto !important;
            }
            .st-key-joint_workspace [data-testid="stHorizontalBlock"]:has(.st-key-joint_pdf_panel):has(.st-key-joint_code_panel)
            > [data-testid="stColumn"] {
                grid-column:1 !important;grid-row:auto !important;width:100% !important;
                min-width:0 !important;height:100% !important;min-height:440px !important;
            }
            .st-key-joint_workspace [data-testid="stHorizontalBlock"]:has(.st-key-joint_code_panel):has(.st-key-joint_conversation_panel):not(:has(.st-key-joint_pdf_panel)),
            .st-key-joint_workspace [data-testid="stHorizontalBlock"]:has(.st-key-qa_source_panel):has(.st-key-qa_conversation_panel) {
                height:auto !important;min-height:0 !important;flex-wrap:wrap !important;gap:.75rem !important;
            }
            .st-key-joint_workspace [data-testid="stHorizontalBlock"]:has(.st-key-joint_code_panel):has(.st-key-joint_conversation_panel):not(:has(.st-key-joint_pdf_panel))
            > [data-testid="stColumn"],
            .st-key-joint_workspace [data-testid="stHorizontalBlock"]:has(.st-key-qa_source_panel):has(.st-key-qa_conversation_panel)
            > [data-testid="stColumn"] {
                flex:1 1 100% !important;width:100% !important;min-width:0 !important;
                height:68vh !important;min-height:440px !important;
            }
            .st-key-joint_conversation_panel {font-size:.88rem;}
        }
        @media (max-width:700px) {
            /* The desktop workspace is viewport-locked; release that lock on
               phones so the natural single-column flow remains scrollable. */
            section.main:has(.st-key-joint_workspace) {height:auto;overflow:visible;}
            .block-container:has(.st-key-joint_workspace) {height:auto;min-height:0;overflow:visible;}
            section.main:has(.st-key-peer_review_workspace),
            .block-container:has(.st-key-peer_review_workspace) {
                height:auto !important;max-height:none !important;min-height:0 !important;overflow:visible !important;
            }
            .st-key-peer_review_workspace,
            .st-key-peer_review_source_panel,
            .st-key-peer_review_side_panel {
                height:auto !important;max-height:none !important;min-height:0 !important;overflow:visible !important;
            }
            .st-key-joint_workspace {
                height:auto !important;max-height:none !important;min-height:0 !important;
                overflow:visible;
            }
            .pa-audit-summary {align-items:flex-start;gap:.6rem;padding:.65rem;}
            .st-key-audit_project_header {padding-right:0;}
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
            .pa-audit-evidence-list {grid-template-columns:minmax(0,1fr);}
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
            body:has(.pa-learning-layout) .stApp,
            body:has(.pa-learning-layout) [data-testid="stAppViewContainer"],
            body:has(.pa-learning-layout) [data-testid="stMain"] {
                height:auto !important;max-height:none !important;overflow:visible !important;
            }
            .block-container:has(.pa-learning-layout) {
                width:100% !important;max-width:none !important;height:auto !important;
                min-height:0 !important;padding:0 .75rem !important;overflow:visible !important;
            }
            .block-container:has(.pa-learning-layout) > [data-testid="stVerticalBlock"] {
                height:auto !important;min-height:0 !important;overflow:visible !important;
            }
            .st-key-project_nav,.st-key-audit_activity_strip {
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

        /* ── Academic paper theme layer ─────────────────────── */
        /* Display type is set in serif like a paper; UI text stays sans for density. */
        .pa-header-title,.pa-workspace-title,.pa-learning-section-title,.pa-sidebar-library-title,
        .pa-storage-setup-title,.pa-upload-title,.pa-setup-title,.pa-grade-title,.pa-learning-topic-title,
        .pa-panel-title,.pa-pdf-panel-title,.pa-explanation-panel-title,.pa-audit-panel-heading,
        .pa-audit-summary-grade strong,.pa-audit-summary-score strong,.pa-peer-header-stat strong,
        .pa-launch-step-index,.pa-learning-point-title,
        [data-testid="stMain"] h1,[data-testid="stMain"] h2,[data-testid="stMain"] h3 {
            font-family:var(--pa-font-sans) !important;letter-spacing:0;
        }
        [data-testid="stMain"] h1,[data-testid="stMain"] h2 {font-size:1.25rem !important;font-weight:600 !important;}
        [data-testid="stMain"] h3 {font-size:1rem !important;font-weight:600 !important;}
        [data-testid="stBaseButton-primary"] p,[data-testid="stBaseButton-secondary"] p {white-space:nowrap;}

        /* Upload zone: a sheet of paper on the desk */
        .st-key-launch_pdf_upload_empty {
            margin:1.4rem 0 .4rem;padding:2.2rem 1.5rem 2rem;border:1px dashed var(--pa-border-strong);
            border-radius:var(--pa-radius-md);background:var(--pa-bg);box-shadow:var(--pa-shadow-sm);
        }
        .st-key-launch_pdf_upload_empty:hover {border-color:var(--pa-primary-border);}
        .pa-upload-title {font-size:1.25rem;font-weight:700;margin-bottom:.35rem;text-align:center;}
        .pa-upload-subtitle {font-size:.8rem;text-align:center;}
        .st-key-launch_pdf_upload_empty [data-testid="stFileUploaderDropzone"] button {
            min-height:2.3rem;padding:0 1.1rem;border-color:var(--pa-primary);
            background:var(--pa-primary);color:var(--pa-bg);
        }
        .st-key-launch_pdf_upload_empty [data-testid="stFileUploaderDropzone"] button:hover {
            background:var(--pa-primary-hover);border-color:var(--pa-primary-hover);color:var(--pa-bg);
        }
        .st-key-launch_pdf_upload_empty [data-testid="stFileUploaderDropzone"] button [data-testid="stMarkdownContainer"] {display:none;}
        .st-key-launch_pdf_upload_empty [data-testid="stFileUploaderDropzone"] button::after {
            content:"选择 PDF 文件";font-size:.82rem;font-weight:650;
        }

        /* Sidebar: tighter top, quieter controls */
        /* The collapse control floats beside the library title instead of taking its own row. */
        section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {position:relative;}
        section[data-testid="stSidebar"] [data-testid="stSidebarHeader"] {
            position:absolute;top:.85rem;right:.55rem;z-index:3;height:auto;min-height:0;
            margin:0 !important;padding:0;background:transparent;
        }
        section[data-testid="stSidebar"] [data-testid="stLogoSpacer"] {display:none;}
        section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {padding-top:0 !important;padding-bottom:.5rem !important;}
        section[data-testid="stSidebar"] hr {margin:.55rem 0 !important;}
        /* Leave room for the controls above and the settings/status/footer below the list. */
        .st-key-sidebar_project_list {max-height:calc(100vh - 32rem) !important;}
        section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {background:var(--pa-bg-page);}
        .pa-sidebar-library-title {font-size:1.1rem;font-weight:700;margin:0 0 .7rem;}
        /* The search box key also matches the project-card selector; undo the card. */
        .st-key-sidebar_project_search,
        .st-key-sidebar_project_search:hover {
            padding:0 !important;border:0 !important;background:transparent !important;
            box-shadow:none !important;transform:none !important;overflow:visible !important;
        }
        .st-key-sidebar_project_search [data-testid="stTextInputRootElement"] {
            background:var(--pa-bg);border-color:var(--pa-border-medium);
        }
        .st-key-sidebar_project_search [data-baseweb="input"],
        .st-key-sidebar_project_search [data-testid="stTextInputRootElement"] {height:2.1rem;min-height:2.1rem;}
        .st-key-sidebar_project_search input {padding-top:0;padding-bottom:0;font-size:.78rem;}
        div[class*="st-key-sidebar_project_"]:hover {transform:none;}
        div[class*="st-key-sidebar_project_"]:has(.pa-sidebar-project-marker.is-active) {
            border-left-width:3px;box-shadow:none;background:var(--pa-bg);
        }
        .pa-sidebar-version > span {font-family:var(--pa-font-sans);font-size:1rem;color:var(--pa-text-muted);}
        .pa-sidebar-version div {color:var(--pa-text-secondary);font-weight:650;}

        /* Workspace headers */
        .pa-workspace-title {font-size:1.08rem;font-weight:700;}
        .pa-workspace-brand-icon {background:var(--pa-primary-surface);color:var(--pa-primary);}
        .pa-learning-section-title {font-size:1.3rem;font-weight:700;}
        .pa-learning-section-kicker {color:var(--pa-text-muted);letter-spacing:.1em;}
        .pa-learning-section-overview {font-size:.84rem;line-height:1.7;}
        .pa-audit-summary,.pa-peer-summary-strip {border-radius:var(--pa-radius-md);}
        mark.pa-mark {background:var(--pa-highlight);color:inherit;padding:0 .1em;border-radius:2px;}

        /* Six-dimension scores */
        [data-testid="stMarkdownContainer"] ul.pa-dim-scores {width:100%;margin:.4rem 0 0;padding:0;list-style:none;}
        .pa-dim-scores li {
            display:grid;grid-template-columns:8.5rem minmax(0,1fr) 3rem;align-items:center;gap:.9rem;
            margin:0;padding:.62rem 0;border-bottom:1px solid var(--pa-border-light);
        }
        .pa-dim-scores li span {color:var(--pa-text-body);font-size:.8rem;}
        .pa-dim-scores li strong {
            color:var(--pa-text-heading);font-family:var(--pa-font-sans);font-size:.95rem;text-align:right;
        }
        .pa-dim-bar {height:6px;border-radius:3px;background:var(--pa-surface-alt);overflow:hidden;}
        .pa-dim-bar i {display:block;height:100%;background:var(--pa-primary);}
        .pa-dim-scores li.is-na span,.pa-dim-scores li.is-na strong {color:var(--pa-text-faint);}
        .pa-dim-scores li.is-na .pa-dim-bar {
            background:repeating-linear-gradient(90deg,var(--pa-border) 0 4px,transparent 4px 8px);height:1px;
        }

        /* Buttons never break CJK labels into vertical stacks */
        [data-testid^="stBaseButton-primary"] p,[data-testid^="stBaseButton-secondary"] p {white-space:nowrap;}
        .st-key-learning_section_followup [data-testid^="stBaseButton-primary"] {min-width:3.4rem;padding:0 .6rem;}

        /* Evidence locate buttons read as left-aligned citations */
        div[class*="st-key-learning_point_"] [data-testid="stBaseButton-tertiary"] {
            justify-content:flex-start !important;text-align:left !important;
        }
        div[class*="st-key-learning_point_"] [data-testid="stBaseButton-tertiary"] p {text-align:left !important;}

        /* PDF toolbars: one control height, vertically centred labels */
        :is(.st-key-learning_pdf_toolbar,.st-key-qa_pdf_toolbar,.st-key-peer_review_pdf_toolbar,.st-key-joint_pdf_toolbar)
            [data-testid="stHorizontalBlock"] {align-items:center !important;}
        :is(.st-key-learning_pdf_toolbar,.st-key-qa_pdf_toolbar,.st-key-peer_review_pdf_toolbar,.st-key-joint_pdf_toolbar)
            :is([data-testid="stNumberInputContainer"],[data-testid="stTextInputRootElement"],[data-baseweb="input"]) {
            height:1.85rem !important;min-height:1.85rem !important;
        }
        :is(.st-key-learning_pdf_toolbar,.st-key-qa_pdf_toolbar,.st-key-peer_review_pdf_toolbar,.st-key-joint_pdf_toolbar)
            input {padding-top:0 !important;padding-bottom:0 !important;font-size:.78rem;text-align:center;}
        :is(.st-key-learning_pdf_toolbar,.st-key-qa_pdf_toolbar,.st-key-peer_review_pdf_toolbar,.st-key-joint_pdf_toolbar)
            [data-testid="stMarkdownContainer"] p {margin:0 !important;line-height:1.85rem;}
        :is(.st-key-learning_pdf_toolbar,.st-key-qa_pdf_toolbar,.st-key-peer_review_pdf_toolbar,.st-key-joint_pdf_toolbar)
            [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {margin-top:0 !important;margin-bottom:0 !important;}
        :is(.st-key-learning_pdf_toolbar,.st-key-qa_pdf_toolbar,.st-key-peer_review_pdf_toolbar,.st-key-joint_pdf_toolbar)
            [data-testid="stMarkdownContainer"] {margin-bottom:0 !important;}
        .pa-pdf-panel-title {line-height:1.85rem;}

        /* Peer-review dimension cards: body copy at reading size, not display size */
        div[class*="st-key-peer_dimension_"] {background:var(--pa-bg);}
        div[class*="st-key-peer_dimension_"] [data-testid="stMarkdownContainer"] p {font-size:.85rem;line-height:1.7;}
        div[class*="st-key-peer_dimension_"] [data-testid="stMarkdownContainer"] p strong {
            font-family:var(--pa-font-sans);font-size:.98rem;
        }

        .st-key-storage_setup_shell {border-radius:var(--pa-radius-xl);box-shadow:var(--pa-shadow-lg);}

        /* ── Flat reading layout (pass 2): fewer boxes, larger text ───────── */
        /* Lecture panel: section intro and points read as one column of text. */
        .pa-learning-topic-card {
            padding:.35rem 0 1rem;margin:0 0 .25rem;border:0;border-bottom:1px solid var(--pa-border);
            border-radius:0;background:transparent;box-shadow:none;
        }
        .pa-learning-topic-title {font-size:1.35rem !important;font-weight:700;margin:0 0 .45rem;}
        .pa-learning-section-overview {font-size:.9rem;line-height:1.75;color:var(--pa-text-body);}
        div[class*="st-key-learning_point_"],
        div[class*="st-key-learning_page_point_"] {
            margin:0;padding:1rem 0 .85rem;border:0;border-bottom:1px solid var(--pa-border-light);
            border-radius:0;background:transparent;box-shadow:none;
        }
        div[class*="st-key-learning_point_"]:hover,
        div[class*="st-key-learning_page_point_"]:hover {transform:none;box-shadow:none;border-color:var(--pa-border-light);}
        .pa-learning-bullet-item {padding-left:0;margin-bottom:.35rem;border-left:0;}
        .pa-learning-bullet-item.is-active {padding-left:.75rem;border-left:2px solid var(--pa-primary);}
        .pa-learning-bullet-title {font-size:.95rem;font-weight:700;margin-bottom:.35rem;color:var(--pa-text-heading);}
        .pa-learning-bullet-text {font-size:.88rem;line-height:1.75;color:var(--pa-text-body);margin-bottom:.3rem;}
        /* Citations look like references, not form buttons. */
        div[class*="st-key-learning_point_"] [data-testid="stBaseButton-tertiary"],
        div[class*="st-key-learning_page_point_"] [data-testid="stBaseButton-tertiary"] {
            min-height:0 !important;height:auto;padding:.1rem 0 !important;border:0 !important;
            background:transparent !important;box-shadow:none !important;transform:none !important;
            color:var(--pa-primary) !important;
        }
        div[class*="st-key-learning_point_"] [data-testid="stBaseButton-tertiary"] p,
        div[class*="st-key-learning_page_point_"] [data-testid="stBaseButton-tertiary"] p {
            font-size:.78rem !important;font-weight:500;white-space:normal;
        }
        div[class*="st-key-learning_point_"] [data-testid="stBaseButton-tertiary"]:hover p,
        div[class*="st-key-learning_page_point_"] [data-testid="stBaseButton-tertiary"]:hover p {
            text-decoration:underline;text-underline-offset:3px;
        }
        div[class*="st-key-learning_point_"] [data-testid="stBaseButton-primary"] {
            min-height:0 !important;padding:.15rem .5rem !important;justify-content:flex-start;
            background:var(--pa-highlight) !important;border:0 !important;color:var(--pa-text-heading) !important;
        }
        div[class*="st-key-learning_point_"] [data-testid="stBaseButton-primary"] p {font-size:.78rem !important;font-weight:600;}
        /* Bordered wrappers around lecture/source panels: keep one quiet frame. */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.pa-learning-nav-marker),
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.pa-learning-source-marker) {
            border-radius:var(--pa-radius-md);box-shadow:none;
        }

        /* Workspace header: show the paper title, drop the decorative icon. */
        .pa-workspace-brand-icon {display:none;}
        .pa-workspace-title {max-width:68%;font-size:1.15rem;}
        .pa-workspace-summary {flex:1 1 0;max-width:none;font-size:.78rem;}

        /* Sidebar: a quiet list instead of stacked cards. */
        div[class*="st-key-sidebar_project_"]:not(.st-key-sidebar_project_list):not(.st-key-sidebar_project_search) {
            margin:0 0 .15rem;padding:.55rem .6rem .5rem .7rem;border:0 !important;border-radius:var(--pa-radius-sm);
            background:transparent;box-shadow:none !important;
        }
        div[class*="st-key-sidebar_project_"]:not(.st-key-sidebar_project_list):not(.st-key-sidebar_project_search):hover {
            background:#e9e8e5;transform:none;
        }
        div[class*="st-key-sidebar_project_"]:has(.pa-sidebar-project-marker.is-active):not(.st-key-sidebar_project_list) {
            background:var(--pa-bg) !important;border-left:0 !important;
            box-shadow:inset 2px 0 0 var(--pa-primary), 0 1px 2px rgba(26,26,25,.06) !important;
        }
        div[class*="st-key-sidebar_project_"] button p {font-size:.8rem !important;}
        .pa-sidebar-project-meta {margin-top:.3rem;}
        /* Content-type tags: tinted badges, one per saved artifact. */
        .pa-project-chip {
            height:20px;padding:0 6px !important;border:0 !important;border-radius:4px;
            font-size:.75rem !important;font-weight:500;display:inline-flex;align-items:center;
        }
        .pa-project-chips {display:inline-flex;align-items:center;gap:4px;flex-shrink:0;}
        .chip-paper {background:#e8f1ea !important;color:#2f6b45 !important;}
        .chip-audit {background:#f7eedb !important;color:#8a5a12 !important;}
        .chip-review {background:#f1eaf4 !important;color:#6d4c7d !important;}
        .chip-code {background:#eaf0f6 !important;color:#1e4a7a !important;}
        .chip-empty {background:#e9e8e5 !important;color:#4f4a42 !important;}
        /* Destructive confirm: never reuse the brand-blue primary style. */
        .st-key-confirm_project_delete button {
            background:var(--pa-danger) !important;border-color:var(--pa-danger) !important;color:#fff !important;
        }
        .st-key-confirm_project_delete button:hover {
            background:var(--pa-danger-dark) !important;border-color:var(--pa-danger-dark) !important;
        }
        .st-key-confirm_project_delete button p {color:#fff !important;}
        .pa-sidebar-filename {font-size:.75rem;color:var(--pa-text-faint);}
        section[data-testid="stSidebar"] [data-testid="stExpander"] details {border-color:var(--pa-border);background:transparent;}
        section[data-testid="stSidebar"] [data-testid="stExpander"] summary p {font-size:.8rem;color:var(--pa-text-secondary);}
        .pa-sidebar-status {
            display:flex;align-items:center;gap:.4rem;flex-wrap:wrap;margin:.7rem .15rem .2rem;
            color:var(--pa-text-secondary);font-size:.75rem;
        }
        .pa-sidebar-status > span {width:7px;height:7px;border-radius:50%;background:var(--pa-success);}
        .pa-sidebar-status.is-warning > span {background:var(--pa-warning);}
        .pa-sidebar-status em {
            flex:1 0 100%;padding-left:calc(7px + .4rem);font-style:normal;color:var(--pa-text-faint);
            overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
        }
        .pa-sidebar-version {padding:.6rem .15rem 0;}
        /* The top nav already says 论文讲解; keep only the scope switch here. */
        .st-key-learning_explanation_header .pa-explanation-panel-title {visibility:hidden;}
        .st-key-learning_explanation_header {min-height:0;padding:.35rem .9rem;}
        /* Section tabs scroll horizontally; fade the edge so cut-off labels read as "more". */
        .st-key-learning_section_bar [role="radiogroup"] {
            mask-image:linear-gradient(90deg,#000 85%,transparent);-webkit-mask-image:linear-gradient(90deg,#000 85%,transparent);
        }

        /* Sidebar cards: Streamlit's -1rem markdown margin would clip the meta row. */
        div[class*="st-key-sidebar_project_"] [data-testid="stMarkdownContainer"] {margin-bottom:0 !important;}
        div[class*="st-key-sidebar_project_"]:not(.st-key-sidebar_project_list) {overflow:visible !important;}

        /* Peer review: risks read as a list, evidence actions as links. */
        div[class*="st-key-peer-risk-card-"] {
            padding:1rem 0 .9rem !important;margin:0 !important;border:0 !important;
            border-bottom:1px solid var(--pa-border-light) !important;border-radius:0 !important;
            background:transparent !important;box-shadow:none !important;
        }
        .pa-peer-risk-card {padding:0 !important;border:0 !important;background:transparent !important;}
        .pa-peer-risk-card strong {font-size:.92rem;line-height:1.45;}
        .pa-peer-risk-card span {font-size:.75rem;font-weight:600;color:var(--pa-text-muted);white-space:nowrap;}
        .pa-peer-risk-card p {font-size:.86rem;line-height:1.7;margin:.35rem 0 .3rem;}
        .pa-peer-risk-card small {font-size:.75rem;}
        .pa-peer-risk-card.pa-peer-risk-high strong::before,
        .pa-peer-risk-card.pa-peer-risk-medium strong::before {
            content:"";display:inline-block;width:7px;height:7px;margin:0 .45rem .1rem 0;border-radius:50%;
            background:var(--pa-warning);vertical-align:middle;
        }
        .pa-peer-risk-card.pa-peer-risk-high strong::before {background:var(--pa-danger);}
        div[class*="-evidence-actions"] [data-testid="stHorizontalBlock"] {justify-content:flex-start;gap:1rem !important;}
        div[class*="-evidence-actions"] [data-testid="stColumn"] {flex:0 0 auto !important;width:auto !important;}
        div[class*="-evidence-actions"] button {
            min-height:0 !important;padding:.1rem 0 !important;border:0 !important;
            background:transparent !important;color:var(--pa-primary) !important;
        }
        div[class*="-evidence-actions"] button p {font-size:.78rem !important;font-weight:500;}
        div[class*="-evidence-actions"] button:hover p {text-decoration:underline;text-underline-offset:3px;}
        div[class*="-evidence-actions"] button p::after {content:" ↗";}
        div[class*="st-key-peer_dimension_"] {
            border:0 !important;border-bottom:1px solid var(--pa-border-light) !important;border-radius:0 !important;
            background:transparent !important;padding:.9rem 0 !important;
        }
        .pa-peer-meta-line {font-size:.75rem !important;color:var(--pa-text-muted);}
        .pa-peer-meta-line small {cursor:help;color:var(--pa-text-faint);}
        .pa-peer-summary-strip {font-size:.8rem;}
        /* One frame around the peer-review PDF, not two. */
        .st-key-peer_review_pdf_panel {border:0 !important;border-radius:0 !important;background:transparent !important;padding:0 !important;}

        /* ── Content typography (pass 3): measure, rhythm, hierarchy ─────── */
        [class*="st-key-learning_report_scroll_"],
        [class*="st-key-learning_page_context_scroll_"] {padding:1.1rem 1.5rem 1.25rem !important;}
        /* Streamlit puts 1rem between every element; inside a point that splits title from body. */
        div[class*="st-key-learning_point_"] > [data-testid="stVerticalBlock"],
        div[class*="st-key-learning_page_point_"] > [data-testid="stVerticalBlock"] {gap:.15rem !important;}
        .pa-learning-topic-card {padding:0 0 1.1rem;}
        .pa-learning-topic-title {margin:0 0 .55rem !important;line-height:1.3;}
        .pa-learning-section-overview {font-size:.92rem;line-height:1.8;margin:0;}
        div[class*="st-key-learning_point_"],
        div[class*="st-key-learning_page_point_"] {padding:1.05rem 0 .9rem !important;}
        .pa-learning-bullet-title {font-size:.98rem;line-height:1.45;margin:0 0 .4rem;}
        .pa-learning-bullet-text {font-size:.9rem;line-height:1.8;margin:0;text-align:justify;}
        div[class*="st-key-learning_point_"] [data-testid="stBaseButton-tertiary"] p,
        div[class*="st-key-learning_page_point_"] [data-testid="stBaseButton-tertiary"] p {color:var(--pa-primary) !important;}
        div[class*="st-key-learning_point_"] [data-testid="stButton"] {margin-top:.35rem;}
        /* Scope switch: a compact control in the panel header, not a full-width row. */
        .st-key-learning_explanation_header {padding:.45rem 1.5rem !important;}
        .st-key-learning_explanation_header [role="radiogroup"] {min-height:0 !important;width:auto !important;}
        .st-key-learning_explanation_header [role="radio"] {min-height:1.75rem !important;height:1.75rem;padding:0 .9rem !important;}
        .st-key-learning_explanation_header [role="radio"] p {font-size:.76rem !important;}
        /* Logic chain: an inline section, not a grey box. */
        [class*="st-key-learning_report_scroll_"] [data-testid="stExpander"] details {
            border:0;border-top:1px solid var(--pa-border-light);border-radius:0;background:transparent;
        }
        [class*="st-key-learning_report_scroll_"] [data-testid="stExpander"] summary {padding-left:0;background:transparent;}
        [class*="st-key-learning_report_scroll_"] [data-testid="stExpander"] summary p {
            font-family:var(--pa-font-sans);font-size:.98rem;font-weight:700;color:var(--pa-text-heading);
        }

        /* Peer review: let the title use the row, condense the notes. */
        .st-key-peer_review_header .pa-workspace-title {max-width:none;white-space:normal;
            display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;font-size:1.15rem;line-height:1.35;}
        .st-key-peer_review_header .pa-workspace-title-row {flex-direction:column;align-items:flex-start;gap:.15rem;}
        .st-key-peer_review_header .pa-workspace-summary {flex:0 0 auto;max-width:none;font-size:.76rem;}
        .pa-peer-meta-line {line-height:1.6;margin:.2rem 0 .55rem !important;}
        .pa-peer-summary-strip {padding:.6rem .85rem !important;line-height:1.65;}
        div[class*="st-key-peer-risk-card-"] > [data-testid="stVerticalBlock"],
        div[class*="st-key-peer_dimension_"] > [data-testid="stVerticalBlock"] {gap:.25rem !important;}
        .pa-peer-risk-card p {text-align:justify;}
        [class*="st-key-learning_report_scroll_"] .pa-learning-topic-card {padding-top:0;}
        [class*="st-key-learning_report_scroll_"] {padding-top:.6rem !important;}
        .st-key-peer_review_header {padding-bottom:.65rem !important;}
        .st-key-peer_review_header .pa-workspace-summary {margin-top:.2rem;}

        /* ── Audit results (pass 3): label + text, quotes as blockquotes ─── */
        .st-key-audit_selected_detail {padding:1.1rem 1.35rem !important;box-shadow:none !important;gap:.2rem !important;}
        .st-key-audit_selected_detail .pa-audit-detail-section,
        .pa-audit-claim-panel {
            padding:.85rem 0 !important;border:0 !important;border-radius:0 !important;background:transparent !important;
        }
        .st-key-audit_selected_detail .pa-audit-detail-section + .pa-audit-detail-section {border-top:1px solid var(--pa-border-light) !important;}
        .pa-audit-detail-label {
            margin-bottom:.4rem;color:var(--pa-text-muted);font-size:.75rem;font-weight:600;letter-spacing:.06em;
        }
        .pa-audit-detail-copy {font-size:.9rem;line-height:1.8;color:var(--pa-text-body);}
        .pa-audit-claim-panel .pa-audit-detail-copy,.pa-audit-claim-panel .pa-audit-claim {
            padding-left:.85rem;border-left:2px solid var(--pa-primary);
            font-size:1rem;line-height:1.7;color:var(--pa-text-heading);
        }
        .pa-audit-assessment-grid {gap:1.5rem;}
        .pa-audit-suggestion-panel {padding:.75rem .9rem !important;border-radius:var(--pa-radius-md) !important;}
        .pa-audit-evidence-item {
            padding:.15rem 0 .15rem .9rem !important;border:0 !important;border-left:2px solid var(--pa-cyan-light) !important;
            border-radius:0 !important;background:transparent !important;
        }
        .pa-audit-evidence-meta {font-size:.75rem;font-weight:600;color:var(--pa-cyan);margin-bottom:.35rem;}
        .pa-audit-evidence-text {font-family:var(--pa-font-serif);font-size:.92rem;line-height:1.7;color:var(--pa-text-body);}
        .st-key-audit_evidence_actions [data-testid^="stBaseButton-"] {
            min-height:0 !important;height:auto !important;padding:.1rem 0 !important;border:0 !important;
            background:transparent !important;color:var(--pa-primary) !important;justify-content:flex-start;
        }
        .st-key-audit_evidence_actions [data-testid^="stBaseButton-"] p {font-size:.78rem !important;color:var(--pa-primary);}
        .st-key-audit_evidence_actions [data-testid^="stBaseButton-"]:hover p {text-decoration:underline;text-underline-offset:3px;}
        /* Claim list: rows with hairlines; only the selected row is tinted. */
        [class*="st-key-audit_claim_item_"] {
            margin:0 !important;padding:.75rem .7rem !important;border:0 !important;border-radius:0 !important;
            border-bottom:1px solid var(--pa-border-light) !important;background:transparent !important;box-shadow:none !important;
        }
        [class*="st-key-audit_claim_item_active_"] {
            background:var(--pa-bg) !important;box-shadow:inset 2px 0 0 var(--pa-primary) !important;
        }
        [class*="st-key-audit_claim_item_"] .stButton > button p {font-size:.86rem !important;line-height:1.6;color:var(--pa-text-body);}
        .pa-audit-list-foot {font-size:.75rem;}
        .pa-audit-summary-meta,.pa-audit-summary-meta small {font-size:.75rem !important;}
        .pa-audit-summary-metric span {font-size:.75rem;}
        .pa-audit-evidence-text {font-weight:400;}
        .st-key-audit_selected_detail .pa-audit-assessment-grid .pa-audit-detail-section {border-top:0 !important;}
        .st-key-audit_evidence_actions {margin-top:.45rem !important;padding-left:calc(.9rem + 2px);}
        .st-key-audit_evidence_actions [data-testid="stHorizontalBlock"] {justify-content:flex-start !important;}
        .st-key-audit_evidence_actions [data-testid="stColumn"] {flex:0 0 auto !important;width:auto !important;}

        /* ── Peer-review issues (pass 4): list rows, readable sizes ──────── */
        div[class*="st-key-peer-major-card-"],div[class*="st-key-peer-minor-card-"] {
            margin:0 !important;padding:1.1rem 0 1rem !important;border:0 !important;border-radius:0 !important;
            border-bottom:1px solid var(--pa-border-light) !important;background:transparent !important;box-shadow:none !important;
        }
        div[class*="st-key-peer-major-card-"] > [data-testid="stVerticalBlock"],
        div[class*="st-key-peer-minor-card-"] > [data-testid="stVerticalBlock"] {gap:.3rem !important;}
        .pa-peer-concern-head {display:block !important;margin:0 0 .4rem !important;padding:0 !important;border:0 !important;background:transparent !important;}
        .pa-peer-concern-kicker {display:flex;align-items:center;gap:.5rem;flex-wrap:wrap;margin-bottom:.35rem;
            color:var(--pa-text-muted);font-size:.75rem;}
        .pa-peer-concern-kicker .pa-peer-severity-badge {padding:.05rem .4rem;border-radius:3px;font-size:.75rem;font-weight:700;}
        .pa-peer-concern-kicker .pa-peer-status-badge {margin-left:auto;padding:.05rem .45rem;border-radius:3px;
            background:var(--pa-warning-surface);color:var(--pa-warning-text);font-size:.75rem;font-weight:600;white-space:nowrap;}
        .pa-peer-concern-head strong.pa-peer-concern-title {
            display:block;font-family:var(--pa-font-sans);font-size:1rem !important;font-weight:700;line-height:1.5;
            color:var(--pa-text-heading);white-space:normal;
        }
        .pa-peer-subsection-label {margin:.5rem 0 .25rem !important;color:var(--pa-text-muted) !important;
            font-size:.75rem !important;font-weight:600 !important;letter-spacing:.06em;}
        div[class*="st-key-peer-major-card-"] [data-testid="stMarkdownContainer"] > p,
        div[class*="st-key-peer-minor-card-"] [data-testid="stMarkdownContainer"] > p {
            font-size:.88rem !important;line-height:1.75 !important;color:var(--pa-text-body) !important;text-align:justify;
        }
        div[class*="st-key-peer-major-card-"] .pa-peer-metadata,
        div[class*="st-key-peer-minor-card-"] .pa-peer-metadata {font-size:.75rem !important;margin:.2rem 0 .3rem !important;}
        div[class*="st-key-peer-major-card-"] .pa-peer-why-text,
        div[class*="st-key-peer-minor-card-"] .pa-peer-why-text {font-size:.84rem !important;line-height:1.75 !important;color:var(--pa-text-secondary) !important;max-width:none;}
        .pa-peer-action-callout {margin:.6rem 0 .3rem !important;padding:.75rem .9rem !important;border:0 !important;
            border-left:2px solid var(--pa-primary) !important;border-radius:0 !important;background:var(--pa-primary-surface) !important;}
        .pa-peer-action-callout strong {font-size:.76rem !important;margin-bottom:.45rem !important;}
        .pa-peer-action-callout li {position:relative;padding-left:1.35rem !important;font-size:.84rem !important;line-height:1.65 !important;}
        .pa-peer-action-callout li::before {content:"";position:absolute;left:0;top:.32em;width:.8em;height:.8em;
            border:1.5px solid var(--pa-primary-border);border-radius:2px;background:var(--pa-bg);}
        .pa-peer-note {margin:.4rem 0 .2rem;padding:.55rem .8rem;border-left:2px solid var(--pa-warning);
            background:var(--pa-warning-surface);color:var(--pa-warning-text);font-size:.8rem;line-height:1.6;}
        div[class*="st-key-peer-major-card-"] [data-testid="stExpander"] details,
        div[class*="st-key-peer-minor-card-"] [data-testid="stExpander"] details {border-color:var(--pa-border-light);background:transparent;}

        /* Streamlit's uploader copy is English-only; relabel every dropzone. */
        [data-testid="stFileUploaderDropzone"] button [data-testid="stMarkdownContainer"] {display:none;}
        [data-testid="stFileUploaderDropzone"] button::after {content:"选择文件";font-size:.8rem;font-weight:600;}
        [data-testid="stFileUploaderDropzoneInstructions"] span {font-size:0 !important;}
        [data-testid="stFileUploaderDropzoneInstructions"] span::after {
            content:"拖拽文件到此处，或点击选择 · 单个文件最大 200MB";font-size:.75rem;color:var(--pa-text-muted);
        }
        [data-testid="stFileUploaderDropzone"] {border:1px dashed var(--pa-border-strong);background:var(--pa-bg);}
        /* Sidebar settings: the custom field row already shows the value. */
        section[data-testid="stSidebar"] [data-testid="stSliderThumbValue"] {display:none;}
        .pa-learning-section-missing {margin:.1rem 0 .6rem;color:var(--pa-text-faint);font-size:.82rem;}
        div[class*="st-key-learning_page_point_"] [data-testid="stBaseButton-tertiary"] {justify-content:flex-start !important;}
        div[class*="st-key-learning_page_point_"] [data-testid="stBaseButton-tertiary"] p {text-align:left !important;}
        .pa-page-point-section {color:var(--pa-text-muted) !important;font-size:.75rem !important;letter-spacing:.04em;}
        .pa-page-relation {border-left:2px solid var(--pa-primary) !important;border-radius:0 !important;background:transparent !important;padding:.2rem 0 .2rem .85rem !important;}
        .pa-page-relation strong {font-size:.75rem !important;color:var(--pa-text-muted) !important;font-weight:600 !important;}
        .pa-page-relation span {font-size:.88rem !important;line-height:1.75 !important;color:var(--pa-text-body) !important;}
        .pa-qa-empty {margin:1.2rem 0;padding:0 .2rem;}
        .pa-qa-empty strong {display:block;margin-bottom:.4rem;font-family:var(--pa-font-sans);font-size:1.05rem;color:var(--pa-text-heading);}
        .pa-qa-empty p {margin:0 0 .7rem;font-size:.88rem;line-height:1.75;color:var(--pa-text-body);}
        .pa-qa-empty small {display:block;padding-top:.6rem;border-top:1px solid var(--pa-border-light);
            font-size:.75rem;line-height:1.6;color:var(--pa-text-muted);}
        .pa-popover-section {margin:.55rem 0 .1rem;padding-top:.55rem;border-top:1px solid var(--pa-border-light);
            color:var(--pa-text-muted);font-size:.75rem;font-weight:600;letter-spacing:.08em;}
        [data-testid="stPopoverBody"] [data-testid="stElementContainer"]:first-child .pa-popover-section {border-top:0;padding-top:0;margin-top:0;}
        [data-testid="stPopoverBody"] hr {margin:.5rem 0 !important;}
        /* Project menu: discoverable at rest, emphasised on hover. */
        div[class*="st-key-sidebar_project_"] div[class*="st-key-sidebar-delete-"] [data-testid="stButton"] button {opacity:.6 !important;}
        div[class*="st-key-sidebar_project_"] div[class*="st-key-sidebar-delete-"] [data-testid="stButton"] button p {font-size:1rem !important;font-weight:700;}
        /* Tabs share one size across workspaces. */
        [data-testid="stTabs"] [data-baseweb="tab"] p {font-size:.82rem !important;}
        [data-testid="stTabs"] [data-baseweb="tab"] {padding:.45rem .1rem !important;}
        div[class*="st-key-learning_page_point_"] :is([data-testid="stTooltipHoverTarget"],[data-testid="stTooltipIcon"]),
        div[class*="st-key-learning_point_"] :is([data-testid="stTooltipHoverTarget"],[data-testid="stTooltipIcon"]) {
            justify-content:flex-start !important;
        }
        div[class*="st-key-learning_page_point_"] [data-testid="stBaseButton-tertiary"] {width:auto !important;}
        /* Issue cards: undo Streamlit's -1rem markdown margin so rows do not overlap. */
        div[class*="st-key-peer-major-card-"] [data-testid="stMarkdownContainer"],
        div[class*="st-key-peer-minor-card-"] [data-testid="stMarkdownContainer"] {margin-bottom:0 !important;}
        div[class*="st-key-peer-major-card-"] [data-testid="stMarkdownContainer"] > p,
        div[class*="st-key-peer-minor-card-"] [data-testid="stMarkdownContainer"] > p {margin:0 0 .2rem !important;}
        div[class*="-evidence-actions"] button p {color:var(--pa-primary) !important;font-weight:500 !important;}

        /* ── Visual refresh (design spec v1) ─────────────────── */
        /* System UI fonts everywhere; serif is reserved for quoted paper text. */
        .stApp, .stApp button, .stApp input, .stApp textarea, .stApp select,
        section[data-testid="stSidebar"] {font-family:var(--pa-font-sans);}
        [data-testid="stMain"] {background:var(--pa-bg-page);}
        /* Panels: white surface + soft shadow instead of beige-on-beige borders. */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"]) {
            background:var(--pa-bg);
        }
        /* Buttons: one height, one radius. */
        .stApp [data-testid^="stBaseButton-"] {min-height:2.25rem;border-radius:var(--pa-radius-sm);}
        .stApp [data-testid="stBaseButton-secondary"] {background:var(--pa-bg);border-color:var(--pa-border-strong);}
        .stApp [data-testid="stBaseButton-secondary"]:hover {border-color:var(--pa-primary);color:var(--pa-primary);}

        /* Sidebar */
        .pa-sidebar-brand {display:flex;align-items:center;gap:10px;margin:0 0 1rem;padding:0 .25rem;}
        .pa-sidebar-brand div {display:flex;flex-direction:column;line-height:1.3;}
        .pa-sidebar-brand strong {font-size:1rem;font-weight:600;color:var(--pa-text-heading);}
        .pa-sidebar-brand span {font-size:.75rem;color:var(--pa-text-muted);}
        .pa-sidebar-section-heading {font-size:.75rem !important;}
        div[class*="st-key-sidebar_project_"] button p {font-size:.875rem !important;font-weight:500;}
        div[class*="st-key-sidebar_project_"]:has(.pa-sidebar-project-marker.is-active) button p {font-weight:600;}
        .pa-sidebar-filename {font-size:.75rem !important;color:var(--pa-text-muted) !important;}
        .pa-sidebar-status {font-size:.75rem;}
        .pa-sidebar-status em {color:var(--pa-text-muted);}

        /* Home: title, step labels, mode cards, upload */
        .st-key-launch_shell_empty {padding-top:2rem;}
        .st-key-launch_shell_empty > div:first-child {gap:1rem;}
        .pa-launch-head {margin-bottom:.5rem;}
        .pa-launch-title {font-size:1.5rem;font-weight:600;line-height:1.3;color:var(--pa-text-heading);}
        .pa-launch-head p {margin:.5rem 0 0;font-size:1rem;line-height:1.6;color:var(--pa-text-secondary);}
        .pa-launch-section {margin-top:.75rem;font-size:.875rem;font-weight:600;color:var(--pa-text-secondary);}
        div[class*="st-key-launch_mode_card_"] {
            position:relative;height:100%;padding:20px;border:1px solid var(--pa-border);border-radius:10px;
            background:var(--pa-bg);box-shadow:0 1px 2px rgba(26,26,25,.05);
            transition:border-color var(--pa-transition-fast),box-shadow var(--pa-transition-fast);
        }
        div[class*="st-key-launch_mode_card_"]:hover {border-color:var(--pa-primary-border);}
        div[class*="st-key-launch_mode_card_"]:has(.pa-mode-card.is-selected) {
            border:2px solid var(--pa-primary);padding:19px;box-shadow:0 2px 8px rgba(30,74,122,.12);
        }
        div[class*="st-key-launch_mode_card_"]:has(button:focus-visible) {outline:2px solid var(--pa-primary);outline-offset:2px;}
        div[class*="st-key-launch_mode_card_"] [data-testid="stElementContainer"]:has([data-testid="stButton"]) {
            position:absolute !important;inset:0;width:auto !important;margin:0;z-index:1;
        }
        div[class*="st-key-launch_mode_card_"] [data-testid="stButton"],
        div[class*="st-key-launch_mode_card_"] [data-testid="stButton"] button {
            width:100%;height:100%;min-height:0;opacity:0;cursor:pointer;
        }
        [data-testid="stHorizontalBlock"]:has(div[class*="st-key-launch_mode_card_"]) {align-items:stretch;}
        [data-testid="stColumn"]:has(> div > div[class*="st-key-launch_mode_card_"]) > div {height:100%;}
        .pa-mode-card {display:flex;flex-direction:column;gap:10px;}
        .pa-mode-card-icon {
            width:40px;height:40px;border-radius:8px;background:var(--pa-bg-page);color:var(--pa-text-secondary);
            display:flex;align-items:center;justify-content:center;
        }
        .pa-mode-card.is-selected .pa-mode-card-icon {background:var(--pa-primary);color:#fff;}
        .pa-mode-card strong {font-size:1rem;font-weight:600;color:var(--pa-text-heading);}
        .pa-mode-card p {margin:0;font-size:.875rem;line-height:1.6;color:var(--pa-text-secondary);}
        .pa-mode-card small {font-size:.75rem;color:var(--pa-text-muted);}
        .st-key-launch_pdf_upload_empty {
            margin:0;padding:2.25rem 1.5rem 1.75rem;border:1.5px dashed var(--pa-border-strong);border-radius:10px;
            background:var(--pa-bg);box-shadow:none;
        }
        .st-key-launch_pdf_upload_empty:hover {border-color:var(--pa-primary);}
        .pa-upload-title {font-size:1rem !important;font-weight:600 !important;}
        .pa-upload-subtitle {font-size:.875rem !important;color:var(--pa-text-secondary) !important;}
        .st-key-launch_pdf_upload_empty [data-testid="stFileUploaderDropzone"] button::after {font-size:.875rem;font-weight:500;}
        .pa-launch-hint {display:flex;align-items:center;gap:8px;margin:0;color:var(--pa-text-muted);font-size:.75rem;}
        .st-key-peer_review_rubric_empty {background:var(--pa-bg);}
        .pa-ready-toolbar svg {color:var(--pa-text-secondary);flex-shrink:0;}

        /* Project header + tab bar (shared by lecture / Q&A / audit / review) */
        .st-key-project_nav {margin:-2.2rem 0 .5rem;min-height:52px;position:relative;z-index:999991;}
        .block-container:has(.pa-learning-layout) .st-key-project_nav {
            width:100%;margin:.35rem 0 0;flex:0 0 auto;
        }
        .pa-project-head {min-width:0;}
        .pa-project-title {
            font-size:.9375rem;font-weight:600;line-height:1.35;color:var(--pa-text-heading);
            overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
        }
        .pa-project-meta {margin-top:.25rem;font-size:.75rem;color:var(--pa-text-muted);}
        /* Pill switch: 阅读 / 审计 / 评审 */
        .st-key-project_nav_tab {display:flex;justify-content:center;}
        .st-key-project_nav_tab [data-testid="stButtonGroup"],
        .st-key-project_nav_tab [role="radiogroup"] {
            display:inline-flex !important;width:auto !important;gap:2px !important;padding:3px !important;
            border:0 !important;border-radius:10px !important;background:#e9e8e5 !important;
        }
        .st-key-project_nav_tab button[data-variant="segmented_control"] {
            flex:0 0 auto !important;min-height:30px !important;height:30px !important;padding:0 14px !important;
            border:0 !important;border-radius:8px !important;background:transparent !important;box-shadow:none !important;
            color:var(--pa-text-secondary) !important;
        }
        .st-key-project_nav_tab button[data-variant="segmented_control"] p {font-size:.8125rem !important;font-weight:500;color:inherit !important;white-space:nowrap;}
        .st-key-project_nav_tab button[aria-checked="true"] {
            background:var(--pa-bg) !important;color:var(--pa-text-heading) !important;
            box-shadow:0 1px 2px rgba(26,26,25,.1) !important;
        }
        .st-key-project_nav_tab button[aria-checked="true"] p {font-weight:600;}
        /* Empty states (lecture / audit / review) */
        .st-key-lecture_empty_panel,.st-key-audit_empty_panel,.st-key-review_empty_panel {
            padding:1.5rem;border-radius:10px;background:var(--pa-bg);box-shadow:var(--pa-shadow-sm);gap:.75rem;
        }
        .pa-empty-title {font-size:1.125rem;font-weight:600;color:var(--pa-text-heading);}
        .pa-empty-copy {margin:0;font-size:.875rem;line-height:1.7;color:var(--pa-text-secondary);}
        .st-key-audit_page_actions {margin-bottom:.25rem;}
        .st-key-project_nav_actions button {width:max-content !important;min-width:max-content !important;padding:0 .75rem !important;}
        .st-key-project_nav_actions button p {white-space:nowrap;overflow:visible !important;text-overflow:clip !important;max-width:none !important;}

        /* PDF toolbar: icon buttons, page + zoom on the right, extras in "more". */
        .st-key-learning_pdf_toolbar,.st-key-qa_pdf_toolbar {padding:.4rem .75rem;background:var(--pa-bg);}
        .st-key-learning_pdf_toolbar [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child,
        .st-key-qa_pdf_toolbar [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child {
            flex:1 1 auto !important;
        }
        .st-key-learning_pdf_toolbar [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:last-child,
        .st-key-qa_pdf_toolbar [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:last-child {
            flex-basis:2.5rem !important;width:2.5rem !important;
        }
        .st-key-learning_pdf_toolbar [data-testid="stBaseButton-tertiary"],
        .st-key-qa_pdf_toolbar [data-testid="stBaseButton-tertiary"],
        .st-key-peer_review_pdf_toolbar [data-testid="stBaseButton-tertiary"],
        .st-key-learning_pdf_toolbar [data-testid="stPopoverButton"],
        .st-key-qa_pdf_toolbar [data-testid="stPopoverButton"] {
            min-height:2rem !important;height:2rem;padding:0 !important;border:0 !important;border-radius:6px;
            background:transparent !important;color:var(--pa-text-secondary) !important;justify-content:center;
        }
        .st-key-learning_pdf_toolbar [data-testid="stBaseButton-tertiary"]:hover:not(:disabled),
        .st-key-peer_review_pdf_toolbar [data-testid="stBaseButton-tertiary"]:hover:not(:disabled),
        .st-key-qa_pdf_toolbar [data-testid="stBaseButton-tertiary"]:hover:not(:disabled),
        .st-key-learning_pdf_toolbar [data-testid="stPopoverButton"]:hover,
        .st-key-qa_pdf_toolbar [data-testid="stPopoverButton"]:hover {background:var(--pa-bg-page) !important;color:var(--pa-text-heading) !important;}
        .st-key-learning_pdf_toolbar [data-testid="stPopoverButton"] [data-testid="stIconMaterial"]:last-child,
        .st-key-qa_pdf_toolbar [data-testid="stPopoverButton"] [data-testid="stIconMaterial"]:last-child {display:none;}
        .pa-pdf-panel-title {font-size:.875rem !important;font-weight:600 !important;}
        .pa-pdf-zoom,.pa-pdf-page-total {font-size:.875rem !important;color:var(--pa-text-body) !important;}
        /* Chapter buttons wrap into pills instead of a clipped scrolling row. */
        .st-key-learning_section_bar {height:auto !important;padding:.6rem .75rem !important;}
        .st-key-learning_section_bar [role="radiogroup"] {
            height:auto !important;flex-wrap:wrap !important;gap:.375rem !important;overflow:visible !important;
        }
        .st-key-learning_section_bar [role="radio"],
        .st-key-learning_section_bar button {
            height:30px !important;min-height:30px !important;min-width:0 !important;padding:0 .75rem !important;
            border:1px solid var(--pa-border) !important;border-radius:999px !important;
            background:var(--pa-bg) !important;color:var(--pa-text-secondary) !important;box-shadow:none !important;
        }
        .st-key-learning_section_bar [role="radio"] p,
        .st-key-learning_section_bar button p {font-size:.8125rem !important;font-weight:500;}
        .st-key-learning_section_bar [role="radio"][aria-checked="true"],
        .st-key-learning_section_bar button[aria-checked="true"] {
            background:var(--pa-text-heading) !important;border-color:var(--pa-text-heading) !important;
            color:#fff !important;box-shadow:none !important;
        }
        .st-key-learning_section_bar button[aria-checked="true"] p {color:#fff !important;}

        /* Review: verdict card */
        .pa-peer-verdict {
            display:flex;flex-wrap:wrap;align-items:center;gap:1.25rem 2rem;margin:0 0 .75rem;padding:1.1rem 1.5rem;
            border-radius:10px;background:var(--pa-bg);box-shadow:var(--pa-shadow-sm);
        }
        .pa-peer-verdict span {display:block;font-size:.75rem;font-weight:600;color:var(--pa-text-muted);}
        .pa-peer-verdict-main div {display:flex;align-items:baseline;gap:.6rem;margin-top:.2rem;}
        .pa-peer-verdict-main strong {font-size:1.5rem;font-weight:600;line-height:1.2;color:var(--pa-text-heading);}
        .pa-peer-verdict-main em {font-style:normal;font-size:.875rem;color:var(--pa-text-secondary);}
        .pa-peer-decision-weak-reject .pa-peer-verdict-main strong,
        .pa-peer-decision-strong-reject .pa-peer-verdict-main strong {color:var(--pa-danger);}
        .pa-peer-decision-borderline .pa-peer-verdict-main strong {color:var(--pa-warning-dark);}
        .pa-peer-decision-weak-accept .pa-peer-verdict-main strong,
        .pa-peer-decision-strong-accept .pa-peer-verdict-main strong {color:var(--pa-success-muted);}
        .pa-peer-verdict-stat b {display:block;margin-top:.2rem;font-size:1.5rem;font-weight:600;line-height:1.2;color:var(--pa-text-heading);}
        .pa-peer-verdict-stat b small {font-size:.875rem;font-weight:400;color:var(--pa-text-muted);}
        .pa-peer-verdict-stat b.is-text {font-size:1rem;font-weight:500;line-height:1.8;}
        .pa-peer-verdict-risk {flex:1 1 320px;min-width:0;padding-left:1.5rem;border-left:1px solid var(--pa-border-light);}
        .pa-peer-verdict-risk p {margin:.25rem 0 0;font-size:.875rem;line-height:1.65;color:var(--pa-text-body);}
        .pa-peer-verdict-note {flex:1 1 100%;font-size:.75rem;color:var(--pa-text-muted);}
        .pa-peer-verdict-note span {display:inline;font-weight:500;cursor:help;}
        .pa-peer-sev {
            display:inline-flex !important;align-items:center;height:20px;margin-right:.5rem;padding:0 .4rem;border-radius:4px;
            background:var(--pa-danger-surface);color:var(--pa-danger) !important;font-size:.75rem;font-weight:600;vertical-align:1px;
        }
        .pa-peer-risk-medium .pa-peer-sev {background:var(--pa-warning-surface);color:var(--pa-warning-dark) !important;}

        /* ══ V3 shell: neutral grey ground, white rounded cards ══ */
        .stApp,[data-testid="stMain"] {background:var(--pa-bg-page) !important;}
        section[data-testid="stSidebar"] {background:var(--pa-bg-page) !important;border-right:0 !important;}
        .pa-sidebar-brand strong {font-size:.95rem;}
        .pa-sidebar-brand span {display:none;}
        .st-key-sidebar-new-project button {
            justify-content:flex-start !important;padding:0 .75rem !important;border:0 !important;
            background:#e9e8e5 !important;color:var(--pa-text-heading) !important;box-shadow:none !important;
        }
        .st-key-sidebar-new-project button:hover {background:#e1e0dc !important;}
        .st-key-sidebar_project_search input {background:var(--pa-bg) !important;}
        div[class*="st-key-sidebar_project_"]:not(.st-key-sidebar_project_list):not(.st-key-sidebar_project_search) {
            margin:0 0 2px !important;padding:.5rem .6rem !important;border-radius:8px !important;
            background:transparent !important;box-shadow:none !important;border:0 !important;
        }
        div[class*="st-key-sidebar_project_"]:not(.st-key-sidebar_project_list):not(.st-key-sidebar_project_search):hover {background:#ecebe8 !important;}
        div[class*="st-key-sidebar_project_"]:has(.pa-sidebar-project-marker.is-active):not(.st-key-sidebar_project_list) {
            background:#e9e8e5 !important;box-shadow:none !important;
        }
        div[class*="st-key-sidebar_project_"] button p {
            font-size:.875rem !important;font-weight:500 !important;line-height:1.4 !important;
            display:-webkit-box !important;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;white-space:normal !important;
        }
        .pa-sidebar-project-meta {margin-top:.15rem !important;}
        .pa-project-chips {font-size:.75rem;font-weight:400;color:var(--pa-text-muted);}
        .pa-sidebar-section-heading {padding-top:.5rem;color:var(--pa-text-muted) !important;font-weight:500 !important;}
        /* Cards */
        .st-key-learning_source_panel,.st-key-qa_source_panel,
        .st-key-learning_assistant_card,.st-key-qa_assistant_card,
        .st-key-audit_list_card,.st-key-audit_detail_card,.st-key-audit_source_card,
        .st-key-review_main_card,.st-key-review_props_card {
            background:var(--pa-bg) !important;border-radius:14px !important;border:0 !important;
            box-shadow:0 0 0 1px var(--pa-border) !important;overflow:hidden;
        }

        /* Reader: assistant card header (讲解 / 追问) and chapter stepper */
        .st-key-assistant_switch {padding:.35rem 1rem 0;border-bottom:1px solid var(--pa-border-light);}
        .st-key-assistant_switch [data-testid="stButtonGroup"],
        .st-key-assistant_switch [role="radiogroup"] {gap:1.25rem !important;background:transparent !important;border:0 !important;padding:0 !important;}
        .st-key-assistant_switch button[data-variant="segmented_control"] {
            flex:0 0 auto !important;min-height:0 !important;height:auto !important;padding:.5rem 0 .55rem !important;
            margin-bottom:-1px;border:0 !important;border-bottom:2px solid transparent !important;border-radius:0 !important;
            background:transparent !important;box-shadow:none !important;color:var(--pa-text-muted) !important;
        }
        .st-key-assistant_switch button[data-variant="segmented_control"] p {font-size:.875rem !important;font-weight:500;color:inherit !important;}
        .st-key-assistant_switch button[aria-checked="true"] {border-bottom-color:var(--pa-text-heading) !important;color:var(--pa-text-heading) !important;}
        .st-key-assistant_switch button[aria-checked="true"] p {font-weight:600;}
        .st-key-learning_section_bar {
            height:auto !important;padding:.6rem 1rem .25rem !important;margin:0 !important;
            border:0 !important;border-radius:0 !important;background:transparent !important;
        }
        .st-key-learning_section_bar [data-testid="stHorizontalBlock"] {gap:.375rem !important;flex-wrap:nowrap !important;}
        .st-key-learning_section_bar [data-testid="stColumn"] {min-width:0 !important;}
        .st-key-learning_section_bar button[data-testid="stBaseButton-tertiary"] {
            width:32px !important;min-width:32px !important;height:32px !important;min-height:32px !important;padding:0 !important;
            border:1px solid var(--pa-border) !important;border-radius:8px !important;background:var(--pa-bg) !important;
            color:var(--pa-text-secondary) !important;
        }
        .st-key-learning_section_bar [data-baseweb="select"] > div {
            min-height:32px !important;border-radius:8px !important;background:var(--pa-bg) !important;
            border:1px solid var(--pa-border) !important;font-size:.8125rem;font-weight:500;
        }
        /* Reader cards fill the column; inner panels drop their own chrome. */
        [data-testid="stLayoutWrapper"]:has(> .st-key-learning_assistant_card),
        [data-testid="stLayoutWrapper"]:has(> .st-key-qa_assistant_card) {
            flex:1 1 0 !important;min-height:0 !important;display:flex !important;flex-direction:column !important;
        }
        .st-key-learning_assistant_card,.st-key-qa_assistant_card {
            flex:1 1 0 !important;min-height:0 !important;height:100%;display:flex !important;flex-direction:column !important;gap:0 !important;
        }
        [data-testid="stLayoutWrapper"]:has(> .st-key-qa_conversation_panel) {flex:1 1 0 !important;min-height:0 !important;}
        /* Keep the 全局 / 当前页 scope switch, drop the redundant "论文讲解" title. */
        .st-key-learning_assistant_card .st-key-learning_explanation_header {padding:0 1rem !important;border:0 !important;background:transparent !important;}
        .st-key-learning_assistant_card .pa-explanation-panel-title {visibility:hidden;}
        .st-key-learning_source_panel .st-key-learning_pdf_toolbar,
        .st-key-qa_source_panel .st-key-qa_pdf_toolbar {border-bottom:1px solid var(--pa-border-light) !important;border-radius:0 !important;}

        /* Home V3: white canvas, one centred upload card with mode pills inside */
        body:has(.st-key-launch_shell_empty) [data-testid="stMain"] {
            background:var(--pa-bg) !important;margin:8px 8px 8px 0;border-radius:14px;
            box-shadow:0 0 0 1px var(--pa-border);
        }
        .st-key-launch_shell_empty {max-width:680px !important;padding-top:max(4rem,14vh) !important;}
        .st-key-launch_shell_empty > div:first-child {gap:1.25rem !important;}
        .pa-launch-title {text-align:center;font-size:1.875rem !important;letter-spacing:-.01em;}
        .st-key-launch_upload_card {
            gap:0 !important;border:1px solid var(--pa-border);border-radius:16px;background:var(--pa-bg);
            box-shadow:0 4px 16px rgba(26,26,25,.06);overflow:hidden;
        }
        .st-key-launch_upload_card .st-key-launch_pdf_upload_empty {
            border:0 !important;border-bottom:1px dashed var(--pa-border) !important;border-radius:0 !important;
            padding:2rem 1.5rem 1.25rem !important;box-shadow:none !important;
        }
        .st-key-launch_upload_card .st-key-launch_pdf_upload_empty [data-testid="stFileUploaderDropzone"] button {
            background:var(--pa-primary) !important;border-color:var(--pa-primary) !important;border-radius:10px !important;
        }
        .st-key-launch_mode_row {padding:.75rem;gap:.75rem !important;}
        .st-key-launch_mode_row [data-testid="stButtonGroup"],
        .st-key-launch_mode_row [role="radiogroup"] {gap:6px !important;background:transparent !important;border:0 !important;padding:0 !important;}
        .st-key-launch_mode_row button[data-variant="segmented_control"] {
            flex:0 0 auto !important;min-height:32px !important;height:32px !important;padding:0 12px !important;
            border:1px solid var(--pa-border) !important;border-radius:999px !important;background:var(--pa-bg) !important;
            box-shadow:none !important;color:var(--pa-text-body) !important;
        }
        .st-key-launch_mode_row button[data-variant="segmented_control"] p {font-size:.8125rem !important;font-weight:500;color:inherit !important;}
        .st-key-launch_mode_row button[aria-checked="true"] {
            background:var(--pa-text-heading) !important;border-color:var(--pa-text-heading) !important;color:#fff !important;
        }
        .pa-launch-desc {text-align:center;font-size:.8125rem;line-height:1.7;color:var(--pa-text-muted);}
        .st-key-launch_shell_empty .pa-launch-hint {justify-content:center;}

        /* Audit V3: list / detail / source cards (Linear-style issue view) */
        .st-key-audit_list_card {padding:.75rem .5rem;gap:2px !important;}
        .pa-audit-list-title {display:flex;align-items:baseline;gap:.5rem;padding:0 .5rem .5rem;}
        .pa-audit-list-title strong {font-size:.875rem;font-weight:600;}
        .pa-audit-list-title span {font-size:.75rem;color:var(--pa-text-muted);}
        div[class*="st-key-audit_claim_item_"] {
            gap:0 !important;padding:.5rem .5rem .55rem !important;border:0 !important;border-radius:8px !important;
            background:transparent !important;box-shadow:none !important;
        }
        div[class*="st-key-audit_claim_item_"]:hover {background:#f6f6f4 !important;}
        div[class*="st-key-audit_claim_item_active_"] {background:var(--pa-surface-alt) !important;}
        div[class*="st-key-audit_claim_item_"] [data-testid="stBaseButton-tertiary"] {
            justify-content:flex-start !important;min-height:0 !important;padding:0 !important;text-align:left;
        }
        div[class*="st-key-audit_claim_item_"] [data-testid="stBaseButton-tertiary"] p {
            font-size:.8125rem !important;line-height:1.55 !important;font-weight:400 !important;color:var(--pa-text-heading) !important;
            white-space:normal !important;text-align:left;
        }
        div[class*="st-key-audit_claim_item_active_"] [data-testid="stBaseButton-tertiary"] p {font-weight:500 !important;}
        .pa-audit-row-meta {display:flex;align-items:center;gap:6px;margin-top:.2rem;font-size:.75rem;color:var(--pa-text-muted);}
        .pa-label-dot {width:7px;height:7px;border-radius:50%;flex-shrink:0;background:#a8a29e;}
        .pa-label-dot.label-supported {background:#3f8a5a;}
        .pa-label-dot.label-partially_supported {background:#b7791f;}
        .pa-label-dot.label-contradicted {background:#c2410c;}
        .pa-label-dot.label-no_support_found {background:#b5473a;}
        .pa-label-dot.label-abstain {background:#a8a29e;}
        .st-key-audit_detail_card {gap:0 !important;}
        .st-key-audit_detail_card .st-key-audit_detail_navigation {
            padding:.35rem .5rem .35rem 1.25rem !important;border-bottom:1px solid var(--pa-border-light);margin:0 !important;
        }
        .pa-audit-position {font-size:.8125rem;color:var(--pa-text-muted);}
        .st-key-audit_detail_card .st-key-audit_selected_detail {padding:1.25rem 1.5rem !important;border:0 !important;box-shadow:none !important;}
        .st-key-audit_source_card {padding:0 0 .5rem;gap:0 !important;}
        .pa-audit-source-head {padding:.7rem 1rem;border-bottom:1px solid var(--pa-border-light);font-size:.8125rem;color:var(--pa-text-secondary);text-align:center;}
        .pa-audit-source-empty {padding:2rem 1.25rem;font-size:.875rem;color:var(--pa-text-muted);text-align:center;}

        [data-testid="stHorizontalBlock"]:has(.st-key-audit_source_card) {
            display:grid !important;grid-template-columns:minmax(240px,300px) minmax(0,1fr) minmax(300px,380px) !important;
            gap:8px !important;align-items:start !important;
        }
        [data-testid="stHorizontalBlock"]:has(.st-key-audit_source_card) > [data-testid="stColumn"] {min-width:0 !important;width:auto !important;}
        [data-testid="stHorizontalBlock"]:has(.st-key-audit_selected_detail):not(:has(.st-key-audit_source_card)) {
            grid-template-columns:minmax(240px,320px) minmax(0,1fr) !important;gap:8px !important;align-items:start !important;
        }
        /* List and source stay in view while the long claim detail scrolls. */
        [data-testid="stHorizontalBlock"]:has(.st-key-audit_selected_detail) > [data-testid="stColumn"]:has(.st-key-audit_list_card),
        [data-testid="stHorizontalBlock"]:has(.st-key-audit_selected_detail) > [data-testid="stColumn"]:has(.st-key-audit_source_card) {
            position:sticky !important;top:4.5rem;align-self:start;
        }
        .st-key-audit_list_card {max-height:calc(100vh - 6rem);overflow-y:auto !important;}
        .st-key-audit_source_card {max-height:calc(100vh - 6rem);overflow-y:auto !important;}
        /* Detail never wider than its card: padding inside the width, one-column assessment. */
        .st-key-audit_detail_card,.st-key-audit_detail_card .st-key-audit_selected_detail {
            box-sizing:border-box !important;width:100% !important;max-width:100% !important;min-width:0 !important;
        }
        .st-key-audit_detail_card .pa-audit-detail,.st-key-audit_detail_card .pa-audit-detail * {min-width:0;max-width:100%;}
        .st-key-audit_detail_card .pa-audit-assessment-grid {grid-template-columns:minmax(0,1fr) !important;gap:.25rem !important;}
        .st-key-audit_detail_card .pa-audit-claim,.st-key-audit_detail_card .pa-audit-detail-copy,
        .st-key-audit_detail_card .pa-audit-evidence-text {overflow-wrap:anywhere;word-break:break-word;}
        .st-key-audit_detail_card .pa-audit-detail-head {flex-wrap:wrap !important;}
        /* Filter row: search + status + "more" popover */
        .st-key-audit_advanced_filters [data-testid="stHorizontalBlock"] {
            display:flex !important;grid-template-columns:none !important;flex-wrap:nowrap !important;gap:.5rem !important;
        }
        .st-key-audit_advanced_filters {padding:0 !important;background:transparent !important;border:0 !important;box-shadow:none !important;}

        /* Empty-state PDF preview: same card + icon toolbar as the reader */
        .st-key-upload_pdf_preview {
            background:var(--pa-bg) !important;border-radius:14px !important;border:0 !important;
            box-shadow:0 0 0 1px var(--pa-border) !important;overflow:hidden;padding:.4rem .75rem .75rem !important;
        }
        .st-key-upload_pdf_preview [data-testid="stBaseButton-tertiary"] {
            min-height:2rem !important;height:2rem;padding:0 !important;border:0 !important;border-radius:6px;
            background:transparent !important;color:var(--pa-text-secondary) !important;
        }
        .st-key-upload_pdf_preview [data-testid="stBaseButton-tertiary"]:hover:not(:disabled) {background:var(--pa-bg-page) !important;}
        /* Review: properties stay in view */
        [data-testid="stHorizontalBlock"]:has(.st-key-review_props_card) > [data-testid="stColumn"]:has(.st-key-review_props_card) {
            position:sticky !important;top:4.5rem;align-self:start;
        }
        /* Top-bar actions: never clipped, keep clear of Streamlit's toolbar */
        .st-key-project_nav {padding-right:2.75rem !important;}
        .st-key-project_nav_actions {flex-wrap:nowrap !important;}
        .st-key-project_nav_actions > div,.st-key-project_nav_actions [data-testid="stPopover"],
        .st-key-project_nav_actions [data-testid="stButton"] {flex:0 0 auto !important;width:auto !important;}

        .st-key-project_nav_actions [data-testid="stMarkdownContainer"] {overflow:visible !important;text-overflow:clip !important;max-width:none !important;}
        .st-key-project_nav_actions [data-testid="stMarkdownContainer"] p {white-space:nowrap !important;}

        .st-key-audit_detail_card .pa-audit-detail,.st-key-audit_detail_card .pa-audit-detail * {box-sizing:border-box !important;}
        .st-key-audit_detail_card .pa-audit-evidence-list {width:100% !important;grid-template-columns:minmax(0,1fr) !important;}
        .st-key-audit_detail_card .pa-audit-evidence-item {width:auto !important;max-width:100% !important;margin-right:0 !important;}
        .st-key-audit_detail_card .pa-audit-evidence-meta,.st-key-audit_detail_card .pa-audit-evidence-text {width:auto !important;}
        .st-key-project_nav_actions [data-testid="stPopoverButton"] {min-width:6.5rem !important;}
        .st-key-project_nav_actions [data-testid="stPopoverButton"] [data-testid="stMarkdownContainer"] {flex:0 0 auto !important;}

        /* Review V3: main card + properties card */
        .st-key-review_main_card {padding:1.75rem 2.25rem 1.5rem !important;gap:1rem !important;}
        .pa-review-head {display:flex;flex-direction:column;gap:.6rem;max-width:820px;}
        .pa-review-head > span {font-size:.75rem;font-weight:500;color:var(--pa-text-muted);}
        .pa-review-head > div {display:flex;align-items:baseline;gap:.75rem;flex-wrap:wrap;}
        .pa-review-head strong {font-size:1.75rem;font-weight:600;letter-spacing:-.01em;line-height:1.2;}
        .pa-review-head em {font-style:normal;font-size:.9375rem;color:var(--pa-text-secondary);}
        .pa-review-head p {margin:0;font-size:.9375rem;line-height:1.8;color:var(--pa-text-body);}
        .pa-peer-decision-text {color:var(--pa-text-heading);}
        .pa-peer-decision-text.pa-peer-decision-weak-reject,.pa-peer-decision-text.pa-peer-decision-strong-reject {color:#c2410c;}
        .pa-peer-decision-text.pa-peer-decision-borderline {color:#b7791f;}
        .pa-peer-decision-text.pa-peer-decision-weak-accept,.pa-peer-decision-text.pa-peer-decision-strong-accept {color:#2f6b45;}
        .st-key-review_main_card [data-testid="stTabs"] {max-width:860px;}
        .st-key-review_props_card {padding:1.25rem !important;}
        .pa-review-props {display:flex;flex-direction:column;gap:1rem;}
        .pa-review-props > div {display:flex;justify-content:space-between;align-items:baseline;gap:.75rem;}
        .pa-review-props span {font-size:.8125rem;color:var(--pa-text-muted);}
        .pa-review-props strong,.pa-review-props b {font-size:.875rem;font-weight:500;text-align:right;}
        .pa-review-props hr {margin:0;border:0;border-top:1px solid var(--pa-border-light);}
        .pa-review-props .pa-review-progress {display:flex;flex-direction:column;align-items:stretch;gap:.5rem;}
        .pa-review-progress i {display:block;height:6px;border-radius:3px;background:var(--pa-surface-alt);overflow:hidden;}
        .pa-review-progress i b {display:block;height:100%;background:var(--pa-text-heading);}
        .pa-review-progress small {font-size:.75rem;color:var(--pa-text-muted);}
        .pa-review-props p {margin:0;font-size:.75rem;line-height:1.7;color:var(--pa-text-muted);}
        .pa-review-props p span {cursor:help;font-size:.75rem;}
        [data-testid="stHorizontalBlock"]:has(.st-key-review_props_card) {align-items:flex-start !important;gap:8px !important;}
        /* Review V3: the tab body flows inside the main card (no fixed-height side rail). */
        .st-key-review_main_card .st-key-peer_review_side_panel {
            flex:none !important;height:auto !important;max-height:none !important;overflow:visible !important;
            padding:0 !important;border:0 !important;background:transparent !important;box-shadow:none !important;
        }

        /* ══ Clickable rows: one HTML body, a transparent full-size button on top ══ */
        div[class*="st-key-audit_claim_item_"],
        div[class*="st-key-sidebar_project_"]:not(.st-key-sidebar_project_list):not(.st-key-sidebar_project_search) {
            position:relative !important;gap:0 !important;cursor:pointer;
        }
        div[class*="st-key-audit_claim_item_"] [data-testid="stElementContainer"]:has(.pa-row-body),
        div[class*="st-key-sidebar_project_"] [data-testid="stElementContainer"]:has(.pa-row-body) {
            margin:0 !important;height:auto !important;
        }
        div[class*="st-key-audit_claim_item_"] [data-testid="stMarkdownContainer"]:has(.pa-row-body),
        div[class*="st-key-sidebar_project_"] [data-testid="stMarkdownContainer"]:has(.pa-row-body) {margin:0 !important;}
        .pa-row-body {display:flex;flex-direction:column;gap:4px;min-width:0;}
        .pa-row-title {
            font-size:.8125rem;line-height:1.55;color:var(--pa-text-heading);
            display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;
        }
        div[class*="st-key-audit_claim_item_active_"] .pa-row-title {font-weight:600;}
        div[class*="st-key-sidebar_project_"] .pa-row-title {font-size:.875rem;font-weight:500;padding-right:1.5rem;}
        div[class*="st-key-sidebar_project_"]:has(.pa-sidebar-project-marker.is-active) .pa-row-title {font-weight:600;}
        .pa-row-body .pa-audit-row-meta {margin-top:0 !important;}
        [class*="st-key-select_audit_claim_"],[class*="st-key-sidebar-open-"] {
            position:absolute !important;inset:0 !important;width:auto !important;height:auto !important;margin:0 !important;z-index:1;
        }
        [class*="st-key-select_audit_claim_"] [data-testid="stButton"],
        [class*="st-key-select_audit_claim_"] button,
        [class*="st-key-sidebar-open-"] [data-testid="stButton"],
        [class*="st-key-sidebar-open-"] button {
            width:100% !important;height:100% !important;min-height:0 !important;opacity:0 !important;cursor:pointer;
        }
        div[class*="st-key-audit_claim_item_"]:has(button:focus-visible),
        div[class*="st-key-sidebar_project_"]:has([class*="st-key-sidebar-open-"] button:focus-visible) {
            outline:2px solid var(--pa-primary);outline-offset:1px;
        }
        [class*="st-key-sidebar-delete-"] {
            position:absolute !important;top:.4rem;right:.3rem;width:auto !important;margin:0 !important;z-index:2;
            opacity:0;transition:opacity var(--pa-transition-fast);
        }
        div[class*="st-key-sidebar_project_"]:hover [class*="st-key-sidebar-delete-"],
        [class*="st-key-sidebar-delete-"]:focus-within {opacity:1;}
        [class*="st-key-sidebar-delete-"] button {
            width:28px !important;height:28px !important;min-height:28px !important;padding:0 !important;border-radius:6px !important;
            color:var(--pa-text-muted) !important;background:transparent !important;
        }
        [class*="st-key-sidebar-delete-"] button:hover {color:var(--pa-danger) !important;background:#e9e8e5 !important;}
        </style>
        """,
        unsafe_allow_html=True,
    )
