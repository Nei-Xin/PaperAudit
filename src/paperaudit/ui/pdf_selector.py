"""Selectable local PDF page rendered as a Streamlit bidirectional component."""

from __future__ import annotations

import base64
from typing import Any

import pymupdf
import streamlit as st

from paperaudit.models import PageRect


_PDF_SELECTOR_HTML = """
<div class="pa-selectable-pdf" aria-label="可选择文字的论文 PDF 页面"></div>
"""

_PDF_SELECTOR_CSS = """
.pa-selectable-pdf {
  position: relative;
  width: 100%;
  height: auto !important;
  min-height: 0 !important;
  overflow: visible;
  padding: 0;
  box-sizing: border-box;
  background: white;
  color: var(--st-text-color);
}
.pa-pdf-frame {
  position: relative;
  width: 100%;
  margin: 0;
  overflow: hidden;
  border: 0;
  border-radius: 0;
  background: white;
  box-shadow: none;
}
.pa-pdf-frame img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  display: block;
  object-fit: contain;
  user-select: none;
  pointer-events: none;
}
.pa-pdf-highlight-layer,
.pa-pdf-text-layer {
  position: absolute;
  inset: 0;
}
.pa-pdf-highlight-layer { pointer-events: none; }
.pa-pdf-highlight {
  position: absolute;
  border-radius: 2px;
  background: rgba(250, 204, 21, .32);
  box-shadow: inset 0 0 0 1px rgba(234, 179, 8, .12);
}
.pa-pdf-highlight.is-focus {
  animation: paPdfEvidencePulse 1.5s ease-out 1;
}
@keyframes paPdfEvidencePulse {
  0%, 45% { background: rgba(250, 204, 21, .72); box-shadow: 0 0 0 3px rgba(250, 204, 21, .22); }
  100% { background: rgba(250, 204, 21, .32); box-shadow: inset 0 0 0 1px rgba(234, 179, 8, .12); }
}
.pa-pdf-text-layer { z-index: 3; cursor: text; user-select: text; }
.pa-pdf-word {
  position: absolute;
  margin: 0;
  padding: 0;
  border: 0;
  color: rgba(0, 0, 0, .01);
  white-space: pre;
  line-height: 1;
  user-select: text;
  transform-origin: left top;
}
.pa-pdf-word::selection {
  color: transparent;
  background: rgba(37, 99, 235, .34);
}
.pa-pdf-selection-action {
  position: absolute;
  z-index: 5;
  left: 12px;
  display: none;
  align-items: center;
  width: max-content;
  box-sizing: border-box;
  border: 1px solid rgba(6, 95, 70, .22);
  border-radius: 999px;
  background: #147052;
  box-shadow: 0 8px 20px rgba(15, 23, 42, .2);
  font: 12px/1.2 var(--st-font);
}
.pa-pdf-selection-action.is-visible { display: flex; }
.pa-pdf-selection-action::after {
  position: absolute;
  left: 18px;
  width: 0;
  height: 0;
  border: 6px solid transparent;
  content: '';
}
.pa-pdf-selection-action.is-above::after {
  top: 100%;
  border-top-color: #147052;
}
.pa-pdf-selection-action.is-below::after {
  bottom: 100%;
  border-bottom-color: #147052;
}
.pa-pdf-selection-button {
  padding: 8px 12px;
  border: 0;
  border-radius: inherit;
  background: transparent;
  color: white;
  font-weight: 650;
  letter-spacing: .01em;
  cursor: pointer;
}
.pa-pdf-selection-action:hover { background: #0f6047; }
.pa-pdf-selection-action:hover::after { border-top-color: #0f6047; }
.pa-pdf-selection-action.is-below:hover::after {
  border-top-color: transparent;
  border-bottom-color: #0f6047;
}
"""

