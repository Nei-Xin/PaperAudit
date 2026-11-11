import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { READ_ONLY } from "@/api/client";
import { TopBar } from "@/app/ProjectLayout";
import {
  useConsistencyJobs,
  useConsistencyReport,
  useProject,
  useStartConsistency,
} from "@/api/queries";
import type {
  ConsistencyItem,
  ConsistencyReport,
  PaperCodeFinding,
} from "@/api/types";
import {
  EmptyState,
  ErrorState,
  Loading,
  MockNote,
  Progress,
} from "@/components/States";
import { InvestigationTrace, VERDICTS } from "@/features/reader/investigation";

const CATEGORY: Record<ConsistencyItem["checkpoint"]["category"], string> = {
  hyperparameter: "超参数",
  architecture: "结构",
  training: "训练",
  data: "数据",
  evaluation: "评估",
  other: "其他",
};

type Group =
  | "INCONSISTENT"
  | "PARTIAL"
  | "NOT_LOCATED"
  | "UNRESOLVED"
  | "SKIPPED"
  | "CONSISTENT";

const GROUPS: { key: Group; title: string; hint: string }[] = [
  {
    key: "INCONSISTENT",
    title: "不一致",
    hint: "论文与代码给出了不同的取值或做法",
  },
  { key: "PARTIAL", title: "部分对应", hint: "代码只实现了论文描述的一部分" },
  {
    key: "NOT_LOCATED",
    title: "未定位",
    hint: "本次调查没有在代码中找到，不代表仓库里一定没有",
  },
  {
    key: "UNRESOLVED",
    title: "证据不足",
    hint: "调查完成，但证据不足以下结论",
  },
  { key: "SKIPPED", title: "未完成", hint: "达到请求上限或调查失败，没有结论" },
  { key: "CONSISTENT", title: "一致", hint: "论文与代码说的是同一件事" },
];

/** An item sits in the group of its most serious finding, so nothing inconsistent hides under "一致". */
function groupOf(item: ConsistencyItem): Group {
  if (item.status !== "checked" || !item.answer) return "SKIPPED";
  const findings = item.answer.findings ?? [];
  if (item.answer.status !== "ANSWERED" || findings.length === 0)
    return "UNRESOLVED";
  for (const verdict of ["INCONSISTENT", "PARTIAL", "NOT_LOCATED"] as const)
    if (findings.some((f) => f.verdict === verdict)) return verdict;
  return "CONSISTENT";
}

