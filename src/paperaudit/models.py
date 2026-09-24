from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ClaimCategory(str, Enum):
    RESEARCH_QUESTION = "research_question"
    CONTRIBUTION = "contribution"
    METHOD = "method"
    DATASET_SETUP = "dataset_setup"
    RESULTS = "results"
    LIMITATIONS = "limitations"
    OTHER = "other"


class AutoLabel(str, Enum):
    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    NO_SUPPORT_FOUND = "NO_SUPPORT_FOUND"
    ABSTAIN = "ABSTAIN"


class ClaimErrorType(str, Enum):
    NUMERIC_OR_METRIC_MISMATCH = "numeric_or_metric_mismatch"
    WRONG_ATTRIBUTION = "wrong_attribution"
    MISSING_CONDITION = "missing_condition"
    OVERGENERALIZATION = "overgeneralization"
    EXTERNAL_HALLUCINATION = "external_hallucination"
    CONTRADICTION = "contradiction"


class EvidenceErrorType(str, Enum):
    EVIDENCE_MISMATCH = "evidence_mismatch"
    FABRICATED_EVIDENCE = "fabricated_evidence"


class PageRect(StrictModel):
    """A PDF-space rectangle in points, relative to its source page."""

    x0: float
    y0: float
    x1: float
    y1: float


