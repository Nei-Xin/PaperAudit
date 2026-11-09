import { useEffect, useRef, type ReactNode } from "react";
import clsx from "clsx";

/** <details> dropdown that also closes on an outside click or Esc. */
export function Popover({ summary, children, className }: { summary: ReactNode; children: ReactNode; className?: string }) {
  const ref = useRef<HTMLDetailsElement>(null);
  useEffect(() => {
    const close = (focusSummary: boolean) => {
      const details = ref.current;
      if (!details?.open) return;
      details.open = false;
      if (focusSummary) details.querySelector("summary")?.focus();
    };
    const onPointer = (event: PointerEvent) => {
      if (!ref.current?.contains(event.target as Node)) close(false);
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape" && ref.current?.open) { event.preventDefault(); close(true); }
    };
    document.addEventListener("pointerdown", onPointer);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("pointerdown", onPointer);
      document.removeEventListener("keydown", onKey);
    };
  }, []);
  return (
    <details ref={ref} className="relative">
      <summary className="btn-secondary cursor-pointer list-none">{summary}</summary>
      <div className={clsx("absolute right-0 z-20 mt-1 rounded-xl bg-card p-3 shadow-pop", className)}>{children}</div>
    </details>
  );
}
