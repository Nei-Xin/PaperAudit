import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { READ_ONLY } from "@/api/client";
import { keys } from "@/api/queries";
import type { ConsistencyEvent, ConsistencyJob } from "@/api/types";
import { AgentSteps, VERDICTS } from "@/features/reader/investigation";

/** EventSource carries Last-Event-ID on network reconnect; a page reload replays from zero. */
function useEvents(projectId: string, jobId: string) {
  const client = useQueryClient();
  const [events, setEvents] = useState<ConsistencyEvent[]>([]);
  const [connection, setConnection] = useState("连接中");
  const [terminal, setTerminal] = useState<string>();
  useEffect(() => {
    if (READ_ONLY) return;
    let disposed = false;
    const seen = new Set<number>();
    const source = new EventSource(`/api/projects/${projectId}/consistency-jobs/${jobId}/events`);
    source.onopen = () => { if (!disposed) setConnection("实时连接已建立"); };
    source.addEventListener("audit", message => {
      if (disposed) return;
      try {
        const event = JSON.parse((message as MessageEvent).data) as ConsistencyEvent;
        if (event.job_id !== jobId || !Number.isSafeInteger(event.event_id) || seen.has(event.event_id)) return;
        seen.add(event.event_id);
        setEvents(previous => [...previous, event].sort((a, b) => a.event_id - b.event_id));
      } catch { setConnection("部分事件无法读取，最终结果请查看报告"); }
    });
    source.addEventListener("end", message => {
      if (disposed) return;
      try { setTerminal(JSON.parse((message as MessageEvent).data).status); }
      catch { /* The polled job remains authoritative. */ }
      source.close();
      setConnection("任务已结束，事件已同步");
      void client.invalidateQueries({ queryKey: keys.consistencyJobs(projectId) });
    });
    source.addEventListener("stream_error", () => {
      source.close();
      if (!disposed) setConnection("事件日志暂不可读，任务状态仍会更新");
    });
    source.onerror = () => {
      if (!disposed) setConnection(source.readyState === EventSource.CLOSED
        ? "实时连接不可用，任务状态仍会更新" : "连接中断，正在重连并补齐事件");
    };
    return () => { disposed = true; source.close(); };
  }, [projectId, jobId, client]);
  return { events, connection, terminal };
}

export function ConsistencyProgress({ projectId, job }: { projectId: string; job: ConsistencyJob }) {
  const { events, connection, terminal } = useEvents(projectId, job.job_id);
  if (READ_ONLY) return null;
  const items = new Map<string, { topic: string; events: ConsistencyEvent[] }>();
  for (const event of events) {
    if (!event.checkpoint_id) continue;
    const row = items.get(event.checkpoint_id) ?? { topic: event.checkpoint_id, events: [] };
    if (event.topic) row.topic = event.topic;
    row.events.push(event);
    items.set(event.checkpoint_id, row);
  }
  const phase = events.filter(e => !e.checkpoint_id);
  const ended = terminal ?? job.status;
  const interrupted = ended === "FAILED" || ended === "INTERRUPTED";
  const steps = (rows: ConsistencyEvent[]) => rows.filter(e => e.tool).map(e => ({
    tool: e.tool, arguments: e.arguments, outcome: e.outcome, ok: e.ok,
  }));
  return <section aria-label="任务实时进度" className="rounded-card bg-card p-4 shadow-card">
    <header className="flex flex-wrap items-baseline justify-between gap-2">
      <h3 className="text-sm font-semibold">任务过程</h3>
      <span role="status" className="text-xs text-ink-4">{connection}</span>
    </header>
    {interrupted && <p className="mt-2 text-sm text-warn-text">任务{ended === "INTERRUPTED" ? "已中断" : "失败"}，未结束的要点没有最终结论。</p>}
    <p className="mt-2 text-xs text-ink-3">{phase.at(-1)?.outcome || job.stage}</p>
    {steps(phase).length > 0 && <details className="mt-2 text-xs text-ink-3">
      <summary className="cursor-pointer">规划与任务步骤</summary><AgentSteps steps={steps(phase)} />
    </details>}
    <ul className="mt-3 flex flex-col gap-2">
      {[...items].map(([id, row]) => {
        const last = row.events.at(-1)!;
        const finish = [...row.events].reverse().find(e => e.kind === "item_finished");
        const label = finish ? (finish.status === "not_checked" ? "未执行" : finish.status === "failed" ? "调查失败"
          : finish.pending_review > 0 ? "待核对" : finish.verdicts.length ? [...new Set(finish.verdicts)].map(v => VERDICTS[v]?.label ?? v).join("、") : "证据不足")
          : interrupted ? "未完成" : last.kind === "checkpoint_accepted" ? "已接受" : last.kind === "item_queued" ? "等待核对" : "核对中";
        return <li key={id} data-checkpoint-id={id} className="min-w-0 rounded-lg bg-page px-3 py-2">
          <div className="flex items-start justify-between gap-2 text-sm">
            <span className="min-w-0 break-words">{id} · {row.topic}</span>
            <span className="shrink-0 text-xs text-ink-3">{label}</span>
          </div>
          {last.tool ? <div className="text-xs text-ink-3"><AgentSteps steps={steps([last])} /></div>
            : <p className="mt-1 text-xs text-ink-3">{last.outcome}</p>}
          {steps(row.events).length > 0 && <details className="mt-1 text-xs text-ink-3">
            <summary className="cursor-pointer">查看 {steps(row.events).length} 个步骤</summary>
            <AgentSteps steps={steps(row.events)} />
          </details>}
        </li>;
      })}
    </ul>
    {!events.length && <p className="mt-2 text-xs text-ink-4">{["QUEUED", "RUNNING"].includes(job.status) ? "等待任务事件。" : "此任务没有事件记录，可查看已有报告。"}</p>}
  </section>;
}
