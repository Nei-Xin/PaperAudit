import { useState } from "react";
import { Maximize2 } from "lucide-react";
import clsx from "clsx";
import type { ClaimAudit, EvidenceAnchor, EvidenceCandidate } from "@/api/types";
import {
  CATEGORY_LABELS, CLAIM_ERROR_NAMES, EVIDENCE_ERROR_NAMES, LABEL_NAMES, LABEL_TONE, SEVERITY_NAMES, anchorLabel,
} from "@/lib/labels";
import { PdfCrop, PdfDocument } from "@/components/PdfCrop";
import { detailEvidence, normalizeEvidence, splitClaimNumbers } from "./auditView";

function Section({ label, aside, children }: { label: string; aside?: React.ReactNode; children: React.ReactNode }) {
  return (
    <section className="flex flex-col gap-2.5">
      <div className="flex items-baseline gap-2">
        <h3 className="label">{label}</h3>
        {aside}
      </div>
      {children}
    </section>
  );
}

type View = "page" | "text";

/** One piece of evidence: a magnified crop of the page, or its extracted text. */
function EvidenceItem({
  item, index, anchor, pageSize, active, defaultView, onOpenPage, fillHeight,
}: {
  fillHeight?: number;
  item: EvidenceCandidate;
  index: number;
  anchor: EvidenceAnchor | undefined;
  pageSize: { width: number; height: number } | undefined;
  active: boolean;
  defaultView: View;
  onOpenPage: () => void;
}) {
  const canCrop = Boolean(anchor?.page && anchor.rects.length && pageSize);
  const [view, setView] = useState<View>(canCrop ? defaultView : "text");
  const [expanded, setExpanded] = useState(false);
  const text = normalizeEvidence(item.text);
  const long = text.length > 320;
  return (
    <li className={clsx("evidence-item flex flex-col gap-2.5 rounded-xl p-3 transition-shadow", active ? "bg-accent-soft/60 shadow-[inset_0_0_0_1px_rgba(30,74,122,.18)]" : "bg-[#FAFAF9] shadow-[inset_0_0_0_1px_#F0EFEC]")}>
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs">
        <span className="inline-flex h-5 items-center rounded-md bg-accent px-1.5 font-semibold text-white">证据 {index + 1}</span>
        <span className="min-w-0 truncate text-ink-3" title={anchor ? anchorLabel(anchor) : undefined}>{anchor ? anchorLabel(anchor) : `第 ${item.page} 页`}</span>
        <span className="ml-auto flex items-center gap-1">
          {canCrop && (
            <span className="inline-flex rounded-md bg-card p-0.5 shadow-card" role="group" aria-label="显示方式">
              {([["page", "原文"], ["text", "文字"]] as [View, string][]).map(([key, text]) => (
                <button
                  key={key}
                  type="button"
                  aria-pressed={view === key}
                  onClick={() => setView(key)}
                  className={clsx("h-6 rounded px-2 text-xs", view === key ? "bg-ink text-white" : "text-ink-3 hover:text-ink")}
                >
                  {text}
                </button>
              ))}
            </span>
          )}
          <button
            type="button"
            className="inline-flex h-7 items-center gap-1 rounded-md px-2 font-medium text-accent hover:bg-card disabled:text-ink-4"
            onClick={onOpenPage}
            disabled={!anchor?.page}
          >
            <Maximize2 className="h-3.5 w-3.5" aria-hidden /> 整页
          </button>
        </span>
      </div>
      {view === "page" && canCrop && anchor?.page ? (
        <PdfCrop
          page={anchor.page}
          pageSize={pageSize}
          rects={anchor.rects}
          // A table/figure caption is often what gets cited: show the body next to it.
          contextPt={/table|fig|表|图/i.test(anchor.locator ?? "") ? 120 : undefined}
          fillHeight={fillHeight}
          label={`证据 ${index + 1} 原文，${anchorLabel(anchor)}`}
        />
      ) : (
        <div className="flex flex-col items-start gap-1 px-1">
          <p className={clsx("break-words font-serif text-[15px] leading-[1.75] text-ink", long && !expanded && "line-clamp-4")}>{text}</p>
          {long && (
            <button type="button" className="text-xs font-medium text-accent hover:underline" onClick={() => setExpanded((value) => !value)} aria-expanded={expanded}>
              {expanded ? "收起" : "展开全文"}
            </button>
          )}
        </div>
      )}
    </li>
  );
}

