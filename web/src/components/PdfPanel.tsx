import {
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { Document, Page, pdfjs } from "react-pdf";
import workerSrc from "pdfjs-dist/build/pdf.worker.min.mjs?url";
import "react-pdf/dist/Page/TextLayer.css";
import {
  ChevronLeft,
  ChevronRight,
  Maximize2,
  Minus,
  Plus,
} from "lucide-react";
import clsx from "clsx";
import { pdfUrl } from "@/api/client";
import type { PageRect, PaperSelection } from "@/api/types";
import { Loading } from "./States";

pdfjs.GlobalWorkerOptions.workerSrc = workerSrc;

/** Widest a page is drawn at 100% (≈1.5× an A4/Letter page); wide screens get margins, not giant text. */
const MAX_FIT_WIDTH = 920;

function useElementWidth<T extends HTMLElement>() {
  const ref = useRef<T>(null);
  const [width, setWidth] = useState(0);
  useLayoutEffect(() => {
    const element = ref.current;
    if (!element) return;
    const observer = new ResizeObserver(([entry]) =>
      setWidth(Math.floor(entry.contentRect.width)),
    );
    observer.observe(element);
    return () => observer.disconnect();
  }, []);
  return [ref, width] as const;
}

/**
 * One PDF page with evidence highlights. Rects are PyMuPDF page coordinates
 * (points, top-left origin), so scale = rendered width / PyMuPDF page width.
 */
export function PdfPage({
  projectId,
  page,
  pageWidthPt,
  highlights = [],
  zoom = 1,
  scrollToHighlight = true,
}: {
  projectId: string;
  page: number;
  pageWidthPt: number;
  highlights?: PageRect[];
  zoom?: number;
  scrollToHighlight?: boolean;
}) {
  const [boxRef, boxWidth] = useElementWidth<HTMLDivElement>();
  const firstMark = useRef<HTMLDivElement>(null);
  // "Fit width" stops at a comfortable reading size; zoom still goes beyond it.
  const renderWidth = Math.max(0, Math.floor(Math.min(boxWidth, MAX_FIT_WIDTH) * zoom));
  const scale = pageWidthPt > 0 ? renderWidth / pageWidthPt : 1;

  // Scroll once the page has actually rendered: before that the page box has
  // no height and the highlight would be scrolled to the wrong place.
  const [renderedPage, setRenderedPage] = useState(0);
  useEffect(() => {
    if (scrollToHighlight && highlights.length && renderedPage === page) {
      const mark = firstMark.current;
      const scroller = mark?.closest<HTMLElement>(".pdf-scroll");
      if (mark && scroller) {
        // Scroll only the PDF viewport; scrollIntoView would also move dialogs and the page.
        const offset = mark.getBoundingClientRect().top - scroller.getBoundingClientRect().top;
        scroller.scrollTo({ top: scroller.scrollTop + offset - scroller.clientHeight / 3, behavior: "smooth" });
      } else {
        mark?.scrollIntoView({ block: "center", behavior: "smooth" });
      }
    }
  }, [highlights, page, scrollToHighlight, renderWidth, renderedPage]);

  return (
    <div ref={boxRef} className="w-full">
      {renderWidth > 0 && (
        <Document
          file={pdfUrl(projectId)}
          loading={<Loading label="正在加载 PDF…" />}
          error={<p className="p-4 text-sm text-bad-text">PDF 加载失败</p>}
        >
          <div
            className="relative mx-auto shadow-[0_0_0_1px_#EEEDEA,0_6px_20px_rgba(26,26,25,.06)]"
            style={{ width: renderWidth }}
          >
            <Page
              pageNumber={page}
              width={renderWidth}
              renderAnnotationLayer={false}
              renderTextLayer
              loading={<Loading />}
              onRenderSuccess={() => setRenderedPage(page)}
            />
            {highlights.map((rect, index) => (
              <div
                key={`${rect.x0}-${rect.y0}-${index}`}
                ref={index === 0 ? firstMark : undefined}
                aria-hidden
                className="pointer-events-none absolute rounded-[2px] bg-yellow-300/35 ring-1 ring-yellow-500/40"
                style={{
                  left: rect.x0 * scale,
                  top: rect.y0 * scale,
                  width: (rect.x1 - rect.x0) * scale,
                  height: (rect.y1 - rect.y0) * scale,
                }}
              />
            ))}
          </div>
        </Document>
      )}
    </div>
  );
}

/** Typing is a draft; the page changes on Enter or blur, and Esc restores it. */
function PageInput({
  page,
  pageCount,
  onPage,
}: {
  page: number;
  pageCount: number;
  onPage: (page: number) => void;
}) {
  const [draft, setDraft] = useState(String(page));
  useEffect(() => setDraft(String(page)), [page]);
  const commit = () => {
    const value = Number.parseInt(draft, 10);
    // Reset first: an out-of-range value clamps to the current page and would not re-render.
    setDraft(String(page));
    if (Number.isFinite(value) && value !== page) onPage(value);
  };
  return (
    <input
      type="text"
      inputMode="numeric"
      aria-label={`页码，共 ${pageCount} 页`}
      value={draft}
      onChange={(event) => setDraft(event.target.value.replace(/[^0-9]/g, ""))}
      onBlur={commit}
      onKeyDown={(event) => {
        if (event.key === "Enter") {
          event.preventDefault();
          commit();
        }
        if (event.key === "Escape") setDraft(String(page));
      }}
      onFocus={(event) => event.currentTarget.select()}
      className="h-7 w-12 rounded-md bg-page text-center text-ink outline-none focus:ring-2 focus:ring-accent/30"
    />
  );
}

/** Card with a compact toolbar (page ‹ n/N ›, zoom) around a scrollable PdfPage. */
export function PdfPanel({
  projectId,
  page,
  pageCount,
  pageSizes,
  onPage,
  highlights,
  title = "论文原文",
  footer,
  className,
  onSelection,
}: {
  projectId: string;
  page: number;
  pageCount: number;
  pageSizes: { width: number; height: number }[];
  onPage: (page: number) => void;
  highlights?: PageRect[];
  title?: string;
  footer?: ReactNode;
  className?: string;
  onSelection?: (selection: PaperSelection) => void;
}) {
  const [zoom, setZoom] = useState(1);
  const selectionBox = useRef<HTMLDivElement>(null);
  const [selectedText, setSelectedText] = useState("");
  useEffect(() => {
    setSelectedText("");
    if (!onSelection) return;
    const changed = () => {
      const selected = window.getSelection();
      if (
        selected?.anchorNode &&
        selected.focusNode &&
        selectionBox.current?.contains(selected.anchorNode) &&
        selectionBox.current.contains(selected.focusNode)
      ) {
        setSelectedText(selected.toString().trim());
      } else setSelectedText("");
    };
    document.addEventListener("selectionchange", changed);
    return () => document.removeEventListener("selectionchange", changed);
  }, [page, projectId, onSelection]);
  const clamp = (value: number) => Math.min(Math.max(value, 1), pageCount);
  return (
    <section
      className={clsx(
        "pdf-panel card flex h-full min-h-0 min-w-0 flex-col overflow-hidden",
        className,
      )}
      aria-label={title}
    >
      <div className="pdf-toolbar flex shrink-0 flex-wrap items-center gap-1 border-b border-line-soft px-2 py-1.5">
        <span className="pdf-toolbar-title mr-auto text-[13px] font-semibold">
          {title}
        </span>
        <button
          type="button"
          className="icon-btn"
          onClick={() => onPage(clamp(page - 1))}
          disabled={page <= 1}
          aria-label="上一页"
        >
          <ChevronLeft className="h-4 w-4" />
        </button>
        <label className="flex items-center gap-1 text-[13px] text-ink-3">
          <span className="sr-only">页码</span>
          <PageInput
            page={page}
            pageCount={pageCount}
            onPage={(value) => onPage(clamp(value))}
          />
          / {pageCount}
        </label>
        <button
          type="button"
          className="icon-btn"
          onClick={() => onPage(clamp(page + 1))}
          disabled={page >= pageCount}
          aria-label="下一页"
        >
          <ChevronRight className="h-4 w-4" />
        </button>
        <span className="mx-1 h-4 w-px bg-line" aria-hidden />
        <button
          type="button"
          className="icon-btn"
          onClick={() => setZoom((z) => Math.max(1, +(z - 0.1).toFixed(1)))}
          disabled={zoom <= 1}
          aria-label="缩小"
        >
          <Minus className="h-4 w-4" />
        </button>
        <span className="w-11 text-center text-[13px] text-ink-3">
          {Math.round(zoom * 100)}%
        </span>
        <button
          type="button"
          className="icon-btn"
          onClick={() => setZoom((z) => Math.min(2, +(z + 0.1).toFixed(1)))}
          disabled={zoom >= 2}
          aria-label="放大"
        >
          <Plus className="h-4 w-4" />
        </button>
        <button
          type="button"
          className="icon-btn"
          onClick={() => setZoom(1)}
          aria-label="适应宽度"
          title="适应宽度"
        >
          <Maximize2 className="h-4 w-4" />
        </button>
      </div>
      {onSelection && selectedText && (
        <div className="flex shrink-0 flex-wrap items-center gap-2 border-b border-line-soft px-3 py-2 text-xs">
          <span>
            已选 {selectedText.length} 字符
            {selectedText.length > 2000 ? "，请缩短到 2000 字符以内" : ""}
          </span>
          <button
            className="btn-secondary"
            disabled={selectedText.length > 2000}
            onMouseDown={(e) => e.preventDefault()}
            onClick={() => {
              onSelection({ text: selectedText, page, chunk_ids: [] });
              window.getSelection()?.removeAllRanges();
              setSelectedText("");
            }}
          >
            就选中原文提问
          </button>
        </div>
      )}
      <div
        ref={selectionBox}
        className="pdf-scroll min-h-0 flex-1 overflow-auto bg-[#F6F6F4] p-3 sm:p-5"
      >
        <PdfPage
          projectId={projectId}
          page={page}
          pageWidthPt={pageSizes[page - 1]?.width ?? 0}
          highlights={highlights}
          zoom={zoom}
        />
      </div>
      {footer && (
        <div className="shrink-0 border-t border-line-soft px-4 py-2 text-xs text-ink-4">
          {footer}
        </div>
      )}
    </section>
  );
}
