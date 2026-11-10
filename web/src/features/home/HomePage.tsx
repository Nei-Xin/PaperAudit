import { useRef, useState, type DragEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowUpRight, FileText, FileUp, Lock } from "lucide-react";
import clsx from "clsx";
import { READ_ONLY, send } from "@/api/client";
import { keys, useProjects } from "@/api/queries";
import { DEFAULT_WEIGHTS, RubricFields } from "@/features/review/ReviewForms";
import type { ProjectSummary, Venue, ClaimCategory } from "@/api/types";
import { ErrorState, MockNote } from "@/components/States";
import { AUDIT_SCOPE, ReportFields } from "./ReportFields";
import { useDocumentTitle } from "@/lib/useDocumentTitle";

type Mode = "learn" | "audit_existing" | "peer_review";

const MODES: {
  value: Mode;
  label: string;
  description: string;
  privacy: string;
}[] = [
  {
    value: "learn",
    label: "生成讲解",
    description:
      "研究问题、贡献、方法、实验、结果、局限与术语，每条都能跳回原文高亮。",
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
    privacy:
      "模拟评审会把论文文本发送到你配置的模型服务；结果是辅助预审意见，不代表真实录用结果。",
  },
];

const MAX_BYTES = 200 * 1024 * 1024;

export function HomePage() {
  useDocumentTitle("新建论文");
  const navigate = useNavigate();
  const client = useQueryClient();
  const input = useRef<HTMLInputElement>(null);
  const [mode, setMode] = useState<Mode>("learn");
  const [pdf, setPdf] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [report, setReport] = useState("");
  const [reportFile, setReportFile] = useState<File>();
  const [reportSource, setReportSource] = useState<"paste" | "file">("paste");
  const [scope, setScope] = useState<ClaimCategory[]>(AUDIT_SCOPE);
  const [reportReady, setReportReady] = useState(false);
  const [venue, setVenue] = useState<Venue>("general_ai_ml");
  const [weights, setWeights] =
    useState<Record<string, number>>(DEFAULT_WEIGHTS);
  const [code, setCode] = useState<File | null>(null);
  const [privacyAck, setPrivacyAck] = useState(false);
  const [fileError, setFileError] = useState("");
  const current = MODES.find((m) => m.value === mode)!;

  const pick = (file: File | undefined) => {
    if (!file) return;
    setPdf(null);
    if (
      file.type !== "application/pdf" &&
      !file.name.toLowerCase().endsWith(".pdf")
    )
      return setFileError("请选择 PDF 文件。");
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
      if (mode === "audit_existing") {
        if (reportSource === "paste") form.set("report_text", report);
        else form.set("report_file", reportFile!);
        scope.forEach((s) => form.append("scope", s));
      }
      if (mode === "peer_review") {
        form.set("venue", venue);
        form.set(
          "rubric_weights",
          JSON.stringify(venue === "custom" ? weights : {}),
        );
      }
      if (mode === "learn" && code) form.set("code_zip", code);
      form.set("privacy_ack", String(privacyAck));
      return send<{ project: ProjectSummary; job?: { job_id: string } | null }>(
        "POST",
        "/api/projects",
        form,
      );
    },
    onSuccess: (result) => {
      client.invalidateQueries({ queryKey: keys.projects });
      navigate(
        mode === "audit_existing"
          ? `/p/${result.project.project_id}/audit?job=${result.job?.job_id ?? ""}`
          : mode === "peer_review"
            ? `/p/${result.project.project_id}/review`
            : `/p/${result.project.project_id}/read`,
      );
    },
  });
  const ready =
    !fileError &&
    pdf !== null &&
    privacyAck &&
    (mode !== "peer_review" ||
      venue !== "custom" ||
      Object.values(weights).reduce((a, b) => a + b, 0) > 0) &&
    (mode !== "audit_existing" ||
      (scope.length > 0 &&
        (reportSource === "paste"
          ? report.trim().length > 0
          : reportFile && reportReady)));

  return (
    <div className="card flex h-full items-start justify-center overflow-auto px-4 sm:px-6">
      <div className="flex w-full min-w-0 max-w-[680px] flex-col gap-6 pb-12 pt-[clamp(2rem,10vh,7rem)]">
        <h1 className="text-center text-[30px] font-semibold tracking-tight">
          今天读哪篇论文？
        </h1>

        <div className="overflow-hidden rounded-2xl bg-card shadow-[0_4px_16px_rgba(26,26,25,.06),0_0_0_1px_#E7E5E1]">
          <button
            type="button"
            onClick={() => input.current?.click()}
            onDragOver={(event) => {
              event.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
            className={clsx(
              "flex w-full flex-col items-center gap-2 border-b border-dashed border-line px-6 py-9 transition-colors",
              dragging ? "bg-accent-soft" : "hover:bg-[#FAFAF9]",
            )}
          >
            <FileUp className="h-7 w-7 text-ink-3" aria-hidden />
            <strong
              title={pdf?.name}
              className="max-w-full break-all text-base font-semibold"
            >
              {pdf ? pdf.name : "拖入论文 PDF，或点击选择"}
            </strong>
            <span className="text-[13px] text-ink-4">
              {pdf
                ? `${(pdf.size / 1024 / 1024).toFixed(1)} MB · 点击更换`
                : "带文字层的英文论文 · 最大 200MB"}
            </span>
          </button>
          <input
            ref={input}
            type="file"
            accept="application/pdf"
            className="hidden"
            onChange={(event) => pick(event.target.files?.[0])}
          />

          <fieldset
            disabled={create.isPending}
            className="flex min-w-0 flex-col gap-3 p-3"
          >
            <div className="flex flex-wrap items-center gap-2">
              <div
                role="radiogroup"
                aria-label="要做什么"
                className="flex flex-wrap gap-1.5"
              >
                {MODES.map((item) => (
                  <button
                    key={item.value}
                    type="button"
                    role="radio"
                    aria-checked={mode === item.value}
                    disabled={create.isPending}
                    onClick={() => setMode(item.value)}
                    className={clsx(
                      "pill",
                      mode === item.value
                        ? "bg-ink text-white shadow-none"
                        : "bg-card text-ink-2 hover:bg-hover",
                    )}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
              <button
                type="button"
                className="btn-primary ml-auto"
                disabled={!ready || READ_ONLY || create.isPending}
                onClick={() => create.mutate()}
              >
                {create.isPending
                  ? "正在上传并解析…"
                  : mode === "learn"
                    ? "生成讲解"
                    : mode === "peer_review"
                      ? "开始评审"
                      : "开始审计"}
              </button>
            </div>
            {mode === "audit_existing" && (
              <ReportFields
                text={report}
                onText={setReport}
                file={reportFile}
                onFile={setReportFile}
                source={reportSource}
                onSource={setReportSource}
                scope={scope}
                onScope={setScope}
                onReady={setReportReady}
              />
            )}
            {mode === "peer_review" && (
              <RubricFields
                venue={venue}
                weights={weights}
                onVenue={setVenue}
                onWeights={setWeights}
              />
            )}
            {mode === "learn" && (
              <label className="flex min-w-0 flex-col gap-2 text-[13px] text-ink-3 sm:flex-row sm:items-center">
                <span className="label">源码 ZIP（可选）</span>
                <input
                  className="min-w-0 max-w-full flex-1"
                  type="file"
                  accept=".zip"
                  onChange={(e) => {
                    const f = e.target.files?.[0];
                    setCode(null);
                    setFileError("");
                    if (
                      f &&
                      (!f.name.toLowerCase().endsWith(".zip") ||
                        f.size > 30 * 1024 * 1024)
                    ) {
                      setFileError("请选择不超过 30MB 的 ZIP。");
                      return;
                    }
                    setCode(f ?? null);
                  }}
                />
              </label>
            )}
          </fieldset>
        </div>

        {!READ_ONLY && (
          <label className="flex items-start gap-2 text-sm text-ink-3">
            <input
              type="checkbox"
              checked={privacyAck}
              onChange={(e) => setPrivacyAck(e.target.checked)}
              className="mt-1"
            />
            我同意将论文文本发送到已配置的模型服务以完成所选操作。
          </label>
        )}
        {fileError && <ErrorState error={new Error(fileError)} />}
        {create.error && <ErrorState error={create.error} />}
        <div className="flex flex-col items-center gap-1.5 text-center text-[13px] text-ink-4">
          <p>{current.description}</p>
          <p className="flex items-start gap-1.5">
            <Lock className="mt-1 h-3.5 w-3.5 shrink-0" aria-hidden />
            {current.privacy}
          </p>
          <MockNote />
        </div>
        <RecentProjects />
      </div>
    </div>
  );
}

const PROJECT_FEATURES: [keyof ProjectSummary, string][] = [
  ["has_learning_report", "讲解"], ["has_audit", "审计"], ["has_peer_review", "评审"], ["has_code", "代码"],
];

/** The latest papers, so the start page is also a way back into recent work. */
function RecentProjects() {
  const projects = useProjects();
  const recent = [...(projects.data ?? [])]
    .sort((a, b) => b.updated_at.localeCompare(a.updated_at))
    .slice(0, 6);
  if (!recent.length) return null;
  return (
    <section className="home-recent mt-6 flex flex-col gap-3" aria-label="最近的论文">
      <h2 className="label px-1">最近的论文</h2>
      <ul className="home-recent-grid">
        {recent.map((project) => {
          const features = PROJECT_FEATURES.filter(([key]) => project[key]).map(([, label]) => label);
          return (
            <li key={project.project_id}>
              <Link
                to={`/p/${project.project_id}`}
                className="group flex h-full flex-col gap-3 rounded-xl bg-[#FAFAF9] p-4 shadow-[0_0_0_1px_#ECEBE8] transition-[box-shadow,background-color] hover:bg-card hover:shadow-[0_6px_18px_rgba(26,26,25,.07),0_0_0_1px_#DAD8D3]"
              >
                <span className="flex items-start gap-2.5">
                  <FileText className="mt-0.5 h-4 w-4 shrink-0 text-ink-4" aria-hidden />
                  <span className="line-clamp-2 flex-1 text-sm font-medium leading-snug">{project.title}</span>
                  <ArrowUpRight className="h-4 w-4 shrink-0 text-ink-4 opacity-0 transition-opacity group-hover:opacity-100" aria-hidden />
                </span>
                <span className="mt-auto flex flex-wrap items-center gap-1.5 pl-[26px] text-xs text-ink-4">
                  {features.length ? features.map((label) => (
                    <span key={label} className="rounded-md bg-page px-1.5 py-0.5 text-ink-3">{label}</span>
                  )) : <span>仅原文</span>}
                  <span className="ml-auto whitespace-nowrap">{new Date(project.updated_at).toLocaleDateString("zh-CN", { month: "numeric", day: "numeric" })}</span>
                </span>
              </Link>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
