import { useMemo, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight, Download, Send } from "lucide-react";
import clsx from "clsx";
import { keys, useGenerateLecture, useConversations, useJobs, useLecture, useProject } from "@/api/queries";
import { READ_ONLY, USE_MOCK, resourceUrl, send } from "@/api/client";
import type { EvidenceAnchor, LearningReport, PageRect, ProjectDetail, PaperAnswer } from "@/api/types";
import { TopBar } from "@/app/ProjectLayout";
import { ResponsiveReader } from "@/components/ResponsiveReader";
import { PdfPanel } from "@/components/PdfPanel";
import { EmptyState, ErrorState, Loading, MockNote, Progress } from "@/components/States";
import { SECTION_LABELS, anchorLabel } from "@/lib/labels";

type View = "lecture" | "qa";

function CitationChip({ anchor, active, onClick }: { anchor: EvidenceAnchor; active: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={!anchor.page}
      className={clsx(
        "inline-flex min-h-6 max-w-full items-center break-words rounded-md px-2 py-1 text-left text-xs font-medium transition-colors",
        active ? "bg-accent text-white" : "bg-accent-soft text-accent hover:bg-[#E2EAF3]",
      )}
      title={anchor.text ?? undefined}
    >
      {anchorLabel(anchor)} ↗
    </button>
  );
}

function LectureView({
  report, section, onSection, activeAnchor, onAnchor, currentPage,
}: {
  report: LearningReport;
  section: number;
  onSection: (index: number) => void;
  activeAnchor: string | undefined;
  onAnchor: (anchor: EvidenceAnchor) => void;
  currentPage: number;
}) {
  const [scope, setScope] = useState<"all" | "page">("all");
  const current = report.sections[section] ?? report.sections[0];
  if (!current) return <EmptyState title="讲解尚无章节">请检查生成结果。</EmptyState>;
  const points = scope === "page"
    ? report.sections.flatMap((s) => s.points).filter((p) => p.evidence.some((a) => a.page === currentPage))
    : current.points;
  return (
    <>
      <div className="flex shrink-0 flex-wrap items-center gap-1.5 px-4 pt-3">
        <button type="button" className="icon-btn shadow-card" disabled={section <= 0 || scope === "page"} onClick={() => onSection(section - 1)} aria-label="上一节">
          <ChevronLeft className="h-4 w-4" />
        </button>
        <label className="min-w-[120px] flex-1">
          <span className="sr-only">章节</span>
          <select
            value={section}
            onChange={(event) => onSection(Number(event.target.value))}
            disabled={scope === "page"}
            className="h-8 w-full rounded-lg bg-card px-2.5 text-[13px] font-medium shadow-card outline-none disabled:opacity-50"
          >
            {report.sections.map((s, i) => (
              <option key={s.section_type} value={i}>{SECTION_LABELS[s.section_type] ?? s.title} · {i + 1} / {report.sections.length}</option>
            ))}
          </select>
        </label>
        <button type="button" className="icon-btn shadow-card" disabled={section >= report.sections.length - 1 || scope === "page"} onClick={() => onSection(section + 1)} aria-label="下一节">
          <ChevronRight className="h-4 w-4" />
        </button>
        <div role="radiogroup" aria-label="讲解范围" className="ml-1 flex rounded-lg bg-page p-0.5 text-xs">
          {([["all", "全文"], ["page", "当前页"]] as const).map(([value, label]) => (
            <button
              key={value}
              type="button"
              role="radio"
              aria-checked={scope === value}
              onClick={() => setScope(value)}
              className={clsx("h-7 rounded-md px-2.5", scope === value ? "bg-card font-semibold shadow-card" : "text-ink-4")}
            >
              {label}
            </button>
          ))}
        </div>
      </div>
      <div className="min-h-0 flex-1 overflow-auto px-5 py-4">
        {scope === "all" && <p className="mb-5 text-[15px] leading-[1.8]">{current.overview}</p>}
        {scope === "page" && <p className="mb-4 text-xs text-ink-4">第 {currentPage} 页相关的讲解要点 · {points.length} 条</p>}
        <ol className="flex flex-col gap-5">
          {points.map((point, index) => (
            <li key={`${point.title}-${index}`} className="flex gap-3">
              <span
                aria-hidden
                className={clsx("w-[3px] shrink-0 rounded-full", point.evidence.some((a) => a.chunk_id === activeAnchor) ? "bg-yellow-400" : "bg-line")}
              />
              <div className="flex min-w-0 flex-col gap-1.5">
                <h3 className="text-sm font-semibold">{point.title}</h3>
                <p className="text-sm leading-[1.75] text-ink-2">{point.explanation}</p>
                <div className="flex flex-wrap gap-1.5">
                  {point.evidence.map((anchor) => (
                    <CitationChip key={anchor.chunk_id} anchor={anchor} active={anchor.chunk_id === activeAnchor} onClick={() => onAnchor(anchor)} />
                  ))}
                </div>
              </div>
            </li>
          ))}
        </ol>
        {points.length === 0 && <p className="text-sm text-ink-4">这一页没有对应的讲解要点。</p>}
      </div>
    </>
  );
}

