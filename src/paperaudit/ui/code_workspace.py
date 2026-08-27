"""Paper-and-code joint reading workspace."""

from __future__ import annotations

from hashlib import sha256
from html import escape

import streamlit as st

from paperaudit.code_service import CodeLearningService
from paperaudit.hy3_client import Hy3ResponseError
from paperaudit.models import (
    AnswerScope,
    AnswerStatus,
    CodeCitation,
    CodeSelection,
    EvidenceAnchor,
    JointAnswer,
    PageRect,
    ParsedCodebase,
    ParsedPaper,
)
from paperaudit.service import match_selected_chunks
from paperaudit.ui.code_selector import render_selectable_code
from paperaudit.ui.pdf_selector import render_selectable_pdf_page


_SCOPE_LABELS = {
    AnswerScope.AUTO: "自动判断",
    AnswerScope.PAPER: "仅论文",
    AnswerScope.CODE: "仅代码",
    AnswerScope.JOINT: "论文 + 代码",
}

_RELATION_LABELS = {
    "IMPLEMENTS": "代码实现了论文描述",
    "CONFIGURES": "代码配置了论文方法",
    "EVALUATES": "代码用于论文实验评估",
    "LOADS_DATA": "代码负责数据加载",
    "DOCUMENTS": "代码文档解释了论文内容",
    "PARTIAL_MATCH": "论文与代码部分对应",
    "NOT_LOCATED": "当前候选中未定位到对应实现",
}

_LAYOUT_LABELS = {
    "balanced": "均衡",
    "paper": "论文",
    "code": "代码",
}


def _selected_source_label(path: str) -> str:
    suffix = path.rsplit(".", 1)[-1].lower() if "." in path else ""
    if suffix == "md":
        return "仓库文档"
    if suffix in {"yaml", "yml", "json", "toml"}:
        return "配置文件"
    return "代码"


def _selected_source_language(path: str) -> str | None:
    suffix = path.rsplit(".", 1)[-1].lower() if "." in path else ""
    return {
        "py": "python",
        "md": "markdown",
        "yaml": "yaml",
        "yml": "yaml",
        "json": "json",
        "toml": "toml",
        "sh": "bash",
    }.get(suffix)


def _selection_question(action: str, selection: CodeSelection) -> tuple[str, AnswerScope]:
    source_label = _selected_source_label(selection.path)
    if action == "relate":
        return (
            f"这段{source_label}对应论文中的哪部分？请说明论文描述与仓库内容的关系。",
            AnswerScope.JOINT,
        )
    if source_label == "仓库文档":
        return (
            "请解释这段仓库文档的含义、用途和关键信息。不要将其当作可执行代码，"
            "并且只围绕选中内容回答。",
            AnswerScope.CODE,
        )
    if source_label == "配置文件":
        return (
            "请解释这段配置的字段、取值和作用，并且只围绕选中内容回答。",
            AnswerScope.CODE,
        )
    return (
        "请解释这段代码的输入、输出、核心流程和作用。",
        AnswerScope.CODE,
    )


def _file_tree(paths: list[str]) -> str:
    roots: dict[str, list[str]] = {}
    for path in paths:
        head, _, tail = path.partition("/")
        roots.setdefault(head, []).append(tail)
    lines: list[str] = []
    for head in sorted(roots):
        tails = roots[head]
        if tails == [""]:
            lines.append(f"- `{head}`")
            continue
        lines.append(f"- **{head}/**")
        for tail in sorted(item for item in tails if item):
            lines.append(f"  - `{tail}`")
    return "\n".join(lines)


def _file_tree_nodes(paths: list[str]) -> dict[str, object]:
    root: dict[str, object] = {}
    for path in sorted(paths, key=str.casefold):
        node = root
        parts = [part for part in path.split("/") if part]
        for part in parts[:-1]:
            child = node.setdefault(part, {})
            if isinstance(child, dict):
                node = child
        node.setdefault(parts[-1], None)
    return root


def _file_icon(path: str) -> str:
    suffix = path.rsplit(".", 1)[-1].lower() if "." in path else ""
    return {
        "py": ":material/code:",
        "md": ":material/article:",
        "json": ":material/data_object:",
        "yaml": ":material/settings:",
        "yml": ":material/settings:",
        "toml": ":material/settings:",
        "sh": ":material/terminal:",
    }.get(suffix, ":material/description:")


