"""Conservative, geometry-based table-caption links over existing parsed blocks.

No new model call, inferred setting, concatenated quotation, or index migration.
A link is a layout hint, not proof of semantic equivalence. Missing rectangles,
competing equally close captions, and cross-page matches produce no link.
"""
from __future__ import annotations

import re
import unicodedata

from .models import EvidenceContext, PaperChunk, ParsedPaper

_CAPTION = re.compile(r"^\s*(?:table|tab\.|表)\s*\d+[A-Za-z]?(?=[\s.:：。]|$)", re.I)


def _caption(chunk: PaperChunk) -> bool:
    return bool(_CAPTION.search(chunk.content))


def _body(chunk: PaperChunk) -> bool:
    if not chunk.content.strip() or _caption(chunk) or _CAPTION.search(chunk.content.splitlines()[-1]):
        return False
    lines = [unicodedata.normalize('NFKC', line).strip().lower() for line in chunk.content.splitlines()]
    return chunk.content_type == 'table' or (len(lines) >= 4 and lines[:2] == ['config', 'value'])


def _bounds(chunk: PaperChunk):
    if not chunk.rects:
        return None
    return (min(r.x0 for r in chunk.rects), min(r.y0 for r in chunk.rects),
            max(r.x1 for r in chunk.rects), max(r.y1 for r in chunk.rects))


def _distance(body: PaperChunk, caption: PaperChunk) -> float | None:
    a, b = _bounds(body), _bounds(caption)
    if body.page != caption.page or a is None or b is None:
        return None
    overlap = min(a[2], b[2]) - max(a[0], b[0])
    if overlap <= 0 or overlap < .65 * min(a[2] - a[0], b[2] - b[0]):
        return None
    gap = max(b[1] - a[3], a[1] - b[3])
    return gap if 0 <= gap <= 32 else None


def table_caption_links(paper: ParsedPaper) -> dict[str, EvidenceContext]:
    bodies = [c for c in paper.chunks if _body(c)]
    captions = [c for c in paper.chunks if _caption(c) and len(c.content) <= 2000]
    edges = [(b, c, d) for b in bodies for c in captions if (d := _distance(b, c)) is not None]
    links = {}
    for body in bodies:
        candidates = sorted([(d, c) for b, c, d in edges if b.chunk_id == body.chunk_id], key=lambda x: x[0])
        if not candidates or len(candidates) > 1 and candidates[1][0] - candidates[0][0] < 2:
            continue
        distance, caption = candidates[0]
        # Do not borrow a caption whose nearest table is another body. Split
        # blocks with identical geometry may legitimately share one caption.
        competing = [d for b, c, d in edges if c.chunk_id == caption.chunk_id
                     and b.chunk_id != body.chunk_id and _bounds(b) != _bounds(body)]
        if competing and min(competing) <= distance + 2:
            continue
        links[body.chunk_id] = EvidenceContext(chunk_id=caption.chunk_id, page=caption.page,
            text=caption.content, rects=caption.rects)
    return links
