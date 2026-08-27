from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


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


class ClaimExtraction(StrictModel):
    claims: list[AtomicClaim]


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


class ClaimAudit(StrictModel):
    claim: AtomicClaim
    candidates: list[EvidenceCandidate]
    judgment: ClaimJudgment


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
