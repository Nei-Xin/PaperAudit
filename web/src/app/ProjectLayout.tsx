import { useState, type ReactNode } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { READ_ONLY, send } from "@/api/client";
import { Modal } from "@/components/Modal";
import { NavLink, Outlet, useLocation, useParams } from "react-router-dom";
import clsx from "clsx";
import {
  hasActiveJob,
  keys,
  useAudits,
  useJobs,
  useProject,
  useReview,
} from "@/api/queries";
import { DECISION_LABELS } from "@/lib/labels";
import { useDocumentTitle } from "@/lib/useDocumentTitle";
import { ErrorState, Loading, Progress } from "@/components/States";

/** One-row top bar: title · 阅读/审计/评审 switch · page actions. */
export function TopBar({ actions }: { actions?: ReactNode }) {
  const { projectId = "" } = useParams();
  const [renaming, setRenaming] = useState(false);
  const [title, setTitle] = useState("");
  const client = useQueryClient();
  const rename = useMutation({
    mutationFn: () =>
      send("PATCH", `/api/projects/${projectId}`, { title: title.trim() }),
    onSuccess: async () => {
      await Promise.all([
        client.invalidateQueries({ queryKey: keys.project(projectId) }),
        client.invalidateQueries({ queryKey: keys.projects }),
      ]);
      setRenaming(false);
    },
  });
  const project = useProject(projectId);
  const audits = useAudits(projectId);
  const review = useReview(projectId);
  const auditCount = audits.data?.length ?? 0;
  const decision = review.data?.report.decision;
  const { pathname } = useLocation();
  const view = pathname.includes("/audit")
    ? "审计"
    : pathname.endsWith("/review")
      ? "评审"
      : "阅读";
  useDocumentTitle(project.data?.title, view);
  const tabs = [
    { to: "read", label: "阅读" },
    { to: "audit", label: auditCount ? `审计 · ${auditCount}` : "审计" },
    {
      to: "review",
      label: decision ? `评审 · ${DECISION_LABELS[decision].zh}` : "评审",
    },
  ];
  return (
    <>
      <header className="project-topbar">
        <h1
          className="project-title min-w-0 truncate text-[15px] font-semibold"
          title={project.data?.original_filename}
        >
          <button
            className="max-w-full truncate text-left"
            disabled={READ_ONLY}
            title="修改项目标题"
            onClick={() => {
              setTitle(project.data?.title ?? "");
              rename.reset();
              setRenaming(true);
            }}
          >
            {project.data?.title ?? "…"}
          </button>
        </h1>
        <nav
          aria-label="项目视图"
          className="project-tabs flex w-max max-w-full gap-0.5 overflow-x-auto rounded-[10px] bg-active p-[3px]"
        >
          {tabs.map((tab) => (
            <NavLink
              key={tab.to}
              to={`/p/${projectId}/${tab.to}`}
              className={({ isActive }) =>
                clsx(
                  "flex h-[30px] items-center whitespace-nowrap rounded-lg px-3.5 text-[13px] transition-colors",
                  isActive
                    ? "bg-card font-semibold text-ink shadow-[0_1px_2px_rgba(26,26,25,.1)]"
                    : "font-medium text-ink-3 hover:text-ink",
                )
              }
            >
              {tab.label}
            </NavLink>
          ))}
        </nav>
        <div className="project-actions">{actions}</div>
      </header>
      <Modal
        open={renaming}
        onClose={() => {
          if (!rename.isPending) setRenaming(false);
        }}
        title="修改项目标题"
      >
        <form
          className="flex flex-col gap-3"
          onSubmit={(e) => {
            e.preventDefault();
            if (!rename.isPending) rename.mutate();
          }}
        >
          <label className="text-sm">
            项目标题
            <input
              className="mt-2 w-full rounded-lg bg-page p-2"
              maxLength={300}
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </label>
          {rename.error && <ErrorState error={rename.error} />}
          <button
            className="btn-primary self-start"
            disabled={!title.trim() || rename.isPending}
          >
            保存标题
          </button>
        </form>
      </Modal>
      <ActiveJobs />
    </>
  );
}

function ActiveJobs() {
  const { projectId = "" } = useParams();
  const jobs = useJobs(projectId);
  if (!hasActiveJob(jobs.data)) return null;
  const all = jobs.data
    ? [...jobs.data.learning, ...jobs.data.review, ...jobs.data.revision]
    : [];
  const active = all.filter(
    (job) => job.status === "QUEUED" || job.status === "RUNNING",
  );
  return (
    <div className="card mb-2 flex max-h-32 shrink-0 flex-col gap-2 overflow-auto px-4 py-3">
      {active.map((job) => (
        <Progress
          key={job.job_id}
          value={job.progress}
          label={`${"source_label" in job ? job.source_label : "original_filename" in job ? job.original_filename : "后台任务"} · ${job.stage}`}
        />
      ))}
    </div>
  );
}

export function ProjectLayout() {
  const { projectId = "" } = useParams();
  const project = useProject(projectId);
  if (project.isLoading) return <Loading />;
  if (project.error)
    return (
      <div className="p-6">
        <ErrorState error={project.error} />
      </div>
    );
  return (
    <div className="flex h-full min-h-0 min-w-0 flex-col">
      <Outlet key={projectId} />
    </div>
  );
}
