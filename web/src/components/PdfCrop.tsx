import { useLayoutEffect, useRef, useState, type ReactNode } from "react";
import { Document, Page } from "react-pdf";
import { pdfUrl } from "@/api/client";
import type { PageRect } from "@/api/types";
import { Loading } from "./States";
// PdfPanel configures the pdf.js worker; importing it keeps that side effect.
import "./PdfPanel";

/** One pdf.js document shared by several crops (one download, one parse). */
export function PdfDocument({ projectId, children }: { projectId: string; children: ReactNode }) {
  return (
    <Document
      file={pdfUrl(projectId)}
      loading={<Loading label="正在加载原文…" />}
      error={<p className="py-3 text-sm text-bad-text">原文加载失败</p>}
    >
      {children}
    </Document>
  );
}

type Box = { x0: number; y0: number; x1: number; y1: number };

/**
 * Pick the region of the page to show and its scale.
 * - Width: the highlighted lines (at least a text column), so a neighbouring
 *   column is not sliced in half; never magnified past `maxScale`.
 * - Height: a band of extra page above/below is rendered so the reader can
 *   scroll to a table body or the preceding sentence; the viewport starts
 *   at the highlight with `contextPt` above it.
 */
export function cropGeometry(
  rects: PageRect[], page: { width: number; height: number }, boxWidth: number,
  { maxScale = 1.6, minWidthPt = 240, contextPt = 30, bandPt = 220, padPt = 8 } = {},
) {
  const bbox: Box = rects.reduce(
    (acc, r) => ({ x0: Math.min(acc.x0, r.x0), y0: Math.min(acc.y0, r.y0), x1: Math.max(acc.x1, r.x1), y1: Math.max(acc.y1, r.y1) }),
    { x0: Infinity, y0: Infinity, x1: -Infinity, y1: -Infinity },
  );
  // Evidence wider than ~half the page spans the whole text block (two-column
  // figures, tables, captions): show the full block so lines are not cut mid-word.
  const spansBlock = bbox.x1 - bbox.x0 > page.width * 0.45;
  const left = spansBlock ? Math.max(0, Math.min(bbox.x0 - padPt, page.width * 0.08)) : undefined;
  const right = spansBlock ? Math.min(page.width, Math.max(bbox.x1 + padPt, page.width * 0.92)) : undefined;
  const width = spansBlock
    ? right! - left!
    : Math.min(page.width, Math.max(bbox.x1 - bbox.x0 + padPt * 2, minWidthPt));
  const scale = Math.min(maxScale, boxWidth / width);
  const center = (bbox.x0 + bbox.x1) / 2;
  const x = spansBlock ? left! : Math.min(Math.max(center - width / 2, 0), Math.max(page.width - width, 0));
  const top = Math.max(0, bbox.y0 - bandPt);
  const bottom = Math.min(page.height, bbox.y1 + bandPt);
  const focusTop = Math.max(top, bbox.y0 - contextPt);
  const focusBottom = Math.min(bottom, bbox.y1 + contextPt);
  return { scale, x, y: top, width, height: bottom - top, focusOffset: focusTop - top, focusHeight: focusBottom - focusTop };
}

/**
 * A magnified slice of one PDF page around the evidence highlights.
 * Must be rendered inside <PdfDocument>. Rects are PyMuPDF points (top-left origin).
 */
export function PdfCrop({
  page, pageSize, rects, maxHeight = 360, label, contextPt,
}: {
  page: number;
  pageSize: { width: number; height: number } | undefined;
  rects: PageRect[];
  maxHeight?: number;
  label?: string;
  /** Page context shown above/below the highlight before scrolling (points). */
  contextPt?: number;
}) {
  const boxRef = useRef<HTMLDivElement>(null);
  const [boxWidth, setBoxWidth] = useState(0);
  useLayoutEffect(() => {
    const element = boxRef.current;
    if (!element) return;
    const observer = new ResizeObserver(([entry]) => setBoxWidth(Math.floor(entry.contentRect.width)));
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  const ready = boxWidth > 0 && pageSize && pageSize.width > 0 && rects.length > 0;
  const crop = ready ? cropGeometry(rects, pageSize, boxWidth, contextPt === undefined ? {} : { contextPt }) : undefined;
  const scroller = useRef<HTMLDivElement>(null);
  const viewport = crop ? Math.min(maxHeight, Math.max(150, crop.focusHeight * crop.scale)) : 0;
  const focus = crop ? crop.focusOffset * crop.scale : 0;
  // Start each crop at the highlight; the band around it stays reachable by scrolling.
  useLayoutEffect(() => {
    if (scroller.current) scroller.current.scrollTop = focus;
  }, [focus, page]);

  return (
    <div ref={boxRef} className="w-full">
      {crop && pageSize && (
        <div
          ref={scroller}
          className="pdf-crop relative overflow-y-auto overflow-x-hidden rounded-lg bg-white shadow-[inset_0_0_0_1px_#ECEBE8]"
          style={{ height: viewport }}
          tabIndex={0}
          role="img"
          aria-label={label ?? `原文第 ${page} 页片段`}
        >
          <div className="relative mx-auto overflow-hidden" style={{ width: crop.width * crop.scale, height: crop.height * crop.scale }}>
            <div className="absolute" style={{ left: -crop.x * crop.scale, top: -crop.y * crop.scale }}>
              <Page
                pageNumber={page}
                width={pageSize.width * crop.scale}
                renderAnnotationLayer={false}
                renderTextLayer={false}
                loading={<div style={{ width: pageSize.width * crop.scale, height: pageSize.height * crop.scale }} />}
                // Re-apply the start position once drawn: canvas layout can move the scroll offset.
                onRenderSuccess={() => { if (scroller.current) scroller.current.scrollTop = focus; }}
              />
              {rects.map((rect, index) => (
                <div
                  key={`${rect.x0}-${rect.y0}-${index}`}
                  aria-hidden
                  className="pointer-events-none absolute rounded-[2px] bg-yellow-300/30 mix-blend-multiply"
                  style={{
                    left: rect.x0 * crop.scale - 1,
                    top: rect.y0 * crop.scale - 1,
                    width: (rect.x1 - rect.x0) * crop.scale + 2,
                    height: (rect.y1 - rect.y0) * crop.scale + 2,
                  }}
                />
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