export const isCandidateLabel = (audit: ClaimAudit) =>
  audit.judgment.label === "NO_SUPPORT_FOUND" || audit.judgment.label === "ABSTAIN";

export function evidenceHint(audit: ClaimAudit): string {
  const count = detailEvidence(audit).length;
  return `${count} 处${count && !isCandidateLabel(audit) ? " · 黄色为引用位置，片段可上下滚动" : ""}`;
}

/** The evidence list for one claim: page crops (or text), with a full-page action. */
export function ClaimEvidence({
  projectId, audit, anchors, pageSizes, activeChunk, onOpenEvidence, availableHeight,
}: {
  /** Height of the evidence column (split layout): crops share it instead of leaving it empty. */
  availableHeight?: number;
  projectId: string;
  audit: ClaimAudit;
  anchors: Record<string, EvidenceAnchor>;
  pageSizes: { width: number; height: number }[];
  activeChunk: string | undefined;
  onOpenEvidence: (chunkId: string) => void;
}) {
  const evidence = detailEvidence(audit);
  const [showAll, setShowAll] = useState(false);
  const COLLAPSED = 3;
  const shown = showAll ? evidence : evidence.slice(0, COLLAPSED);
  const candidates = isCandidateLabel(audit);
  const defaultView = (index: number): View => (candidates || index >= 3 ? "text" : "page");
  const crops = shown.filter((_, index) => defaultView(index) === "page").length;
  // Per-crop height: the column minus each card's header/padding and the gaps, shared evenly.
  const fillHeight = availableHeight && crops
    ? Math.min(1600, Math.max(320, Math.floor((availableHeight - crops * 70 - (shown.length - 1) * 12 - (evidence.length > COLLAPSED ? 48 : 0) - (shown.length - crops) * 160) / crops)))
    : undefined;
  if (!evidence.length) {
    return <p className="rounded-xl bg-[#FAFAF9] px-4 py-3 text-sm text-ink-4">当前没有已验证的原文证据。</p>;
  }
  return (
    <PdfDocument projectId={projectId}>
      <ol className="flex flex-col gap-3">
        {shown.map((item, index) => {
          const anchor = anchors[item.chunk_id];
          return (
            <EvidenceItem
              key={`${audit.claim.claim_id}-${item.evidence_id}`}
              item={item}
              index={index}
              anchor={anchor}
              pageSize={anchor?.page ? pageSizes[anchor.page - 1] : undefined}
              active={item.chunk_id === activeChunk}
              // Candidates were not judged as support: show text first, the page on demand.
              defaultView={defaultView(index)}
              fillHeight={fillHeight}
              onOpenPage={() => onOpenEvidence(item.chunk_id)}
            />
          );
        })}
      </ol>
      {evidence.length > COLLAPSED && (
        <button type="button" className="btn-ghost mt-2 self-start" onClick={() => setShowAll((value) => !value)} aria-expanded={showAll}>
          {showAll ? "收起" : `显示其余 ${evidence.length - COLLAPSED} 处`}
        </button>
      )}
    </PdfDocument>
  );
}

