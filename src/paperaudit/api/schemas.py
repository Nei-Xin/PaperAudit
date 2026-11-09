from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from paperaudit.models import (
    AuditJob, AuditRun, EvidenceAnchor, JointAnswer, LearningJob, PaperAnswer,
    PeerReviewJob, PeerReviewReport, PeerReviewRevision, PeerReviewRevisionJob,
)
from paperaudit.storage import AuditRecordMetadata


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class SettingsView(BaseModel):
    api_base: str
    model: str
    reasoning_effort: str
    retrieval_top_k: int
    judge_batch_size: int
    deep_audit: bool
    configured: bool


class SettingsUpdate(Input):
    api_base: str = Field(max_length=2048)
    model: str = Field(max_length=200)
    api_key: str | None = Field(default=None, max_length=4096)
    reasoning_effort: Literal["no_think", "low", "medium", "high"] = "no_think"
    retrieval_top_k: int = Field(default=5, ge=1, le=50)
    judge_batch_size: int = Field(default=6, ge=1, le=50)
    deep_audit: bool = False


class ProjectSummary(BaseModel):
    project_id: str
    title: str
    original_filename: str
    created_at: str
    updated_at: str
    has_code: bool
    has_learning_report: bool
    has_peer_review: bool
    has_audit: bool


class PageSize(BaseModel):
    width: float
    height: float


class ProjectDetail(ProjectSummary):
    page_count: int
    pages: list[PageSize]
    suggested_pages: list[int]


class ProjectCreated(BaseModel):
    project: ProjectSummary
    job: LearningJob | None


class Conversation(BaseModel):
    conversation_id: str
    title: str
    created_at: str
    updated_at: str
    paper_history: list[PaperAnswer]
    joint_history: list[JointAnswer]


class Conversations(BaseModel):
    active_conversation_id: str
    conversations: list[Conversation]


class Question(Input):
    question: str = Field(min_length=1, max_length=1000)
    conversation_id: str | None = None
    new_conversation: bool = False
    selected_text: str | None = Field(default=None, max_length=2000)
    selected_chunk_ids: list[str] = Field(default_factory=list, max_length=100)


class ProjectJobs(BaseModel):
    audit: list[AuditJob]
    learning: list[LearningJob]
    review: list[PeerReviewJob]
    revision: list[PeerReviewRevisionJob]


class AuditDetail(BaseModel):
    record: AuditRecordMetadata
    run: AuditRun
    anchors: dict[str, EvidenceAnchor]


class ProgressItem(BaseModel):
    key: str
    done: bool
    updated_at: str | None = None


class ReviewProgress(BaseModel):
    schema_version: int = 1
    review_generated_at: str | None = None
    items: list[ProgressItem] = Field(default_factory=list)


class ReviewPayload(BaseModel):
    report: PeerReviewReport
    progress: ReviewProgress
    revisions: list[PeerReviewRevision]
