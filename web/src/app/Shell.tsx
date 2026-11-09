import { useEffect, useMemo, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { READ_ONLY, READING_ONLY, send } from "@/api/client";
import { Link, NavLink, Outlet, useLocation, useNavigate, useParams } from "react-router-dom";
import { Menu, PanelLeftClose, Plus, Search, Settings as SettingsIcon, Trash2 } from "lucide-react";
import clsx from "clsx";
import { keys, useDeleteProject, useProjects, useSettings, useStorage } from "@/api/queries";
import type { Settings, ProjectSummary } from "@/api/types";
import { Modal } from "@/components/Modal";
import { ErrorState, MockNote } from "@/components/States";

function Logo() {
  return (
    <svg width="24" height="24" viewBox="0 0 28 28" aria-hidden>
      <rect width="28" height="28" rx="7" fill="#1E4A7A" />
      <path d="M9 7h7l4 4v10H9z" fill="none" stroke="#fff" strokeWidth="1.8" strokeLinejoin="round" />
      <path d="m12 16 2 2 3-4" fill="none" stroke="#fff" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function projectTags(project: ProjectSummary): string {
  const parts = [
    project.has_learning_report && "讲解",
    project.has_audit && "审计",
    project.has_peer_review && "评审",
    project.has_code && "代码",
  ].filter(Boolean);
  return parts.length ? parts.join(" · ") : "仅原文";
}

function ProjectRow({ project, onDelete }: { project: ProjectSummary; onDelete: (p: ProjectSummary) => void }) {
  return (
    <li className="group relative">
      <NavLink
        to={`/p/${project.project_id}`}
        title={project.original_filename}
        className={({ isActive }) =>
          clsx(
            "flex flex-col gap-1 rounded-lg py-2 pl-2.5 pr-8 transition-colors",
            isActive ? "bg-active" : "hover:bg-hover",
          )
        }
      >
        {({ isActive }) => (
          <>
            <span className={clsx("line-clamp-2 text-sm leading-snug", isActive ? "font-semibold" : "font-medium")}>
              {project.title}
            </span>
            <span className="text-xs text-ink-4">{projectTags(project)}</span>
          </>
        )}
      </NavLink>
      <button
        type="button"
        disabled={READ_ONLY || READING_ONLY}
        title="删除功能仍在接入，请使用旧版"
        onClick={() => onDelete(project)}
        className="icon-btn absolute right-1 top-1.5 h-7 w-7 opacity-100 hover:text-bad focus:opacity-100 min-[1100px]:opacity-0 group-hover:opacity-100"
        aria-label={`删除 ${project.title}`}
      >
        <Trash2 className="h-4 w-4" />
      </button>
    </li>
  );
}

function SettingsDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const settings = useSettings();
  const client = useQueryClient();
  const [values, setValues] = useState<Settings | undefined>();
  const [apiKey, setApiKey] = useState("");
  const save = useMutation({
    mutationFn: () => {
      const { configured: _, ...body } = values!;
      return send<Settings>("PUT", "/api/settings", { ...body, api_key: apiKey || undefined });
    },
    onSuccess: result => { client.setQueryData(keys.settings, result); setApiKey(""); onClose(); },
  });
  useEffect(() => { if (open && settings.data) { setValues(settings.data); setApiKey(""); save.reset(); } }, [open, settings.data]);
  const s = values ?? settings.data;
  return <Modal open={open} onClose={onClose} title="模型与检索设置" footer={!READ_ONLY && <>
    <button type="button" className="btn-secondary" onClick={onClose}>取消</button>
    <button type="button" className="btn-primary" disabled={!values || save.isPending} onClick={() => save.mutate()}>{save.isPending ? "正在保存…" : "保存设置"}</button>
  </>}>
    {s && READ_ONLY ? <dl className="grid grid-cols-[6.5rem_minmax(0,1fr)] gap-x-4 gap-y-3 text-sm [&_dd]:break-words">
      <dt>API 地址</dt><dd>{s.api_base || "未设置"}</dd><dt>API Key</dt><dd>{s.configured ? "已配置（不显示）" : "未配置"}</dd>
      <dt>模型</dt><dd>{s.model || "未设置"}</dd><dt>推理强度</dt><dd>{s.reasoning_effort}</dd>
      <dt>候选证据 Top-K</dt><dd>{s.retrieval_top_k}</dd><dt>研判批大小</dt><dd>{s.judge_batch_size}</dd><dt>深度核验</dt><dd>{s.deep_audit ? "开启" : "关闭"}</dd>
    </dl> : s && <div className="flex flex-col gap-3">
      {([["api_base", "API 地址"], ["model", "模型"]] as const).map(([key, label]) => <label key={key} className="flex flex-col gap-1 text-sm">{label}
        <input className="h-9 rounded-lg bg-page px-3" value={s[key]} onChange={e => setValues({ ...s, [key]: e.target.value })} />
      </label>)}
      <label className="flex flex-col gap-1 text-sm">API Key
        <input type="password" autoComplete="new-password" value={apiKey} placeholder={s.configured ? "已配置；留空保留现有密钥" : "输入模型服务密钥"} onChange={e => setApiKey(e.target.value)} className="h-9 rounded-lg bg-page px-3" />
      </label>
      <label className="flex flex-col gap-1 text-sm">推理强度<select className="h-9 rounded-lg bg-page px-3" value={s.reasoning_effort} onChange={e => setValues({ ...s, reasoning_effort: e.target.value })}>
        {["no_think", "low", "medium", "high"].map(v => <option key={v}>{v}</option>)}
      </select></label>
      <p className="text-xs text-ink-4">密钥只保存于服务端。留空会保留现有密钥。</p>
    </div>}
    {settings.error && <ErrorState error={settings.error} />}{save.error && <div className="mt-3"><ErrorState error={save.error} /></div>}
    <div className="mt-4"><MockNote /></div>
  </Modal>;
}

export function Shell() {
  const projects = useProjects();
  const settings = useSettings();
  const storage = useStorage();
  const remove = useDeleteProject();
  const navigate = useNavigate();
  const { projectId } = useParams();
  const [query, setQuery] = useState("");
  const [pendingDelete, setPendingDelete] = useState<ProjectSummary | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);

  const location = useLocation();
  const [desktop, setDesktop] = useState(() => window.matchMedia("(min-width: 1100px)").matches);
  const [collapsed, setCollapsed] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  useEffect(() => {
    const media = window.matchMedia("(min-width: 1100px)");
    const update = () => { setDesktop(media.matches); setDrawerOpen(false); };
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);
  useEffect(() => { setDrawerOpen(false); }, [location.pathname]);

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    return (projects.data ?? []).filter(
      (p) => !q || p.title.toLowerCase().includes(q) || p.original_filename.toLowerCase().includes(q),
    );
  }, [projects.data, query]);

  const sidebar = (
      <aside className="flex h-full min-h-0 w-60 shrink-0 flex-col gap-1 px-3 py-4" aria-label="论文项目">
        <div className="mb-3 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2 px-2">
          <Logo />
          <strong className="text-[15px] font-semibold">PaperAudit</strong>
        </Link>
        {desktop && !collapsed && <button type="button" className="icon-btn" onClick={() => setCollapsed(true)} aria-label="收起项目侧栏"><PanelLeftClose className="h-4 w-4" /></button>}
        </div>
        <Link to="/" className="flex h-9 shrink-0 items-center gap-2 rounded-lg bg-active px-2.5 text-sm font-medium hover:bg-hover">
          <Plus className="h-4 w-4" aria-hidden /> 新建论文
        </Link>
        <label className="mt-1 flex h-9 items-center gap-2 rounded-lg bg-card px-2.5 text-ink-4 shadow-card">
          <Search className="h-4 w-4 shrink-0" aria-hidden />
          <span className="sr-only">搜索论文</span>
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="搜索论文"
            className="min-w-0 flex-1 bg-transparent text-sm text-ink outline-none placeholder:text-ink-4"
          />
        </label>
        <div className="mt-4 flex items-center justify-between px-2.5 text-xs font-medium text-ink-4">
          <span>我的项目</span><span>{visible.length}</span>
        </div>
        <ul className="-mx-1 flex min-h-0 flex-1 flex-col gap-0.5 overflow-y-auto px-1">
          {visible.map((project) => (
            <ProjectRow key={project.project_id} project={project} onDelete={(item) => { setDrawerOpen(false); setPendingDelete(item); }} />
          ))}
          {projects.data && !visible.length && (
            <li className="px-2.5 py-4 text-center text-xs text-ink-4">{query ? "没有匹配的论文" : "还没有保存的论文"}</li>
          )}
        </ul>
        <button
          type="button"
          onClick={() => { setDrawerOpen(false); setSettingsOpen(true); }}
          className="mt-2 flex items-center gap-2 rounded-lg px-2.5 py-2 text-left text-xs text-ink-3 hover:bg-hover"
        >
          <span className={clsx("h-2 w-2 shrink-0 rounded-full", settings.data?.configured ? "bg-ok" : "bg-warn")} />
          <span className="min-w-0 flex-1 truncate">
            {settings.data?.configured ? `已配置 · ${settings.data.model}` : "API 配置不完整"}
            <span className="block text-ink-4">保存于 {storage.data?.name ?? "…"}</span>
          </span>
          <SettingsIcon className="h-4 w-4 shrink-0" aria-hidden />
        </button>
      </aside>
  );
  return (
    <div className="app-shell">
      {desktop && !collapsed && sidebar}
      <div className="flex min-h-0 min-w-0 flex-1 flex-col p-2">
        {(!desktop || collapsed) && (
          <div className="flex h-10 shrink-0 items-center gap-2 pb-2">
            <button type="button" className="btn-secondary" aria-label="打开项目侧栏" onClick={() => desktop ? setCollapsed(false) : setDrawerOpen(true)}>
              <Menu className="h-4 w-4" /> 项目
            </button>
            <Link to="/" className="text-sm font-semibold">PaperAudit</Link>
          </div>
        )}
        <main className="workspace"><Outlet /></main>
      </div>
      <Modal open={drawerOpen && !desktop} onClose={() => setDrawerOpen(false)} title="论文项目" drawer>
        {sidebar}
      </Modal>

      <SettingsDialog open={settingsOpen} onClose={() => setSettingsOpen(false)} />
      <Modal open={pendingDelete !== null} onClose={() => { setPendingDelete(null); remove.reset(); }} title="删除论文项目">
        <p className="font-medium">{pendingDelete?.title}</p>
        <p className="mt-3 rounded-lg bg-warn-soft px-3 py-2 text-sm text-warn-text">
          论文 PDF、讲解、追问、审计与评审记录将被永久删除，无法恢复。
        </p>
        {remove.error && <div className="mt-3"><ErrorState error={remove.error} /></div>}
        <div className="mt-5 flex justify-end gap-2">
          <button type="button" className="btn-secondary" onClick={() => setPendingDelete(null)}>取消</button>
          <button
            type="button"
            className="btn bg-[#A63D31] text-white hover:bg-[#8C2F25]"
            disabled={remove.isPending}
            onClick={() => {
              if (!pendingDelete) return;
              remove.mutate(pendingDelete.project_id, {
                onSuccess: () => {
                  if (pendingDelete.project_id === projectId) navigate("/");
                  setPendingDelete(null);
                },
              });
            }}
          >
            永久删除
          </button>
        </div>
      </Modal>
    </div>
  );
}