export function ClaimDetail({
  projectId, audit, anchors, pageSizes, activeChunk, onOpenEvidence, split = false,
}: {
  /** Evidence is rendered in its own column by the page (wide screens). */
  split?: boolean;
  projectId: string;
  audit: ClaimAudit;
  anchors: Record<string, EvidenceAnchor>;
  pageSizes: { width: number; height: number }[];
  activeChunk: string | undefined;
  onOpenEvidence: (chunkId: string) => void;
}) {
  const { claim, judgment, citation_review: review } = audit;
  const candidates = isCandidateLabel(audit);
  const tone = LABEL_TONE[judgment.label];
  const severityTone = judgment.severity === "critical" || judgment.severity === "high" ? "bg-bad-soft text-bad" : "bg-line-soft text-ink-2";
  const errors = [
    judgment.claim_error_type && `论断：${CLAIM_ERROR_NAMES[judgment.claim_error_type]}`,
    judgment.evidence_error_type && `证据：${EVIDENCE_ERROR_NAMES[judgment.evidence_error_type]}`,
  ].filter(Boolean) as string[];

  return (
    <article className={clsx("claim-detail mx-auto flex w-full min-w-0 flex-col gap-7 break-words px-4 py-5", split ? "max-w-[780px]" : "max-w-[860px]")}>
      <header className="flex flex-col gap-3">
        <div className="flex flex-wrap items-center gap-2 text-xs text-ink-4">
          <span>{claim.claim_id} · {CATEGORY_LABELS[claim.category]}{claim.report_location ? ` · ${claim.report_location}` : ""}</span>
          <span className="ml-auto flex flex-wrap gap-1.5">
            <span className={clsx("inline-flex h-6 items-center gap-1.5 rounded-md px-2 text-xs font-semibold", tone.chip)}>
              <span className={clsx("h-1.5 w-1.5 rounded-full", tone.dot)} aria-hidden />{LABEL_NAMES[judgment.label]}
            </span>
            <span className={clsx("inline-flex h-6 items-center rounded-md px-2 text-xs font-semibold", severityTone)}>
              {SEVERITY_NAMES[judgment.severity]}
            </span>
          </span>
        </div>
        <h2 className="text-[20px] font-semibold leading-[1.6] tracking-[-0.005em]">
          {splitClaimNumbers(claim.text, claim.numbers).map((part, i) =>
            part.number ? <mark key={i} className="rounded-[3px] bg-yellow-200/70 px-0.5 text-inherit">{part.text}</mark> : <span key={i}>{part.text}</span>,
          )}
        </h2>
      </header>

      <Section label="判断说明">
        <p className="whitespace-pre-line text-[15px] leading-[1.8] text-ink-2">{judgment.explanation}</p>
        {errors.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {errors.map((text) => <span key={text} className="rounded-md bg-line-soft px-2 py-0.5 text-xs text-ink-3">{text}</span>)}
          </div>
        )}
      </Section>

      {!split && (
        <Section label={candidates ? "候选原文片段" : "原文依据"} aside={<span className="text-xs text-ink-4">{evidenceHint(audit)}</span>}>
          <ClaimEvidence projectId={projectId} audit={audit} anchors={anchors} pageSizes={pageSizes} activeChunk={activeChunk} onOpenEvidence={onOpenEvidence} />
        </Section>
      )}

      {judgment.suggestion && (
        <Section label="修改建议">
          <p className="rounded-xl bg-accent-soft px-4 py-3 text-[15px] leading-[1.75]">{judgment.suggestion}</p>
        </Section>
      )}

      {review && (
        <Section label="引用完整性复核">
          <p className="text-sm leading-7 text-ink-2">
            <strong className={review.complete ? "text-ok-text" : "text-warn-text"}>{review.complete ? "通过" : "未通过，需人工核对"}</strong>
            {" · "}{review.explanation}
          </p>
          {review.aspects.length > 0 && (
            <ul className="flex flex-col gap-3 border-l-2 border-line-soft pl-4">
              {review.aspects.map((aspect) => (
                <li key={aspect.aspect} className="text-sm leading-7">
                  <strong className="font-semibold">{aspect.aspect}：</strong>
                  <span className="text-ink-2">{aspect.reasoning}</span>
                  {aspect.citations.map((citation) => (
                    <span key={citation.evidence_id + citation.quote} className="mt-1 block break-words font-serif text-[13px] text-ink-3">
                      “{citation.quote}” <span className="font-sans text-xs text-ink-4">{citation.evidence_id}</span>
                    </span>
                  ))}
                </li>
              ))}
            </ul>
          )}
          {review.missing_aspects.length > 0 && (
            <p className="text-sm text-warn-text">缺少：{review.missing_aspects.join("、")}</p>
          )}
        </Section>
      )}

      {audit.investigation ? (
        <p className="rounded-lg bg-page px-3 py-2 text-sm text-ink-3">本条论断启动了深度核验，调查记录随结果保存。</p>
      ) : null}
    </article>
  );
}