export function ConsistencyPage() {
  const { projectId = "" } = useParams();
  const project = useProject(projectId);
  const hasCode = project.data?.has_code ?? false;
  const jobs = useConsistencyJobs(projectId, hasCode);
  const start = useStartConsistency(projectId);
  const [ack, setAck] = useState(false);
  const [limit, setLimit] = useState(20);
  const active = jobs.data?.find(
    (job) => job.status === "QUEUED" || job.status === "RUNNING",
  );
  const latest = jobs.data?.[0];
  const finished = jobs.data?.filter((job) => job.report_id) ?? [];
  const [chosen, setChosen] = useState<string>();
  const reportId = chosen ?? finished[0]?.report_id;
  const report = useConsistencyReport(projectId, reportId);

  if (!project.data) return <Loading />;
  if (!hasCode)
    return (
      <div className="flex h-full min-h-0 min-w-0 flex-col">
        <TopBar />
        <EmptyState title="还没有代码">
          一致性审计会逐项核对论文中的做法与代码实现。请先在
          <Link className="text-accent" to={`/p/${projectId}/read?view=code`}>
            阅读页的“代码”标签
          </Link>
          上传源码 ZIP。
        </EmptyState>
      </div>
    );

  return (
    <div className="flex h-full min-h-0 min-w-0 flex-col">
      <TopBar />
      <div className="min-h-0 flex-1 overflow-auto">
        <div className="mx-auto flex w-full max-w-5xl flex-col gap-4 px-1 pb-6">
          <section className="rounded-card bg-card p-4 shadow-card">
            <h2 className="text-[15px] font-semibold">论文与代码一致性审计</h2>
            <p className="mt-1 text-sm leading-6 text-ink-3">
              先从论文中列出可以通过阅读代码核对的要点，再为每个要点单独启动一次调查并行核对。每条结论都附带论文与代码的原文引用。
            </p>
            {active ? (
              <div className="mt-3">
                <Progress value={active.progress} label={active.stage} />
              </div>
            ) : (
              <form
                className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2 text-sm"
                onSubmit={(e) => {
                  e.preventDefault();
                  if (!READ_ONLY && ack && !start.isPending)
                    start.mutate({ privacy_ack: true, max_checkpoints: limit });
                }}
              >
                <label className="flex items-center gap-2 text-ink-3">
                  最多核对
                  <select
                    className="rounded bg-page p-1"
                    value={limit}
                    onChange={(e) => setLimit(Number(e.target.value))}
                  >
                    {[5, 10, 20, 30].map((n) => (
                      <option key={n} value={n}>
                        {n} 项
                      </option>
                    ))}
                  </select>
                </label>
                <label className="flex items-center gap-2 text-ink-3">
                  <input
                    type="checkbox"
                    checked={ack}
                    onChange={(e) => setAck(e.target.checked)}
                  />
                  我同意将论文与代码片段发送到已配置的模型服务。
                </label>
                <button
                  type="submit"
                  className="btn-primary"
                  disabled={READ_ONLY || !ack || start.isPending}
                >
                  {finished.length ? "重新审计" : "开始审计"}
                </button>
                <span className="basis-full text-xs text-ink-4">
                  每个要点约需 4–8
                  次模型请求；整份审计有总请求上限，超出后剩余要点会标为未完成。
                </span>
                <MockNote />
              </form>
            )}
            {start.error && (
              <div className="mt-3">
                <ErrorState error={start.error} />
              </div>
            )}
            {!active &&
              latest &&
              (latest.status === "FAILED" ||
                latest.status === "INTERRUPTED") && (
                <div className="mt-3 flex flex-wrap items-center gap-3 rounded-lg bg-bad-soft px-3 py-2 text-sm text-bad-text">
                  <span>上一次审计未完成：{latest.error ?? latest.stage}</span>
                  <button
                    type="button"
                    className="underline"
                    disabled={READ_ONLY || start.isPending}
                    onClick={() => start.mutate({ retry: latest.job_id })}
                  >
                    重试
                  </button>
                </div>
              )}
            {finished.length > 1 && (
              <label className="mt-3 flex items-center gap-2 text-xs text-ink-3">
                查看历史结果
                <select
                  className="rounded bg-page p-1"
                  value={reportId ?? ""}
                  onChange={(e) => setChosen(e.target.value)}
                >
                  {finished.map((job) => (
                    <option key={job.job_id} value={job.report_id ?? ""}>
                      {new Date(job.created_at).toLocaleString("zh-CN")}
                    </option>
                  ))}
                </select>
              </label>
            )}
          </section>

          {jobs.error && <ErrorState error={jobs.error} />}
          {report.error && <ErrorState error={report.error} />}
          {reportId && report.isLoading && <Loading />}
          {report.data && <Report projectId={projectId} report={report.data} />}
          {!reportId && !active && jobs.data && (
            <p className="px-1 text-sm text-ink-4">还没有审计结果。</p>
          )}
        </div>
      </div>
    </div>
  );
}

function Report({
  projectId,
  report,
}: {
  projectId: string;
  report: ConsistencyReport;
}) {
  const grouped = useMemo(() => {
    const map = new Map<Group, ConsistencyItem[]>();
    for (const item of report.items) {
      const key = groupOf(item);
      map.set(key, [...(map.get(key) ?? []), item]);
    }
    return map;
  }, [report]);
  const s = report.summary;
  if (report.items.length === 0)
    return (
      <p className="px-1 text-sm text-ink-3">
        规划阶段没有从论文中找到可以通过阅读代码核对的要点。
      </p>
    );
  return (
    <div className="flex flex-col gap-4">
      <section className="rounded-card bg-card p-4 shadow-card">
        <div className="flex flex-wrap gap-2 text-sm">
          {GROUPS.map(({ key, title }) => {
            const count = grouped.get(key)?.length ?? 0;
            return (
              <a
                key={key}
                href={`#group-${key}`}
                className={`rounded-lg px-2.5 py-1 ${count ? TONE[key] : "bg-page text-ink-4"}`}
              >
                {title} {count}
              </a>
            );
          })}
        </div>
        <p className="mt-3 text-xs leading-5 text-ink-4">
          共 {s.checkpoints} 个要点，完成核对 {s.checked}{" "}
          个；上方按要点计数，一个要点可包含多条发现（一致 {s.consistent} ·
          不一致 {s.inconsistent} · 部分对应 {s.partial} · 未定位{" "}
          {s.not_located}）。规划提出 {report.planned} 个，剔除{" "}
          {report.plan_rejected} 个（引文不在论文中或重复），另有{" "}
          {report.plan_over_limit ?? 0} 个因超出上限未核对。用了{" "}
          {report.requests} 次模型请求（上限 {report.max_requests}），耗时{" "}
          {Math.round(report.elapsed_seconds)} 秒。
        </p>
      </section>
      {GROUPS.map(({ key, title, hint }) => {
        const items = grouped.get(key);
        if (!items?.length) return null;
        return (
          <section
            key={key}
            id={`group-${key}`}
            className="flex flex-col gap-2"
          >
            <h3 className="px-1 text-sm font-semibold">
              {title} · {items.length}
              <span className="ml-2 font-normal text-ink-4">{hint}</span>
            </h3>
            {items.map((item) => (
              <Item
                key={item.checkpoint.checkpoint_id}
                projectId={projectId}
                item={item}
              />
            ))}
          </section>
        );
      })}
    </div>
  );
}