_PDF_SELECTOR_JS = r"""
export default function(component) {
  const { data, parentElement, setTriggerValue } = component;
  const host = parentElement.querySelector('.pa-selectable-pdf');
  if (!host || !data) return;
  host.replaceChildren();

  const frame = document.createElement('div');
  frame.className = 'pa-pdf-frame';
  frame.style.aspectRatio = `${data.page_width} / ${data.page_height}`;
  const zoom = Math.max(50, Math.min(Number(data.zoom_percent || 100), 180));
   // Fit the page to the reader on ordinary screens, while capping the page
   // width on very wide displays so more of the document remains visible.
   // Zoom levels above 100% can still grow beyond the cap and scroll.
   const fitScale = Math.max(.6, Math.min(Number(data.fit_scale || .92), 1.08));
   const availableWidth = Math.max(120, host.clientWidth - 28);
   const fitWidth = Math.min(availableWidth * fitScale, 1120);
   const pageWidth = fitWidth * zoom / 100;
  frame.style.width = `${Math.max(120, pageWidth)}px`;

  const image = document.createElement('img');
  image.src = data.image_url;
  image.alt = `论文 PDF 第 ${data.page_number} 页`;
  frame.appendChild(image);

  const highlightLayer = document.createElement('div');
  highlightLayer.className = 'pa-pdf-highlight-layer';
  const highlightNodes = [];
  for (const rect of data.highlights || []) {
    const marker = document.createElement('div');
    marker.className = `pa-pdf-highlight${data.focus_highlight ? ' is-focus' : ''}`;
    marker.style.left = `${rect.x0 / data.page_width * 100}%`;
    marker.style.top = `${rect.y0 / data.page_height * 100}%`;
    marker.style.width = `${(rect.x1 - rect.x0) / data.page_width * 100}%`;
    marker.style.height = `${(rect.y1 - rect.y0) / data.page_height * 100}%`;
    highlightLayer.appendChild(marker);
    highlightNodes.push(marker);
  }
  frame.appendChild(highlightLayer);

  const textLayer = document.createElement('div');
  textLayer.className = 'pa-pdf-text-layer';
  const wordNodes = [];
  for (const word of data.words || []) {
    const span = document.createElement('span');
    span.className = 'pa-pdf-word';
    span.textContent = `${word.text} `;
    span.dataset.x0 = word.x0;
    span.dataset.y0 = word.y0;
    span.dataset.x1 = word.x1;
    span.dataset.y1 = word.y1;
    textLayer.appendChild(span);
    wordNodes.push(span);
  }
  frame.appendChild(textLayer);

  const action = document.createElement('div');
  action.className = 'pa-pdf-selection-action';
  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'pa-pdf-selection-button';
  button.textContent = '提问选中内容';
  button.title = '针对选中内容提问';
  action.appendChild(button);
  frame.appendChild(action);
  host.appendChild(frame);

  const positionWords = () => {
    const scale = frame.clientWidth / data.page_width;
    for (const span of wordNodes) {
      const x0 = Number(span.dataset.x0);
      const y0 = Number(span.dataset.y0);
      const x1 = Number(span.dataset.x1);
      const y1 = Number(span.dataset.y1);
      span.style.left = `${x0 * scale}px`;
      span.style.top = `${y0 * scale}px`;
      span.style.width = `${Math.max((x1 - x0) * scale, 1)}px`;
      span.style.height = `${Math.max((y1 - y0) * scale, 1)}px`;
      span.style.fontSize = `${Math.max((y1 - y0) * scale * .88, 4)}px`;
    }
  };

  let pendingSelection = null;
  const readSelection = () => {
    const root = textLayer.getRootNode();
    return typeof root.getSelection === 'function'
      ? root.getSelection()
      : window.getSelection();
  };
  const readRange = (selection) => {
    const root = textLayer.getRootNode();
    if (typeof selection.getComposedRanges === 'function' && root?.nodeType === 11) {
      try {
        const composed = selection.getComposedRanges({shadowRoots: [root]});
        if (composed.length) {
          const source = composed[0];
          const range = document.createRange();
          range.setStart(source.startContainer, source.startOffset);
          range.setEnd(source.endContainer, source.endOffset);
          return range;
        }
      } catch (_) {
        // Fall back to the regular selection range on older browsers.
      }
    }
    return selection.rangeCount ? selection.getRangeAt(0) : null;
  };
  const hideAction = () => {
    pendingSelection = null;
    action.classList.remove('is-visible');
  };
  const positionAction = (anchorBox, frameBox) => {
    const edge = 12;
    const gap = 10;
    action.classList.add('is-visible');
    action.style.visibility = 'hidden';
    action.style.left = '0px';
    action.style.top = '0px';

    const actionWidth = action.offsetWidth;
    const actionHeight = action.offsetHeight;
    const preferredLeft = anchorBox.left - frameBox.left;
    const maxLeft = Math.max(edge, frameBox.width - actionWidth - edge);
    const localLeft = Math.max(edge, Math.min(preferredLeft, maxLeft));
    const above = anchorBox.top - frameBox.top - actionHeight - gap;
    const below = anchorBox.bottom - frameBox.top + gap;
    const placeAbove = above >= edge;
    const preferredTop = placeAbove ? above : below;
    const maxTop = Math.max(edge, frameBox.height - actionHeight - edge);
    const localTop = Math.max(edge, Math.min(preferredTop, maxTop));

    action.classList.toggle('is-above', placeAbove);
    action.classList.toggle('is-below', !placeAbove);
    action.style.left = `${localLeft}px`;
    action.style.top = `${localTop}px`;
    action.style.visibility = '';
  };
  const handleSelection = (event) => {
    const selection = readSelection();
    if (!selection) {
      hideAction();
      return;
    }
    const range = readRange(selection);
    if (!range || range.collapsed) {
      hideAction();
      return;
    }
    const text = range.toString().replace(/\s+/g, ' ').trim();
    if (text.length < 4) {
      hideAction();
      return;
    }
    const frameBox = frame.getBoundingClientRect();
    const scaleX = data.page_width / frameBox.width;
    const scaleY = data.page_height / frameBox.height;
    const clientRects = Array.from(range.getClientRects())
      .filter(rect =>
        rect.width > 0 && rect.height > 0 &&
        rect.right >= frameBox.left && rect.left <= frameBox.right &&
        rect.bottom >= frameBox.top && rect.top <= frameBox.bottom
      );
    if (!clientRects.length) {
      hideAction();
      return;
    }
    const rects = clientRects
      .map(rect => ({
        x0: Math.max(0, (rect.left - frameBox.left) * scaleX),
        y0: Math.max(0, (rect.top - frameBox.top) * scaleY),
        x1: Math.min(data.page_width, (rect.right - frameBox.left) * scaleX),
        y1: Math.min(data.page_height, (rect.bottom - frameBox.top) * scaleY),
      }));
    pendingSelection = {
      page: data.page_number,
      text: text.slice(0, 2000),
      rects,
    };
    const anchorBox = {
      left: Math.min(...clientRects.map(rect => rect.left)),
      top: Math.min(...clientRects.map(rect => rect.top)),
      right: Math.max(...clientRects.map(rect => rect.right)),
      bottom: Math.max(...clientRects.map(rect => rect.bottom)),
    };
    positionAction(anchorBox, frameBox);
  };
  const handleWordPick = (event) => {
    const word = event.target.closest?.('.pa-pdf-word');
    if (!word) return;
    const text = word.textContent.replace(/\s+/g, ' ').trim();
    if (!text) return;
    const frameBox = frame.getBoundingClientRect();
    const wordBox = word.getBoundingClientRect();
    const scaleX = data.page_width / frameBox.width;
    const scaleY = data.page_height / frameBox.height;
    pendingSelection = {
      page: data.page_number,
      text,
      rects: [{
        x0: Math.max(0, (wordBox.left - frameBox.left) * scaleX),
        y0: Math.max(0, (wordBox.top - frameBox.top) * scaleY),
        x1: Math.min(data.page_width, (wordBox.right - frameBox.left) * scaleX),
        y1: Math.min(data.page_height, (wordBox.bottom - frameBox.top) * scaleY),
      }],
    };
    positionAction(wordBox, frameBox);
  };
  const submitSelection = (event) => {
    event.preventDefault();
    if (pendingSelection) setTriggerValue('selected', pendingSelection);
  };

  const selectionChanged = () => requestAnimationFrame(() => handleSelection(null));
  if (data.selection_enabled !== false) {
    button.addEventListener('mousedown', event => event.preventDefault());
    button.addEventListener('click', submitSelection);
    textLayer.addEventListener('mouseup', handleSelection);
    textLayer.addEventListener('pointerup', handleSelection);
    textLayer.addEventListener('click', handleWordPick);
    textLayer.addEventListener('dblclick', handleWordPick);
    document.addEventListener('selectionchange', selectionChanged);
  }
  const resizePage = () => {
    const currentZoom = Math.max(50, Math.min(Number(data.zoom_percent || 100), 180));
    const availableWidth = Math.max(120, host.clientWidth);
    const fitScale = Math.max(.6, Math.min(Number(data.fit_scale || 1.0), 1.25));
    const fitWidth = availableWidth * fitScale;
    const pageWidth = fitWidth * currentZoom / 100;
    const aspectRatio = data.page_height > 0 ? (data.page_height / data.page_width) : 1.414;
    const pageHeight = pageWidth * aspectRatio;

    frame.style.width = `${Math.max(120, pageWidth)}px`;
    frame.style.height = `${Math.max(160, pageHeight)}px`;
    positionWords();
  };
  // Switching among balanced / paper / code changes the panel width without
  // resizing the browser window. Observe the actual PDF host as well, or the
  // frame can keep the width measured in the previous layout and appear at a
  // different scale when the user returns to the same mode.
  const frameResizeObserver = new ResizeObserver(positionWords);
  frameResizeObserver.observe(frame);
  const hostResizeObserver = new ResizeObserver(resizePage);
  hostResizeObserver.observe(host);
  window.addEventListener('resize', resizePage);
  resizePage();
  positionWords();
  if (data.focus_highlight && highlightNodes.length) {
    requestAnimationFrame(() => {
      const marker = highlightNodes[0];
      const mainScroller = host.closest('section.stMain');
      if (mainScroller) {
        const markerBox = marker.getBoundingClientRect();
        const scrollerBox = mainScroller.getBoundingClientRect();
        const targetTop = Math.max(
          0,
          mainScroller.scrollTop
            + markerBox.top
            - scrollerBox.top
            - mainScroller.clientHeight * .35,
        );
        mainScroller.scrollTo({top: targetTop, left: 0, behavior: 'smooth'});
      }
      if (Number(data.zoom_percent || 100) <= 100) {
        host.scrollLeft = 0;
      } else {
        const targetLeft = Math.max(
          0,
          marker.offsetLeft + marker.offsetWidth / 2 - host.clientWidth / 2,
        );
        host.scrollTo({left: targetLeft, behavior: 'smooth'});
      }
    });
  }

  return () => {
    frameResizeObserver.disconnect();
    hostResizeObserver.disconnect();
    window.removeEventListener('resize', resizePage);
    button.removeEventListener('click', submitSelection);
    textLayer.removeEventListener('mouseup', handleSelection);
    textLayer.removeEventListener('pointerup', handleSelection);
    textLayer.removeEventListener('click', handleWordPick);
    textLayer.removeEventListener('dblclick', handleWordPick);
    document.removeEventListener('selectionchange', selectionChanged);
  };
}
"""