class Severity(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TrustGrade(str, Enum):
    TRUSTED = "可信"
    REVIEW = "需复核"
    UNTRUSTED = "不可信"
    UNRATED = "无法评级"


class PaperChunk(StrictModel):
    chunk_id: str
    page: int = Field(ge=1)
    content: str
    content_type: str = "text"
    rects: list[PageRect] = Field(default_factory=list)


class ParsedPaper(StrictModel):
    title: str
    page_count: int = Field(ge=1)
    chunks: list[PaperChunk]
    warnings: list[str] = Field(default_factory=list)


class LearningSectionType(str, Enum):
    RESEARCH_PROBLEM = "research_problem"
    CONTRIBUTIONS = "contributions"
    METHOD = "method"
    EXPERIMENTS = "experiments"
    RESULTS = "results"
    LIMITATIONS = "limitations"
    KEY_TERMS = "key_terms"


class EvidenceAnchor(StrictModel):
    chunk_id: str
    page: int | None = Field(default=None, ge=1)
    text: str | None = None
    quote: str | None = None
    locator: str | None = None
    context_text: str | None = None
    rects: list[PageRect] = Field(default_factory=list)


class ExplanationPoint(StrictModel):
    title: str
    explanation: str
    key_point: bool = False
    evidence: list[EvidenceAnchor] = Field(default_factory=list)


class ReportSection(StrictModel):
    section_type: LearningSectionType
    title: str
    overview: str
    points: list[ExplanationPoint] = Field(default_factory=list)


class LearningReport(StrictModel):
    paper_title: str
    one_sentence_summary: str
    sections: list[ReportSection]
    suggested_pages: list[int] = Field(default_factory=list)


class ReviewDecision(str, Enum):
    STRONG_ACCEPT = "STRONG_ACCEPT"
    WEAK_ACCEPT = "WEAK_ACCEPT"
    BORDERLINE = "BORDERLINE"
    WEAK_REJECT = "WEAK_REJECT"
    STRONG_REJECT = "STRONG_REJECT"

    # Compatibility aliases for callers that used the former three-way scale.
    ACCEPT = "WEAK_ACCEPT"
    REJECT = "WEAK_REJECT"


class PeerReviewVenue(str, Enum):
    GENERAL = "general_ai_ml"
    IJCAI = "ijcai"
    NEURIPS = "neurips"
    ICLR = "iclr"
    AAAI = "aaai"
    CUSTOM = "custom"


class ReviewSeverity(str, Enum):
    MAJOR = "major"
    MINOR = "minor"


class IssueSeverity(str, Enum):
    """Product-facing issue priority, independent from the legacy major/minor label."""

    FATAL = "P0"
    MAJOR = "P1"
    MINOR = "P2"
    EDITORIAL = "P3"


class IssueCategory(str, Enum):
    CORRECTNESS = "correctness"
    EVIDENCE = "evidence"
    EVALUATION = "evaluation"
    NOVELTY = "novelty"
    REPRODUCIBILITY = "reproducibility"
    ETHICS = "ethics"
    CLARITY = "clarity"
    OTHER = "other"


class IssueStatus(str, Enum):
    OPEN = "open"
    AUTHOR_REPLIED = "author_replied"
    PARTIAL = "partially_resolved"
    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"
    NEEDS_REVIEW = "needs_manual_review"
    IGNORED = "ignored"


class IssueSupportType(str, Enum):
    """How a review issue relates to the paper evidence."""

    FACT = "fact"
    INFERENCE = "inference"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class HumanReviewDecision(str, Enum):
    """Human disposition recorded independently from the AI assessment."""

    UNREVIEWED = "unreviewed"
    CONFIRMED = "confirmed"
    PARTIAL = "partial"
    FALSE_POSITIVE = "false_positive"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class RebuttalResolution(str, Enum):
    OPEN = "open"
    RESOLVED = "resolved"
    PARTIAL = "partial"
    UNRESOLVED = "unresolved"


class ReviewDimension(StrictModel):
    name: str
    score: int = Field(ge=1, le=5)
    rationale: str
    confidence: int = Field(default=3, ge=1, le=5)
    evidence: list[EvidenceAnchor] = Field(default_factory=list)


class ReviewConcern(StrictModel):
    issue_id: str = ""
    category: IssueCategory = IssueCategory.OTHER
    severity_level: IssueSeverity | None = None
    status: IssueStatus = IssueStatus.OPEN
    confidence: int = Field(default=3, ge=1, le=5)
    support_type: IssueSupportType = IssueSupportType.INFERENCE
    ai_severity_level: IssueSeverity | None = None
    ai_category: IssueCategory | None = None
    human_reviewed: bool = False
    human_note: str = ""
    human_decision: HumanReviewDecision = HumanReviewDecision.UNREVIEWED
    title: str
    # Kept for compatibility with older prompts; the product-facing
    # ``severity_level`` is authoritative when the legacy field is omitted.
    severity: ReviewSeverity = ReviewSeverity.MINOR
    description: str
    why_it_matters: str
    suggestion: str
    evidence: list[EvidenceAnchor] = Field(default_factory=list)

    @model_validator(mode="after")
    def _set_legacy_severity_level(self) -> "ReviewConcern":
        if self.severity_level is None:
            self.severity_level = (
                IssueSeverity.MAJOR if self.severity == ReviewSeverity.MAJOR else IssueSeverity.MINOR
            )
        if self.ai_severity_level is None:
            self.ai_severity_level = self.severity_level
        if self.ai_category is None:
            self.ai_category = self.category
        if self.severity_level in {IssueSeverity.FATAL, IssueSeverity.MAJOR}:
            self.severity = ReviewSeverity.MAJOR
        elif self.severity_level in {IssueSeverity.MINOR, IssueSeverity.EDITORIAL}:
            self.severity = ReviewSeverity.MINOR
        return self


class RebuttalItem(StrictModel):
    issue_id: str = ""
    concern_title: str
    response: str = ""
    resolution: RebuttalResolution = RebuttalResolution.OPEN
    assessment: str = ""


class RebuttalAssessmentDraft(StrictModel):
    resolution: RebuttalResolution
    assessment: str


class RelatedWorkReference(StrictModel):
    """A user-supplied related-work record; URLs are metadata, not fetched instructions."""

    citation: str
    year: int | None = Field(default=None, ge=1900, le=2100)
    url: str = ""
    distinction: str = ""


class RelatedWorkComparison(StrictModel):
    references: list[RelatedWorkReference] = Field(default_factory=list)
    assessment: str = ""
    distinctions: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    confidence: int = Field(default=1, ge=1, le=5)
    warning: str = ""


class PeerReviewReport(StrictModel):
    paper_title: str
    venue: PeerReviewVenue = PeerReviewVenue.GENERAL
    rubric_version: str = "general_ai_ml@1.0"
    rubric_updated_at: str = ""
    rubric_change_note: str = ""
    decision: ReviewDecision
    overall_score: float = Field(ge=1, le=10)
    # The model's suggested score is retained for auditability; ``overall_score``
    # is the deterministic system result calculated from the six dimensions.
    model_raw_score: float | None = Field(default=None, ge=1, le=10)
    rubric_weights: dict[str, float] = Field(default_factory=dict)
    score_breakdown: dict[str, float] = Field(default_factory=dict)
    score_calculation_version: str = "weighted-v1"
    confidence: int = Field(default=3, ge=1, le=5)
    summary: str
    core_contributions: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    major_concerns: list[ReviewConcern] = Field(default_factory=list)
    minor_concerns: list[ReviewConcern] = Field(default_factory=list)
    questions_for_authors: list[str] = Field(default_factory=list)
    dimensions: list[ReviewDimension] = Field(default_factory=list)
    decision_rationale: str
    why_not_adjacent: str = ""
    acceptance_blockers: list[str] = Field(default_factory=list)
    fatal_flaws: list[str] = Field(default_factory=list)
    confidence_rationale: str = ""
    review_limitations: list[str] = Field(default_factory=list)
    required_changes: list[str] = Field(default_factory=list)
    suggested_changes: list[str] = Field(default_factory=list)
    top_priorities: list[str] = Field(default_factory=list)
    rebuttals: list[RebuttalItem] = Field(default_factory=list)
    post_rebuttal_decision: ReviewDecision | None = None
    post_rebuttal_score: float | None = Field(default=None, ge=1, le=10)
    rebuttal_summary: str = ""
    parse_warnings: list[str] = Field(default_factory=list)
    related_work_comparison: RelatedWorkComparison | None = None
    run_id: str = ""
    generated_at: str = ""
    model_name: str = ""
    reasoning_effort: str = ""
    prompt_version: str = "peer-review-v5"
    elapsed_seconds: float | None = Field(default=None, ge=0)


class RevisionDiff(StrictModel):
    added_chunks: int = Field(default=0, ge=0)
    removed_chunks: int = Field(default=0, ge=0)
    changed_chunks: int = Field(default=0, ge=0)
    added_samples: list[str] = Field(default_factory=list)
    removed_samples: list[str] = Field(default_factory=list)
    changed_samples: list[str] = Field(default_factory=list)
    summary: str = ""


class PeerReviewRevision(StrictModel):
    revision_id: str
    created_at: str
    original_filename: str
    paper_title: str
    page_count: int = Field(ge=1)
    diff: RevisionDiff
    report: PeerReviewReport
    resolved_concerns: list[str] = Field(default_factory=list)
    remaining_concerns: list[str] = Field(default_factory=list)
    resolved_issue_ids: list[str] = Field(default_factory=list)
    remaining_issue_ids: list[str] = Field(default_factory=list)
    new_concerns: list[str] = Field(default_factory=list)
    ambiguous_matches: list[str] = Field(default_factory=list)
    match_confirmed: bool = False


class QuestionQuery(StrictModel):
    query_en: str
    entities: list[str] = Field(default_factory=list)
    numbers: list[str] = Field(default_factory=list)


class AnswerStatus(str, Enum):
    ANSWERED = "ANSWERED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class AnswerSupportType(str, Enum):
    DIRECT = "DIRECT"
    INFERENCE = "INFERENCE"


class AnswerEvidenceDraft(StrictModel):
    chunk_id: str
    quote: str


class AnswerConclusionDraft(StrictModel):
    text: str
    support_type: AnswerSupportType
    evidence: list[AnswerEvidenceDraft] = Field(default_factory=list)


class AnswerDraft(StrictModel):
    answer: str
    status: AnswerStatus
    citation_chunk_ids: list[str] = Field(default_factory=list)
    conclusions: list[AnswerConclusionDraft]


class AnswerConclusion(StrictModel):
    text: str
    support_type: AnswerSupportType
    citations: list[EvidenceAnchor] = Field(default_factory=list)


class PaperAnswer(StrictModel):
    question: str
    answer: str
    status: AnswerStatus
    citations: list[EvidenceAnchor] = Field(default_factory=list)
    conclusions: list[AnswerConclusion] = Field(default_factory=list)


class CodeFile(StrictModel):
    path: str
    language: str
    content: str
    line_count: int = Field(ge=1)


class CodeChunk(StrictModel):
    chunk_id: str
    path: str
    language: str
    symbol: str | None = None
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    content: str


class ParsedCodebase(StrictModel):
    name: str
    files: list[CodeFile]
    chunks: list[CodeChunk]
    warnings: list[str] = Field(default_factory=list)
    index_version: int = 1


class CodeCandidate(StrictModel):
    chunk_id: str
    path: str
    language: str
    symbol: str | None = None
    start_line: int
    end_line: int
    text: str
    score: float


class CodeCitation(StrictModel):
    chunk_id: str
    path: str
    start_line: int
    end_line: int
    symbol: str | None = None
    text: str


class CodeSelection(StrictModel):
    path: str
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    text: str = Field(max_length=8_000)
    context_text: str = Field(max_length=12_000)


class AnswerScope(str, Enum):
    AUTO = "auto"
    PAPER = "paper"
    CODE = "code"
    JOINT = "joint"


class PaperCodeRelation(str, Enum):
    IMPLEMENTS = "IMPLEMENTS"
    CONFIGURES = "CONFIGURES"
    EVALUATES = "EVALUATES"
    LOADS_DATA = "LOADS_DATA"
    DOCUMENTS = "DOCUMENTS"
    PARTIAL_MATCH = "PARTIAL_MATCH"
    NOT_LOCATED = "NOT_LOCATED"


class JointQuery(StrictModel):
    paper_query_en: str
    code_query_en: str
    entities: list[str] = Field(default_factory=list)


class CodeAnswerDraft(StrictModel):
    answer: str
    status: AnswerStatus
    citation_chunk_ids: list[str] = Field(default_factory=list)


class JointAnswerDraft(StrictModel):
    answer: str
    status: AnswerStatus
    paper_citation_chunk_ids: list[str] = Field(default_factory=list)
    code_citation_chunk_ids: list[str] = Field(default_factory=list)
    relation: PaperCodeRelation | None = None


class JointAnswer(StrictModel):
    question: str
    answer: str
    scope: AnswerScope
    status: AnswerStatus
    selected_code: CodeSelection | None = None
    paper_citations: list[EvidenceAnchor] = Field(default_factory=list)
    code_citations: list[CodeCitation] = Field(default_factory=list)
    relation: PaperCodeRelation | None = None


class AtomicClaim(StrictModel):
    claim_id: str
    text: str
    category: ClaimCategory
    key_claim: bool = False
    query_en: str
    entities: list[str] = Field(default_factory=list)
    numbers: list[str] = Field(default_factory=list)
    metric: str | None = None
    dataset: str | None = None
    provided_evidence: str | None = None
    report_location: str | None = None
    source_id: str | None = None
    source_quote: str | None = None


class SkippedReportSource(StrictModel):
    source_id: str
    text: str
    report_location: str
    reason: Literal["heading", "opinion", "out_of_scope", "non_claim"]


class ClaimExtraction(StrictModel):
    claims: list[AtomicClaim]
    source_count: int = 0
    skipped_sources: list[SkippedReportSource] = Field(default_factory=list)


class EvidenceCandidate(StrictModel):
    evidence_id: str
    chunk_id: str
    page: int
    text: str
    score: float


class ClaimJudgment(StrictModel):
    claim_id: str
    label: AutoLabel
    evidence_ids: list[str] = Field(default_factory=list)
    explanation: str
    claim_error_type: ClaimErrorType | None = None
    evidence_error_type: EvidenceErrorType | None = None
    severity: Severity = Severity.NONE
    suggestion: str | None = None


class JudgmentBatch(StrictModel):
    judgments: list[ClaimJudgment]


class EvidenceReview(StrictModel):
    evidence_sufficient: bool
    judgment: ClaimJudgment

    @model_validator(mode="after")
    def require_evidence_for_sufficient_review(self) -> "EvidenceReview":
        """A positive supplementary review must point to at least one passage.

        The audit service still validates each ID against the candidate set. This
        model check catches the earlier failure mode where a review claimed the
        evidence was sufficient while returning an empty evidence list.
        """
        if self.evidence_sufficient and not self.judgment.evidence_ids:
            raise ValueError(
                "证据充分的补查裁决必须返回至少一个 evidence_id。"
            )
        return self


class CitationQuote(StrictModel):
    evidence_id: str
    quote: str = Field(min_length=1)


class CitationAspect(StrictModel):
    aspect: str = Field(min_length=1)
    citations: list[CitationQuote] = Field(min_length=1)
    reasoning: str = Field(min_length=1)


class CitationReview(StrictModel):
    claim_id: str
    complete: bool
    evidence_ids: list[str]
    aspects: list[CitationAspect]
    missing_aspects: list[str]
    explanation: str


class ClaimAudit(StrictModel):
    claim: AtomicClaim
    candidates: list[EvidenceCandidate]
    judgment: ClaimJudgment
    citation_review: CitationReview | None = None
    citation_review_before_repair: CitationReview | None = None
    judgment_before_citation_review: ClaimJudgment | None = None


class DimensionScores(StrictModel):
    factual_support: float | None = None
    evidence_correctness: float | None = None
    evidence_completeness: float | None = None
    numeric_consistency: float | None = None
    content_coverage: float | None = None
    conclusion_boundary: float | None = None


class AuditSummary(StrictModel):
    grade: TrustGrade
    total_score: float | None
    audit_coverage: float
    evidence_discovery_rate: float
    dimensions: DimensionScores
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    review_count: int = 0


class AuditRun(StrictModel):
    paper_title: str
    page_count: int
    mode: str
    scope: list[ClaimCategory]
    report_text: str
    audits: list[ClaimAudit]
    summary: AuditSummary
    parse_warnings: list[str] = Field(default_factory=list)
    source_count: int = 0
    skipped_sources: list[SkippedReportSource] = Field(default_factory=list)


class AuditJobStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    INTERRUPTED = "INTERRUPTED"


class AuditRuntimeSnapshot(StrictModel):
    """Non-secret runtime settings retained for reproducibility."""

    model: str
    reasoning_effort: str
    retrieval_top_k: int = Field(ge=1)
    judge_batch_size: int = Field(ge=1)


class AuditJob(StrictModel):
    """Persisted input and status for one background audit."""

    schema_version: int = 1
    job_id: str
    project_id: str
    created_at: str
    started_at: str | None = None
    completed_at: str | None = None
    source_type: str
    source_label: str
    source_filename: str | None = None
    report_hash: str
    report_text: str
    scope: list[ClaimCategory]
    audit_mode: str
    status: AuditJobStatus = AuditJobStatus.QUEUED
    progress: float = Field(default=0.0, ge=0.0, le=1.0)
    stage: str = "等待执行"
    audit_id: str | None = None
    error: str | None = None
    runtime: AuditRuntimeSnapshot


class LearningJob(StrictModel):
    """Persisted status for generating a learning report in the background."""

    schema_version: int = 1
    job_id: str
    project_id: str
    created_at: str
    started_at: str | None = None
    completed_at: str | None = None
    status: AuditJobStatus = AuditJobStatus.QUEUED
    progress: float = Field(default=0.0, ge=0.0, le=1.0)
    stage: str = "等待生成"
    error: str | None = None
    runtime: AuditRuntimeSnapshot


class PeerReviewJob(StrictModel):
    """Persisted status for generating a simulated peer review."""

    schema_version: int = 2
    job_id: str
    project_id: str
    created_at: str
    started_at: str | None = None
    completed_at: str | None = None
    status: AuditJobStatus = AuditJobStatus.QUEUED
    progress: float = Field(default=0.0, ge=0.0, le=1.0)
    stage: str = "等待评审"
    error: str | None = None
    runtime: AuditRuntimeSnapshot
    venue: PeerReviewVenue = PeerReviewVenue.GENERAL
    rubric_version: str = "general_ai_ml@1.0"
    rubric_weights: dict[str, float] = Field(default_factory=dict)


class PeerReviewRevisionJob(StrictModel):
    """Persisted status for reviewing one uploaded paper revision."""

    schema_version: int = 1
    job_id: str
    project_id: str
    created_at: str
    started_at: str | None = None
    completed_at: str | None = None
    original_filename: str
    pdf_hash: str
    status: AuditJobStatus = AuditJobStatus.QUEUED
    progress: float = Field(default=0.0, ge=0.0, le=1.0)
    stage: str = "等待复审"
    error: str | None = None
    runtime: AuditRuntimeSnapshot
    venue: PeerReviewVenue = PeerReviewVenue.GENERAL
    rubric_version: str = "general_ai_ml@1.0"
    rubric_weights: dict[str, float] = Field(default_factory=dict)
    revision_id: str | None = None
