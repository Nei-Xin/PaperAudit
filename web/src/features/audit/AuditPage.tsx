import { AuditTasks } from "./AuditTasks";
import { useEffect, useMemo, useRef, useState } from "react";
import { Navigate, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { ArrowDown, ArrowUp, Maximize2, List, Plus, Search, SlidersHorizontal } from "lucide-react";
import clsx from "clsx";
import { useAudit, useAudits, useProject } from "@/api/queries";
import { USE_MOCK, resourceUrl } from "@/api/client";
import type { AuditDetail, ClaimAudit, ClaimCategory, EvidenceAnchor, Severity } from "@/api/types";
import { TopBar } from "@/app/ProjectLayout";
import { useContainerWidth } from "@/components/useContainerWidth";
import { PdfPage, PdfPanel } from "@/components/PdfPanel";
import { EmptyState, ErrorState, Loading } from "@/components/States";
import { Modal } from "@/components/Modal";
import { Popover } from "@/components/Popover";
import {
  AUDIT_DIMENSION_NAMES, CATEGORY_LABELS, LABEL_NAMES, LABEL_TONE, SEVERITY_NAMES, anchorLabel,
} from "@/lib/labels";
import { ClaimDetail } from "./ClaimDetail";
import { NewAuditDialog } from "./NewAuditDialog";
import {
  filterAudits, isAttentionRequired, labelCounts, selectedEvidence, sortAudits,
  type SortMode, type StatusFilter,
} from "./auditView";

type Tab = "claims" | "stats" | "export";

function useParam<T extends string>(params: URLSearchParams, key: string, fallback: T): T {
  return (params.get(key) as T | null) ?? fallback;
}

/** Placeholder with the final layout while a (possibly large) audit loads. */
function AuditSkeleton() {
  const bar = "animate-pulse rounded bg-line-soft";
  return (
    <div className="flex min-h-0 flex-1 flex-col gap-2" role="status" aria-label="正在载入审计结果">
      <div className="card flex h-[74px] items-center gap-6 px-4">
        {[40, 24, 24, 24, 24].map((w, i) => <div key={i} className={bar} style={{ width: `${w * 3}px`, height: i ? 28 : 36 }} />)}
      </div>
      <div className="audit-columns min-h-0 flex-1">
        <div className="audit-list card flex-col gap-3 p-3">
          {Array.from({ length: 7 }, (_, i) => <div key={i} className={clsx(bar, "h-12")} />)}
        </div>
        <div className="card flex flex-col gap-4 p-6">
          <div className={clsx(bar, "h-6 w-3/4")} />
          <div className={clsx(bar, "h-4 w-full")} />
          <div className={clsx(bar, "h-4 w-5/6")} />
          <div className={clsx(bar, "h-24 w-full")} />
        </div>
      </div>
      <span className="sr-only">正在载入审计结果…</span>
    </div>
  );
}

function SummaryStrip({ detail }: { detail: AuditDetail }) {
  const { summary, audits } = detail.run;
  const counts = labelCounts(audits);
  const attention = audits.filter(isAttentionRequired).length;
  const gradeTone = summary.grade === "可信" ? "text-ok-text" : summary.grade === "不可信" ? "text-bad" : "text-warn-text";
  const cells: [string, number, string][] = [
    ["需关注", attention, "text-warn-text"],
    ["冲突", counts.CONTRADICTED, "text-bad"],
    ["未找到证据", counts.NO_SUPPORT_FOUND, "text-ink"],
    ["证据不足", counts.ABSTAIN, "text-ink"],
    ["严重 / 高风险", summary.critical_count + summary.high_count, "text-bad"],
  ];
  return (
    <div className="audit-summary card shrink-0">
      <div className="flex min-w-[180px] items-center justify-between gap-4 bg-[#FAFAF9] px-4 py-2.5">
        <div>
          <div className="text-xs text-ink-4">审计结果</div>
          <div className={clsx("text-lg font-semibold", gradeTone)}>{summary.grade}</div>
        </div>
        <div className="text-2xl font-semibold">
          {summary.total_score === null ? "—" : summary.total_score.toFixed(1)}
          <span className="ml-0.5 text-sm font-normal text-ink-4">分</span>
        </div>
      </div>
      {cells.map(([label, value, tone]) => (
        <div key={label} className="flex flex-1 flex-col items-center justify-center border-l border-line-soft py-2">
          <span className="text-xs text-ink-4">{label}</span>
          <span className={clsx("text-lg font-semibold", tone)}>{value}</span>
        </div>
      ))}
    </div>
  );
}

function ClaimList({
  audits, selectedId, onSelect,
}: { audits: ClaimAudit[]; selectedId: string | undefined; onSelect: (id: string) => void }) {
  const activeRef = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    activeRef.current?.scrollIntoView({ block: "nearest" });
  }, [selectedId]);
  if (!audits.length) {
    return <p className="px-3 py-6 text-center text-sm text-ink-4">当前筛选条件下没有论断</p>;
  }
  return (
    <ol className="flex flex-col gap-0.5 p-1.5" aria-label="论断列表">
      {audits.map((audit) => {
        const active = audit.claim.claim_id === selectedId;
        return (
          <li key={audit.claim.claim_id}>
            <button
              type="button"
              ref={active ? activeRef : undefined}
              aria-current={active}
              onClick={() => onSelect(audit.claim.claim_id)}
              className={clsx(
                "flex w-full flex-col gap-1 rounded-lg px-2.5 py-2 text-left transition-colors",
                active ? "bg-line-soft" : "hover:bg-[#F6F6F4]",
              )}
            >
              <span className={clsx("line-clamp-2 text-[13px] leading-[1.55]", active && "font-semibold")}>{audit.claim.text}</span>
              <span className="flex items-center gap-1.5 text-xs text-ink-4">
                <span className={clsx("h-[7px] w-[7px] shrink-0 rounded-full", LABEL_TONE[audit.judgment.label].dot)} aria-hidden />
                {audit.claim.claim_id} · {LABEL_NAMES[audit.judgment.label]} · {SEVERITY_NAMES[audit.judgment.severity]}
              </span>
            </button>
          </li>
        );
      })}
    </ol>
  );
}

