import { useEffect, useMemo, useState, type ReactNode } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { ExternalLink } from "lucide-react";
import clsx from "clsx";
import { useJobs, useProject, useReview, useSaveReviewProgress } from "@/api/queries";
import { READ_ONLY, READING_ONLY, USE_MOCK, resourceUrl } from "@/api/client";
import type {
  EvidenceAnchor, IssueCategory, IssueSeverity, IssueStatus, PeerReviewReport, ProjectDetail, ReviewConcern, ReviewProgress,
} from "@/api/types";
import { TopBar } from "@/app/ProjectLayout";
import { Modal } from "@/components/Modal";
import { useContainerWidth } from "@/components/useContainerWidth";
import { ResponsiveReader } from "@/components/ResponsiveReader";
import { PdfPage, PdfPanel } from "@/components/PdfPanel";
import { EmptyState, ErrorState, Loading, MockNote, Progress } from "@/components/States";
import {
  DECISION_LABELS, ISSUE_CATEGORY_LABELS, ISSUE_SEVERITY_NAMES, ISSUE_STATUS_LABELS, REVIEW_DIMENSION_NAMES, VENUE_LABELS,
} from "@/lib/labels";

type Tab = "overview" | "dimensions" | "issues" | "revisions";
const SEVERITY_ORDER: IssueSeverity[] = ["P0", "P1", "P2", "P3"];

const severityOf = (concern: ReviewConcern): IssueSeverity => concern.severity_level ?? "P2";
const allConcerns = (report: PeerReviewReport) => [...report.major_concerns, ...report.minor_concerns];

/** Same source order as ui/peer_review.py `_plan_actions`. */
function planActions(report: PeerReviewReport): string[] {
  const actions = report.top_priorities.length ? report.top_priorities : report.required_changes;
  if (actions.length) return actions.slice(0, 5);
  return allConcerns(report).map((c) => c.suggestion).filter((s) => s.trim()).slice(0, 3);
}

