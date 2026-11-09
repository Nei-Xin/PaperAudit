import type { ReactNode } from "react";
import { AlertCircle, Loader2 } from "lucide-react";
import { READ_ONLY } from "@/api/client";

export function Loading({ label = "加载中…" }: { label?: string }) {
  return (
    <div className="flex h-full min-h-40 items-center justify-center gap-2 text-ink-4" role="status">
      <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
      <span>{label}</span>
    </div>
  );
}

export function ErrorState({ error }: { error: unknown }) {
  const message = error instanceof Error ? error.message : "请求失败";
  return (
    <div className="flex items-center gap-2 rounded-lg bg-bad-soft px-3 py-2 text-bad-text" role="alert">
      <AlertCircle className="h-4 w-4 shrink-0" aria-hidden />
      <span>{message}</span>
    </div>
  );
}

export function EmptyState({ title, children, action }: { title: string; children?: ReactNode; action?: ReactNode }) {
  return (
    <div className="flex flex-col gap-3 p-6">
      <h2 className="text-lg font-semibold">{title}</h2>
      {children && <div className="text-sm leading-7 text-ink-3">{children}</div>}
      {action}
    </div>
  );
}

/** Shown next to write actions while the app runs on exported demo data. */
export function MockNote() {
  if (!READ_ONLY) return null;
  return <p className="text-xs text-ink-4">只读预览：写入接口尚未接入，此操作暂不可用。</p>;
}

export function Progress({ value, label }: { value: number; label?: string }) {
  return (
    <div className="flex flex-col gap-1.5">
      <div className="h-1.5 overflow-hidden rounded-full bg-line-soft" role="progressbar" aria-valuenow={Math.round(value * 100)} aria-valuemin={0} aria-valuemax={100}>
        <div className="h-full rounded-full bg-accent transition-[width]" style={{ width: `${Math.round(value * 100)}%` }} />
      </div>
      {label && <span className="text-xs text-ink-4">{label}</span>}
    </div>
  );
}
