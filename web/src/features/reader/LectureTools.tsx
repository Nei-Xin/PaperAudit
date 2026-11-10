import { useState } from "react";
import { useGenerateLecture, useJobs, useRetryLecture } from "@/api/queries";
import { READ_ONLY } from "@/api/client";
import { ErrorState, Progress } from "@/components/States";
import { Modal } from "@/components/Modal";

/** Regeneration leaves the old lecture mounted throughout the background job. */
export function LectureTools({ projectId }: { projectId: string }) {
  const jobs = useJobs(projectId);
  const generate = useGenerateLecture(projectId);
  const retry = useRetryLecture(projectId);
  const [open, setOpen] = useState(false);
  const [consent, setConsent] = useState(false);
  const active = jobs.data?.learning.find(j => ["QUEUED", "RUNNING"].includes(j.status));
  const latest = jobs.data?.learning[0];
  const failed = !active && latest && ["FAILED", "INTERRUPTED"].includes(latest.status) ? latest : undefined;
  return <>
    <div className="shrink-0 border-b border-line-soft px-4 py-2" aria-label="讲解生成状态">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-xs text-ink-4">{active ? "生成期间可继续阅读当前讲解" : "按论文内容展开方法、实验与结果"}</span>
        <button type="button" className="btn-secondary" disabled={READ_ONLY || Boolean(active) || generate.isPending || retry.isPending}
          onClick={() => { setConsent(false); generate.reset(); setOpen(true); }}>重新生成详细讲解</button>
      </div>
      {active && <div className="mt-2"><Progress value={active.progress} label={active.stage} /></div>}
      {failed && <div className="mt-2 max-h-28 overflow-auto">
        <p role="alert" className="text-xs text-bad">详细讲解未完成，当前讲解已保留：{failed.error || failed.stage}</p>
        <button type="button" className="btn-secondary mt-2" disabled={READ_ONLY || retry.isPending}
          onClick={() => retry.mutate(failed.job_id)}>{retry.isPending ? "正在提交…" : "重试详细讲解"}</button>
      </div>}
      {retry.error && <ErrorState error={retry.error} />}
      {jobs.error && <ErrorState error={jobs.error} />}
    </div>
    <Modal open={open} onClose={() => setOpen(false)} title="重新生成详细讲解">
      <div className="flex flex-col gap-4 text-sm leading-7">
        <p>将重新梳理论文，并检查方法解释、实验结果和原文引用。通常需要数分钟，会产生模型调用费用。</p>
        <p>生成期间保留当前讲解；检查通过后更新，失败则继续保留当前版本。</p>
        <label className="flex items-start gap-2"><input type="checkbox" className="mt-2" checked={consent} onChange={e => setConsent(e.target.checked)} />
          我同意将论文文本发送至已配置的模型服务，重新生成详细讲解。</label>
        {generate.error && <ErrorState error={generate.error} />}
        <div className="flex justify-end gap-2">
          <button type="button" className="btn-secondary" onClick={() => setOpen(false)}>取消</button>
          <button type="button" className="btn-primary" disabled={!consent || READ_ONLY || Boolean(active) || generate.isPending}
            onClick={() => generate.mutate({ regenerate: true, privacy_ack: true }, { onSuccess: () => setOpen(false) })}>
            {generate.isPending ? "正在提交…" : "开始生成"}
          </button>
        </div>
      </div>
    </Modal>
  </>;
}
