import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { READ_ONLY } from "@/api/client";
import { useExecuteConsistency } from "@/api/queries";
import type { ConsistencyItem, ConsistencyPlan } from "@/api/types";
import { ErrorState } from "@/components/States";
import { AgentSteps, PaperSourceContext } from "@/features/reader/investigation";

export const CATEGORY: Record<ConsistencyItem["checkpoint"]["category"], string> = {
  hyperparameter: "超参数", architecture: "结构", training: "训练",
  data: "数据", evaluation: "评估", other: "其他",
};

export function ConsistencyPlanReview({ projectId, plan, busy, onExecute }: {
  projectId: string; plan: ConsistencyPlan; busy: boolean; onExecute: () => void;
}) {
  const key = `consistency-selection:${projectId}:${plan.plan_id}`;
  const [draft, setDraft] = useState<{ selected: string[]; extra: string }>(() => {
    try {
      const saved = JSON.parse(sessionStorage.getItem(key) ?? "null");
      if (saved && Array.isArray(saved.selected) && typeof saved.extra === "string")
        return { selected: plan.checkpoints.filter(c => saved.selected.includes(c.checkpoint_id)).map(c => c.checkpoint_id), extra: saved.extra };
    } catch { /* Start from the plan if browser storage is unavailable. */ }
    return { selected: plan.checkpoints.slice(0, plan.target ?? 20).map(c => c.checkpoint_id), extra: "" };
  });
  useEffect(() => { try { sessionStorage.setItem(key, JSON.stringify(draft)); } catch { /* Optional draft. */ } }, [key, draft]);
  const [ack, setAck] = useState(false);
  const execute = useExecuteConsistency(projectId);
  const extra = draft.extra.split("\n").map(q => q.trim()).filter(Boolean);
  const count = draft.selected.length + extra.length;
  const invalid = count === 0 || count > 40 || extra.length > 10 || extra.some(q => q.length > 300);
  const disabled = busy || execute.isPending || READ_ONLY;
  const ceiling = plan.max_requests ?? 160;
  const spent = plan.requests ?? 0;
  const estimated = spent + count * 7;
  const estimatedCapacity = Math.max(0, Math.floor((ceiling - spent) / 7));
  return <section aria-label="审阅规划" className="rounded-card bg-card p-4 shadow-card">
    <h3 className="text-[15px] font-semibold">2. 审阅核对要点</h3>
    <p className="mt-1 text-sm leading-6 text-ink-3">选择需要核对的内容，确认后开始调查。共 {plan.checkpoints.length} 个可选要点。</p>
    <details className="mt-3 rounded-lg bg-page px-3 py-2 text-xs text-ink-3">
      <summary className="cursor-pointer">规划过程 · {spent} 次请求 · {plan.tokens ?? 0} tokens</summary>
      <p className="mt-2">提出 {plan.proposed ?? 0} 次，拒绝 {plan.rejected ?? 0} 次。
        {plan.fallback ? "规划未产出要点，已回退到单次规划。" : ""}
        {plan.stop_reason === "request_limit" || plan.stop_reason === "time_limit" ? "达到规划预算，已保留通过校验的要点。" : ""}
      </p>
      <AgentSteps steps={plan.steps ?? []} />
    </details>
    <form className="mt-4 flex flex-col gap-3" onSubmit={e => {
      e.preventDefault();
      if (!disabled && !invalid && ack) execute.mutate({ planId: plan.plan_id ?? "", privacy_ack: true,
        selected_ids: draft.selected, extra_questions: extra }, { onSuccess: () => { setAck(false); onExecute(); } });
    }}>
      <div className="flex flex-wrap gap-3 text-xs">
        <button type="button" className="text-accent" disabled={disabled} onClick={() => setDraft(d => ({ ...d, selected: plan.checkpoints.slice(0, 40).map(c => c.checkpoint_id) }))}>选择前 {Math.min(40, plan.checkpoints.length)} 项</button>
        <button type="button" className="text-accent" disabled={disabled} onClick={() => setDraft(d => ({ ...d, selected: [] }))}>清空选择</button>
      </div>
      {plan.checkpoints.map(c => <article key={c.checkpoint_id} className="min-w-0 rounded-lg border border-line p-3">
        <label className="flex items-start gap-2 text-sm font-medium">
          <input type="checkbox" className="mt-1 shrink-0" disabled={disabled} checked={draft.selected.includes(c.checkpoint_id)}
            onChange={e => setDraft(d => ({ ...d, selected: e.target.checked ? [...d.selected, c.checkpoint_id] : d.selected.filter(id => id !== c.checkpoint_id) }))} />
          <span className="min-w-0 break-words">{c.topic}</span>
        </label>
        <p className="mt-1 text-xs text-ink-4">{CATEGORY[c.category]} · {c.checkpoint_id}</p>
        {c.paper_anchor && <blockquote className="mt-2 break-words border-l-2 border-line pl-3 text-sm leading-6 text-ink-3">
          {c.paper_anchor.quote}
          <Link className="ml-2 whitespace-nowrap text-xs text-accent" to={`/p/${projectId}/read?pdfPage=${c.paper_anchor.page}`}>论文第 {c.paper_anchor.page} 页 ↗</Link>
        </blockquote>}
        {c.paper_anchor && <PaperSourceContext anchor={c.paper_anchor} />}
        <p className="mt-2 break-words text-sm text-ink-2">{c.question}</p>
      </article>)}
      <label className="flex flex-col gap-2 text-sm">补充问题（每行一个，最多 10 个，每个不超过 300 字）
        <textarea rows={3} className="w-full rounded-lg border border-line bg-page p-2" value={draft.extra} disabled={disabled}
          onChange={e => setDraft(d => ({ ...d, extra: e.target.value }))} placeholder="例如：训练时采用了什么学习率调度？" />
      </label>
      <div className="rounded-lg bg-page p-3 text-sm leading-6" aria-live="polite">
        已选 {draft.selected.length} 项，补充 {extra.length} 项。预计共约 {estimated} 次模型请求（含规划 {spent} 次），本次上限 {ceiling} 次。
        <p className="text-xs text-ink-4">按每项约 7 次估算（含一次证据支持复核），实际用量取决于调查过程；预算不足的项会保留为未完成。</p>
        {estimated > ceiling && <p className="text-warn-text">预计超出预算，按规划顺序靠后的约 {Math.max(0, count - estimatedCapacity)} 项可能无法完成；可减少选择。补充问题排在最后。</p>}
        {invalid && <p className="text-warn-text">请选择至少一项；合计最多 40 项，补充问题最多 10 个且每个不超过 300 字。</p>}
      </div>
      <label className="flex items-start gap-2 text-sm text-ink-3">
        <input type="checkbox" className="mt-1" checked={ack} disabled={disabled} onChange={e => setAck(e.target.checked)} />
        我确认所选内容，并同意将论文与代码片段发送到已配置的模型服务。
      </label>
      {execute.error && <ErrorState error={execute.error} />}
      <button type="submit" className="btn-primary self-start" disabled={disabled || invalid || !ack}>
        {execute.isPending ? "正在提交" : `开始核对 ${count} 项`}
      </button>
    </form>
  </section>;
}
