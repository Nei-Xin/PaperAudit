import { useMutation } from "@tanstack/react-query";
import { READ_ONLY, send } from "@/api/client";
import type { ClaimCategory } from "@/api/types";
import type { components } from "@/api/schema";
import { ErrorState } from "@/components/States";
import { CATEGORY_LABELS } from "@/lib/labels";

export const AUDIT_SCOPE: ClaimCategory[] = [
  "research_question",
  "contribution",
  "method",
  "dataset_setup",
  "results",
  "limitations",
];
export function ReportFields({
  text,
  onText,
  file,
  onFile,
  source,
  onSource,
  scope,
  onScope,
  onReady,
}: {
  text: string;
  onText: (s: string) => void;
  file: File | undefined;
  onFile: (f: File | undefined) => void;
  source: "paste" | "file";
  onSource: (s: "paste" | "file") => void;
  scope: ClaimCategory[];
  onScope: (s: ClaimCategory[]) => void;
  onReady: (v: boolean) => void;
}) {
  const preview = useMutation({
    mutationFn: (f: File) => {
      const form = new FormData();
      form.set("report_file", f);
      return send<components["schemas"]["ReportPreview"]>(
        "POST",
        "/api/report-files/parse",
        form,
      );
    },
    onSuccess: () => onReady(true),
    onError: () => onReady(false),
  });
  return (
    <div className="flex flex-col gap-3">
      <div role="radiogroup" aria-label="报告来源" className="flex gap-2">
        {(["paste", "file"] as const).map((s) => (
          <button
            className="pill"
            role="radio"
            aria-checked={source === s}
            key={s}
            onClick={() => onSource(s)}
          >
            {s === "paste" ? "粘贴文本" : "上传文件"}
          </button>
        ))}
      </div>
      {source === "paste" ? (
        <label className="flex flex-col gap-1.5">
          <span className="label">中文解读内容</span>
          <textarea
            className="rounded-lg bg-page p-3 text-sm leading-6"
            rows={5}
            maxLength={100000}
            value={text}
            onChange={(e) => onText(e.target.value)}
            placeholder="粘贴针对该论文的总结、解读或阅读笔记…"
          />
        </label>
      ) : (
        <label className="flex flex-col gap-2 text-sm">
          报告文件（.txt / .md / .pptx）
          <input
            className="w-full min-w-0"
            type="file"
            accept=".txt,.md,.pptx"
            disabled={preview.isPending}
            onChange={(e) => {
              const f = e.target.files?.[0];
              onFile(f);
              onReady(false);
              preview.reset();
              if (f && !READ_ONLY) preview.mutate(f);
            }}
          />
          {file && (
            <span className="break-all text-xs text-ink-3">{file.name}</span>
          )}
        </label>
      )}
      {source === "file" && preview.isPending && (
        <p role="status" className="text-xs">
          正在解析报告文件…
        </p>
      )}
      {source === "file" && preview.error && (
        <ErrorState error={preview.error} />
      )}{" "}
      {source === "file" && preview.data && (
        <p role="status" className="text-xs">
          可审计文本 {preview.data.character_count} 字符
          {preview.data.page_count
            ? ` · ${preview.data.page_count} 页幻灯片`
            : ""}{" "}
          {preview.data.warnings.join("；")}
        </p>
      )}
      <fieldset>
        <legend className="mb-2 text-xs">审计范围</legend>
        <div className="flex flex-wrap gap-2">
          {AUDIT_SCOPE.map((s) => (
            <label className="flex items-center gap-1 text-xs" key={s}>
              <input
                type="checkbox"
                checked={scope.includes(s)}
                onChange={() =>
                  onScope(
                    scope.includes(s)
                      ? scope.filter((v) => v !== s)
                      : [...scope, s],
                  )
                }
              />
              {CATEGORY_LABELS[s]}
            </label>
          ))}
        </div>
      </fieldset>
    </div>
  );
}
