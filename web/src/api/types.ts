// Mirrors src/paperaudit/models.py and the response shapes in
// docs/react-migration.md §4.3. Hand-written until the FastAPI layer exists;
// then replaced by openapi-typescript output (npm run gen:api).

export type ClaimCategory =
  | "research_question" | "contribution" | "method" | "dataset_setup"
  | "results" | "limitations" | "other";
export type AutoLabel = "SUPPORTED" | "PARTIALLY_SUPPORTED" | "CONTRADICTED" | "NO_SUPPORT_FOUND" | "ABSTAIN";
export type Severity = "none" | "low" | "medium" | "high" | "critical";
export type ClaimErrorType =
  | "numeric_or_metric_mismatch" | "wrong_attribution" | "missing_condition"
  | "overgeneralization" | "external_hallucination" | "contradiction";
export type EvidenceErrorType = "evidence_mismatch" | "fabricated_evidence";
export type TrustGrade = "可信" | "需复核" | "不可信" | "无法评级";
export type JobStatus = "QUEUED" | "RUNNING" | "SUCCEEDED" | "FAILED" | "INTERRUPTED";
export type LearningSectionType =
  | "research_problem" | "contributions" | "method" | "experiments"
  | "results" | "limitations" | "key_terms";
export type ReviewDecision = "STRONG_ACCEPT" | "WEAK_ACCEPT" | "BORDERLINE" | "WEAK_REJECT" | "STRONG_REJECT";
export type Venue = "general_ai_ml" | "ijcai" | "neurips" | "iclr" | "aaai" | "custom";
export type IssueSeverity = "P0" | "P1" | "P2" | "P3";
export type IssueCategory =
  | "correctness" | "evidence" | "evaluation" | "novelty"
  | "reproducibility" | "ethics" | "clarity" | "other";
export type IssueStatus =
  | "open" | "author_replied" | "partially_resolved" | "resolved"
  | "unresolved" | "needs_manual_review" | "ignored";

export interface PageRect { x0: number; y0: number; x1: number; y1: number }

export interface EvidenceAnchor {
  chunk_id: string;
  page: number | null;
  text: string | null;
  quote: string | null;
  locator: string | null;
  context_text: string | null;
  rects: PageRect[];
}

export interface Settings {
  api_base: string;
  model: string;
  reasoning_effort: string;
  retrieval_top_k: number;
  judge_batch_size: number;
  deep_audit: boolean;
  configured: boolean;
}

export interface ProjectSummary {
  project_id: string;
  title: string;
  original_filename: string;
  created_at: string;
  updated_at: string;
  has_code: boolean;
  has_learning_report: boolean;
  has_peer_review: boolean;
  has_audit: boolean;
}

export interface ProjectDetail extends ProjectSummary {
  page_count: number;
  /** PyMuPDF page sizes in PDF points; evidence rects use the same space. */
  pages: { width: number; height: number }[];
  suggested_pages: number[];
}

// ── Lecture ──────────────────────────────────────────────
export interface ExplanationPoint {
  title: string;
  explanation: string;
  key_point: boolean;
  evidence: EvidenceAnchor[];
}
export interface ReportSection {
  section_type: LearningSectionType;
  title: string;
  overview: string;
  points: ExplanationPoint[];
}
export interface LearningReport {
  paper_title: string;
  one_sentence_summary: string;
  sections: ReportSection[];
  suggested_pages: number[];
}

// ── Conversations ───────────────────────────────────────
export interface PaperAnswer {
  question: string;
  answer?: string;
  status?: string;
  conclusions?: { text: string; citations?: EvidenceAnchor[] }[];
  citations?: EvidenceAnchor[];
  [key: string]: unknown;
}
export interface Conversation {
  conversation_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  paper_history: PaperAnswer[];
  joint_history: PaperAnswer[];
}
export interface Conversations {
  active_conversation_id: string;
  conversations: Conversation[];
}

