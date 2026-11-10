import { useState, type ReactNode } from "react";
import clsx from "clsx";

/** Keep both panels mounted so switching panes preserves PDF and conversation state. */
export function ResponsiveReader({ source, children, pane: controlled, onPane, sourceLabel = "论文原文" }: {
  source: ReactNode;
  sourceLabel?: string;
  children: ReactNode;
  pane?: "source" | "assistant";
  onPane?: (pane: "source" | "assistant") => void;
}) {
  const [local, setLocal] = useState<"source" | "assistant">("source");
  const pane = controlled ?? local;
  return (
    <div className="reader-layout">
      <nav className="reader-pane-switch grid grid-cols-2 gap-0.5 rounded-[10px] bg-active p-[3px]" aria-label="阅读面板">
        {([["source", sourceLabel], ["assistant", "助手与设置"]] as const).map(([value, label]) => (
          <button type="button" key={value} aria-pressed={pane === value}
            className={clsx("h-9 rounded-lg text-[13px] transition-colors", pane === value ? "bg-card font-semibold text-ink shadow-[0_1px_2px_rgba(26,26,25,.1)]" : "font-medium text-ink-3 hover:text-ink")}
            onClick={() => { setLocal(value); onPane?.(value); }}>{label}</button>
        ))}
      </nav>
      <div className={clsx("reader-source", pane !== "source" && "reader-pane-hidden")}>{source}</div>
      <div className={clsx("reader-assistant", pane !== "assistant" && "reader-pane-hidden")}>{children}</div>
    </div>
  );
}