function SourcePane({
  projectId, anchor, pageWidthPt, onExpand,
}: { projectId: string; anchor: EvidenceAnchor | undefined; pageWidthPt: number; onExpand: () => void }) {
  return (
    <section className="card flex h-full min-h-0 min-w-0 flex-col" aria-label="原文">
      <div className="flex h-11 shrink-0 items-center gap-2 border-b border-line-soft px-3 text-[13px] text-ink-3">
        <span className="min-w-0 flex-1 truncate" title={anchor ? anchorLabel(anchor) : undefined}>{anchor?.page ? `原文 · ${anchorLabel(anchor)}` : "原文"}</span>
        <button type="button" className="icon-btn" onClick={onExpand} disabled={!anchor?.page} aria-label="放大原文"><Maximize2 className="h-4 w-4" /></button>
      </div>
      <div className="min-h-0 flex-1 overflow-auto p-4">
        {anchor?.page ? (
          <PdfPage projectId={projectId} page={anchor.page} pageWidthPt={pageWidthPt} highlights={anchor.rects} />
        ) : (
          <p className="py-8 text-center text-sm text-ink-4">这条论断没有可定位的原文证据。</p>
        )}
      </div>
    </section>
  );
}

function StatsTab({ detail }: { detail: AuditDetail }) {
  const { summary, audits } = detail.run;
  const counts = labelCounts(audits);
  const supportedRate = audits.length ? (counts.SUPPORTED / audits.length) * 100 : 0;
  return (
    <div className="audit-stats grid min-h-0 flex-1 gap-2 overflow-auto">
      <section className="card p-5">
        <h2 className="mb-4 text-sm font-semibold">六维评估体系得分</h2>
        <ul className="flex flex-col gap-3">
          {Object.entries(AUDIT_DIMENSION_NAMES).map(([key, name]) => {
            const value = summary.dimensions[key as keyof typeof summary.dimensions];
            return (
              <li key={key} className="grid grid-cols-[7rem_minmax(0,1fr)_2.5rem] items-center gap-3 text-sm">
                <span className="text-ink-3">{name}</span>
                <span className="h-1.5 overflow-hidden rounded-full bg-line-soft">
                  <span className="block h-full rounded-full bg-accent" style={{ width: `${value ?? 0}%` }} />
                </span>
                <span className="text-right font-medium">{value === null || value === undefined ? "N/A" : value.toFixed(1)}</span>
              </li>
            );
          })}
        </ul>
      </section>
      <section className="card flex flex-col gap-4 p-5 text-sm">
        <h2 className="text-sm font-semibold">统计与核对</h2>
        <p className="leading-7 text-ink-3">
          自动拆分并审计 {audits.length} 条论断：支持 {counts.SUPPORTED} · 部分支持 {counts.PARTIALLY_SUPPORTED} · 冲突 {counts.CONTRADICTED} ·
          未找到支持 {counts.NO_SUPPORT_FOUND} · 证据不足 {counts.ABSTAIN}。完全支持率 {supportedRate.toFixed(1)}%，
          已抽取论断非弃权比例 {summary.audit_coverage.toFixed(1)}%，候选证据检索覆盖率 {summary.evidence_discovery_rate.toFixed(1)}%。
        </p>
        <p className="text-xs text-ink-4">综合总分不等同于事实正确率；非弃权比例不代表报告原文抽取完整率。</p>
        {detail.run.deep_audit && (
          <p className="text-ink-3">本次使用深度核验 · {audits.filter((a) => a.investigation).length} 条论断启动调查</p>
        )}
        {detail.run.source_count > 0 && (
          <details className="rounded-lg bg-page px-3 py-2">
            <summary className="cursor-pointer">原文抽取核对 · {detail.run.source_count} 句 · {detail.run.skipped_sources.length} 句未抽取</summary>
            <ul className="mt-2 flex flex-col gap-2 text-xs text-ink-3">
              {detail.run.skipped_sources.map((source, index) => (
                <li key={index}><span className="font-medium">{source.report_location}</span> · {source.reason}<br />{source.text}</li>
              ))}
            </ul>
          </details>
        )}
        {detail.run.parse_warnings.map((warning) => (
          <p key={warning} className="rounded-lg bg-warn-soft px-3 py-2 text-warn-text">{warning}</p>
        ))}
      </section>
    </div>
  );
}

