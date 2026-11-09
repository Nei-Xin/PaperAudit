import { useEffect } from "react";

/** Sets the tab title as "part · part · PaperAudit"; empty parts are skipped. */
export function useDocumentTitle(...parts: (string | undefined | null | false)[]) {
  const title = [...parts.filter(Boolean), "PaperAudit"].join(" · ");
  useEffect(() => {
    document.title = title;
  }, [title]);
}
