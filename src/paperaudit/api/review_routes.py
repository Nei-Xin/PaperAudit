"""Reviews, human decisions, generation-scoped progress and revision management."""
from typing import Annotated
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from paperaudit.models import PeerReviewJob, PeerReviewRevisionJob, PeerReviewRevision, RelatedWorkComparison, ReviewConcern
from paperaudit.workflows import require_model, submit_peer_review, submit_revision, save_peer_review_edit, compare_related_work
from .audit_routes import require_project
from .schemas import (ReviewRequest, ReviewPayload, ConcernUpdate, ProgressUpdate,
                      ReviewProgress, RelatedWorkRequest, RevisionUpdate)

router = APIRouter(prefix="/api/projects")


def review_idle(state, pid):
    if any(j.status in {"QUEUED", "RUNNING"} for j in state.api.store.list_peer_review_jobs(pid)):
        raise HTTPException(409, "评审正在生成，请完成后再修改。")


def current_review(state, pid, expected_run_id=None):
    review_idle(state, pid)
    report = state.api.store.load_peer_review(pid)
    if report is None:
        raise HTTPException(409, "当前项目没有基准评审。")
    if expected_run_id is not None and expected_run_id != report.run_id:
        raise HTTPException(409, "评审已更新，请刷新后重试。")
    return report


@router.post("/{pid}/review-jobs", response_model=PeerReviewJob, status_code=202)
def generate_review(request: Request, pid: str, body: ReviewRequest):
    state = request.app.state
    require_project(state.api, pid)
    if not body.privacy_ack:
        raise HTTPException(422, "请确认将论文发送到模型服务。")
    with state.locks.hold(pid):
        return submit_peer_review(state.api.store, state.review_manager, state.api.settings,
                                   pid, body.venue, body.rubric_weights)


@router.post("/{pid}/review-jobs/{job_id}/retry", response_model=PeerReviewJob, status_code=202)
def retry_review(request: Request, pid: str, job_id: str):
    state = request.app.state
    require_project(state.api, pid)
    with state.locks.hold(pid):
        previous = state.api.store.load_peer_review_job(pid, job_id)
        if previous.status not in {"FAILED", "INTERRUPTED"}:
            raise HTTPException(409, "只有失败或中断的评审可以重试。")
        if any(j.job_id != job_id and j.created_at >= previous.created_at and j.status in {"QUEUED", "RUNNING", "SUCCEEDED"}
               for j in state.api.store.list_peer_review_jobs(pid)):
            raise HTTPException(409, "已有更新的评审任务。")
        require_model(state.api.settings)
        job = state.api.store.create_peer_review_job(pid, runtime=previous.runtime,
            venue=previous.venue, rubric_version=previous.rubric_version,
            rubric_weights=previous.rubric_weights)
        state.review_manager.submit(pid, job.job_id, state.api.settings)
        return job


@router.patch("/{pid}/review/concerns/{concern_index}", response_model=ReviewPayload)
def edit_concern(request: Request, pid: str, concern_index: int, body: ConcernUpdate):
    state = request.app.state
    require_project(state.api, pid)
    with state.locks.hold(pid):
        report = current_review(state, pid, body.expected_run_id)
        concerns = [*report.major_concerns, *report.minor_concerns]
        if concern_index < 0 or concern_index >= len(concerns):
            raise HTTPException(404)
        changes = body.model_dump(exclude_none=True, exclude={"expected_run_id"})
        concerns[concern_index] = ReviewConcern.model_validate({**concerns[concern_index].model_dump(), **changes})
        updated = report.model_copy(update={
            "major_concerns": [c for c in concerns if c.severity == "major"],
            "minor_concerns": [c for c in concerns if c.severity != "major"],
        })
        save_peer_review_edit(state.api.store, pid, updated)
        return state.api.review(pid)


@router.put("/{pid}/review/progress", response_model=ReviewProgress)
def save_progress(request: Request, pid: str, body: ProgressUpdate):
    state = request.app.state
    require_project(state.api, pid)
    with state.locks.hold(pid):
        current_review(state, pid, body.review_run_id)
        return state.api.store.save_review_progress(pid, body.model_dump())


@router.post("/{pid}/review/related-work", response_model=RelatedWorkComparison)
def related_work(request: Request, pid: str, body: RelatedWorkRequest):
    state = request.app.state
    require_project(state.api, pid)
    if not body.privacy_ack:
        raise HTTPException(422, "请确认将论文和相关工作发送到模型服务。")
    if any(not r.citation.strip() or len(r.citation) > 2000 or len(r.distinction) > 10000 or len(r.url) > 2048 for r in body.references):
        raise HTTPException(422, "相关工作条目为空或过长。")
    require_model(state.api.settings)
    with state.locks.hold(pid):
        report = current_review(state, pid, body.expected_run_id)
        return compare_related_work(state.api.store, state.service_factory(state.api.settings),
                                    pid, body.references, report=report)


