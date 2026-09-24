from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import streamlit as st

from paperaudit.code_parser import CodeParseError, parse_code_zip
from paperaudit.models import AuditJobStatus, ClaimCategory, ParsedCodebase
from paperaudit.report_input import parse_report_file
from paperaudit.storage import ProjectStore, StorageError
from paperaudit.ui.components import render_header_banner
from .constants import CATEGORY_LABELS, FULL_SCOPE
from .rubric_controls import render_peer_review_rubric_controls
from .upload_preview import render_uploaded_pdf_preview


@st.cache_data(show_spinner=False, max_entries=4)
def parse_uploaded_code(zip_bytes: bytes, filename: str) -> ParsedCodebase:
    return parse_code_zip(zip_bytes, filename)


@dataclass
class UploadSubmission:
    pdf_bytes: bytes
    filename: str
    mode: str
    report_text: str
    report_source_label: str
    report_source_filename: str | None
    scope: list[ClaimCategory]
    code_bytes: bytes | None
    code_filename: str | None
    codebase: ParsedCodebase | None
    status: object
    progress_bar: object


def render_upload_page(
    project_store: ProjectStore, api_ready: bool, on_open_audit: Callable[[str], None],
) -> UploadSubmission | None:
    report_text = ""
    report_source_label = "粘贴报告"
    report_source_filename = None
    source_code_file = None
    uploaded_codebase = None
    scope = FULL_SCOPE
    run_clicked = False
    status = None
    progress_bar = None

    upload_has_value = st.session_state.get("paper_pdf_upload") is not None
    launch_shell_key = "launch_shell_ready" if upload_has_value else "launch_shell_empty"
    with st.container(key=launch_shell_key):
        if st.session_state.get("launch_mode") not in ("生成论文讲解", "审计已有报告", "模拟投稿评审"):
            st.session_state["launch_mode"] = "生成论文讲解"
        launch_title_col, launch_mode_col = st.columns([1.55, 1], vertical_alignment="center")
        with launch_title_col:
            render_header_banner()
        with launch_mode_col:
            mode_label = st.segmented_control(
                "选择工作模式",
                ["生成论文讲解", "审计已有报告", "模拟投稿评审"],
                key="launch_mode",
                required=True,
                label_visibility="collapsed",
                width="stretch",
            )
        mode = (
            "learn" if mode_label == "生成论文讲解"
            else "peer_review" if mode_label == "模拟投稿评审"
            else "audit_existing"
        )

        if not upload_has_value:
            with st.container(key="launch_pdf_upload_empty"):
                st.markdown(
                    '<div class="pa-upload-title">拖拽论文 PDF 到这里</div>'
                    '<div class="pa-upload-subtitle">或点击下方选择文件 · PDF · 最大 200MB</div>',
                    unsafe_allow_html=True,
                )
                pdf_file = st.file_uploader(
                    "上传英文论文 PDF",
                    type=["pdf"],
                    accept_multiple_files=False,
                    help="支持带文本层的公开英文论文 PDF",
                    key="paper_pdf_upload",
                    label_visibility="collapsed",
                )
        else:
            current_pdf = st.session_state.get("paper_pdf_upload")
            file_bar, replace_bar = st.columns([7, 1], vertical_alignment="center")
            with file_bar:
                st.markdown(
                    f'<div class="pa-ready-toolbar"><span>📄</span><strong>{current_pdf.name}</strong>'
                    f'<small>{len(current_pdf.getvalue()) / 1024 / 1024:.1f} MB</small></div>',
                    unsafe_allow_html=True,
                )
            with replace_bar.popover("更换文件", width="stretch"):
                pdf_file = st.file_uploader(
                    "选择另一篇论文 PDF",
                    type=["pdf"],
                    accept_multiple_files=False,
                    help="支持带文本层的公开英文论文 PDF",
                    key="paper_pdf_upload",
                )

        if pdf_file is None:
            if mode == "peer_review":
                with st.container(border=True, key="peer_review_rubric_empty"):
                    st.markdown('<div class="pa-setup-title">评审标准</div>', unsafe_allow_html=True)
                    render_peer_review_rubric_controls()
                    st.caption("上传论文后将按所选标准生成五档投稿预审建议。")
            with st.expander("高级选项", expanded=False):
                if mode == "learn":
                    st.markdown(
                        "标准讲解包含研究问题、核心贡献、方法、实验、结果、局限与关键术语。"
                    )
                    st.caption("隐私提示：生成讲解会将论文文本发送至当前配置的 Hy3 模型服务；请确认该服务符合你的数据授权要求。")
                    st.caption("上传论文后可继续关联开源代码 ZIP。")
                elif mode == "audit_existing":
                    st.markdown(
                        "上传论文后，可粘贴中文报告或上传 `.txt` / `.md` / `.pptx` 文件。"
                    )
                    st.caption("隐私提示：报告审计会将论文文本和你提供的报告发送至当前配置的 Hy3 模型服务。")
                    st.caption("审计会逐条检索论文原文并给出证据定位。")
            st.markdown(
                '<div class="pa-launch-hint">上传 PDF 后进入论文准备页</div>',
                unsafe_allow_html=True,
            )
        else:
            preview_col, setup_col = st.columns([1.86, 1], gap="large")
            with preview_col:
                try:
                    render_uploaded_pdf_preview(pdf_file.getvalue(), pdf_file.name)
                except (ValueError, RuntimeError) as exc:
                    st.error(f"PDF 预览失败：{exc}")

            with setup_col:
                with st.container(border=True, key="launch_setup_panel"):
                    st.markdown('<div class="pa-setup-heading">生成设置</div>', unsafe_allow_html=True)
                    st.markdown(
                        f'<div class="pa-ready-file"><span>✓ PDF 已就绪</span>'
                        f'<strong>{pdf_file.name}</strong>'
                        f'<small>{len(pdf_file.getvalue()) / 1024 / 1024:.1f} MB</small></div>',
                        unsafe_allow_html=True,
                    )
                    if mode == "audit_existing":
                        st.markdown('<div class="pa-setup-title">已有报告</div>', unsafe_allow_html=True)
                        if st.session_state.get("report_source_mode") not in ("粘贴文本", "上传文件"):
                            st.session_state["report_source_mode"] = "粘贴文本"
                        report_source = st.segmented_control(
                            "报告输入方式",
                            ["粘贴文本", "上传文件"],
                            key="report_source_mode",
                            required=True,
                            label_visibility="collapsed",
                            width="stretch",
                        )
                        if report_source == "粘贴文本":
                            report_text = st.text_area(
                                "中文解读内容",
                                height=160,
                            key="upload_report_text",
                                placeholder="粘贴针对该论文的中文总结、解读或阅读笔记…",
                                label_visibility="collapsed",
                            )
                        else:
                            report_file = st.file_uploader(
                                "选择报告文件",
                                type=["txt", "md", "pptx"],
                                accept_multiple_files=False,
                                key="report_file_upload",
                                help="PowerPoint 将按幻灯片提取文字、表格、图表数据和备注。",
                            )
                            if report_file is not None:
                                report_source_label = report_file.name
                                report_source_filename = report_file.name
                                try:
                                    parsed_report = parse_report_file(
                                        report_file.getvalue(), report_file.name
                                    )
                                    report_text = parsed_report.text
                                except ValueError as exc:
                                    st.error(str(exc))
                                else:
                                    if parsed_report.kind == "pptx":
                                        st.caption(
                                            f"已读取 {parsed_report.page_count} 页幻灯片 · "
                                            f"{len(report_text)} 个字符"
                                        )
                                        for warning in parsed_report.warnings:
                                            st.warning(warning)
                                    else:
                                        st.caption(f"已读取 {len(report_text)} 个字符")

                        if st.session_state.get("audit_scope_mode") not in ("完整解读", "自定义重点"):
                            st.session_state["audit_scope_mode"] = "完整解读"
                        scope_mode = st.segmented_control(
                            "审计范围",
                            ["完整解读", "自定义重点"],
                            key="audit_scope_mode",
                            required=True,
                            width="stretch",
                        )
                        if scope_mode == "自定义重点":
                            selected_labels = st.multiselect(
                                "选择检查范围",
                                list(CATEGORY_LABELS.values()),
                                default=["核心贡献", "方法", "主要结果"],
                            key="upload_report_scope",
                            )
                            scope = [
                                category
                                for category, label in CATEGORY_LABELS.items()
                                if label in selected_labels
                            ]
                    elif mode == "peer_review":
                        st.markdown(
                            '<div class="pa-setup-title">评审模式</div>'
                            '<div class="pa-setup-mode"><strong>通用 AI 会议模拟评审</strong>'
                            '<span>贡献 · 方法 · 实验 · 清晰度 · 可复现性 · 投稿建议</span></div>',
                            unsafe_allow_html=True,
                        )
                        st.markdown('<div class="pa-setup-title">评审标准</div>', unsafe_allow_html=True)
                        render_peer_review_rubric_controls()
                        st.caption("结果为 Strong Accept / Weak Accept / Borderline / Weak Reject / Strong Reject 的预审建议，不代表真实录用决定。")
                        st.caption("隐私提示：评审会将论文文本发送至当前配置的 Hy3 模型服务；请确认该服务符合你的数据授权要求。")
                        privacy_ack = st.checkbox(
                            "我确认可以将该论文发送至当前 Hy3 服务",
                            key="peer-review-privacy-ack",
                        )
                    else:
                        st.markdown(
                            '<div class="pa-setup-title">讲解模式</div>'
                            '<div class="pa-setup-mode"><strong>标准论文学习</strong>'
                            '<span>研究问题 · 主要贡献 · 方法 · 实验 · 结果 · 局限 · 关键术语</span></div>',
                            unsafe_allow_html=True,
                        )
                        st.markdown('<div class="pa-setup-title">关联开源代码</div>', unsafe_allow_html=True)
                        with st.expander("上传代码 ZIP（可选）", expanded=False):
                            source_code_file = st.file_uploader(
                                "上传论文开源代码 ZIP",
                                type=["zip"],
                                accept_multiple_files=False,
                                help="只读取文本文件，不运行代码或安装依赖。",
                                key="source_code_upload",
                            )
                            if source_code_file is not None:
                                try:
                                    uploaded_codebase = parse_uploaded_code(
                                        source_code_file.getvalue(), source_code_file.name
                                    )
                                    st.success(
                                        f"已解析 {len(uploaded_codebase.files)} 个文件、"
                                        f"{len(uploaded_codebase.chunks)} 个代码块"
                                    )
                                except (CodeParseError, ValueError) as exc:
                                    st.error(f"代码 ZIP 无法解析：{exc}")
                        if source_code_file is None:
                            st.caption("当前未关联代码，可直接生成论文讲解。")

                    can_run = bool(
                        api_ready
                        and (mode in {"learn", "peer_review"} or (scope and report_text.strip()))
                    )
                    if mode == "peer_review" and not st.session_state.get("peer-review-privacy-ack", False):
                        can_run = False
                    launch_job = None
                    launch_job_id = st.session_state.get("launch_audit_job_id")
                    active_launch_project_id = st.session_state.get("active_project_id")
                    if mode == "audit_existing" and launch_job_id and active_launch_project_id:
                        try:
                            launch_job = project_store.load_audit_job(
                                str(active_launch_project_id), str(launch_job_id)
                            )
                        except StorageError:
                            st.session_state.pop("launch_audit_job_id", None)
                    launch_job_active = bool(
                        launch_job
                        and launch_job.status
                        in {AuditJobStatus.QUEUED, AuditJobStatus.RUNNING}
                    )
                    if launch_job_active:
                        can_run = False
                    tips = []
                    if not api_ready:
                        tips.append("请先在侧栏配置 API")
                    if mode == "peer_review" and not st.session_state.get("peer-review-privacy-ack", False):
                        tips.append("请先确认论文数据发送范围")
                    if mode == "audit_existing" and not report_text.strip():
                        tips.append("请提供中文报告")
                    if tips:
                        st.caption(" · ".join(tips))
                    with st.container(key="launch_setup_actions"):
                        st.divider()
                        if launch_job_active and launch_job is not None:
                            st.progress(launch_job.progress, text=launch_job.stage)
                            st.caption("审计正在后台执行，可以继续翻阅左侧论文。")
                            if st.button(
                                "刷新审计状态",
                                width="stretch",
                                key="launch_audit_refresh",
                            ):
                                st.rerun()
                        elif (
                            launch_job is not None
                            and launch_job.status == AuditJobStatus.SUCCEEDED
                            and launch_job.audit_id
                        ):
                            st.success("后台审计已完成。")
                            if st.button(
                                "查看审计结果 →",
                                type="primary",
                                width="stretch",
                                key="launch_open_audit_result",
                            ):
                                on_open_audit(launch_job.audit_id)
                                st.session_state.pop("launch_audit_job_id", None)
                                st.rerun()
                        elif launch_job is not None and launch_job.status in {
                            AuditJobStatus.FAILED,
                            AuditJobStatus.INTERRUPTED,
                        }:
                            st.error(launch_job.error or "审计任务未能完成。")
                            if st.button(
                                "重新审计",
                                width="stretch",
                                key="launch_retry_audit",
                            ):
                                st.session_state.pop("launch_audit_job_id", None)
                                st.rerun()
                        else:
                            button_label = (
                                "生成论文讲解 →" if mode == "learn"
                                else "开始模拟评审 →" if mode == "peer_review"
                                else "开始审计 →"
                            )
                            run_clicked = st.button(
                                button_label,
                                type="primary",
                                width="stretch",
                                disabled=not can_run,
                            )
                    if run_clicked:
                        status_label = (
                            "正在生成论文学习讲解" if mode == "learn" else "正在执行证据审计"
                        )
                        status = st.status(status_label, expanded=True)
                        progress_bar = st.progress(0.0, text="正在读取并解析 PDF 文本块")

    if run_clicked and pdf_file is not None:
        return UploadSubmission(
            pdf_file.getvalue(), pdf_file.name, mode, report_text,
            report_source_label, report_source_filename, scope,
            source_code_file.getvalue() if source_code_file is not None else None,
            source_code_file.name if source_code_file is not None else None,
            uploaded_codebase, status, progress_bar,
        )
    return None
