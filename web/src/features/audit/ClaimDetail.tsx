import { ExternalLink } from "lucide-react";
import clsx from "clsx";
import type { ClaimAudit, EvidenceAnchor } from "@/api/types";
import {
  CATEGORY_LABELS, CLAIM_ERROR_NAMES, EVIDENCE_ERROR_NAMES, LABEL_NAMES, LABEL_TONE, SEVERITY_NAMES, anchorLabel,
} from "@/lib/labels";
import { detailEvidence, normalizeEvidence, splitClaimNumbers } from "./auditView";

function Section({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <section className="flex flex-col gap-2">
      <h3 className="label">{label}</h3>
      {children}
    </section>
  );
}

export function ClaimDetail({
  audit, anchors, activeChunk, onOpenEvidence,
}: {
  audit: ClaimAudit;
  anchors: Record<string, EvidenceAnchor>;
  activeChunk: string | undefined;
  onOpenEvidence: (chunkId: string) => void;
}) {
  const { claim, judgment, citation_review: review } = audit;
  const evidence = detailEvidence(audit);
  const tone = LABEL_TONE[judgment.label];
  const severityTone = judgment.severity === "critical" || judgment.severity === "high" ? "bg-bad-soft text-bad" : "bg-line-soft text-ink-2";
  return (
    <article className="claim-detail flex min-w-0 flex-col gap-6 break-words px-4 py-5">
      <header className="flex flex-wrap items-center gap-2 text-xs text-ink-4">
        <span>{claim.claim_id} · {CATEGORY_LABELS[claim.category]}{claim.report_location ? ` · ${claim.report_location}` : ""}</span>
        <span className="ml-auto flex flex-wrap gap-1.5">
          <span className={clsx("inline-flex h-6 items-center gap-1.5 rounded-md px-2 text-xs font-semibold", tone.chip)}>
            <span className={clsx("h-1.5 w-1.5 rounded-full", tone.dot)} aria-hidden />{LABEL_NAMES[judgment.label]}
          </span>
          <span className={clsx("inline-flex h-6 items-center rounded-md px-2 text-xs font-semibold", severityTone)}>
            {SEVERITY_NAMES[judgment.severity]}
          </span>
        </span>
      </header>

      <h2 className="text-[19px] font-semibold leading-[1.55]">
        {splitClaimNumbers(claim.text, claim.numbers).map((part, i) =>
          part.number ? <mark key={i} className="rounded-sm bg-yellow-200/60 px-0.5 text-inherit">{part.text}</mark> : <span key={i}>{part.text}</span>,
        )}
      </h2>

      <Section label="判断说明">
        <p className="whitespace-pre-line text-[15px] leading-[1.8] text-ink-2">{judgment.explanation}</p>
      </Section>

      <Section label="问题分类">
        <p className="text-sm text-ink-2">
          论断：{judgment.claim_error_type ? CLAIM_ERROR_NAMES[judgment.claim_error_type] : "无"} · 证据：
          {judgment.evidence_error_type ? EVIDENCE_ERROR_NAMES[judgment.evidence_error_type] : "无"}
        </p>
      </Section>

      {judgment.suggestion && (
        <Section label="修改建议">
          <p className="rounded-[10px] bg-accent-soft px-4 py-3 text-[15px] leading-[1.7]">{judgment.suggestion}</p>
        </Section>
      )}

      {review && (
        <Section label="引用完整性复核">
          <p className="text-sm leading-7 text-ink-2">
            <strong className={review.complete ? "text-ok-text" : "text-warn-text"}>{review.complete ? "通过" : "未通过，需人工核对"}</strong>
            {" · "}{review.explanation}
          </p>
          {review.aspects.length > 0 && (
            <ul className="flex flex-col gap-3">
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

      <Section label={`${judgment.label === "NO_SUPPORT_FOUND" || judgment.label === "ABSTAIN" ? "候选原文片段" : "关键原文依据"} · ${evidence.length}`}>
        {evidence.length ? (
          <ol className="flex flex-col gap-3">
            {evidence.map((item, index) => {
              const anchor = anchors[item.chunk_id];
              const active = item.chunk_id === activeChunk;
              return (
                <li key={item.evidence_id} className={clsx("rounded-[10px] px-4 py-3 shadow-[inset_0_0_0_1px_#F0EFEC]", active ? "bg-accent-soft" : "bg-[#FAFAF9]")}>
                  <div className="mb-1.5 flex flex-wrap items-center gap-2 text-xs">
                    <span className="font-semibold text-accent">证据 {index + 1}</span>
                    <span className="text-ink-4">{anchor ? anchorLabel(anchor) : `第 ${item.page} 页`}</span>
                    <button
                      type="button"
                      className="ml-auto inline-flex items-center gap-1 font-medium text-accent hover:underline disabled:text-ink-4 disabled:no-underline"
                      onClick={() => onOpenEvidence(item.chunk_id)}
                      disabled={!anchor?.page}
                    >
                      在原文中查看 <ExternalLink className="h-3 w-3" aria-hidden />
                    </button>
                  </div>
                  <p className="break-words font-serif text-[15px] leading-[1.7]">{normalizeEvidence(item.text)}</p>
                </li>
              );
            })}
          </ol>
        ) : (
          <p className="text-sm text-ink-4">当前没有已验证的原文证据。</p>
        )}
      </Section>
    </article>
  );
}