def _render_file_tree(
    paths: list[str],
    active_path: str,
    *,
    key_prefix: str,
) -> str:
    """Render a small searchable tree and return the selected file path."""
    query = st.text_input(
        "搜索文件",
        placeholder="搜索文件…",
        key=f"{key_prefix}-query",
        label_visibility="collapsed",
    ).strip().casefold()
    visible = [path for path in paths if not query or query in path.casefold()]
    if not visible:
        st.caption("没有匹配的文件")
        return active_path
    visible_set = set(visible)
    nodes = _file_tree_nodes(visible)
    selected = active_path

    def walk(branch: dict[str, object], prefix: str = "") -> None:
        nonlocal selected
        for name, child in branch.items():
            path = f"{prefix}/{name}" if prefix else name
            if isinstance(child, dict):
                descendants = [item for item in visible_set if item == path or item.startswith(path + "/")]
                expanded = any(item == active_path or item.startswith(path + "/") for item in descendants)
                with st.expander(
                    name,
                    expanded=expanded,
                    icon=":material/folder:",
                    type="compact",
                ):
                    walk(child, path)
            elif st.button(
                name,
                key=f"{key_prefix}-file-{sha256(path.encode('utf-8')).hexdigest()[:12]}",
                type="primary" if path == active_path else "tertiary",
                icon=_file_icon(path),
                width="stretch",
                help=path,
            ):
                selected = path
                st.session_state["joint_code_path"] = path
                st.session_state.pop("joint_code_selection", None)
                st.session_state.pop("joint_active_code_citation", None)
                st.rerun()

    with st.container(key=f"{key_prefix}-list"):
        walk(nodes)
    return selected


def _render_code(
    codebase: ParsedCodebase,
    active_path: str,
    citation: CodeCitation | None,
) -> dict[str, object] | None:
    file_map = {item.path: item for item in codebase.files}
    source = file_map[active_path]
    return render_selectable_code(
        source,
        citation,
        key=(
            "joint-selectable-code-"
            + sha256(active_path.encode("utf-8")).hexdigest()[:16]
        ),
    )


def _paper_anchor_map(history: list[JointAnswer], paper: ParsedPaper) -> dict[str, EvidenceAnchor]:
    anchors = {
        citation.chunk_id: citation
        for answer in history
        for citation in answer.paper_citations
    }
    selection = st.session_state.get("joint_paper_selection")
    if isinstance(selection, dict):
        chunks = {chunk.chunk_id: chunk for chunk in paper.chunks}
        for chunk_id in selection.get("chunk_ids", []):
            chunk = chunks.get(chunk_id)
            if chunk is not None:
                anchors.setdefault(
                    chunk_id,
                    EvidenceAnchor(
                        chunk_id=chunk.chunk_id,
                        page=chunk.page,
                        text=chunk.content,
                        rects=chunk.rects,
                    ),
                )
    return anchors


