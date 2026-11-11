"""Project, conversation and code operations using project-scoped serialization."""
from dataclasses import replace
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, Request, Response, UploadFile
from paperaudit.code_parser import MAX_ZIP_BYTES, parse_code_zip
from paperaudit.models import CodeFile, JointAnswer
from paperaudit.service import match_selected_chunks
from paperaudit.storage import make_conversation
from paperaudit.workflows import require_model
from .audit_routes import require_project
from .schemas import (TitleUpdate, ConversationCreate, ConversationUpdate, Conversations,
                      CodeQuestion, ProjectSummary)

router = APIRouter(prefix="/api/projects")


def read_code_upload(upload):
    data = upload.file.read(MAX_ZIP_BYTES + 1)
    if len(data) > MAX_ZIP_BYTES:
        raise HTTPException(413, "代码 ZIP 不能超过 30MB。")
    return parse_code_zip(data, (upload.filename or "code.zip").replace("\\", "/").split("/")[-1])


def selected_paper(saved, selection=None, page_scope=None, chunk_ids=None, text=None):
    paper = saved.paper
    page = selection.page if selection else page_scope
    if page and page > paper.page_count:
        raise HTTPException(422, "选择的页码超出论文范围。")
    ids = list(selection.chunk_ids if selection else chunk_ids or [])
    chunks = {c.chunk_id: c for c in paper.chunks}
    if any(cid not in chunks or (page and chunks[cid].page != page) for cid in ids):
        raise HTTPException(422, "所选原文片段不属于当前论文或页码。")
    if selection:
        text = selection.text
        if not ids:
            ids = [c.chunk_id for c in match_selected_chunks(paper, page, text)]
    elif page and not ids:
        ids = [c.chunk_id for c in paper.chunks if c.page == page][:100]
    return ids, text


@router.patch("/{pid}", response_model=ProjectSummary)
def rename_project(request: Request, pid: str, body: TitleUpdate):
    state = request.app.state
    require_project(state.api, pid)
    with state.locks.hold(pid):
        state.api.store.update_project_title(pid, body.title)
        return state.api._summary(pid)


@router.delete("/{pid}", status_code=204)
def delete_project(request: Request, pid: str):
    state = request.app.state
    require_project(state.api, pid)
    with state.locks.hold(pid):
        state.api.store.delete_project(pid)
    return Response(status_code=204)


@router.post("/{pid}/conversations", response_model=Conversations, status_code=201)
def create_conversation(request: Request, pid: str, body: ConversationCreate):
    state = request.app.state
    require_project(state.api, pid)
    with state.locks.hold(pid):
        saved = state.api.store.load_learning_project(pid)
        new = make_conversation(body.title)
        state.api.store.save_conversations(pid, [*saved.conversations, new], new.conversation_id, keep_empty=True)
        return state.api.conversations(pid)


@router.patch("/{pid}/conversations/{cid}", response_model=Conversations)
def update_conversation(request: Request, pid: str, cid: str, body: ConversationUpdate):
    state = request.app.state
    require_project(state.api, pid)
    with state.locks.hold(pid):
        saved = state.api.store.load_learning_project(pid)
        current = next((c for c in saved.conversations if c.conversation_id == cid), None)
        if current is None:
            raise HTTPException(404)
        edited = replace(current, title=body.title or current.title,
                         updated_at=datetime.now(timezone.utc).isoformat())
        state.api.store.save_conversations(pid, [edited if c.conversation_id == cid else c for c in saved.conversations],
                                           cid if body.activate else saved.active_conversation_id, keep_empty=True)
        return state.api.conversations(pid)


@router.delete("/{pid}/conversations/{cid}", response_model=Conversations)
def delete_conversation(request: Request, pid: str, cid: str):
    state = request.app.state
    require_project(state.api, pid)
    with state.locks.hold(pid):
        saved = state.api.store.load_learning_project(pid)
        records = [c for c in saved.conversations if c.conversation_id != cid]
        if len(records) == len(saved.conversations):
            raise HTTPException(404)
        records = records or [make_conversation()]
        active = saved.active_conversation_id if any(c.conversation_id == saved.active_conversation_id for c in records) else records[0].conversation_id
        state.api.store.save_conversations(pid, records, active, keep_empty=True)
        return state.api.conversations(pid)


@router.post("/{pid}/code", response_model=list[CodeFile], status_code=201)
def upload_code(request: Request, pid: str, code_zip: Annotated[UploadFile, File()]):
    state = request.app.state
    require_project(state.api, pid)
    codebase = read_code_upload(code_zip)
    with state.locks.hold(pid):
        state.api.store.save_codebase(pid, codebase)
    return codebase.files


def codebase_for(request, pid):
    api = request.app.state.api
    require_project(api, pid)
    codebase = api.store.load_learning_project(pid).codebase
    if codebase is None:
        raise HTTPException(404, "当前项目没有代码。")
    return codebase


@router.get("/{pid}/code/files", response_model=list[CodeFile])
def code_files(request: Request, pid: str):
    return codebase_for(request, pid).files


@router.get("/{pid}/code/files/{path:path}", response_model=CodeFile)
def code_file(request: Request, pid: str, path: str):
    # Match a stored logical name, never join the browser path to the filesystem.
    item = next((f for f in codebase_for(request, pid).files if f.path == path), None)
    if item is None:
        raise HTTPException(404)
    return item


@router.post("/{pid}/code/qa", response_model=JointAnswer)
def code_question(request: Request, pid: str, body: CodeQuestion):
    state = request.app.state
    require_project(state.api, pid)
    require_model(state.api.settings)
    with state.locks.hold(pid):
        saved = state.api.store.load_learning_project(pid)
        if saved.codebase is None:
            raise HTTPException(409, "请先上传代码 ZIP。")
        ids, text = selected_paper(saved, body.selection)
        selection = body.selected_code
        if selection:
            file = next((f for f in saved.codebase.files if f.path == selection.path), None)
            if not file or selection.end_line < selection.start_line or selection.end_line > file.line_count:
                raise HTTPException(422, "代码选区超出文件范围。")
            lines = file.content.splitlines()
            # Use source content, not caller-supplied quotes, for retrieval/citations.
            selection = selection.model_copy(update={
                "text": "\n".join(lines[selection.start_line - 1:selection.end_line])[:8000],
                "context_text": "\n".join(lines[max(0, selection.start_line - 4):selection.end_line + 3])[:12000],
            })
        records = list(saved.conversations)
        if body.new_conversation:
            current = make_conversation()
            records.append(current)
        else:
            current = next((c for c in records if c.conversation_id == (body.conversation_id or saved.active_conversation_id)), None)
            if current is None:
                raise HTTPException(404, "会话不存在。")
        answer = state.code_service_factory(state.api.settings).answer(
            saved.paper, saved.codebase, body.question, requested_scope=body.scope,
            history=current.joint_history, selected_paper_chunk_ids=ids,
            selected_paper_text=text, selected_code=selection,
            investigate=body.investigate)
        updated = replace(current, joint_history=[*current.joint_history, answer][-10:],
                          title=body.question[:36] if (current.title in {"新对话", "默认对话"}
                          and not current.paper_history and not current.joint_history) else current.title,
                          updated_at=datetime.now(timezone.utc).isoformat())
        state.api.store.save_conversations(pid, [updated if c.conversation_id == current.conversation_id else c for c in records],
                                           updated.conversation_id, keep_empty=True)
        return answer
