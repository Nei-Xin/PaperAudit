import { useEffect } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useSearchParams } from "react-router-dom";
import { keys, useJobs } from "@/api/queries";
import { READ_ONLY, send } from "@/api/client";
import type { ProjectJobs } from "@/api/types";
import { ErrorState, Progress } from "@/components/States";

type AuditJob = ProjectJobs["audit"][number];

export function AuditTasks({ projectId }: { projectId: string }) {
  const jobs = useJobs(projectId);
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const client = useQueryClient();
  const focused = jobs.data?.audit.find(j => j.job_id === params.get("job"));
  const retry = useMutation({
    mutationFn: (job: AuditJob) => send<AuditJob>("POST", `/api/projects/${projectId}/audit-jobs/${job.job_id}/retry`),
    onSuccess: async job => {
      await client.invalidateQueries({ queryKey: keys.jobs(projectId) });
      navigate(`/p/${projectId}/audit?job=${job.job_id}`);
    },
  });
  useEffect(() => {
    if (focused?.status === "SUCCEEDED" && focused.audit_id) {
      navigate(`/p/${projectId}/audit/${focused.audit_id}`, { replace: true });
    }
  }, [focused, navigate, projectId]);
  const latest = jobs.data?.audit[0];
  const job = focused ?? latest;
  if (jobs.error) return <ErrorState error={jobs.error} />;
  if (!job || job.status === "SUCCEEDED") return null;
  const busy = job.status === "RUNNING" || job.status === "QUEUED";
  const newer = jobs.data?.audit.some(j => j.report_hash === job.report_hash && j.job_id !== job.job_id && j.created_at >= job.created_at && ["QUEUED", "RUNNING", "SUCCEEDED"].includes(j.status));
  return <section className="card mb-2 shrink-0 px-4 py-3" aria-label="审计任务">
    <p className="mb-2 text-sm font-medium">{job.source_label}</p>
    {busy ? <Progress value={job.progress} label={job.stage} /> : <>
      <p role="alert" className="text-sm text-bad">审计未完成：{job.error || job.stage}</p>
      {!newer && <button type="button" className="btn-secondary mt-2" disabled={READ_ONLY || retry.isPending} onClick={() => retry.mutate(job)}>
        {retry.isPending ? "正在提交…" : "重试审计"}
      </button>}
      {newer && <p className="text-xs text-ink-4">此报告已有更新的任务，请查看最新记录。</p>}
    </>}
    {retry.error && <ErrorState error={retry.error} />}
  </section>;
}