function downloadJson(detail: AuditDetail) {
  const blob = new Blob([JSON.stringify(detail.run, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = Object.assign(document.createElement("a"), { href: url, download: "paperaudit-result.json" });
  link.click();
  URL.revokeObjectURL(url);
}

function ExportTab({ detail, projectId }: { detail: AuditDetail; projectId: string }) {
  return (
    <section className="card flex flex-col gap-3 p-5">
      <h2 className="text-sm font-semibold">导出完整审计报告</h2>
      <div className="flex flex-wrap gap-2">
        {USE_MOCK ? (
          <button type="button" className="btn-secondary" disabled title="需要后端接口">下载 Markdown 报告</button>
        ) : (
          <a className="btn-secondary" href={resourceUrl(`/api/projects/${projectId}/audits/${detail.record.audit_id}/export?format=md`)}>下载 Markdown 报告</a>
        )}
        <button type="button" className="btn-secondary" onClick={() => downloadJson(detail)}>下载 JSON 结果</button>
      </div>
    </section>
  );
}

export function AuditPage() {
  const { projectId = "", auditId } = useParams();
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const project = useProject(projectId);
  const records = useAudits(projectId);
  const detail = useAudit(projectId, auditId);
  const [newOpen, setNewOpen] = useState(false);
  const [sourceChunk, setSourceChunk] = useState<string | undefined>();
  const [dialogChunk, setDialogChunk] = useState<string | undefined>();
  const [containerRef, containerWidth] = useContainerWidth<HTMLDivElement>();
  const wide = containerWidth >= 1160;
  const [listOpen, setListOpen] = useState(false);
  const [dialogPage, setDialogPage] = useState(1);
  const openEvidence = (chunkId: string) => { setDialogPage(detail.data?.anchors[chunkId]?.page ?? 1); setDialogChunk(chunkId); };

  const tab = useParam<Tab>(params, "tab", "claims");
  const status = useParam<StatusFilter>(params, "status", "all");
  const sort = useParam<SortMode>(params, "sort", "risk");
  const category = useParam<ClaimCategory | "">(params, "cat", "");
  const severity = useParam<Severity | "">(params, "sev", "");
  const query = params.get("q") ?? "";
  const extraFilters = [category, severity, sort !== "risk" && sort].filter(Boolean).length;
  const update = (patch: Record<string, string>) =>
    setParams((current) => {
      const next = new URLSearchParams(current);
      for (const [key, value] of Object.entries(patch)) value ? next.set(key, value) : next.delete(key);
      return next;
    }, { replace: true });

  const visible = useMemo(() => {
    const audits = detail.data?.run.audits ?? [];
    return sortAudits(filterAudits(audits, { status, category, severity, query }), sort);
  }, [detail.data, status, category, severity, query, sort]);
  const selectedId = visible.some((a) => a.claim.claim_id === params.get("claim")) ? params.get("claim")! : visible[0]?.claim.claim_id;
  const index = visible.findIndex((a) => a.claim.claim_id === selectedId);
  const selected = visible[index];
  const select = (id: string) => { setSourceChunk(undefined); setListOpen(false); update({ claim: id }); };

  // ↑ / ↓ (or k / j) move between claims unless typing in a field.
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement;
      if (document.querySelector("dialog[open]") || tab !== "claims" || (target instanceof Element && target.closest("input, textarea, select, [contenteditable]"))) return;
      const delta = event.key === "ArrowDown" || event.key === "j" ? 1 : event.key === "ArrowUp" || event.key === "k" ? -1 : 0;
      if (!delta || index < 0) return;
      const next = visible[index + delta];
      if (next) { event.preventDefault(); select(next.claim.claim_id); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  if (records.isLoading) return <Loading />;
  if (!auditId && !params.get("job") && records.data?.length) {
    return <Navigate to={`/p/${projectId}/audit/${records.data[0].audit_id}`} replace />;
  }

  const actions = (
    <>
      {records.data && records.data.length > 0 && (
        <label className="flex min-w-0 flex-1 items-center">
          <span className="sr-only">审计记录</span>
          <select
            value={auditId}
            onChange={(event) => navigate(`/p/${projectId}/audit/${event.target.value}`)}
            className="h-8 w-full min-w-0 max-w-[220px] truncate rounded-lg bg-card px-2 text-[13px] shadow-card outline-none"
          >
            {records.data.map((record) => (
              <option key={record.audit_id} value={record.audit_id}>
                {record.source_label} · {new Date(record.created_at).toLocaleString("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" })}
              </option>
            ))}
          </select>
        </label>
      )}
      <button type="button" className="btn-primary" onClick={() => setNewOpen(true)}>
        <Plus className="h-4 w-4" aria-hidden /> 审计报告
      </button>
    </>
  );

  const anchors = detail.data?.anchors ?? {};
  const claimChunks = selected ? selectedEvidence(selected).map((c) => c.chunk_id) : [];
  const chunk = sourceChunk && claimChunks.includes(sourceChunk) ? sourceChunk : claimChunks[0];
  const anchor = chunk ? anchors[chunk] : undefined;
  const pageWidth = anchor?.page ? project.data?.pages[anchor.page - 1]?.width ?? 0 : 0;

  return (
    <div ref={containerRef} className="flex h-full min-h-0 min-w-0 flex-col">
      <TopBar actions={actions} />
      <AuditTasks projectId={projectId} />
      {records.error ? <ErrorState error={records.error} /> : !records.data?.length ? (
        <section className="card max-w-xl">
          <EmptyState title="还没有审计记录" action={<button type="button" className="btn-primary self-start" onClick={() => setNewOpen(true)}>审计一份报告</button>}>
            上传一份解读报告，系统会把它拆成论断，逐条对照原文核验事实、数字与结论。
          </EmptyState>
        </section>
      ) : detail.isLoading ? <AuditSkeleton /> : detail.error ? <ErrorState error={detail.error} /> : detail.data && (
        <div className="flex min-h-0 flex-1 flex-col gap-2">
          <details className="audit-summary-wrap" open={containerWidth >= 560}>
            <summary className="audit-summary-toggle card cursor-pointer px-3 py-2 text-sm">
              {detail.data.run.summary.grade} · {detail.data.run.summary.total_score?.toFixed(1) ?? "—"} 分
              <span className="ml-3 text-xs text-ink-4">需关注 {detail.data.run.audits.filter(isAttentionRequired).length} · 查看统计</span>
            </summary>
            <SummaryStrip detail={detail.data} />
          </details>
          <div className="audit-filter-bar">
            <nav className="flex shrink-0 gap-5 overflow-x-auto text-sm" aria-label="审计视图">
              {([["claims", "逐条审计"], ["stats", "统计与核对"], ["export", "报告导出"]] as [Tab, string][]).map(([key, label]) => (
                <button
                  key={key}
                  type="button"
                  onClick={() => update({ tab: key === "claims" ? "" : key })}
                  className={clsx("shrink-0 whitespace-nowrap border-b-2 py-2", tab === key ? "border-ink font-semibold" : "border-transparent text-ink-4 hover:text-ink")}
                >
                  {label}
                </button>
              ))}
            </nav>
            {tab === "claims" && (
              <div className="audit-filters">
                <label className="audit-search flex h-8 min-w-0 items-center gap-2 rounded-lg bg-card px-2.5 shadow-card">
                  <Search className="h-4 w-4 text-ink-4" aria-hidden />
                  <span className="sr-only">搜索论断</span>
                  <input value={query} onChange={(e) => update({ q: e.target.value })} placeholder="搜索论断、证据或内容…" className="min-w-0 flex-1 bg-transparent text-[13px] outline-none" />
                </label>
                <label>
                  <span className="sr-only">状态</span>
                  <select value={status} onChange={(e) => update({ status: e.target.value === "all" ? "" : e.target.value })} className="h-8 rounded-lg bg-card px-2 text-[13px] shadow-card outline-none">
                    <option value="all">全部状态</option>
                    <option value="attention">需关注</option>
                    {Object.entries(LABEL_NAMES).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                  </select>
                </label>
                <Popover
                  className="flex w-56 flex-col gap-3"
                  summary={<><SlidersHorizontal className="h-4 w-4" aria-hidden /> 更多筛选{extraFilters ? ` · ${extraFilters}` : ""}</>}
                >
                    <label className="flex flex-col gap-1 text-xs text-ink-4">分类
                      <select value={category} onChange={(e) => update({ cat: e.target.value })} className="h-8 rounded-md bg-page px-2 text-[13px] text-ink">
                        <option value="">全部分类</option>
                        {Object.entries(CATEGORY_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                      </select>
                    </label>
                    <label className="flex flex-col gap-1 text-xs text-ink-4">风险
                      <select value={severity} onChange={(e) => update({ sev: e.target.value })} className="h-8 rounded-md bg-page px-2 text-[13px] text-ink">
                        <option value="">全部风险</option>
                        {(["critical", "high", "medium", "low", "none"] as Severity[]).map((v) => <option key={v} value={v}>{SEVERITY_NAMES[v]}</option>)}
                      </select>
                    </label>
                    <label className="flex flex-col gap-1 text-xs text-ink-4">排序
                      <select value={sort} onChange={(e) => update({ sort: e.target.value === "risk" ? "" : e.target.value })} className="h-8 rounded-md bg-page px-2 text-[13px] text-ink">
                        <option value="risk">风险优先</option>
                        <option value="report">报告顺序</option>
                      </select>
                    </label>
                </Popover>
              </div>
            )}
          </div>

          {tab === "stats" ? <StatsTab detail={detail.data} /> : tab === "export" ? <ExportTab detail={detail.data} projectId={projectId} /> : (
            <div className={clsx("audit-columns", wide && "audit-columns-wide")}>
              <section className="audit-list card flex min-h-0 min-w-0 flex-col" aria-label="论断">
                <div className="flex h-11 shrink-0 items-baseline gap-2 border-b border-line-soft px-4 pt-3">
                  <strong className="text-sm">论断</strong>
                  <span className="text-xs text-ink-4">{visible.length} 条 · 需关注 {visible.filter(isAttentionRequired).length}</span>
                </div>
                <div className="min-h-0 flex-1 overflow-auto"><ClaimList audits={visible} selectedId={selectedId} onSelect={select} /></div>
              </section>
              <section className="card flex min-h-0 min-w-0 flex-col" aria-label="论断详情">
                <div className="flex h-11 shrink-0 items-center gap-1 border-b border-line-soft pl-5 pr-2 text-[13px] text-ink-4">
                  <button type="button" className="audit-list-trigger btn-secondary mr-1" onClick={() => setListOpen(true)}><List className="h-4 w-4" /> 列表</button>
                  <span className="mr-auto whitespace-nowrap">论断 {index + 1} / {visible.length}</span>
                  <button type="button" className="icon-btn" disabled={index <= 0} onClick={() => select(visible[index - 1].claim.claim_id)} aria-label="上一条 (↑)" title="上一条 (↑)"><ArrowUp className="h-4 w-4" /></button>
                  <button type="button" className="icon-btn" disabled={index >= visible.length - 1} onClick={() => select(visible[index + 1].claim.claim_id)} aria-label="下一条 (↓)" title="下一条 (↓)"><ArrowDown className="h-4 w-4" /></button>
                </div>
                <div className="min-h-0 flex-1 overflow-auto">
                  {selected ? (
                    <ClaimDetail audit={selected} anchors={anchors} activeChunk={chunk} onOpenEvidence={(id) => { setSourceChunk(id); openEvidence(id); }} />
                  ) : <p className="p-6 text-sm text-ink-4">没有可显示的论断。</p>}
                </div>
              </section>
              {wide && <div className="min-h-0 min-w-0">
                <SourcePane projectId={projectId} anchor={anchor} pageWidthPt={pageWidth} onExpand={() => chunk && openEvidence(chunk)} />
              </div>}
            </div>
          )}
        </div>
      )}
      <NewAuditDialog open={newOpen} onClose={() => setNewOpen(false)} />
      <Modal open={listOpen} onClose={() => setListOpen(false)} title={`论断列表 · ${visible.length} 条`}>
        <ClaimList audits={visible} selectedId={selectedId} onSelect={select} />
      </Modal>
      <Modal open={dialogChunk !== undefined} onClose={() => setDialogChunk(undefined)} title="原文证据" wide>
        {dialogChunk && anchors[dialogChunk]?.page && (
          <div className="pdf-modal">
            <PdfPanel projectId={projectId} page={dialogPage} pageCount={project.data?.page_count ?? 1}
              pageSizes={project.data?.pages ?? []} onPage={setDialogPage}
              highlights={dialogPage === anchors[dialogChunk].page ? anchors[dialogChunk].rects : []} />
          </div>
        )}
      </Modal>
    </div>
  );
}