function QaView({ projectId, selected, onSelected, onAnchor }: {
  projectId: string; selected: string | undefined; onSelected: (id: string) => void; onAnchor: (anchor: EvidenceAnchor) => void;
}) {
  const conversations = useConversations(projectId);
  if (conversations.isLoading) return <Loading />;
  if (conversations.error) return <div className="p-4"><ErrorState error={conversations.error} /></div>;
  const data = conversations.data!;
  const active = selected === "new" ? undefined : data.conversations.find((c) => c.conversation_id === (selected ?? data.active_conversation_id)) ?? data.conversations[0];
  const history = active ? [...active.paper_history, ...active.joint_history] : [];
  return <>
    <div className="flex shrink-0 items-center gap-2 px-4 pt-3">
      <label className="min-w-0 flex-1"><span className="sr-only">会话</span>
        <select value={selected === "new" ? "new" : active?.conversation_id} onChange={event => onSelected(event.target.value)} className="h-8 w-full rounded-lg bg-card px-2.5 text-[13px] shadow-card outline-none">
          <option value="new">新对话</option>
          {data.conversations.map(c => <option key={c.conversation_id} value={c.conversation_id}>{c.title}</option>)}
        </select>
      </label>
    </div>
    <div className="min-h-0 flex-1 overflow-auto px-5 py-4">
      {history.length === 0 ? <EmptyState title="从一个具体问题开始">可以问方法细节、实验数字、结果原因或局限性。回答使用本论文检索到的原文证据。</EmptyState> :
        <ol className="flex flex-col gap-5">{history.map((item, index) => <li key={index} className="flex flex-col gap-2">
          <p className="self-end rounded-xl bg-active px-3 py-2 text-sm">{item.question}</p>
          {item.answer && <p className="whitespace-pre-line text-sm leading-7">{item.answer}</p>}
          <div className="flex flex-wrap gap-1.5">{("citations" in item ? item.citations : item.paper_citations)?.map((a: EvidenceAnchor) =>
            <CitationChip key={a.chunk_id} anchor={a} active={false} onClick={() => onAnchor(a)} />)}</div>
        </li>)}</ol>}
    </div>
  </>;
}

function AskBox({ placeholder, projectId, selected, onAnswered }: {
  placeholder: string; projectId: string; selected: string | undefined; onAnswered: () => void;
}) {
  const [text, setText] = useState("");
  const client = useQueryClient();
  const question = useMutation({
    mutationFn: () => send<PaperAnswer>("POST", `/api/projects/${projectId}/qa`, {
      question: text.trim(), conversation_id: selected === "new" ? undefined : selected, new_conversation: selected === "new",
    }),
    onSuccess: async () => {
      await client.invalidateQueries({ queryKey: keys.conversations(projectId) });
      setText(""); onAnswered();
    },
  });
  return <form className="shrink-0 border-t border-line-soft p-3" onSubmit={event => {
    event.preventDefault(); if (!READ_ONLY && text.trim() && !question.isPending) question.mutate();
  }}>
    <label className="flex items-center gap-2 rounded-xl bg-[#FAFAF9] py-1.5 pl-3.5 pr-1.5 shadow-card">
      <span className="sr-only">追问</span>
      <input aria-label="追问" maxLength={1000} disabled={question.isPending} value={text} onChange={event => setText(event.target.value)} placeholder={placeholder} className="min-w-0 flex-1 bg-transparent text-sm outline-none" />
      <button type="submit" className="btn-primary h-8 w-8 px-0" disabled={READ_ONLY || !text.trim() || question.isPending} aria-label="发送"><Send className="h-4 w-4" /></button>
    </label>
    {question.isPending && <p role="status" className="mt-2 text-xs text-ink-3">正在检索论文并生成回答…</p>}
    {question.error && <div className="mt-2"><ErrorState error={question.error} /></div>}
    <div className="mt-1.5"><MockNote /></div>
  </form>;
}

