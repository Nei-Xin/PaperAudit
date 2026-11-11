// Shared presentation of paper-code investigation results: verdict labels and
// the collapsible record of what an investigation did.
import type { JointAnswer, PaperCodeFinding } from "@/api/types";

export const VERDICTS: Record<
  NonNullable<JointAnswer["findings"]>[number]["verdict"],
  { label: string; tone: string }
> = {
  CONSISTENT: { label: "一致", tone: "bg-ok-soft text-ok-text" },
  INCONSISTENT: { label: "不一致", tone: "bg-bad-soft text-bad-text" },
  PARTIAL: { label: "部分对应", tone: "bg-warn-soft text-warn-text" },
  NOT_LOCATED: { label: "未定位", tone: "bg-active text-ink-3" },
};

const TOOL_LABELS: Record<string, string> = {
  list_dir: "查看目录",
  grep_code: "全文查找",
  search_code: "检索代码",
  find_symbol: "定位符号",
  read_file: "读取文件",
  search_paper: "检索论文",
  grep_paper: "查找论文原文",
  read_page: "读取论文页",
  submit_answer: "提交结论",
  propose_checkpoint: "提出核对要点",
  finish_plan: "完成规划",
  continue_reading: "继续阅读",
  verify_findings: "复核证据支持",
};

const STOP_LABELS: Record<string, string> = {
  answered: "结论已通过引用校验",
  verification_pending: "部分发现待人工核对",
  citations_rejected: "引用未通过本地校验",
  request_limit: "达到模型请求上限",
  time_limit: "达到调查时间上限",
  invalid_model_response: "模型响应无效",
  provider_error: "模型服务请求失败",
};

export function InvestigationTrace({
  trace,
}: {
  trace: NonNullable<JointAnswer["investigation"]>;
}) {
  const steps = trace.steps ?? [];
  const rejected = trace.rejected_citations ?? [];
  return (
    <details className="rounded-lg bg-page px-3 py-2 text-xs text-ink-3">
      <summary className="cursor-pointer">
        调查过程 · {steps.length} 步 · {trace.requests} 次模型请求 ·{" "}
        {STOP_LABELS[trace.stop_reason] ?? trace.stop_reason}
        {trace.fallback && "（已改用单次检索回答）"}
      </summary>
      <AgentSteps steps={steps} />
      {rejected.length > 0 && (
        <p className="mt-2">已剔除 {rejected.length} 条未通过校验的引用。</p>
      )}
    </details>
  );
}

export function AgentSteps({ steps }: { steps: NonNullable<NonNullable<JointAnswer["investigation"]>["steps"]> }) {
  return <ol className="mt-2 flex flex-col gap-1">
        {steps.map((step, i) => (
          <li key={i} className="break-all">
            <span className={step.ok ? "text-ink-2" : "text-warn-text"}>
              {TOOL_LABELS[step.tool] ?? step.tool}
            </span>
            {Object.keys(step.arguments ?? {}).length > 0 && (
              <code className="mx-1">
                {Object.values(step.arguments ?? {}).join(" · ")}
              </code>
            )}
            <span> — {step.outcome}</span>
          </li>
        ))}
      </ol>;
}

export function needsReview(finding: PaperCodeFinding): boolean {
  const v = finding.verification;
  return v?.status === "failed" || Boolean(v?.required && v.status !== "passed");
}

export function FindingLabel({ finding }: { finding: PaperCodeFinding }) {
  const pending = needsReview(finding);
  return <span className={`mr-2 rounded px-1.5 py-0.5 text-xs ${pending ? "bg-warn-soft text-warn-text" : VERDICTS[finding.verdict].tone}`}>
    {pending ? "待核对" : VERDICTS[finding.verdict].label}
  </span>;
}

export function VerificationDetails({ finding }: { finding: PaperCodeFinding }) {
  const v = finding.verification;
  if (finding.verdict === "NOT_LOCATED") return null;
  if (!v || v.status === "not_reviewed" && !v.required)
    return <p className="mt-1 text-xs text-ink-4">未进行证据支持复核。</p>;
  return <details className="mt-1 text-xs text-ink-3" open={needsReview(finding)}>
    <summary className="cursor-pointer">{v.status === "passed" ? "证据支持复核通过" : `待核对 · 原判定：${VERDICTS[finding.verdict].label}`}</summary>
    <p className="mt-1">{v.reason}</p>
    {v.paper_statement && <p>论文陈述：{v.paper_statement}</p>}
    {v.code_statement && <p>代码陈述：{v.code_statement}</p>}
  </details>;
}