async function sha1(text: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-1", new TextEncoder().encode(text));
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

function useActionKeys(actions: string[]): string[] {
  const [keysList, setKeys] = useState<string[]>([]);
  useEffect(() => {
    let cancelled = false;
    Promise.all(actions.map(sha1)).then((result) => { if (!cancelled) setKeys(result); });
    return () => { cancelled = true; };
  }, [actions]);
  return keysList;
}

function EvidenceButton({ anchor, onOpen }: { anchor: EvidenceAnchor; onOpen: (a: EvidenceAnchor) => void }) {
  if (!anchor.page) return null;
  return (
    <button type="button" onClick={() => onOpen(anchor)} className="inline-flex items-center gap-1 text-xs font-medium text-accent hover:underline">
      定位原文 · 第 {anchor.page} 页 <ExternalLink className="h-3 w-3" aria-hidden />
    </button>
  );
}

function SeverityChip({ severity }: { severity: IssueSeverity }) {
  const tone = severity === "P0" || severity === "P1" ? "bg-bad-soft text-bad" : "bg-warn-soft text-warn-text";
  return <span className={clsx("inline-flex h-5 shrink-0 items-center rounded px-1.5 text-xs font-semibold", tone)}>{ISSUE_SEVERITY_NAMES[severity]}</span>;
}

function Fold({ title, hint, children }: { title: string; hint?: string; children: ReactNode }) {
  return (
    <details className="group border-b border-line-soft">
      <summary className="flex cursor-pointer list-none items-center gap-2 py-3 text-sm font-medium">
        <span className="text-ink-4 transition-transform group-open:rotate-90" aria-hidden>›</span>
        {title}
        {hint && <span className="ml-auto text-xs font-normal text-ink-4">{hint}</span>}
      </summary>
      <div className="pb-4 pl-4 text-sm leading-7 text-ink-2">{children}</div>
    </details>
  );
}

function Overview({
  report, progress, onToggle, onOpen,
}: {
  report: PeerReviewReport;
  progress: Record<string, boolean>;
  onToggle: (key: string, done: boolean) => void;
  onOpen: (a: EvidenceAnchor) => void;
}) {
  const risks = useMemo(
    () => [...allConcerns(report)].sort((a, b) =>
      SEVERITY_ORDER.indexOf(severityOf(a)) - SEVERITY_ORDER.indexOf(severityOf(b)) || b.confidence - a.confidence,
    ).slice(0, 4),
    [report],
  );
  const actions = useMemo(() => planActions(report), [report]);
  const actionKeys = useActionKeys(actions);
  const doneCount = actionKeys.filter((key) => progress[key]).length;
  const changes = report.acceptance_blockers.length + report.required_changes.length + report.suggested_changes.length;
  return (
    <div className="flex flex-col gap-8">
      <section className="flex flex-col gap-3">
        <h2 className="text-sm font-semibold">投稿风险</h2>
        <ol className="flex flex-col divide-y divide-line-soft">
          {risks.map((concern) => (
            <li key={concern.issue_id || concern.title} className="flex flex-col gap-2 py-4 first:pt-0">
              <div className="flex flex-wrap items-start gap-2">
                <SeverityChip severity={severityOf(concern)} />
                <h3 className="min-w-0 flex-1 text-sm font-semibold leading-6">{concern.title}</h3>
                <span className="w-full text-xs text-ink-4">置信度 {concern.confidence} / 5</span>
              </div>
              <p className="text-sm leading-7 text-ink-2">{concern.description}</p>
              <div className="flex flex-wrap items-center gap-3 text-xs text-ink-4">
                <span>{concern.evidence.length} 处证据 · {ISSUE_STATUS_LABELS[concern.status]}</span>
                {concern.evidence.slice(0, 2).map((anchor) => <EvidenceButton key={anchor.chunk_id} anchor={anchor} onOpen={onOpen} />)}
              </div>
              {concern.evidence[0]?.quote && <p className="font-serif text-[13px] leading-6 text-ink-3">“{concern.evidence[0].quote}”</p>}
            </li>
          ))}
        </ol>
      </section>

      {actions.length > 0 && (
        <section className="flex flex-col gap-3">
          <div className="flex items-baseline gap-2">
            <h2 className="text-sm font-semibold">投稿前修改计划</h2>
            <span className="text-xs text-ink-4">{doneCount} / {actions.length} 已完成</span>
          </div>
          <ol className="flex flex-col gap-2">
            {actions.map((action, index) => {
              const key = actionKeys[index];
              const done = key ? Boolean(progress[key]) : false;
              return (
                <li key={action} className="flex items-start gap-3 rounded-[10px] bg-[#FAFAF9] px-4 py-3 shadow-[inset_0_0_0_1px_#F0EFEC]">
                  <input
                    type="checkbox"
                    className="mt-1 h-4 w-4 shrink-0 accent-ink"
                    checked={done}
                    disabled={!key || READ_ONLY || READING_ONLY}
                    onChange={(event) => key && onToggle(key, event.target.checked)}
                    aria-label={`第 ${index + 1} 步已完成`}
                  />
                  <div className="flex flex-col gap-1">
                    <span className="text-xs font-semibold text-ink-4">第 {index + 1} 步</span>
                    <p className={clsx("text-sm leading-7", done && "text-ink-4 line-through")}>{action}</p>
                  </div>
                </li>
              );
            })}
          </ol>
        </section>
      )}

      {report.fatal_flaws.length > 0 && (
        <section className="flex flex-col gap-2">
          <h2 className="text-sm font-semibold text-bad">致命问题</h2>
          <ul className="list-disc pl-5 text-sm leading-7">{report.fatal_flaws.map((item) => <li key={item}>{item}</li>)}</ul>
        </section>
      )}

      <section>
        <Fold title="完整 AI 评审总结">
          <p className="whitespace-pre-line">{report.summary}</p>
          {report.why_not_adjacent && <><p className="mt-3 font-medium text-ink">为什么不是相邻档位</p><p>{report.why_not_adjacent}</p></>}
        </Fold>
        {changes > 0 && (
          <Fold title="完整修改清单" hint={`${changes} 项`}>
            {([["接收阻碍", report.acceptance_blockers], ["必须修改", report.required_changes], ["建议修改", report.suggested_changes]] as const).map(([label, items]) =>
              items.length ? <div key={label} className="mb-3"><p className="font-medium text-ink">{label}</p><ul className="list-disc pl-5">{items.map((i) => <li key={i}>{i}</li>)}</ul></div> : null,
            )}
          </Fold>
        )}
        <Fold title="贡献与优势" hint={`${report.core_contributions.length + report.strengths.length} 项`}>
          {report.core_contributions.length > 0 && <><p className="font-medium text-ink">核心贡献</p><ul className="mb-3 list-disc pl-5">{report.core_contributions.map((i) => <li key={i}>{i}</li>)}</ul></>}
          {report.strengths.length > 0 && <><p className="font-medium text-ink">论文已有优势</p><ul className="list-disc pl-5">{report.strengths.map((i) => <li key={i}>{i}</li>)}</ul></>}
        </Fold>
        <Fold title="评审边界与置信度">
          {report.confidence_rationale && <p className="mb-3">{report.confidence_rationale}</p>}
          <p className="text-xs text-ink-4">以下项目无法仅凭上传论文正文独立确认，不应视为已证实的缺陷。</p>
          <ul className="list-disc pl-5">
            {(report.review_limitations.length ? report.review_limitations : ["本评审仅基于上传论文文本；代码、完整附录、数据泄漏和未报告实验无法独立验证。"]).map((i) => <li key={i}>{i}</li>)}
          </ul>
        </Fold>
      </section>
    </div>
  );
}

function Dimensions({ report, onOpen }: { report: PeerReviewReport; onOpen: (a: EvidenceAnchor) => void }) {
  return (
    <ul className="flex flex-col divide-y divide-line-soft">
      {report.dimensions.map((dimension) => (
        <li key={dimension.name} className="flex flex-col gap-2 py-4 first:pt-0">
          <div className="review-dimension">
            <strong className="w-24 shrink-0 text-sm">{REVIEW_DIMENSION_NAMES[dimension.name] ?? dimension.name}</strong>
            <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-line-soft"><span className="block h-full rounded-full bg-accent" style={{ width: `${(dimension.score / 5) * 100}%` }} /></span>
            <span className="w-12 text-right text-sm font-medium">{dimension.score} / 5</span>
            <span className="w-20 text-right text-xs text-ink-4">置信度 {dimension.confidence} / 5</span>
          </div>
          <p className="text-sm leading-7 text-ink-2">{dimension.rationale}</p>
          <div className="flex flex-wrap gap-3">
            {dimension.evidence.length ? dimension.evidence.slice(0, 3).map((a) => <EvidenceButton key={a.chunk_id} anchor={a} onOpen={onOpen} />) : <span className="text-xs text-ink-4">AI 评审判断 · 未绑定可定位原文依据</span>}
          </div>
        </li>
      ))}
    </ul>
  );
}

function Issues({ report, onOpen }: { report: PeerReviewReport; onOpen: (a: EvidenceAnchor) => void }) {
  const [severity, setSeverity] = useState<IssueSeverity | "">("");
  const [category, setCategory] = useState<IssueCategory | "">("");
  const [status, setStatus] = useState<IssueStatus | "">("");
  const list = allConcerns(report).filter((c) =>
    (!severity || severityOf(c) === severity) && (!category || c.category === category) && (!status || c.status === status),
  );
  const select = "h-8 rounded-lg bg-card px-2 text-[13px] shadow-card outline-none";
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap gap-2">
        <label><span className="sr-only">严重度</span><select className={select} value={severity} onChange={(e) => setSeverity(e.target.value as IssueSeverity | "")}><option value="">全部严重度</option>{SEVERITY_ORDER.map((s) => <option key={s} value={s}>{ISSUE_SEVERITY_NAMES[s]}</option>)}</select></label>
        <label><span className="sr-only">问题类别</span><select className={select} value={category} onChange={(e) => setCategory(e.target.value as IssueCategory | "")}><option value="">全部类别</option>{Object.entries(ISSUE_CATEGORY_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></label>
        <label><span className="sr-only">处理状态</span><select className={select} value={status} onChange={(e) => setStatus(e.target.value as IssueStatus | "")}><option value="">全部状态</option>{Object.entries(ISSUE_STATUS_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></label>
      </div>
      {list.length === 0 && <p className="text-sm text-ink-4">当前筛选条件下没有问题。</p>}
      {list.map((concern) => (
        <article key={concern.issue_id || concern.title} className="flex flex-col gap-2 rounded-[10px] px-4 py-3 shadow-[inset_0_0_0_1px_#F0EFEC]">
          <div className="flex flex-wrap items-center gap-2 text-xs text-ink-4">
            <SeverityChip severity={severityOf(concern)} />
            <span>{ISSUE_CATEGORY_LABELS[concern.category]}</span>
            <span className="ml-auto">{ISSUE_STATUS_LABELS[concern.status]}{concern.human_reviewed ? " · 已人工确认" : ""}</span>
          </div>
          <h3 className="min-w-0 flex-1 text-sm font-semibold leading-6">{concern.title}</h3>
          <p className="text-sm leading-7 text-ink-2">{concern.description}</p>
          <p className="text-sm leading-7"><span className="text-ink-4">为什么重要 · </span>{concern.why_it_matters}</p>
          <p className="rounded-lg bg-accent-soft px-3 py-2 text-sm leading-7"><span className="text-ink-4">怎么改 · </span>{concern.suggestion}</p>
          <div className="flex flex-wrap gap-3">{concern.evidence.slice(0, 3).map((a) => <EvidenceButton key={a.chunk_id} anchor={a} onOpen={onOpen} />)}</div>
        </article>
      ))}
      <MockNote />
    </div>
  );
}

function Revisions({ projectId, count }: { projectId: string; count: number }) {
  return (
    <div className="flex flex-col gap-4">
      <section className="flex flex-col gap-2">
        <h2 className="text-sm font-semibold">修改稿复审</h2>
        <p className="text-sm text-ink-3">上传新版本后保留当前评审，并生成段落级差异与新的五档投稿建议。已有修改稿 {count} 版。</p>
        <label className="flex flex-col gap-1.5 text-sm">
          <span className="sr-only">修改稿 PDF</span>
          <input type="file" accept="application/pdf" disabled={READ_ONLY || READING_ONLY} />
        </label>
        <MockNote />
      </section>
      <section className="flex flex-col gap-2">
        <h2 className="text-sm font-semibold">导出</h2>
        {USE_MOCK ? <button type="button" className="btn-secondary self-start" disabled>下载 Markdown 评审</button>
          : <a className="btn-secondary self-start" href={resourceUrl(`/api/projects/${projectId}/review/export?format=md`)}>下载 Markdown 评审</a>}
      </section>
    </div>
  );
}

function NoReview({ projectId, project }: { projectId: string; project: ProjectDetail }) {
  const jobs = useJobs(projectId);
  const running = jobs.data?.review.find((job) => job.status === "QUEUED" || job.status === "RUNNING");
  const [page, setPage] = useState(1);
  return (
    <ResponsiveReader source={<PdfPanel projectId={projectId} page={page} pageCount={project.page_count} pageSizes={project.pages} onPage={setPage} />}>
      <section className="card self-start">
        {running ? (
          <div className="flex flex-col gap-3 p-6"><h2 className="text-lg font-semibold">模拟评审正在后台进行</h2><Progress value={running.progress} label={running.stage} /></div>
        ) : (
          <EmptyState title="还没有模拟评审">
            按会议标准给出六维评分、主要问题和修改优先级；结果是辅助预审意见。
            <label className="mt-3 flex flex-col gap-1.5">
              <span className="label">评审标准</span>
              <select className="h-9 rounded-lg bg-page px-2 text-sm">{Object.entries(VENUE_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select>
            </label>
            <button type="button" className="btn-primary mt-3" disabled={READ_ONLY || READING_ONLY}>开始模拟评审</button>
            <span className="mt-2 block text-xs text-ink-4">模拟评审会把论文文本发送到你配置的模型服务。</span>
            <MockNote />
          </EmptyState>
        )}
      </section>
    </ResponsiveReader>
  );
}

export function ReviewPage() {
  const { projectId = "" } = useParams();
  const [params, setParams] = useSearchParams();
  const project = useProject(projectId);
  const review = useReview(projectId);
  const save = useSaveReviewProgress(projectId);
  const [evidence, setEvidence] = useState<EvidenceAnchor | undefined>();
  const [localProgress, setLocalProgress] = useState<Record<string, boolean>>({});
  const tab = (params.get("tab") as Tab | null) ?? "overview";

  const saved = useMemo(
    () => Object.fromEntries((review.data?.progress.items ?? []).map((item) => [item.key, item.done])),
    [review.data],
  );
  const progress = { ...saved, ...localProgress };
  const toggle = (key: string, done: boolean) => {
    const next = { ...progress, [key]: done };
    setLocalProgress(next);
    const payload: ReviewProgress = {
      schema_version: 1,
      review_run_id: review.data?.report.run_id ?? "",
      review_generated_at: review.data?.report.generated_at ?? "",
      items: Object.entries(next).map(([k, d]) => ({ key: k, done: d, updated_at: new Date().toISOString() })),
    };
    save.mutate(payload);
  };

  const [containerRef, containerWidth] = useContainerWidth<HTMLDivElement>();
  const report = review.data?.report;
  const actions = useMemo(() => report ? planActions(report) : [], [report]);
  const actionKeys = useActionKeys(actions);
  const done = actionKeys.filter((key) => progress[key]).length;

  return (
    <div ref={containerRef} className="flex h-full min-h-0 min-w-0 flex-col">
      <TopBar actions={report ? <button type="button" className="btn-secondary" disabled={READ_ONLY || READING_ONLY} title={READ_ONLY || READING_ONLY ? "需要后端接口" : undefined}>重新评审</button> : null} />
      {review.isLoading || project.isLoading ? <Loading /> : review.error ? <ErrorState error={review.error} /> : !report ? (
        project.data && <NoReview projectId={projectId} project={project.data} />
      ) : (
        <div className="review-layout">
          <section className="review-main card min-h-0 min-w-0 overflow-auto">
            <div className="review-copy mx-auto flex max-w-[860px] flex-col gap-6 px-4 py-5">
              <header className="flex flex-col gap-2.5">
                <span className="text-xs font-medium text-ink-4">模拟投稿评审 · {VENUE_LABELS[report.venue]}</span>
                <div className="flex flex-wrap items-baseline gap-3">
                  <h1 className={clsx("text-[28px] font-semibold tracking-tight", DECISION_LABELS[report.decision].tone)}>{DECISION_LABELS[report.decision].zh}</h1>
                  <span className="text-[15px] text-ink-3">{DECISION_LABELS[report.decision].en} · {report.overall_score.toFixed(1)} / 10</span>
                </div>
                <p className="text-[15px] leading-[1.8] text-ink-2">{report.decision_rationale}</p>
              </header>
              <nav className="flex shrink-0 gap-5 overflow-x-auto border-b border-line-soft text-sm" aria-label="评审视图">
                {([["overview", "评审意见"], ["dimensions", "维度评分"], ["issues", "问题"], ["revisions", "修改稿与导出"]] as [Tab, string][]).map(([key, label]) => (
                  <button
                    key={key}
                    type="button"
                    onClick={() => setParams(key === "overview" ? {} : { tab: key }, { replace: true })}
                    className={clsx("-mb-px shrink-0 whitespace-nowrap border-b-2 py-2", tab === key ? "border-ink font-semibold" : "border-transparent text-ink-4 hover:text-ink")}
                  >
                    {label}
                  </button>
                ))}
              </nav>
              {save.error && <ErrorState error={save.error} />}
              {tab === "overview" && <Overview report={report} progress={progress} onToggle={toggle} onOpen={setEvidence} />}
              {tab === "dimensions" && <Dimensions report={report} onOpen={setEvidence} />}
              {tab === "issues" && <Issues report={report} onOpen={setEvidence} />}
              {tab === "revisions" && <Revisions projectId={projectId} count={review.data?.revisions.length ?? 0} />}
            </div>
          </section>
          <details className="review-properties card" open={containerWidth >= 900}>
            <summary className="cursor-pointer px-4 py-3 text-sm font-semibold">评审属性与修改进度</summary>
            <aside className="flex flex-col gap-4 p-4 text-sm" aria-label="评审属性">
            {([
              ["结论", <span key="d" className={DECISION_LABELS[report.decision].tone}>{DECISION_LABELS[report.decision].zh}</span>],
              ["总分", `${report.overall_score.toFixed(1)} / 10`],
              ["置信度", `${report.confidence} / 5`],
              ["评审标准", VENUE_LABELS[report.venue]],
              ["修改稿复审", review.data?.revisions.length ? `${review.data.revisions.length} 版` : "暂无"],
            ] as [string, ReactNode][]).map(([key, value]) => (
              <div key={key} className="flex items-baseline justify-between gap-3">
                <span className="text-[13px] text-ink-4">{key}</span>
                <strong className="text-right font-medium">{value}</strong>
              </div>
            ))}
            <hr className="border-line-soft" />
            <div className="flex flex-col gap-2">
              <span className="text-[13px] text-ink-4">修改进度</span>
              <span className="h-1.5 overflow-hidden rounded-full bg-line-soft"><span className="block h-full rounded-full bg-ink" style={{ width: `${actions.length ? (done / actions.length) * 100 : 0}%` }} /></span>
              <span className="text-xs text-ink-4">{done} / {actions.length} 已处理</span>
            </div>
            <hr className="border-line-soft" />
            <p className="text-xs leading-6 text-ink-4">
              基于论文原文的 AI 辅助预审，不代表真实会议录用决定。{report.rubric_change_note}
              {report.model_name && <span className="block" title={`评审标准 ${report.rubric_version} · 运行 ${report.run_id}`}>模型 {report.model_name}</span>}
            </p>
          </aside>
          </details>
        </div>
      )}
      <Modal open={evidence !== undefined} onClose={() => setEvidence(undefined)} title={evidence?.page ? `原文证据 · 第 ${evidence.page} 页` : "原文证据"} wide>
        {evidence?.page && project.data && (
          <PdfPage projectId={projectId} page={evidence.page} pageWidthPt={project.data.pages[evidence.page - 1]?.width ?? 0} highlights={evidence.rects} />
        )}
      </Modal>
    </div>
  );
}
