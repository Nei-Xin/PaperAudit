import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { ChevronLeft, ChevronRight, Download } from "lucide-react";
import clsx from "clsx";
import {
  useGenerateLecture,
  useJobs,
  useLecture,
  useProject,
  useRetryLecture,
} from "@/api/queries";
import { READ_ONLY, USE_MOCK, resourceUrl } from "@/api/client";
import type {
  EvidenceAnchor,
  LearningReport,
  PageRect,
  PaperSelection,
  CodeSelection,
  CodeCitation,
} from "@/api/types";
import { QaView, AskBox } from "./ConversationPanel";
import { LectureTools } from "./LectureTools";
import { CodeWorkspace } from "./CodeWorkspace";
import { TopBar } from "@/app/ProjectLayout";
import { ResponsiveReader } from "@/components/ResponsiveReader";
import { PdfPanel } from "@/components/PdfPanel";
import {
  EmptyState,
  ErrorState,
  Loading,
  MockNote,
  Progress,
} from "@/components/States";
import { SECTION_LABELS, anchorLabel } from "@/lib/labels";

type View = "lecture" | "qa" | "code";

function CitationChip({
  anchor,
  active,
  onClick,
}: {
  anchor: EvidenceAnchor;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={!anchor.page}
      className={clsx(
        "inline-flex min-h-6 max-w-full items-center break-words rounded-md px-2 py-1 text-left text-xs font-medium transition-colors",
        active
          ? "bg-accent text-white"
          : "bg-accent-soft text-accent hover:bg-[#E2EAF3]",
      )}
      title={anchor.text ?? undefined}
    >
      {anchorLabel(anchor)} ↗
    </button>
  );
}

