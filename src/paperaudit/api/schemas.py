from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from paperaudit.models import (
    AuditJob, AuditRun, EvidenceAnchor, JointAnswer, LearningJob, PaperAnswer,
    PeerReviewJob, PeerReviewReport, PeerReviewRevision, PeerReviewRevisionJob,
)
from paperaudit.models import (
    AnswerScope, CodeSelection, PeerReviewVenue, IssueCategory, IssueSeverity,
    IssueStatus, IssueSupportType, HumanReviewDecision, RelatedWorkReference, ReviewDecision,
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
    reasoning_effort: Literal["", "no_think", "low", "medium", "high"] = "no_think"
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
    # Status shown on the home page: latest audit grade and the review decision.
    audit_count: int = 0
    audit_grade: str | None = None
    audit_score: float | None = None
    review_decision: ReviewDecision | None = None


class PageSize(BaseModel):
    width: float
    height: float


class ProjectDetail(ProjectSummary):
    page_count: int
    pages: list[PageSize]
    suggested_pages: list[int]


class ProjectCreated(BaseModel):
    project: ProjectSummary
    job: LearningJob | AuditJob | PeerReviewJob | None


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


class PaperSelection(Input):
    text: str = Field(min_length=1, max_length=2000)
    page: int = Field(ge=1)
    chunk_ids: list[str] = Field(default_factory=list, max_length=100)


class Question(Input):
    question: str = Field(min_length=1, max_length=1000)
    conversation_id: str | None = None
    new_conversation: bool = False
    selection: PaperSelection | None = None
    page_scope: int | None = Field(default=None, ge=1)
    selected_text: str | None = Field(default=None, max_length=2000)
    selected_chunk_ids: list[str] = Field(default_factory=list, max_length=100)


class ProjectJobs(BaseModel):
    audit: list[AuditJob]
    learning: list[LearningJob]
    review: list[PeerReviewJob]
    revision: list[PeerReviewRevisionJob]


class LearningRequest(Input):
    regenerate: bool = False
    privacy_ack: bool = False


class AuditDetail(BaseModel):
    record: AuditRecordMetadata
    run: AuditRun
    anchors: dict[str, EvidenceAnchor]


class ProgressItem(Input):
    key: str
    done: bool
    updated_at: str | None = None


class ReviewProgress(BaseModel):
    schema_version: int = 1
    review_generated_at: str | None = None
    review_run_id: str = ""
    items: list[ProgressItem] = Field(default_factory=list)


class ReviewPayload(BaseModel):
    report: PeerReviewReport
    progress: ReviewProgress
    revisions: list[PeerReviewRevision]


class TitleUpdate(Input):
    title: str = Field(min_length=1, max_length=300)


class ConversationCreate(Input):
    title: str = Field(default="新对话", min_length=1, max_length=100)


class ConversationUpdate(Input):
    title: str | None = Field(default=None, min_length=1, max_length=100)
    activate: bool = False


class CodeQuestion(Input):
    question: str = Field(min_length=1, max_length=1000)
    conversation_id: str | None = None
    new_conversation: bool = False
    scope: AnswerScope = AnswerScope.AUTO
    selection: PaperSelection | None = None
    selected_code: CodeSelection | None = None
    # None uses the server default (PAPERAUDIT_CODE_AGENT).
    investigate: bool | None = None


class ReviewRequest(Input):
    venue: PeerReviewVenue = PeerReviewVenue.GENERAL
    rubric_weights: dict[str, float] = Field(default_factory=dict, max_length=6)
    privacy_ack: bool = False


class ConcernUpdate(Input):
    expected_run_id: str
    status: IssueStatus | None = None
    support_type: IssueSupportType | None = None
    human_reviewed: bool | None = None
    human_decision: HumanReviewDecision | None = None
    human_note: str | None = Field(default=None, max_length=10000)
    severity_level: IssueSeverity | None = None
    category: IssueCategory | None = None


class ProgressUpdate(Input):
    schema_version: Literal[1] = 1
    review_generated_at: str
    review_run_id: str
    items: list[ProgressItem] = Field(max_length=200)


class RelatedWorkRequest(Input):
    references: list[RelatedWorkReference] = Field(min_length=1, max_length=5)
    privacy_ack: bool = False
    expected_run_id: str


class RevisionUpdate(Input):
    match_confirmed: bool | None = None
    resolved_issue_ids: list[str] | None = Field(default=None, max_length=200)
    remaining_issue_ids: list[str] | None = Field(default=None, max_length=200)
