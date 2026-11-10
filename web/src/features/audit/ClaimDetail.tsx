import { useCallback, useRef, useState } from "react";
import { Maximize2 } from "lucide-react";
import clsx from "clsx";
import type { ClaimAudit, EvidenceAnchor } from "@/api/types";
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

export const isCandidateLabel = (audit: ClaimAudit) =>
  audit.judgment.label === "NO_SUPPORT_FOUND" || audit.judgment.label === "ABSTAIN";

/** "Table 4" / "Figure 5" / "§4 …" from an anchor locator, short enough for a tab. */
function shortLocator(anchor: EvidenceAnchor | undefined): string | undefined {
  const locator = anchor?.locator ?? "";
  const named = locator.match(/(Table|Figure|Fig\.|表|图)\s*[\dA-Za-z.]+/i);
  if (named) return named[0].replace(/^Figure/i, "Fig.");
  const section = locator.split("·")[0]?.trim();
  return section ? (section.length > 18 ? `${section.slice(0, 17)}…` : section) : undefined;
}

/**
 * V4 evidence viewer: one piece of evidence at a time, filling its panel.
 * Tabs switch evidence; the crop scrolls over the whole page; "整页" opens the page dialog.
 */
export function EvidenceViewer({
  projectId, audit, anchors, pageSizes, activeChunk, onSelectChunk, onOpenPage, className,
}: {
  projectId: string;
  audit: ClaimAudit;
  anchors: Record<string, EvidenceAnchor>;
  pageSizes: { width: number; height: number }[];
  activeChunk: string | undefined;
  onSelectChunk: (chunkId: string) => void;
  onOpenPage: (chunkId: string) => void;
  className?: string;
}) {
  const evidence = detailEvidence(audit);
  const candidates = isCandidateLabel(audit);
  const index = Math.max(0, evidence.findIndex((item) => item.chunk_id === activeChunk));
  const item = evidence[index];
  const anchor = item ? anchors[item.chunk_id] : undefined;
  const pageSize = anchor?.page ? pageSizes[anchor.page - 1] : undefined;
  const canCrop = Boolean(anchor?.page && anchor.rects.length && pageSize);
  const [preferred, setPreferred] = useState<View>(candidates ? "text" : "page");
  const view: View = canCrop ? preferred : "text";
  const [bodyHeight, setBodyHeight] = useState(0);
  const observer = useRef<ResizeObserver | null>(null);
  // Callback ref: React calls it with null on unmount, which disconnects the observer.
  const bodyRef = useCallback((element: HTMLDivElement | null) => {
    observer.current?.disconnect();
    observer.current = null;
    if (!element) return;
    observer.current = new ResizeObserver(([entry]) => setBodyHeight(Math.floor(entry.contentRect.height)));
    observer.current.observe(element);
  }, []);

  return (
    <section className={clsx("evidence-viewer card flex min-h-0 min-w-0 flex-col overflow-hidden", className)} aria-label="原文依据">
      <div className="flex shrink-0 items-end gap-2 border-b border-line-soft pl-2 pr-2">
        <div className="flex min-w-0 flex-1 gap-0.5 overflow-x-auto" role="tablist" aria-label={candidates ? "候选原文片段" : "证据"}>
          {evidence.length ? evidence.map((entry, i) => {
            const a = anchors[entry.chunk_id];
            const selected = i === index;
            const where = shortLocator(a);
            return (
              <button
                key={entry.evidence_id}
                type="button"
                role="tab"
                aria-selected={selected}
                onClick={() => onSelectChunk(entry.chunk_id)}
                className={clsx(
                  "shrink-0 whitespace-nowrap border-b-2 px-2.5 pb-2 pt-2.5 text-[13px] transition-colors",
                  selected ? "border-accent font-semibold text-ink" : "border-transparent text-ink-3 hover:text-ink",
                )}
              >
                {candidates ? "候选" : "证据"} {i + 1}{where ? ` · ${where}` : ""}
                <span className="ml-1 font-normal text-ink-4">p.{a?.page ?? entry.page}</span>
              </button>
            );
          }) : <span className="px-2.5 pb-2 pt-2.5 text-[13px] font-semibold">原文依据</span>}
        </div>
        {item && (
          <div className="flex shrink-0 items-center gap-1 pb-1.5">
            {canCrop && (
              <span className="inline-flex rounded-md bg-page p-0.5" role="group" aria-label="显示方式">
                {([["page", "原文"], ["text", "文字"]] as [View, string][]).map(([key, text]) => (
                  <button key={key} type="button" aria-pressed={view === key} onClick={() => setPreferred(key)}
                    className={clsx("h-6 rounded px-2 text-xs", view === key ? "bg-ink text-white" : "text-ink-3 hover:text-ink")}>
                    {text}
                  </button>
                ))}
              </span>
            )}
            <button type="button" className="inline-flex h-7 items-center gap-1 rounded-md px-2 text-xs font-semibold text-accent hover:bg-hover disabled:text-ink-4"
              onClick={() => onOpenPage(item.chunk_id)} disabled={!anchor?.page}>
              <Maximize2 className="h-3.5 w-3.5" aria-hidden /> 整页
            </button>
          </div>
        )}
      </div>
      <div ref={bodyRef} className="relative min-h-0 flex-1 bg-[#F6F6F4]">
        {!item ? (
          <p className="p-6 text-sm text-ink-4">当前没有已验证的原文证据。</p>
        ) : view === "page" && anchor?.page && bodyHeight > 0 ? (
          <div className="absolute inset-0 p-3">
            <PdfDocument projectId={projectId}>
              <PdfCrop
                key={item.chunk_id}
                page={anchor.page}
                pageSize={pageSize}
                rects={anchor.rects}
                // A table/figure caption is often what gets cited: show the body next to it.
                contextPt={/table|fig|表|图/i.test(anchor.locator ?? "") ? 120 : undefined}
                fillHeight={Math.max(160, bodyHeight - 24)}
                label={`证据 ${index + 1} 原文，${anchorLabel(anchor)}`}
              />
            </PdfDocument>
          </div>
        ) : (
          <div className="absolute inset-0 overflow-auto p-5">
            <p className="max-w-[720px] whitespace-pre-line break-words font-serif text-[15px] leading-[1.8] text-ink">{normalizeEvidence(item.text)}</p>
          </div>
        )}
      </div>
      {item && (
        <div className="flex h-9 shrink-0 items-center gap-3 border-t border-line-soft px-4 text-xs text-ink-4">
          <span className="min-w-0 truncate" title={anchor ? anchorLabel(anchor) : undefined}>{anchor ? anchorLabel(anchor) : `第 ${item.page} 页`}</span>
          <span className="ml-auto hidden whitespace-nowrap sm:inline">{candidates ? "候选片段未被判定为支持" : view === "page" ? "滚动查看整页 · 黄色为引用位置" : `${index + 1} / ${evidence.length}`}</span>
        </div>
      )}
    </section>
  );
}

export function ClaimDetail({
  audit,
}: {
  audit: ClaimAudit;
}) {
  const { claim, judgment, citation_review: review } = audit;
  const tone = LABEL_TONE[judgment.label];
  const severityTone = judgment.severity === "critical" || judgment.severity === "high" ? "bg-bad-soft text-bad" : "bg-line-soft text-ink-2";
  const errors = [
    judgment.claim_error_type && `论断：${CLAIM_ERROR_NAMES[judgment.claim_error_type]}`,
    judgment.evidence_error_type && `证据：${EVIDENCE_ERROR_NAMES[judgment.evidence_error_type]}`,
  ].filter(Boolean) as string[];

  return (
    <article className="claim-detail flex w-full min-w-0 max-w-[780px] flex-col gap-6 break-words px-5 py-5">
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