def _render_pdf(
    paper: ParsedPaper,
    pdf_bytes: bytes,
    anchors: dict[str, EvidenceAnchor],
) -> None:
    active_id = st.session_state.get("joint_active_paper_citation")
    active = anchors.get(active_id)
    if active and st.session_state.get("joint_paper_sync") != active_id:
        st.session_state["joint_pdf_page"] = active.page or 1
        st.session_state["joint_paper_sync"] = active_id
    st.session_state.setdefault("joint_pdf_page", 1)
    st.session_state["joint_pdf_page"] = min(
        max(int(st.session_state["joint_pdf_page"]), 1), paper.page_count
    )

    def change_page(delta: int) -> None:
        current = int(st.session_state.get("joint_pdf_page", 1))
        st.session_state["joint_pdf_page"] = min(max(current + delta, 1), paper.page_count)

    title_col, previous, page_input, next_page = st.columns(
        [2.8, 1, 1.25, 1], vertical_alignment="center"
    )
    title_col.markdown(
        f'<div class="pa-panel-title">论文原文 '
        f'<span>{st.session_state["joint_pdf_page"]} / {paper.page_count}</span></div>',
        unsafe_allow_html=True,
    )
    previous.button(
        "‹",
        key="joint-pdf-previous",
        disabled=st.session_state["joint_pdf_page"] <= 1,
        width="stretch",
        on_click=change_page,
        args=(-1,),
    )
    with page_input:
        st.number_input(
            "PDF 页码",
            min_value=1,
            max_value=paper.page_count,
            step=1,
            key="joint_pdf_page",
            label_visibility="collapsed",
        )
    next_page.button(
        "›",
        key="joint-pdf-next",
        disabled=st.session_state["joint_pdf_page"] >= paper.page_count,
        width="stretch",
        on_click=change_page,
        args=(1,),
    )
    display_page = int(st.session_state["joint_pdf_page"])
    highlights = active.rects if active and active.page == display_page else []
    selection = render_selectable_pdf_page(
        pdf_bytes,
        display_page,
        highlights,
        key="joint-selectable-pdf",
    )
    if selection:
        selected_text = str(selection.get("text", "")).strip()
        selected_page = int(selection.get("page", display_page))
        rects: list[PageRect] = []
        for raw_rect in selection.get("rects", []):
            try:
                rects.append(PageRect.model_validate(raw_rect))
            except (TypeError, ValueError):
                continue
        matched = match_selected_chunks(paper, selected_page, selected_text, rects)
        st.session_state["joint_paper_selection"] = {
            "page": selected_page,
            "text": selected_text,
            "chunk_ids": [chunk.chunk_id for chunk in matched],
        }
        st.rerun()
    if active and active.page == display_page:
        st.caption("黄色区域是回答引用的论文原文；也可以直接拖选文字查找对应代码。")
    else:
        st.caption("拖选论文文字后，可直接查找对应代码实现。")


def _set_code_citation(citation: CodeCitation) -> None:
    st.session_state["joint_code_path_pending"] = citation.path
    st.session_state["joint_active_code_citation"] = citation.model_dump()
    st.session_state["joint_layout_mode_pending"] = "code"
    st.session_state.pop("joint_code_selection", None)


def _code_citation_label(citation: CodeCitation) -> str:
    filename = citation.path.rsplit("/", 1)[-1]
    source = citation.symbol or filename
    return f"{source} · L{citation.start_line}–{citation.end_line} ↗"


def _valid_code_citation(citation: CodeCitation, codebase: ParsedCodebase) -> bool:
    source = next((item for item in codebase.files if item.path == citation.path), None)
    return bool(
        source is not None
        and 1 <= citation.start_line <= citation.end_line <= source.line_count
    )


def _render_selection_snapshot(selection: CodeSelection, *, key: str) -> None:
    with st.container(key=key):
        st.markdown(
            '<div class="pa-message-selection-title"><strong>选中内容</strong>'
            f'<span>{escape(selection.path.rsplit("/", 1)[-1])} · '
            f'L{selection.start_line}—{selection.end_line}</span></div>',
            unsafe_allow_html=True,
        )
        st.code(
            selection.text,
            language=_selected_source_language(selection.path),
            wrap_lines=True,
            height=112,
        )


