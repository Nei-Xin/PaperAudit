import { useLayoutEffect, useState } from "react";

/** Callback ref also observes panels mounted after an asynchronous loading state. */
export function useContainerWidth<T extends HTMLElement>() {
  const [element, ref] = useState<T | null>(null);
  const [width, setWidth] = useState(0);
  useLayoutEffect(() => {
    if (!element) return;
    const observer = new ResizeObserver(([entry]) => setWidth(Math.floor(entry.contentRect.width)));
    observer.observe(element);
    return () => observer.disconnect();
  }, [element]);
  return [ref, width] as const;
}
