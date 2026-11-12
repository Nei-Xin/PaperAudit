import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { READ_ONLY } from "@/api/client";
import { TopBar } from "@/app/ProjectLayout";
import {
  useConsistencyJobs,
  useConsistencyPlan,
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
import { FindingLabel, VerificationDetails, PaperSourceContext, needsReview, InvestigationTrace, VERDICTS } from "@/features/reader/investigation";

import { ConsistencyProgress } from "./ConsistencyProgress";
import { CATEGORY, ConsistencyPlanReview } from "./ConsistencyPlanReview";

type Group =
  | "INCONSISTENT"
  | "PARTIAL"
  | "NOT_LOCATED"
  | "REVIEW"
  | "UNRESOLVED"
  | "SKIPPED"
  | "CONSISTENT";

const GROUPS: { key: Group; title: string; hint: string }[] = [
  { key: "REVIEW", title: "待核对", hint: "证据支持复核未通过或未完成，保留原判定供人工核对" },
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
  if (findings.some(needsReview)) return "REVIEW";
  for (const verdict of ["INCONSISTENT", "PARTIAL", "NOT_LOCATED"] as const)
    if (findings.some((f) => f.verdict === verdict)) return verdict;
  return "CONSISTENT";
}

export function ConsistencyPage() {
  const { projectId = "" } = useParams();
  return <ConsistencyWorkspace key={projectId} projectId={projectId} />;
}

function ConsistencyWorkspace({ projectId }: { projectId: string }) {
  const project = useProject(projectId);
  const hasCode = project.data?.has_code ?? false;
  const jobs = useConsistencyJobs(projectId, hasCode);
  const start = useStartConsistency(projectId);
  const [ack, setAck] = useState(false);
  const [limit, setLimit] = useState(20);
  const [strategy, setStrategy] = useState<"one-shot" | "agent">("one-shot");
  const active = jobs.data?.find(
    (job) => job.status === "QUEUED" || job.status === "RUNNING",
  );
  const latest = jobs.data?.[0];
  const plans = jobs.data?.filter(job => job.kind === "plan" && job.status === "SUCCEEDED" && job.plan_id) ?? [];
  const [chosenPlan, setChosenPlan] = useState<string>();
  const planId = chosenPlan ?? plans[0]?.plan_id;
  const plan = useConsistencyPlan(projectId, planId);
  const finished = jobs.data?.filter((job) => job.report_id) ?? [];
  const [chosen, setChosen] = useState<string>();
  const reportId = chosen ?? finished[0]?.report_id;
  const report = useConsistencyReport(projectId, reportId);
  const eventJob = active ?? (chosen ? finished.find(job => job.report_id === chosen)
    : chosenPlan ? plans.find(job => job.plan_id === chosenPlan) : latest);

  if (project.error) return <ErrorState error={project.error} />;
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
              先阅读论文并提出核对要点，由你审阅和选择，再逐项调查代码实现。结果附带可定位的论文与代码引用。
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
                    start.mutate({ privacy_ack: true, max_checkpoints: limit, mode: "plan", planning_strategy: strategy }, { onSuccess: () => setChosenPlan(undefined) });
                }}
              >
                <label className="flex items-center gap-2 text-ink-3">
                  规划方式
                  <select className="rounded bg-page p-1" value={strategy}
                    onChange={e => setStrategy(e.target.value as "one-shot" | "agent")}>
                    <option value="one-shot">单次规划（默认）</option>
                    <option value="agent">自主阅读规划（实验）</option>
                  </select>
                </label>
                <label className="flex items-center gap-2 text-ink-3">
                  目标要点数
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
                  {plans.length ? "重新生成规划" : "1. 生成核对规划"}
                </button>
                <span className="basis-full text-xs text-ink-4">
                  规划完成后等待你确认，可取消部分要点或补充问题。
                  {strategy === "agent" && " 自主阅读会多次调用模型，成本较高，目前尚未证明覆盖更好。"}
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
          {plans.length > 1 && <label className="flex items-center gap-2 text-sm">查看历史规划
            <select className="min-w-0 rounded bg-card p-2" value={planId ?? ""} onChange={e => setChosenPlan(e.target.value)}>
              {plans.map(job => <option key={job.job_id} value={job.plan_id ?? ""}>{new Date(job.created_at).toLocaleString("zh-CN")}</option>)}
            </select>
          </label>}
          {plan.error && <ErrorState error={plan.error} />}
          {planId && plan.isLoading && <Loading />}
          {eventJob && <ConsistencyProgress key={eventJob.job_id} projectId={projectId} job={eventJob} />}
          {plan.data && <ConsistencyPlanReview key={`${projectId}:${planId}`} projectId={projectId} plan={plan.data}
            busy={Boolean(active) || start.isPending} onExecute={() => setChosen(undefined)} />}
          {reportId && <h3 className="px-1 text-[15px] font-semibold">3. 核对报告</h3>}
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
          {s.not_located} · 待核对 {s.pending_review ?? 0}）。规划提出 {report.planned} 个，剔除{" "}
          {report.plan_rejected} 个（引文不在论文中或重复），另有{" "}
          {report.plan_over_limit ?? 0} 个因数量上限未选入，{report.plan_unselected ?? 0} 个未选择。已选项中 {s.not_checked} 个因请求预算不足未执行。用了{" "}
          {report.requests} 次模型请求（上限 {report.max_requests}），耗时{" "}
          {Math.round(report.elapsed_seconds)} 秒。
        </p>
      </section>
      {report.repo_map && <details className="rounded-card bg-card p-4 text-sm text-ink-3">
        <summary className="cursor-pointer">仓库地图 · {report.repo_map_reused ? "复用已保存地图" : "本次生成"} · 新增 {report.repo_map_requests ?? 0} 次请求</summary>
        <p className="mt-2 text-xs text-ink-4">仅帮助定位；判定仍须引用本次实际读到的代码。替换代码后地图失效。</p>
        {!report.repo_map.entries.length && <p className="mt-2">未生成可用地图，本次调查照常进行。</p>}
        <ul className="mt-2 space-y-2">
          {report.repo_map.entries.map((entry, n) => <li key={n}>
            <Link className="break-all text-accent" to={`/p/${projectId}/read?view=code&file=${encodeURIComponent(entry.path)}`}>
              {entry.path} · L{entry.start_line}–{entry.end_line}
            </Link><span className="ml-2">{entry.role}</span>
          </li>)}
        </ul>
      </details>}
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
  REVIEW: "bg-warn-soft text-warn-text",
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
      {anchor ? <blockquote className="mt-2 border-l-2 border-line pl-3 text-sm leading-6 text-ink-2">
        {anchor.quote}
        <span className="ml-2 text-xs text-ink-4">论文第 {anchor.page} 页</span>
      </blockquote> : <p className="mt-2 text-sm text-ink-3">补充问题：{checkpoint.question}</p>}
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
      <FindingLabel finding={finding} />
      {finding.text}
      <VerificationDetails finding={finding} />
      {(finding.paper_citations ?? []).map((a, k) => (
        <div key={`p${k}`} className="mt-1.5 text-xs leading-5 text-ink-3">
          <p><span className="text-ink-4">论文第 {a.page} 页：</span>{a.quote}</p>
          <PaperSourceContext anchor={a} />
        </div>
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
