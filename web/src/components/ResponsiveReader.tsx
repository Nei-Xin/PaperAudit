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
      <nav className="reader-pane-switch" aria-label="阅读面板">
        {([["source", sourceLabel], ["assistant", "助手与设置"]] as const).map(([value, label]) => (
          <button type="button" key={value} aria-pressed={pane === value}
            className={clsx("btn", pane === value ? "bg-ink text-white" : "bg-card text-ink-3")}
            onClick={() => { setLocal(value); onPane?.(value); }}>{label}</button>
        ))}
      </nav>
      <div className={clsx("reader-source", pane !== "source" && "reader-pane-hidden")}>{source}</div>
      <div className={clsx("reader-assistant", pane !== "assistant" && "reader-pane-hidden")}>{children}</div>
    </div>
  );
}