_pdf_selector = st.components.v2.component(
    "paper_pdf_text_selector",
    html=_PDF_SELECTOR_HTML,
    css=_PDF_SELECTOR_CSS,
    js=_PDF_SELECTOR_JS,
    isolate_styles=False,
)


@st.cache_data(show_spinner=False, max_entries=12)
def _page_payload(pdf_bytes: bytes, page_number: int) -> dict[str, Any]:
    document = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    try:
        if page_number < 1 or page_number > document.page_count:
            raise ValueError("PDF 页码超出范围。")
        page = document.load_page(page_number - 1)
        pixmap = page.get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5), alpha=False)
        words = [
            {
                "text": str(item[4]),
                "x0": float(item[0]),
                "y0": float(item[1]),
                "x1": float(item[2]),
                "y1": float(item[3]),
            }
            # Keep the PDF's native block order. Sorting only by visual y/x
            # interleaves the left and right columns of two-column papers.
            for item in page.get_text("words", sort=False)
            if str(item[4]).strip()
        ]
        return {
            "image_url": "data:image/png;base64,"
            + base64.b64encode(pixmap.tobytes("png")).decode("ascii"),
            "page_width": float(page.rect.width),
            "page_height": float(page.rect.height),
            "words": words,
        }
    finally:
        document.close()


def render_selectable_pdf_page(
    pdf_bytes: bytes,
    page_number: int,
    highlights: list[PageRect],
    *,
    key: str,
    selection_enabled: bool = True,
    zoom_percent: int = 100,
    focus_highlight: bool = False,
    fit_scale: float = 0.92,
) -> dict[str, Any] | None:
    """Render one selectable page and return a user-confirmed selection event."""
    payload = _page_payload(pdf_bytes, page_number)
    payload.update(
        {
            "page_number": page_number,
            "highlights": [rect.model_dump() for rect in highlights],
            "selection_enabled": selection_enabled,
            "zoom_percent": zoom_percent,
            "focus_highlight": focus_highlight,
            "fit_scale": fit_scale,
        }
    )
    result = _pdf_selector(
        data=payload,
        key=key,
        height="content",
        width="stretch",
        on_selected_change=lambda: None,
    )
    selected = getattr(result, "selected", None)
    return selected if isinstance(selected, dict) else None


@st.cache_data(show_spinner=False, max_entries=12)
def get_pdf_page_count(pdf_bytes: bytes) -> int:
    document = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    try:
        if document.page_count < 1:
            raise ValueError("PDF 没有可显示的页面。")
        return document.page_count
    finally:
        document.close()
