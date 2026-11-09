import { useRef, useState, type DragEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { FileUp, Lock } from "lucide-react";
import clsx from "clsx";
import { READ_ONLY, send } from "@/api/client";
import { keys } from "@/api/queries";
import type { ProjectSummary } from "@/api/types";
import { ErrorState, MockNote } from "@/components/States";
import { VENUE_LABELS } from "@/lib/labels";

type Mode = "learn" | "audit_existing" | "peer_review";

const MODES: { value: Mode; label: string; description: string; privacy: string }[] = [
  {
    value: "learn",
    label: "生成讲解",
    description: "研究问题、贡献、方法、实验、结果、局限与术语，每条都能跳回原文高亮。",
    privacy: "生成讲解会把论文文本发送到你配置的模型服务。",
  },
  {
    value: "audit_existing",
    label: "审计一份报告",
    description: "把一份中文解读拆成论断，逐条对照原文核验数字、条件和结论。",
    privacy: "报告审计会把论文文本和你提供的报告发送到你配置的模型服务。",
  },
  {
    value: "peer_review",
    label: "模拟投稿评审",
    description: "按会议标准给出六维评分、主要问题和修改优先级。",
    privacy: "模拟评审会把论文文本发送到你配置的模型服务；结果是辅助预审意见，不代表真实录用结果。",
  },
];

const MAX_BYTES = 200 * 1024 * 1024;

export function HomePage() {
  const navigate = useNavigate();
  const client = useQueryClient();
  const input = useRef<HTMLInputElement>(null);
  const [mode, setMode] = useState<Mode>("learn");
  const [pdf, setPdf] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [report, setReport] = useState("");
  const [venue, setVenue] = useState("general_ai_ml");
  const [code, setCode] = useState<File | null>(null);
  const [fileError, setFileError] = useState("");
  const current = MODES.find((m) => m.value === mode)!;

  const pick = (file: File | undefined) => {
    if (!file) return;
    if (file.type !== "application/pdf" && !file.name.toLowerCase().endsWith(".pdf")) return setFileError("请选择 PDF 文件。");
    if (file.size > MAX_BYTES) return setFileError("文件超过 200MB。");
    setFileError("");
    setPdf(file);
  };
  const onDrop = (event: DragEvent) => {
    event.preventDefault();
    setDragging(false);
    pick(event.dataTransfer.files[0]);
  };

  const create = useMutation({
    mutationFn: () => {
      const form = new FormData();
      form.set("pdf", pdf!);
      form.set("mode", mode);
      if (mode === "audit_existing") form.set("report_text", report);
      if (mode === "peer_review") form.set("venue", venue);
      if (mode === "learn" && code) form.set("code_zip", code);
      form.set("privacy_ack", "true");
      return send<{ project: ProjectSummary }>("POST", "/api/projects", form);
    },
    onSuccess: (result) => {
      client.invalidateQueries({ queryKey: keys.projects });
      navigate(`/p/${result.project.project_id}`);
    },
  });
  const ready = pdf !== null && (mode !== "audit_existing" || report.trim().length > 0);

  return (
    <div className="card flex h-full items-start justify-center overflow-auto px-4 sm:px-6">
      <div className="flex w-full min-w-0 max-w-[680px] flex-col gap-6 pb-12 pt-[clamp(2rem,10vh,7rem)]">
        <h1 className="text-center text-[30px] font-semibold tracking-tight">今天读哪篇论文？</h1>

        <div className="overflow-hidden rounded-2xl bg-card shadow-[0_4px_16px_rgba(26,26,25,.06),0_0_0_1px_#E7E5E1]">
          <button
            type="button"
            onClick={() => input.current?.click()}
            onDragOver={(event) => { event.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
            className={clsx(
              "flex w-full flex-col items-center gap-2 border-b border-dashed border-line px-6 py-9 transition-colors",
              dragging ? "bg-accent-soft" : "hover:bg-[#FAFAF9]",
            )}
          >
            <FileUp className="h-7 w-7 text-ink-3" aria-hidden />
            <strong title={pdf?.name} className="max-w-full break-all text-base font-semibold">{pdf ? pdf.name : "拖入论文 PDF，或点击选择"}</strong>
            <span className="text-[13px] text-ink-4">{pdf ? `${(pdf.size / 1024 / 1024).toFixed(1)} MB · 点击更换` : "带文字层的英文论文 · 最大 200MB"}</span>
          </button>
          <input ref={input} type="file" accept="application/pdf" className="hidden" onChange={(event) => pick(event.target.files?.[0])} />

          <div className="flex flex-col gap-3 p-3">
            <div className="flex flex-wrap items-center gap-2">
              <div role="radiogroup" aria-label="要做什么" className="flex flex-wrap gap-1.5">
                {MODES.map((item) => (
                  <button
                    key={item.value}
                    type="button"
                    role="radio"
                    aria-checked={mode === item.value}
                    onClick={() => setMode(item.value)}
                    className={clsx("pill", mode === item.value ? "bg-ink text-white shadow-none" : "bg-card text-ink-2 hover:bg-hover")}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
              <button type="button" className="btn-primary ml-auto" disabled={!ready || READ_ONLY || create.isPending} onClick={() => create.mutate()}>
                {mode === "learn" ? "生成讲解" : mode === "peer_review" ? "开始评审" : "开始审计"}
              </button>
            </div>
            {mode === "audit_existing" && (
              <label className="flex flex-col gap-1.5">
                <span className="label">中文解读内容</span>
                <textarea value={report} onChange={(e) => setReport(e.target.value)} rows={5} placeholder="粘贴针对该论文的中文总结、解读或阅读笔记…" className="resize-y rounded-lg bg-page p-3 text-sm leading-6 outline-none focus:ring-2 focus:ring-accent/30" />
              </label>
            )}
            {mode === "peer_review" && (
              <label className="flex items-center gap-3">
                <span className="label">评审标准</span>
                <select value={venue} onChange={(e) => setVenue(e.target.value)} className="h-8 rounded-lg bg-page px-2 text-[13px]">
                  {Object.entries(VENUE_LABELS).filter(([v]) => v !== "custom").map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                </select>
              </label>
            )}
            {mode === "learn" && (
              <label className="flex min-w-0 flex-col gap-2 text-[13px] text-ink-3 sm:flex-row sm:items-center">
                <span className="label">源码 ZIP（可选）</span>
                <input className="min-w-0 max-w-full flex-1" type="file" accept=".zip" onChange={(e) => setCode(e.target.files?.[0] ?? null)} />
              </label>
            )}
          </div>
        </div>

        {fileError && <ErrorState error={new Error(fileError)} />}
        {create.error && <ErrorState error={create.error} />}
        <div className="flex flex-col items-center gap-1.5 text-center text-[13px] text-ink-4">
          <p>{current.description}</p>
          <p className="flex items-start gap-1.5"><Lock className="mt-1 h-3.5 w-3.5 shrink-0" aria-hidden />{current.privacy}</p>
          <MockNote />
        </div>
      </div>
    </div>
  );
}