// ── Audit ───────────────────────────────────────────────
export interface AtomicClaim {
  claim_id: string;
  text: string;
  category: ClaimCategory;
  key_claim: boolean;
  report_location: string | null;
  source_quote: string | null;
  numbers?: string[];
  [key: string]: unknown;
}
export interface EvidenceCandidate { evidence_id: string; chunk_id: string; page: number; text: string; score: number }
export interface ClaimJudgment {
  claim_id: string;
  label: AutoLabel;
  evidence_ids: string[];
  explanation: string;
  claim_error_type: ClaimErrorType | null;
  evidence_error_type: EvidenceErrorType | null;
  severity: Severity;
  suggestion: string | null;
}
export interface CitationAspect { aspect: string; citations: { evidence_id: string; quote: string }[]; reasoning: string }
export interface CitationReview {
  claim_id: string;
  reviewed_label: "SUPPORTED" | "CONTRADICTED";
  complete: boolean;
  evidence_ids: string[];
  aspects: CitationAspect[];
  missing_aspects: string[];
  explanation: string;
  suggestion_verified: boolean | null;
  suggestion_missing_aspects: string[];
}
export interface ClaimAudit {
  claim: AtomicClaim;
  candidates: EvidenceCandidate[];
  judgment: ClaimJudgment;
  citation_review: CitationReview | null;
  investigation: unknown | null;
  [key: string]: unknown;
}
export interface AuditSummary {
  grade: TrustGrade;
  total_score: number | null;
  audit_coverage: number;
  evidence_discovery_rate: number;
  dimensions: Record<string, number | null>;
  critical_count: number;
  high_count: number;
  medium_count: number;
  review_count: number;
}
export interface AuditRun {
  paper_title: string;
  page_count: number;
  mode: string;
  scope: ClaimCategory[];
  report_text: string;
  audits: ClaimAudit[];
  summary: AuditSummary;
  parse_warnings: string[];
  source_count: number;
  skipped_sources: { report_location: string; reason: string; text: string }[];
  deep_audit: boolean;
}
export interface AuditRecord {
  audit_id: string;
  project_id: string;
  created_at: string;
  source_type: string;
  source_label: string;
  grade: string;
  total_score: number | null;
  audit_coverage: number;
  critical_count: number;
  high_count: number;
  model: string;
}
export interface AuditDetail {
  record: AuditRecord;
  run: AuditRun;
  anchors: Record<string, EvidenceAnchor>;
}

// ── Review ──────────────────────────────────────────────
export interface ReviewDimension { name: string; score: number; rationale: string; confidence: number; evidence: EvidenceAnchor[] }
export interface ReviewConcern {
  issue_id: string;
  category: IssueCategory;
  severity_level: IssueSeverity | null;
  status: IssueStatus;
  confidence: number;
  support_type: string;
  human_reviewed: boolean;
  human_note: string;
  human_decision: string;
  title: string;
  description: string;
  why_it_matters: string;
  suggestion: string;
  evidence: EvidenceAnchor[];
}
export interface PeerReviewReport {
  paper_title: string;
  venue: Venue;
  rubric_version: string;
  rubric_change_note: string;
  decision: ReviewDecision;
  overall_score: number;
  confidence: number;
  summary: string;
  core_contributions: string[];
  strengths: string[];
  major_concerns: ReviewConcern[];
  minor_concerns: ReviewConcern[];
  dimensions: ReviewDimension[];
  decision_rationale: string;
  why_not_adjacent: string;
  acceptance_blockers: string[];
  fatal_flaws: string[];
  confidence_rationale: string;
  review_limitations: string[];
  required_changes: string[];
  suggested_changes: string[];
  top_priorities: string[];
  rubric_weights: Record<string, number>;
  run_id: string;
  generated_at: string;
  model_name: string;
  [key: string]: unknown;
}
export interface ReviewProgress {
  schema_version: number;
  items: { key: string; done: boolean; updated_at?: string }[];
}
export interface ReviewPayload {
  report: PeerReviewReport;
  progress: ReviewProgress;
  revisions: unknown[];
}

// ── Jobs ────────────────────────────────────────────────
export interface Job {
  job_id: string;
  status: JobStatus;
  progress: number;
  stage: string;
  error: string | null;
  source_label?: string;
  audit_id?: string | null;
  original_filename?: string;
}
export interface ProjectJobs { audit: Job[]; learning: Job[]; review: Job[]; revision: Job[] }