function LectureView({
  projectId,
  report,
  section,
  onSection,
  activeAnchor,
  onAnchor,
  currentPage,
  onPage,
}: {
  projectId: string;
  report: LearningReport;
  section: number;
  onSection: (index: number) => void;
  activeAnchor: string | undefined;
  onAnchor: (anchor: EvidenceAnchor) => void;
  currentPage: number;
  onPage: (page: number) => void;
}) {
  const [scope, setScope] = useState<"section" | "all" | "page">("section");
  const scroll = useRef<HTMLDivElement>(null);
  useEffect(() => { scroll.current?.scrollTo({ top: 0 }); }, [section, scope]);
  const current = report.sections[section] ?? report.sections[0];
  if (!current)
    return <EmptyState title="讲解尚无章节">请检查生成结果。</EmptyState>;
  const points =
    scope === "page"
      ? report.sections
          .flatMap((s) => s.points)
          .filter((p) => p.evidence.some((a) => a.page === currentPage))
      : scope === "all" ? report.sections.flatMap(s => s.points) : current.points;
  return (
    <>
      <div className="flex shrink-0 flex-wrap items-center gap-1.5 px-4 pt-3">
        <button
          type="button"
          className="icon-btn shadow-card"
          disabled={section <= 0 || scope !== "section"}
          onClick={() => onSection(section - 1)}
          aria-label="上一节"
        >
          <ChevronLeft className="h-4 w-4" />
        </button>
        <label className="min-w-[120px] flex-1">
          <span className="sr-only">章节</span>
          <select
            value={section}
            onChange={(event) => onSection(Number(event.target.value))}
            disabled={scope !== "section"}
            className="h-8 w-full rounded-lg bg-card px-2.5 text-[13px] font-medium shadow-card outline-none disabled:opacity-50"
          >
            {report.sections.map((s, i) => (
              <option key={s.section_type} value={i}>
                {SECTION_LABELS[s.section_type] ?? s.title} · {i + 1} /{" "}
                {report.sections.length}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          className="icon-btn shadow-card"
          disabled={section >= report.sections.length - 1 || scope !== "section"}
          onClick={() => onSection(section + 1)}
          aria-label="下一节"
        >
          <ChevronRight className="h-4 w-4" />
        </button>
        <div
          role="radiogroup"
          aria-label="讲解范围"
          className="ml-1 flex rounded-lg bg-page p-0.5 text-xs"
        >
          {(
            [
              ["section", "本节全部"],
              ["all", "全部章节"],
              ["page", "当前页"],
            ] as const
          ).map(([value, label]) => (
            <button
              key={value}
              type="button"
              role="radio"
              aria-checked={scope === value}
              onClick={() => setScope(value)}
              className={clsx(
                "h-7 rounded-md px-2.5",
                scope === value
                  ? "bg-card font-semibold shadow-card"
                  : "text-ink-4",
              )}
            >
              {label}
            </button>
          ))}
        </div>
      </div>
      <div ref={scroll} className="min-h-0 flex-1 overflow-auto px-5 py-4">
        <div className="-mx-5 -mt-4 mb-4"><LectureTools projectId={projectId} /></div>
        <section className="mb-5 rounded-lg bg-page p-3" aria-label="阅读导览">
          <p className="text-sm leading-7">{report.one_sentence_summary}</p>
          <p className="mt-1 text-xs text-ink-4">{report.sections.length} 个章节 · {report.sections.reduce((n, s) => n + s.points.length, 0)} 个要点</p>
          {report.suggested_pages.length > 0 && <details className="mt-2 text-xs text-ink-3">
            <summary className="cursor-pointer">推荐阅读页</summary>
            <div className="mt-2 flex flex-wrap gap-2">{report.suggested_pages.map(p => <button key={p} type="button" className="btn-secondary" onClick={() => onPage(p)}>第 {p} 页</button>)}</div>
          </details>}
        </section>
        {scope === "section" && (
          <div className="mb-5"><p className="mb-2 text-xs text-ink-4">本节 {current.points.length} 个要点</p><p className="text-[15px] leading-[1.8]">{current.overview}</p></div>
        )}
        {scope === "page" && (
          <p className="mb-4 text-xs text-ink-4">
            第 {currentPage} 页相关的讲解要点 · {points.length} 条
          </p>
        )}
        {(scope === "all" ? report.sections : [{ ...current, points }]).map((group) => (
        <section key={group.section_type} className="mb-5">
          {scope === "all" && <><h2 className="mb-2 text-base font-semibold">{SECTION_LABELS[group.section_type] ?? group.title} · {group.points.length} 点</h2><p className="mb-4 text-sm leading-7">{group.overview}</p></>}
        <ol className="flex flex-col gap-5">
          {group.points.map((point, index) => (
            <li key={`${point.title}-${index}`} className="flex gap-3">
              <span
                aria-hidden
                className={clsx(
                  "w-[3px] shrink-0 rounded-full",
                  point.evidence.some((a) => a.chunk_id === activeAnchor)
                    ? "bg-yellow-400"
                    : "bg-line",
                )}
              />
              <div className="flex min-w-0 flex-col gap-1.5">
                <h3 className="text-sm font-semibold">{point.title}{point.key_point && <span className="ml-2 whitespace-nowrap rounded bg-accent-soft px-1.5 py-0.5 text-xs font-normal text-accent">重点</span>}</h3>
                <p className="whitespace-pre-line break-words text-sm leading-[1.75] text-ink-2">
                  {point.explanation}
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {point.evidence.map((anchor, evidenceIndex) => (
                    <CitationChip
                      key={`${anchor.chunk_id}-${evidenceIndex}`}
                      anchor={anchor}
                      active={anchor.chunk_id === activeAnchor}
                      onClick={() => onAnchor(anchor)}
                    />
                  ))}
                </div>
              </div>
            </li>
          ))}
        </ol>
        </section>))}
        {points.length === 0 && (
          <p className="text-sm text-ink-4">{scope === "page" ? "这一页没有对应的讲解要点。" : "本节暂无独立要点，请参阅章节导读。"}</p>
        )}
      </div>
    </>
  );
}

function NoLecture({ projectId }: { projectId: string }) {
  const jobs = useJobs(projectId);
  const generate = useGenerateLecture(projectId);
  const retry = useRetryLecture(projectId);
  const latest = jobs.data?.learning[0];
  const failed = latest && ["FAILED", "INTERRUPTED"].includes(latest.status) ? latest : undefined;
  const running = jobs.data?.learning.find(
    (job) => job.status === "QUEUED" || job.status === "RUNNING",
  );
  return (
    <div className="min-h-0 flex-1 overflow-auto">
      <section className="card self-start">
        {running ? (
          <div className="flex flex-col gap-3 p-6">
            <h2 className="text-lg font-semibold">论文讲解正在后台生成</h2>
            <Progress value={running.progress} label={running.stage} />
          </div>
        ) : (
          <EmptyState
            title="这篇论文还没有讲解"
            action={
              <button
                type="button"
                className="btn-primary self-start"
                disabled={READ_ONLY || generate.isPending || retry.isPending}
                onClick={() => failed ? retry.mutate(failed.job_id) : generate.mutate(undefined)}
              >
                {generate.isPending || retry.isPending
                  ? "正在提交…"
                  : failed
                    ? "重试生成讲解"
                    : "生成讲解"}
              </button>
            }
          >
            {failed && (
              <span role="alert" className="mb-2 block text-bad">
                上次任务未完成：{failed.error || failed.stage}
              </span>
            )}
            {generate.error && <ErrorState error={generate.error} />}
            {retry.error && <ErrorState error={retry.error} />}
            {jobs.error && <ErrorState error={jobs.error} />}
            生成后可以按章节阅读中文讲解、点击引用跳回原文高亮，并围绕论文继续追问。
            <span className="mt-2 block text-xs text-ink-4">
              生成讲解会把论文文本发送到你配置的模型服务。
            </span>
            <span className="mt-1 block">
              <MockNote />
            </span>
          </EmptyState>
        )}
      </section>
    </div>
  );
}

export function ReaderPage() {
  const { projectId = "" } = useParams();
  return <Reader key={projectId} projectId={projectId} />;
}
function Reader({ projectId }: { projectId: string }) {
  const [params, setParams] = useSearchParams();
  const project = useProject(projectId);
  const lecture = useLecture(projectId);
  const view: View =
    params.get("view") === "code"
      ? "code"
      : params.get("view") === "qa"
        ? "qa"
        : "lecture";
  const rawSection = Number(params.get("section") ?? 0);
  const section = Number.isFinite(rawSection)
    ? Math.max(0, Math.floor(rawSection))
    : 0;
  const [selectedConversation, setSelectedConversation] = useState<
    string | undefined
  >();
  const [page, setPage] = useState(1);
  const [anchor, setAnchor] = useState<EvidenceAnchor>();
  const [selection, setSelection] = useState<PaperSelection>();
  const [selectedCode, setSelectedCode] = useState<CodeSelection>();
  const [codeCitation, setCodeCitation] = useState<CodeCitation>();
  const [busy, setBusy] = useState(false);
  const [pane, setPane] = useState<"source" | "assistant">(
    view === "qa" ? "assistant" : "source",
  );
  const setParam = useCallback(
    (key: string, value: string) =>
      setParams(
        (current) => {
          const next = new URLSearchParams(current);
          next.set(key, value);
          return next;
        },
        { replace: true },
      ),
    [setParams],
  );
  const selectPaper = useCallback(
    (value: PaperSelection) => {
      setSelection(value);
      setParam("view", "qa");
      setPane("assistant");
    },
    [setParam],
  );
  const openAnchor = (next: EvidenceAnchor) => {
    setAnchor(next);
    if (next.page) setPage(next.page);
    if (view === "code") setParam("view", "qa");
    setPane("source");
  };
  const openCode = (citation: CodeCitation) => {
    setCodeCitation(citation);
    setParams(
      (current) => {
        const next = new URLSearchParams(current);
        next.set("view", "code");
        next.set("file", citation.path);
        return next;
      },
      { replace: true },
    );
    setPane("source");
  };
  // Pages the lecture cites get a dot in the thumbnail strip.
  const citedPages = useMemo(() => new Set(
    (lecture.data?.sections ?? []).flatMap((s) => s.points.flatMap((p) => p.evidence.map((e) => e.page ?? 0))).filter(Boolean),
  ), [lecture.data]);
  const highlights: PageRect[] = useMemo(
    () => (anchor && anchor.page === page ? anchor.rects : []),
    [anchor, page],
  );
  const exportActions =
    lecture.data && !USE_MOCK ? (
      <a
        className="icon-btn"
        href={resourceUrl(
          `/api/projects/${projectId}/lecture/export?format=md`,
        )}
        aria-label="导出讲解"
        title="导出讲解"
      >
        <Download className="h-4 w-4" />
      </a>
    ) : null;
  return (
    <>
      <TopBar actions={exportActions} />
      {project.isLoading || lecture.isLoading ? (
        <Loading />
      ) : project.error ? (
        <ErrorState error={project.error} />
      ) : lecture.error ? (
        <ErrorState error={lecture.error} />
      ) : (
        project.data && (
          <ResponsiveReader
            pane={pane}
            onPane={setPane}
            sourceLabel={view === "code" ? "代码文件" : "论文原文"}
            source={
              view === "code" ? (
                <CodeWorkspace
                  projectId={projectId}
                  hasCode={project.data.has_code}
                  path={params.get("file") ?? ""}
                  onPath={(p) => {
                    setParam("file", p);
                    setCodeCitation(undefined);
                  }}
                  onSelect={(s) => {
                    setSelectedCode(s);
                    setPane("assistant");
                  }}
                  onReplaced={() => {
                    setSelectedCode(undefined);
                    setCodeCitation(undefined);
                  }}
                  citation={codeCitation}
                  busy={busy}
                />
              ) : (
                <PdfPanel
                  thumbnails
                  markedPages={citedPages}
                  projectId={projectId}
                  page={page}
                  pageCount={project.data.page_count}
                  pageSizes={project.data.pages}
                  onPage={setPage}
                  highlights={highlights}
                  onSelection={!READ_ONLY && !busy ? selectPaper : undefined}
                  footer={
                    anchor?.page
                      ? `高亮：${anchorLabel(anchor)}`
                      : "选中原文可以提问，点击回答引用可以定位证据"
                  }
                />
              )
            }
          >
            <section
              className="card flex h-full min-h-0 min-w-0 flex-col"
              aria-label="讲解与追问"
            >
              <div
                role="tablist"
                aria-label="助手"
                className="flex h-11 shrink-0 gap-5 border-b border-line-soft px-5"
              >
                {(
                  [
                    ["lecture", "讲解"],
                    ["qa", "追问"],
                    ["code", "代码"],
                  ] as const
                ).map(([value, label]) => (
                  <button
                    key={value}
                    role="tab"
                    aria-selected={view === value}
                    disabled={busy}
                    onClick={() => {
                      setParam("view", value);
                      if (value === "code") setPane("source");
                    }}
                    className={clsx(
                      "-mb-px border-b-2 text-sm",
                      view === value
                        ? "border-ink font-semibold"
                        : "border-transparent text-ink-4",
                    )}
                  >
                    {label}
                  </button>
                ))}
              </div>
              {view === "lecture" ? (
                lecture.data ? (
                  <>
                    <LectureView
                      projectId={projectId}
                      report={lecture.data}
                      section={Math.min(
                        section,
                        lecture.data.sections.length - 1,
                      )}
                      onSection={(i) => setParam("section", String(i))}
                      activeAnchor={anchor?.chunk_id}
                      onAnchor={openAnchor}
                      currentPage={page}
                      onPage={(p) => { setAnchor(undefined); setPage(p); setPane("source"); }}
                    />
                  </>
                ) : (
                  <NoLecture projectId={projectId} />
                )
              ) : (
                <QaView
                  projectId={projectId}
                  selected={selectedConversation}
                  onSelected={setSelectedConversation}
                  onAnchor={openAnchor}
                  onCode={openCode}
                  busy={busy}
                />
              )}
              <AskBox
                projectId={projectId}
                selected={selectedConversation}
                hasCode={project.data.has_code}
                page={page}
                selection={selection}
                selectedCode={selectedCode}
                onClearPaper={() => setSelection(undefined)}
                onClearCode={() => setSelectedCode(undefined)}
                onBusy={setBusy}
                onAnswered={() => {
                  setSelectedConversation(undefined);
                  if (view !== "code") setParam("view", "qa");
                  setPane("assistant");
                }}
                placeholder={
                  view === "code"
                    ? "结合论文和代码提问…"
                    : "就这篇论文问点什么…"
                }
              />
            </section>
          </ResponsiveReader>
        )
      )}
    </>
  );
}