def _render_answer(
    answer: JointAnswer,
    answer_index: int,
    codebase: ParsedCodebase,
) -> None:
    with st.container(key=f"joint_message_{answer_index}"):
        if answer.selected_code is not None:
            _render_selection_snapshot(
                answer.selected_code,
                key=f"joint_message_selection_{answer_index}",
            )
        st.markdown(
            f'<div class="pa-assistant-user"><span>问题</span>'
            f'{escape(answer.question)}</div>',
            unsafe_allow_html=True,
        )
        if answer.status == AnswerStatus.ANSWERED:
            status = "✓ 已用本地证据回答"
        elif answer.paper_citations or answer.code_citations:
            status = "△ 已定位候选证据，结论需复核"
        else:
            status = "⚠️ 当前证据不足"
        scope = _SCOPE_LABELS.get(answer.scope, answer.scope.value)
        relation = _RELATION_LABELS.get(answer.relation.value, "") if answer.relation else ""
        meta = " · ".join(item for item in (status, scope, relation) if item)
        st.markdown(
            f'<div class="pa-assistant-meta">{escape(meta)}</div>',
            unsafe_allow_html=True,
        )
        with st.container(key=f"joint_answer_body_{answer_index}"):
            st.markdown(answer.answer)

        if answer.paper_citations:
            st.markdown(
                f'<div class="pa-reference-heading">论文依据 '
                f'<span>{len(answer.paper_citations)} 处</span></div>',
                unsafe_allow_html=True,
            )
            with st.container(key=f"joint_paper_refs_{answer_index}"):
                paper_columns = st.columns(min(len(answer.paper_citations), 2))
                for citation_index, citation in enumerate(answer.paper_citations):
                    with paper_columns[citation_index % len(paper_columns)]:
                        if st.button(
                            f"论文 · P{citation.page} ↗",
                            key=(
                                f"joint-paper-ref-{answer_index}-"
                                f"{citation_index}-{citation.chunk_id}"
                            ),
                            type="tertiary",
                            width="stretch",
                            help=f"定位并高亮论文第 {citation.page} 页原文",
                        ):
                            st.session_state["joint_active_paper_citation"] = citation.chunk_id
                            st.session_state["joint_layout_mode_pending"] = "paper"
                            st.session_state.pop("joint_paper_sync", None)
                            st.rerun()
        if answer.code_citations:
            st.markdown(
                f'<div class="pa-reference-heading">代码依据 '
                f'<span>{len(answer.code_citations)} 处</span></div>',
                unsafe_allow_html=True,
            )
            with st.container(key=f"joint_code_refs_{answer_index}"):
                code_columns = st.columns(min(len(answer.code_citations), 2))
                for citation_index, citation in enumerate(answer.code_citations):
                    with code_columns[citation_index % len(code_columns)]:
                        if st.button(
                            _code_citation_label(citation),
                            key=(
                                f"joint-code-ref-{answer_index}-"
                                f"{citation_index}-{citation.chunk_id}"
                            ),
                            type="tertiary",
                            width="stretch",
                            help=(
                                citation.path
                                if _valid_code_citation(citation, codebase)
                                else "历史引用当前无法定位"
                            ),
                            disabled=not _valid_code_citation(citation, codebase),
                        ):
                            _set_code_citation(citation)
                            st.rerun()


def _render_current_context(
    history: list[JointAnswer],
    selection: object,
    *,
    show_code_context: bool = True,
) -> None:
    paper_label: str | None = None
    if isinstance(selection, dict) and selection.get("page"):
        paper_label = f"Paper · 第 {selection['page']} 页选中内容"
    else:
        active_paper_id = st.session_state.get("joint_active_paper_citation")
        active_paper = next(
            (
                citation
                for answer in reversed(history)
                for citation in answer.paper_citations
                if citation.chunk_id == active_paper_id
            ),
            None,
        )
        if active_paper is not None:
            paper_label = f"Paper · 第 {active_paper.page} 页"

    code_label: str | None = None
    selected_code = st.session_state.get("joint_code_selection") if show_code_context else None
    if isinstance(selected_code, dict):
        try:
            active_selection = CodeSelection.model_validate(selected_code)
            code_label = (
                f"{_selected_source_label(active_selection.path)} · {active_selection.path} "
                f"L{active_selection.start_line}—{active_selection.end_line}"
            )
        except ValueError:
            pass
    if code_label is None:
        raw_code = st.session_state.get("joint_active_code_citation")
        if isinstance(raw_code, dict):
            try:
                active_code = CodeCitation.model_validate(raw_code)
                code_label = (
                    f"Code · {active_code.path} "
                    f"L{active_code.start_line}—{active_code.end_line}"
                )
            except ValueError:
                pass

    labels = [label for label in (paper_label, code_label) if label]
    if not labels:
        return
    with st.container(key="joint_current_context"):
        st.markdown(
            '<div class="pa-context-title">当前上下文</div>'
            '<div class="pa-context-chips">'
            + "".join(f'<span>{escape(label)}</span>' for label in labels)
            + "</div>",
            unsafe_allow_html=True,
        )
        if isinstance(selected_code, dict):
            try:
                active_selection = CodeSelection.model_validate(selected_code)
            except ValueError:
                return
            st.caption(
                f"已选{_selected_source_label(active_selection.path)} · "
                f"{active_selection.path} · "
                f"L{active_selection.start_line}—{active_selection.end_line}"
            )
            st.code(
                active_selection.text,
                language=_selected_source_language(active_selection.path),
                wrap_lines=True,
                height=140,
            )