@router.get("/{pid}/revisions", response_model=list[PeerReviewRevision])
def revisions(request: Request, pid: str):
    require_project(request.app.state.api, pid)
    return request.app.state.api.store.list_peer_review_revisions(pid)


@router.post("/{pid}/revisions", response_model=PeerReviewRevisionJob, status_code=202)
def upload_revision(request: Request, pid: str, pdf: Annotated[UploadFile, File()],
                    privacy_ack: Annotated[bool, Form()] = False):
    state = request.app.state
    require_project(state.api, pid)
    if not privacy_ack:
        raise HTTPException(422, "请确认将修改稿发送到模型服务。")
    data = pdf.file.read(200 * 1024 * 1024 + 1)
    if len(data) > 200 * 1024 * 1024:
        raise HTTPException(413, "PDF 文件不能超过 200MB。")
    with state.locks.hold(pid):
        current_review(state, pid)
        return submit_revision(state.api.store, state.revision_manager, state.api.settings, pid,
                               data, (pdf.filename or "revision.pdf").replace("\\", "/").split("/")[-1])


def get_revision(state, pid, rid):
    require_project(state.api, pid)
    result = next((r for r in state.api.store.list_peer_review_revisions(pid) if r.revision_id == rid), None)
    if result is None:
        raise HTTPException(404)
    return result


@router.get("/{pid}/revisions/{rid}", response_model=PeerReviewRevision)
def revision(request: Request, pid: str, rid: str):
    return get_revision(request.app.state, pid, rid)


@router.get("/{pid}/revisions/{rid}/pdf")
def revision_pdf(request: Request, pid: str, rid: str):
    state = request.app.state
    get_revision(state, pid, rid)
    return FileResponse(state.api.store.projects_dir / pid / "peer-review-revisions" / f"{rid}.pdf", media_type="application/pdf")


@router.patch("/{pid}/revisions/{rid}", response_model=PeerReviewRevision)
def edit_revision(request: Request, pid: str, rid: str, body: RevisionUpdate):
    state = request.app.state
    require_project(state.api, pid)
    with state.locks.hold(pid):
        revision = get_revision(state, pid, rid)
        updated = revision.model_copy(update=body.model_dump(exclude_none=True))
        known = set(revision.resolved_issue_ids + revision.remaining_issue_ids)
        resolved, remaining = set(updated.resolved_issue_ids), set(updated.remaining_issue_ids)
        if (resolved & remaining or resolved | remaining != known
                or len(resolved) != len(updated.resolved_issue_ids)
                or len(remaining) != len(updated.remaining_issue_ids)):
            raise HTTPException(422, "问题匹配必须完整且不能重复，不允许新增未知问题 ID。")
        if body.resolved_issue_ids is not None or body.remaining_issue_ids is not None:
            job = next((j for j in state.api.store.list_peer_review_revision_jobs(pid)
                        if j.revision_id == rid), None)
            if job is None:
                raise HTTPException(409, "旧修改稿缺少基准快照，只能确认现有匹配。")
            _, baseline = state.api.store.load_peer_review_revision_input(pid, job.job_id)
            concerns = [*baseline.major_concerns, *baseline.minor_concerns]
            titles = {c.issue_id: c.title for c in concerns if c.issue_id}
            if not known <= titles.keys():
                raise HTTPException(409, "基准问题不完整，无法修改匹配。")
            # Legacy concerns without IDs retain their original grouping.
            named_titles = set(titles.values())
            updated = updated.model_copy(update={
                "resolved_concerns": sorted([titles[i] for i in updated.resolved_issue_ids] +
                    [t for t in revision.resolved_concerns if t not in named_titles]),
                "remaining_concerns": sorted([titles[i] for i in updated.remaining_issue_ids] +
                    [t for t in revision.remaining_concerns if t not in named_titles]),
            })
        state.api.store.update_peer_review_revision(pid, updated)
        return updated


@router.post("/{pid}/revision-jobs/{job_id}/retry", response_model=PeerReviewRevisionJob, status_code=202)
def retry_revision(request: Request, pid: str, job_id: str):
    state = request.app.state
    require_project(state.api, pid)
    require_model(state.api.settings)
    with state.locks.hold(pid):
        previous = state.api.store.load_peer_review_revision_job(pid, job_id)
        if previous.status not in {"FAILED", "INTERRUPTED"}:
            raise HTTPException(409, "只有失败或中断的复审可以重试。")
        if any(j.job_id != job_id and j.created_at >= previous.created_at and j.status in {"QUEUED", "RUNNING", "SUCCEEDED"}
               for j in state.api.store.list_peer_review_revision_jobs(pid)):
            raise HTTPException(409, "已有更新的修改稿任务。")
        data, baseline = state.api.store.load_peer_review_revision_input(pid, job_id)
        job = state.api.store.create_peer_review_revision_job(pid, pdf_bytes=data,
            original_filename=previous.original_filename, runtime=previous.runtime, baseline=baseline)
        state.revision_manager.submit(pid, job.job_id, state.api.settings)
        return job
