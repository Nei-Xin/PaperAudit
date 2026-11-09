// Port of src/paperaudit/ui/audit_view.py — keep the two in sync.
import type { AutoLabel, ClaimAudit, ClaimCategory, EvidenceCandidate, Severity } from "@/api/types";

export type StatusFilter = "attention" | "all" | AutoLabel;
export type SortMode = "risk" | "report";

export const normalizeEvidence = (text: string) =>
  text.replace(/(?<=\w)-\s*[\r\n]+\s*(?=\w)/g, "").split(/\s+/).filter(Boolean).join(" ");

export const isAttentionRequired = (audit: ClaimAudit) =>
  !(audit.judgment.label === "SUPPORTED" && audit.judgment.severity === "none");

export function selectedEvidence(audit: ClaimAudit): EvidenceCandidate[] {
  const ids = new Set(audit.judgment.evidence_ids);
  return audit.candidates.filter((candidate) => ids.has(candidate.evidence_id));
}

/** Evidence shown in the detail view (ui/components.py `_detail_evidence`). */
export function detailEvidence(audit: ClaimAudit): EvidenceCandidate[] {
  const selected = selectedEvidence(audit);
  if (audit.judgment.label !== "NO_SUPPORT_FOUND" && audit.judgment.label !== "ABSTAIN") return selected;
  const ids = new Set(selected.map((item) => item.evidence_id));
  return [...selected, ...audit.candidates.filter((item) => !ids.has(item.evidence_id))];
}

export function filterAudits(
  audits: ClaimAudit[],
  { status, category, severity, query }: { status: StatusFilter; category: ClaimCategory | ""; severity: Severity | ""; query: string },
): ClaimAudit[] {
  const q = query.trim().toLowerCase();
  return audits.filter((audit) => {
    if (status === "attention" && !isAttentionRequired(audit)) return false;
    if (status !== "attention" && status !== "all" && audit.judgment.label !== status) return false;
    if (category && audit.claim.category !== category) return false;
    if (severity && audit.judgment.severity !== severity) return false;
    if (!q) return true;
    return (
      audit.claim.claim_id.toLowerCase().includes(q) ||
      audit.claim.text.toLowerCase().includes(q) ||
      audit.judgment.explanation.toLowerCase().includes(q) ||
      (audit.judgment.suggestion ?? "").toLowerCase().includes(q) ||
      audit.candidates.some((candidate) => candidate.text.toLowerCase().includes(q))
    );
  });
}

const SEVERITY_ORDER: Record<Severity, number> = { critical: 0, high: 1, medium: 2, low: 3, none: 4 };

export function sortAudits(audits: ClaimAudit[], mode: SortMode): ClaimAudit[] {
  if (mode === "report") return audits;
  // Array.prototype.sort is stable, matching Python's sorted().
  return [...audits].sort((a, b) => SEVERITY_ORDER[a.judgment.severity] - SEVERITY_ORDER[b.judgment.severity]);
}

export function labelCounts(audits: ClaimAudit[]): Record<AutoLabel, number> {
  const counts: Record<AutoLabel, number> = {
    SUPPORTED: 0, PARTIALLY_SUPPORTED: 0, CONTRADICTED: 0, NO_SUPPORT_FOUND: 0, ABSTAIN: 0,
  };
  for (const audit of audits) counts[audit.judgment.label] += 1;
  return counts;
}

/** Split text so numbers (0.277, 170万, 79.5%) can be highlighted. */
export function splitNumbers(text: string): { text: string; number: boolean }[] {
  const parts: { text: string; number: boolean }[] = [];
  const pattern = /\d+(?:[.,]\d+)*(?:%|万|亿)?/g;
  let last = 0;
  for (const match of text.matchAll(pattern)) {
    const start = match.index ?? 0;
    if (start > last) parts.push({ text: text.slice(last, start), number: false });
    parts.push({ text: match[0], number: true });
    last = start + match[0].length;
  }
  if (last < text.length) parts.push({ text: text.slice(last), number: false });
  return parts;
}