function NoLecture({ projectId, project }: { projectId: string; project: ProjectDetail }) {
  const jobs = useJobs(projectId);
  const generate = useGenerateLecture(projectId);
  const failed = jobs.data?.learning.find(job => job.status === "FAILED" || job.status === "INTERRUPTED");
  const running = jobs.data?.learning.find((job) => job.status === "QUEUED" || job.status === "RUNNING");
  const [page, setPage] = useState(1);
  return (
    <ResponsiveReader source={<PdfPanel projectId={projectId} page={page} pageCount={project.page_count} pageSizes={project.pages} onPage={setPage} />}>
      <section className="card self-start">
        {running ? (
          <div className="flex flex-col gap-3 p-6">
            <h2 className="text-lg font-semibold">论文讲解正在后台生成</h2>
            <Progress value={running.progress} label={running.stage} />
          </div>
        ) : (
          <EmptyState title="这篇论文还没有讲解" action={<button type="button" className="btn-primary self-start" disabled={READ_ONLY || generate.isPending} onClick={() => generate.mutate()}>{generate.isPending ? "正在提交…" : failed ? "重试生成讲解" : "生成讲解"}</button>}>
            {failed && <span role="alert" className="mb-2 block text-bad">上次任务未完成：{failed.error || failed.stage}</span>}
            {generate.error && <ErrorState error={generate.error} />}
            {jobs.error && <ErrorState error={jobs.error} />}
            生成后可以按章节阅读中文讲解、点击引用跳回原文高亮，并围绕论文继续追问。
            <span className="mt-2 block text-xs text-ink-4">生成讲解会把论文文本发送到你配置的模型服务。</span>
            <span className="mt-1 block"><MockNote /></span>
          </EmptyState>
        )}
      </section>
    </ResponsiveReader>
  );
}

export function ReaderPage() {
  const { projectId = "" } = useParams();
  const [params, setParams] = useSearchParams();
  const project = useProject(projectId);
  const lecture = useLecture(projectId);
  const view = (params.get("view") as View | null) ?? "lecture";
  const rawSection = Number(params.get("section") ?? 0);
  const section = Number.isFinite(rawSection) ? Math.max(0, Math.floor(rawSection)) : 0;
  const [selectedConversation, setSelectedConversation] = useState<string | undefined>();
  const [page, setPage] = useState(1);
  const [anchor, setAnchor] = useState<EvidenceAnchor | undefined>();
  const [pane, setPane] = useState<"source" | "assistant">(view === "qa" ? "assistant" : "source");

  const setParam = (key: string, value: string) =>
    setParams((current) => {
      const next = new URLSearchParams(current);
      next.set(key, value);
      return next;
    }, { replace: true });

  const highlights: PageRect[] = useMemo(() => (anchor && anchor.page === page ? anchor.rects : []), [anchor, page]);
  const exportActions = lecture.data && !USE_MOCK ? (
    <a className="icon-btn" href={resourceUrl(`/api/projects/${projectId}/lecture/export?format=md`)} aria-label="导出讲解" title="导出讲解"><Download className="h-4 w-4" /></a>
  ) : null;

  return (
    <>
      <TopBar actions={exportActions} />
      {lecture.isLoading || project.isLoading ? <Loading /> : lecture.error ? <ErrorState error={lecture.error} /> : !lecture.data ? (
        project.data && <NoLecture projectId={projectId} project={project.data} />
      ) : project.data && (
        <ResponsiveReader pane={pane} onPane={setPane} source={<PdfPanel
            projectId={projectId}
            page={page}
            pageCount={project.data.page_count}
            pageSizes={project.data.pages}
            onPage={setPage}
            highlights={highlights}
            footer={
              anchor?.page
                ? `高亮：${anchorLabel(anchor)}`
                : project.data.suggested_pages.length
                  ? `建议重点读第 ${project.data.suggested_pages.join("、")} 页`
                  : "点击右侧讲解中的引用，可跳到原文并高亮"
            }
          />}>
          <section className="card flex h-full min-h-0 min-w-0 flex-col" aria-label="讲解与追问">
            <div role="tablist" aria-label="助手" className="flex h-11 shrink-0 gap-5 border-b border-line-soft px-5">
              {([["lecture", "讲解"], ["qa", "追问"]] as [View, string][]).map(([value, label]) => (
                <button
                  key={value}
                  type="button"
                  role="tab"
                  aria-selected={view === value}
                  onClick={() => setParam("view", value)}
                  className={clsx("-mb-px border-b-2 text-sm", view === value ? "border-ink font-semibold" : "border-transparent text-ink-4 hover:text-ink")}
                >
                  {label}
                </button>
              ))}
            </div>
            {view === "lecture" ? (
              <LectureView
                report={lecture.data}
                section={Math.min(section, lecture.data.sections.length - 1)}
                onSection={(index) => setParam("section", String(index))}
                activeAnchor={anchor?.chunk_id}
                onAnchor={(next) => { setAnchor(next); if (next.page) setPage(next.page); setPane("source"); }}
                currentPage={page}
              />
            ) : (
              <QaView projectId={projectId} selected={selectedConversation} onSelected={setSelectedConversation} onAnchor={next => { setAnchor(next); if (next.page) setPage(next.page); setPane("source"); }} />
            )}
            <AskBox projectId={projectId} selected={selectedConversation} onAnswered={() => { setSelectedConversation(undefined); setParam("view", "qa"); setPane("assistant"); }} placeholder={view === "lecture" ? `追问「${SECTION_LABELS[lecture.data.sections[Math.min(section, lecture.data.sections.length - 1)]?.section_type] ?? "本节"}」…` : "就这篇论文问点什么…"} />
          </section>
        </ResponsiveReader>
      )}
    </>
  );
}
