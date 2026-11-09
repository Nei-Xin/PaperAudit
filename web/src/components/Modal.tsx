import { useEffect, useRef, type ReactNode } from "react";
import { X } from "lucide-react";
import clsx from "clsx";

/** Native <dialog>: focus trap, Esc to close and backdrop come for free. */
export function Modal({
  open, onClose, title, children, wide = false, drawer = false, footer,
}: { open: boolean; onClose: () => void; title: string; children: ReactNode; wide?: boolean; drawer?: boolean; footer?: ReactNode }) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);
  return (
    <dialog
      ref={ref}
      onClose={onClose}
      onClick={(event) => { if (event.target === ref.current) onClose(); }}
      className={clsx(
        "modal rounded-card bg-card p-0 text-ink shadow-pop backdrop:bg-ink/30",
        drawer && "modal-drawer",
        wide ? "w-[min(960px,94vw)]" : "w-[min(520px,94vw)]",
      )}
      aria-label={title}
    >
      {open && (
        <div className="modal-content">
          <header className="flex shrink-0 items-center justify-between gap-3 border-b border-line-soft px-5 py-3">
            <h2 className="text-[15px] font-semibold">{title}</h2>
            <button type="button" className="icon-btn" onClick={onClose} aria-label="关闭">
              <X className="h-4 w-4" />
            </button>
          </header>
          <div className={clsx("min-h-0 overflow-auto", drawer ? "flex-1" : "p-4 sm:p-5")}>{children}</div>
          {footer && <footer className="shrink-0 border-t border-line-soft bg-card px-4 py-3">{footer}</footer>}
        </div>
      )}
    </dialog>
  );
}