const TONE: Record<Group, string> = {
  INCONSISTENT: VERDICTS.INCONSISTENT.tone,
  PARTIAL: VERDICTS.PARTIAL.tone,
  NOT_LOCATED: VERDICTS.NOT_LOCATED.tone,
  UNRESOLVED: "bg-line-soft text-ink-3",
  SKIPPED: "bg-line-soft text-ink-3",
  CONSISTENT: VERDICTS.CONSISTENT.tone,
};

function Item({
  projectId,
  item,
}: {
  projectId: string;
  item: ConsistencyItem;
}) {
  const { checkpoint, answer } = item;
  const anchor = checkpoint.paper_anchor;
  const findings = answer?.findings ?? [];
  return (
    <article className="rounded-card bg-card p-4 shadow-card">
      <header className="flex flex-wrap items-baseline gap-2">
        <h4 className="text-sm font-semibold">{checkpoint.topic}</h4>
        <span className="rounded bg-page px-1.5 py-0.5 text-xs text-ink-3">
          {CATEGORY[checkpoint.category]}
        </span>
        <span className="text-xs text-ink-4">{checkpoint.checkpoint_id}</span>
      </header>
      <blockquote className="mt-2 border-l-2 border-line pl-3 text-sm leading-6 text-ink-2">
        {anchor.quote}
        <span className="ml-2 text-xs text-ink-4">论文第 {anchor.page} 页</span>
      </blockquote>
      {item.note && <p className="mt-2 text-sm text-ink-3">{item.note}</p>}
      {answer && findings.length === 0 && (
        <p className="mt-2 whitespace-pre-line text-sm leading-6 text-ink-3">
          {answer.answer}
        </p>
      )}
      {findings.length > 0 && (
        <ol className="mt-3 flex flex-col gap-2">
          {findings.map((finding, n) => (
            <Finding key={n} projectId={projectId} finding={finding} />
          ))}
        </ol>
      )}
      {answer?.investigation && (
        <div className="mt-3">
          <InvestigationTrace trace={answer.investigation} />
        </div>
      )}
    </article>
  );
}

function Finding({
  projectId,
  finding,
}: {
  projectId: string;
  finding: PaperCodeFinding;
}) {
  return (
    <li className="rounded-lg bg-page px-3 py-2 text-sm leading-6">
      <span
        className={`mr-2 rounded px-1.5 py-0.5 text-xs ${VERDICTS[finding.verdict].tone}`}
      >
        {VERDICTS[finding.verdict].label}
      </span>
      {finding.text}
      {(finding.paper_citations ?? []).map((a, k) => (
        <p key={`p${k}`} className="mt-1.5 text-xs leading-5 text-ink-3">
          <span className="text-ink-4">论文第 {a.page} 页：</span>
          {a.quote}
        </p>
      ))}
      {(finding.code_citations ?? []).map((c, k) => (
        <div key={`c${k}`} className="mt-1.5">
          <Link
            className="break-all text-xs text-accent"
            to={`/p/${projectId}/read?view=code&file=${encodeURIComponent(c.path)}`}
          >
            {c.path} · L{c.start_line}–{c.end_line} ↗
          </Link>
          <pre className="mt-1 max-h-48 overflow-auto rounded bg-card p-2 text-xs leading-5">
            {c.text}
          </pre>
        </div>
      ))}
    </li>
  );
}
