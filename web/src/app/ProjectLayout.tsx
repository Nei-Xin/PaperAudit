import type { ReactNode } from "react";
import { NavLink, Outlet, useParams } from "react-router-dom";
import clsx from "clsx";
import { hasActiveJob, useAudits, useJobs, useProject, useReview } from "@/api/queries";
import { DECISION_LABELS } from "@/lib/labels";
import { ErrorState, Loading, Progress } from "@/components/States";

/** One-row top bar: title · 阅读/审计/评审 switch · page actions. */
export function TopBar({ actions }: { actions?: ReactNode }) {
  const { projectId = "" } = useParams();
  const project = useProject(projectId);
  const audits = useAudits(projectId);
  const review = useReview(projectId);
  const auditCount = audits.data?.length ?? 0;
  const decision = review.data?.report.decision;
  const tabs = [
    { to: "read", label: "阅读" },
    { to: "audit", label: auditCount ? `审计 · ${auditCount}` : "审计" },
    { to: "review", label: decision ? `评审 · ${DECISION_LABELS[decision].zh}` : "评审" },
  ];
  return (
    <>
    <header className="project-topbar">
      <h1 className="project-title min-w-0 truncate text-[15px] font-semibold" title={project.data?.original_filename}>
        {project.data?.title ?? "…"}
      </h1>
      <nav aria-label="项目视图" className="project-tabs flex w-max max-w-full gap-0.5 overflow-x-auto rounded-[10px] bg-active p-[3px]">
        {tabs.map((tab) => (
          <NavLink
            key={tab.to}
            to={`/p/${projectId}/${tab.to}`}
            className={({ isActive }) =>
              clsx(
                "flex h-[30px] items-center whitespace-nowrap rounded-lg px-3.5 text-[13px] transition-colors",
                isActive ? "bg-card font-semibold text-ink shadow-[0_1px_2px_rgba(26,26,25,.1)]" : "font-medium text-ink-3 hover:text-ink",
              )
            }
          >
            {tab.label}
          </NavLink>
        ))}
      </nav>
      <div className="project-actions">{actions}</div>
    </header>
    <ActiveJobs />
    </>
  );
}

function ActiveJobs() {
  const { projectId = "" } = useParams();
  const jobs = useJobs(projectId);
  if (!hasActiveJob(jobs.data)) return null;
  const all = jobs.data ? [...jobs.data.learning, ...jobs.data.audit, ...jobs.data.review, ...jobs.data.revision] : [];
  const active = all.filter((job) => job.status === "QUEUED" || job.status === "RUNNING");
  return (
    <div className="card mb-2 flex max-h-32 shrink-0 flex-col gap-2 overflow-auto px-4 py-3">
      {active.map((job) => (
        <Progress key={job.job_id} value={job.progress} label={`${job.source_label ?? job.original_filename ?? "后台任务"} · ${job.stage}`} />
      ))}
    </div>
  );
}

export function ProjectLayout() {
  const { projectId = "" } = useParams();
  const project = useProject(projectId);
  if (project.isLoading) return <Loading />;
  if (project.error) return <div className="p-6"><ErrorState error={project.error} /></div>;
  return (
    <div className="flex h-full min-h-0 min-w-0 flex-col">
      <Outlet />
    </div>
  );
}