def _render_conversation(
    paper: ParsedPaper,
    codebase: ParsedCodebase,
    service: CodeLearningService | None,
    *,
    show_code_context: bool = True,
) -> None:
    history: list[JointAnswer] = st.session_state.setdefault("joint_qa_history", [])
    pending = st.session_state.get("joint_qa_pending")
    selection = st.session_state.get("joint_paper_selection")
    selected_code = st.session_state.get("joint_code_selection")

    context_keys = (
        "joint_paper_selection",
        "joint_active_paper_citation",
        "joint_active_code_citation",
        "joint_code_selection",
    )
    has_context = any(st.session_state.get(key) is not None for key in context_keys)
    action_left, clear_context_col, clear_history_col = st.columns(
        [4.6, 1.15, 1], vertical_alignment="center"
    )
    action_left.markdown(
        f'<div class="pa-panel-title">Assistant '
        f'<span>最近 {min(len(history), 10)} 轮</span></div>',
        unsafe_allow_html=True,
    )
    if clear_context_col.button(
        "清除上下文",
        key="clear-joint-context",
        disabled=not has_context,
        type="tertiary",
        width="stretch",
    ):
        for key in context_keys:
            st.session_state.pop(key, None)
        st.rerun()
    if clear_history_col.button(
        "清空对话",
        key="clear-joint-history",
        disabled=not history and not pending,
        type="tertiary",
        width="stretch",
    ):
        history.clear()
        st.session_state.pop("joint_qa_pending", None)
        st.rerun()

    if not history and not pending:
        st.caption("可以询问代码实现，也可以比较论文描述与代码是否一致。")
    for answer_index, answer in enumerate(history):
        _render_answer(answer, answer_index, codebase)
    if isinstance(pending, dict):
        with st.container(key="joint_pending_message"):
            st.markdown('<div class="pa-joint-pending-marker"></div>', unsafe_allow_html=True)
            raw_pending_selection = pending.get("selected_code")
            if isinstance(raw_pending_selection, dict):
                try:
                    pending_selection = CodeSelection.model_validate(raw_pending_selection)
                except ValueError:
                    pending_selection = None
                if pending_selection is not None:
                    _render_selection_snapshot(
                        pending_selection,
                        key="joint_pending_selection",
                    )
            st.markdown(
                f'<div class="pa-assistant-user">{escape(str(pending.get("question", "")))}</div>',
                unsafe_allow_html=True,
            )
            st.markdown('<div class="pa-assistant-meta">正在检索论文与代码并生成回答…</div>', unsafe_allow_html=True)

    if not isinstance(pending, dict):
        _render_current_context(
            history,
            selection,
            show_code_context=show_code_context,
        )

        if isinstance(selected_code, dict):
            try:
                active_selection = CodeSelection.model_validate(selected_code)
            except ValueError:
                active_selection = None
            if active_selection is not None:
                explain_col, relate_col = st.columns(2)
                if explain_col.button(
                    "解释选中内容",
                    key="explain-current-code-selection",
                    type="primary",
                    width="stretch",
                ):
                    question, scope = _selection_question("explain", active_selection)
                    st.session_state["joint_qa_pending"] = {
                        "question": question,
                        "scope": scope.value,
                        "selected_chunk_ids": [],
                        "selected_text": None,
                        "selected_code": active_selection.model_dump(),
                    }
                    st.rerun()
                if relate_col.button(
                    "对应论文",
                    key="relate-current-code-selection",
                    width="stretch",
                ):
                    question, scope = _selection_question("relate", active_selection)
                    st.session_state["joint_qa_pending"] = {
                        "question": question,
                        "scope": scope.value,
                        "selected_chunk_ids": [],
                        "selected_text": None,
                        "selected_code": active_selection.model_dump(),
                    }
                    st.rerun()

        if isinstance(selection, dict) and selection.get("text"):
            with st.container(key="joint_selected_context"):
                st.caption(f"已选论文原文 · 第 {selection.get('page', 1)} 页")
                st.markdown(f"> {escape(str(selection['text']))}")
                find_col, cancel_col = st.columns([4, 1])
                if find_col.button(
                    "查找这段内容对应的代码",
                    type="primary",
                    width="stretch",
                    disabled=service is None,
                ):
                    st.session_state["joint_qa_pending"] = {
                        "question": "这段论文内容在代码中如何实现？请说明对应关系。",
                        "scope": AnswerScope.JOINT.value,
                        "selected_chunk_ids": list(selection.get("chunk_ids", [])),
                        "selected_text": str(selection.get("text", "")),
                        "selected_code": (
                            selected_code if isinstance(selected_code, dict) else None
                        ),
                    }
                    st.rerun()
                if cancel_col.button("取消", width="stretch", key="clear-joint-selection"):
                    st.session_state.pop("joint_paper_selection", None)
                    st.rerun()

    submitted = False
    question = ""
    scope = AnswerScope.AUTO
    if not isinstance(pending, dict):
        with st.form("joint-question-form", clear_on_submit=True):
            st.markdown('<div class="pa-joint-form-marker"></div>', unsafe_allow_html=True)
            question = st.text_area(
                "论文与代码追问",
                placeholder="针对论文、代码或当前选中内容提问…",
                max_chars=1000,
                height=76,
                label_visibility="collapsed",
            )
            scope_col, submit_col = st.columns([4, 1], vertical_alignment="center")
            scope = scope_col.selectbox(
                "回答范围",
                list(AnswerScope),
                format_func=_SCOPE_LABELS.get,
                label_visibility="collapsed",
            )
            submitted = submit_col.form_submit_button(
                "↑",
                type="primary",
                width="stretch",
                disabled=service is None,
                help="发送问题",
            )

    if service is None:
        st.warning("请先配置 Hy3 API，才能进行论文与代码追问。")
    if submitted:
        normalized = question.strip()
        if not normalized:
            st.error("追问内容不能为空。")
        else:
            st.session_state["joint_qa_pending"] = {
                "question": normalized,
                "scope": scope.value,
                "selected_chunk_ids": (
                    list(selection.get("chunk_ids", [])) if isinstance(selection, dict) else []
                ),
                "selected_text": (
                    str(selection.get("text", "")) if isinstance(selection, dict) else None
                ),
                "selected_code": selected_code if isinstance(selected_code, dict) else None,
            }
            st.rerun()

    if isinstance(pending, dict) and service is not None:
        try:
            raw_selected_code = pending.get("selected_code")
            validated_selection = (
                CodeSelection.model_validate(raw_selected_code)
                if isinstance(raw_selected_code, dict)
                else None
            )
            answer = service.answer(
                paper,
                codebase,
                str(pending.get("question", "")),
                AnswerScope(str(pending.get("scope", AnswerScope.AUTO.value))),
                history,
                selected_paper_chunk_ids=pending.get("selected_chunk_ids", []),
                selected_paper_text=pending.get("selected_text"),
                selected_code=validated_selection,
            )
            st.session_state.pop("joint_qa_pending", None)
            history.append(answer)
            del history[:-10]
            if validated_selection is not None:
                st.session_state.pop("joint_code_selection", None)
            if answer.paper_citations:
                st.session_state["joint_active_paper_citation"] = answer.paper_citations[0].chunk_id
            if answer.code_citations:
                _set_code_citation(answer.code_citations[0])
            st.rerun()
        except (Hy3ResponseError, ValueError) as exc:
            st.session_state.pop("joint_qa_pending", None)
            st.error(str(exc))
        except Exception as exc:
            st.session_state.pop("joint_qa_pending", None)
            st.error(f"追问失败：{exc}")


