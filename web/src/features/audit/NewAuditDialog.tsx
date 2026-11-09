import { useState } from "react";
import { useParams } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { READ_ONLY, send } from "@/api/client";
import { keys } from "@/api/queries";
import type { ClaimCategory, Job } from "@/api/types";
import { Modal } from "@/components/Modal";
import { ErrorState, MockNote } from "@/components/States";
import { CATEGORY_LABELS } from "@/lib/labels";

const SCOPE: ClaimCategory[] = ["research_question", "contribution", "method", "dataset_setup", "results", "limitations"];

/** POST /api/projects/{id}/audit-jobs — paste text or upload .txt/.md/.pptx. */
export function NewAuditDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { projectId = "" } = useParams();
  const client = useQueryClient();
  const [source, setSource] = useState<"paste" | "file">("paste");
  const [text, setText] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [scope, setScope] = useState<ClaimCategory[]>(SCOPE);

  const submit = useMutation({
    mutationFn: () => {
      const form = new FormData();
      if (source === "paste") form.set("report_text", text);
      else if (file) form.set("report_file", file);
      scope.forEach((item) => form.append("scope", item));
      form.set("audit_mode", "audit_existing");
      return send<Job>("POST", `/api/projects/${projectId}/audit-jobs`, form);
    },
    onSuccess: () => {
      client.invalidateQueries({ queryKey: keys.jobs(projectId) });
      onClose();
    },
  });

  const ready = scope.length > 0 && (source === "paste" ? text.trim().length > 0 : file !== null);
  return (
    <Modal open={open} onClose={onClose} title="审计一份报告" footer={
      <div className="flex justify-end gap-2">
        <button type="button" className="btn-secondary" onClick={onClose}>取消</button>
        <button type="button" className="btn-primary" disabled={READ_ONLY || !ready || submit.isPending} onClick={() => submit.mutate()}>开始审计</button>
      </div>
    }>
      <div className="flex flex-col gap-4">
        <div role="radiogroup" aria-label="报告来源" className="inline-flex gap-0.5 self-start rounded-[10px] bg-active p-[3px]">
          {([["paste", "粘贴文本"], ["file", "上传文件"]] as const).map(([value, label]) => (
            <button
              key={value}
              type="button"
              role="radio"
              aria-checked={source === value}
              onClick={() => setSource(value)}
              className={source === value ? "h-7 rounded-lg bg-card px-3 text-[13px] font-semibold shadow-[0_1px_2px_rgba(26,26,25,.1)]" : "h-7 rounded-lg px-3 text-[13px] text-ink-3"}
            >
              {label}
            </button>
          ))}
        </div>
        {source === "paste" ? (
          <label className="flex flex-col gap-1.5 text-sm">
            <span className="label">中文解读内容</span>
            <textarea
              value={text}
              onChange={(event) => setText(event.target.value)}
              rows={8}
              placeholder="粘贴针对该论文的中文总结、解读或阅读笔记…"
              className="resize-y rounded-lg bg-page p-3 leading-6 outline-none focus:ring-2 focus:ring-accent/30"
            />
          </label>
        ) : (
          <label className="flex flex-col gap-1.5 text-sm">
            <span className="label">报告文件（.txt / .md / .pptx）</span>
            <input type="file" accept=".txt,.md,.pptx" onChange={(event) => setFile(event.target.files?.[0] ?? null)} />
          </label>
        )}
        <fieldset className="flex flex-col gap-2">
          <legend className="label mb-1">审计范围</legend>
          <div className="flex flex-wrap gap-2">
            {SCOPE.map((item) => {
              const checked = scope.includes(item);
              return (
                <label key={item} className={checked ? "pill bg-ink text-white" : "pill bg-card text-ink-2"}>
                  <input
                    type="checkbox"
                    className="sr-only"
                    checked={checked}
                    onChange={() => setScope(checked ? scope.filter((s) => s !== item) : [...scope, item])}
                  />
                  {CATEGORY_LABELS[item]}
                </label>
              );
            })}
          </div>
        </fieldset>
        <p className="text-xs text-ink-4">报告审计会把论文文本和你提供的报告发送到你配置的模型服务。</p>
        {submit.error && <ErrorState error={submit.error} />}
        <MockNote />

      </div>
    </Modal>
  );
}