def render_code_workspace(
    paper: ParsedPaper,
    pdf_bytes: bytes,
    codebase: ParsedCodebase,
    service: CodeLearningService | None,
) -> None:
    history: list[JointAnswer] = st.session_state.setdefault("joint_qa_history", [])
    pending_path = st.session_state.pop("joint_code_path_pending", None)
    if isinstance(pending_path, str):
        st.session_state["joint_code_path"] = pending_path
    st.session_state.setdefault("joint_code_path", codebase.files[0].path)
    file_paths = [item.path for item in codebase.files]
    if st.session_state["joint_code_path"] not in file_paths:
        st.session_state["joint_code_path"] = file_paths[0]

    layout_options = ["balanced", "paper", "code"]
    pending_layout = st.session_state.pop("joint_layout_mode_pending", None)
    if pending_layout in layout_options:
        st.session_state["joint_layout_mode"] = pending_layout
    if st.session_state.get("joint_layout_mode") not in layout_options:
        st.session_state["joint_layout_mode"] = "balanced"
    status_col, layout_col = st.columns([4, 3], vertical_alignment="center")
    status_col.markdown(
        '<div class="pa-workspace-status"><span></span>论文与代码均在本地解析，引用经过本地校验</div>',
        unsafe_allow_html=True,
    )
    with layout_col:
        layout_mode = st.segmented_control(
            "工作区布局",
            layout_options,
            format_func=_LAYOUT_LABELS.get,
            key="joint_layout_mode",
            required=True,
            label_visibility="collapsed",
            width="stretch",
        )
    if codebase.warnings:
        with st.expander(f"代码解析提示（{len(codebase.warnings)}）"):
            for warning in codebase.warnings:
                st.caption(warning)
    anchors = _paper_anchor_map(history, paper)

    def render_pdf_panel() -> None:
        with st.container(key="joint_pdf_panel"):
            _render_pdf(paper, pdf_bytes, anchors)

    def render_code_panel(*, show_file_tree: bool = False) -> None:
        with st.container(key="joint_code_panel"):
            active_path = st.session_state["joint_code_path"]
            st.markdown(
                f'<div class="pa-panel-title">代码仓库 '
                f'<span>{escape(codebase.name)}</span></div>',
                unsafe_allow_html=True,
            )
            if show_file_tree:
                tree_col, editor_col = st.columns([0.24, 0.76], gap="small")
                with tree_col:
                    with st.container(key="joint_code_file_tree"):
                        st.markdown('<div class="pa-code-tree-title">文件</div>', unsafe_allow_html=True)
                        active_path = _render_file_tree(
                            file_paths,
                            active_path,
                            key_prefix="joint-code-tree",
                        )
            else:
                editor_col = st.container()
                active_path = st.selectbox(
                    "代码文件",
                    file_paths,
                    key="joint_code_path",
                    label_visibility="collapsed",
                )
            with editor_col:
                st.markdown(
                    f'<div class="pa-code-breadcrumb">segment-anything-main / '
                    f'<strong>{escape(active_path)}</strong></div>',
                    unsafe_allow_html=True,
                )
                previous_path = st.session_state.get("joint_code_rendered_path")
                if previous_path is not None and previous_path != active_path:
                    st.session_state.pop("joint_code_selection", None)
                st.session_state["joint_code_rendered_path"] = active_path
                raw_citation = st.session_state.get("joint_active_code_citation")
                citation = None
                if isinstance(raw_citation, dict):
                    try:
                        citation = CodeCitation.model_validate(raw_citation)
                    except ValueError:
                        citation = None
                selection_event = _render_code(codebase, active_path, citation)
                if selection_event:
                    action = str(selection_event.pop("action", ""))
                    try:
                        selected = CodeSelection.model_validate(selection_event)
                    except ValueError as exc:
                        st.error(f"代码选区无效：{exc}")
                    else:
                        st.session_state["joint_code_selection"] = selected.model_dump()
                        st.session_state["joint_layout_mode_pending"] = "balanced"
                        if action in {"explain", "relate"}:
                            question, scope = _selection_question(action, selected)
                            st.session_state["joint_qa_pending"] = {
                                "question": question,
                                "scope": scope.value,
                                "selected_chunk_ids": [],
                                "selected_text": None,
                                "selected_code": selected.model_dump(),
                            }
                        st.rerun()

    def render_conversation_panel(*, show_code_context: bool = True) -> None:
        with st.container(key="joint_conversation_panel"):
            _render_conversation(
                paper,
                codebase,
                service,
                show_code_context=show_code_context,
            )

    if layout_mode == "paper":
        main_col, conversation_col = st.columns([1.85, 1], gap="medium")
        with main_col:
            render_pdf_panel()
        with conversation_col:
            render_conversation_panel(show_code_context=False)
    elif layout_mode == "code":
        main_col, conversation_col = st.columns([1.85, 1], gap="medium")
        with main_col:
            render_code_panel(show_file_tree=True)
        with conversation_col:
            render_conversation_panel()
    else:
        pdf_col, code_col, conversation_col = st.columns([1.25, 1, 0.9], gap="medium")
        with pdf_col:
            render_pdf_panel()
        with code_col:
            render_code_panel(show_file_tree=False)
        with conversation_col:
            render_conversation_panel()
