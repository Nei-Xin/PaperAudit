from __future__ import annotations

import re

import pymupdf as fitz

from .models import PageRect, PaperChunk, ParsedPaper


class PDFParseError(ValueError):
    pass


def _normalize_text(text: str) -> str:
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line).strip()


def _split_block(text: str, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]

    parts: list[str] = []
    remaining = text
    while len(remaining) > max_chars:
        split_at = remaining.rfind("\n", 0, max_chars)
        if split_at < max_chars // 2:
            split_at = remaining.rfind(". ", 0, max_chars)
            split_at = split_at + 1 if split_at >= max_chars // 2 else max_chars
        parts.append(remaining[:split_at].strip())
        remaining = remaining[split_at:].strip()
    if remaining:
        parts.append(remaining)
    return parts


def _looks_truncated_title(title: str) -> bool:
    words = title.rstrip(" :;,-").casefold().split()
    return bool(words) and words[-1] in {
        "and", "as", "at", "by", "for", "from", "in", "of", "on", "or", "to", "with", "without"
    }


_PLACEHOLDER_TITLE = re.compile(
    r"\.(?:eps|dvi|tex|pdf|docx?|ps)\b|^microsoft word\b|^untitled\b|^\s*$", re.IGNORECASE,
)


def _looks_placeholder_title(title: str) -> bool:
    """Metadata titles copied from source file names are not paper titles."""

    return bool(_PLACEHOLDER_TITLE.search(title))


def _largest_font_title(lines: list[tuple[str, float]]) -> str:
    """Join the first run of first-page lines set in the largest font.

    Licence notes or venue banners often precede the title in reading order, but
    the title is still the most prominent horizontal text on the first page.
    """

    if not lines:
        return ""
    sizes = sorted(size for _, size in lines)
    largest = sizes[-1]
    # Without a clearly larger font there is no typographic title to trust.
    if largest < sizes[len(sizes) // 2] + 1.0:
        return ""
    title_lines: list[str] = []
    for text, size in lines:
        if size >= largest - 0.5:
            title_lines.append(text)
        elif title_lines:
            break
    title = " ".join(title_lines).strip()
    return title if 4 <= len(title) <= 300 else ""


def _is_horizontal(line: dict) -> bool:
    direction = line.get("dir") or (1.0, 0.0)
    return abs(direction[0] - 1.0) < 0.01 and abs(direction[1]) < 0.01


def _line_font_size(line: dict) -> float:
    return max((float(span.get("size", 0.0)) for span in line.get("spans", [])), default=0.0)


def _choose_title(
    document: fitz.Document, first_page_lines: list[tuple[str, float]], first_text: str,
) -> str:
    metadata_title = _normalize_text(document.metadata.get("title", "") or "")
    page_title = (
        _largest_font_title(first_page_lines)[:160].strip()
        or " ".join(first_text.splitlines())[:160].strip()
    )
    return (
        page_title
        if not metadata_title
        or _looks_truncated_title(metadata_title)
        or _looks_placeholder_title(metadata_title)
        else " ".join(metadata_title.splitlines())[:160].strip()
    ) or "未命名论文"


def extract_pdf_title(pdf_bytes: bytes) -> str | None:
    """Re-derive a title from the first page, e.g. to repair saved projects."""

    try:
        document = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception:
        return None
    try:
        if document.page_count == 0:
            return None
        lines: list[tuple[str, float]] = []
        first_text = ""
        for block in document[0].get_text("dict", sort=True).get("blocks", []):
            if block.get("type") != 0:
                continue
            block_lines = []
            for line in block.get("lines", []):
                text = _normalize_text("".join(str(span.get("text", "")) for span in line.get("spans", [])))
                if not text:
                    continue
                block_lines.append(text)
                if _is_horizontal(line):
                    lines.append((text, _line_font_size(line)))
            block_text = _normalize_text("\n".join(block_lines))
            if not first_text and len(block_text) >= 2:
                first_text = block_text
        title = _choose_title(document, lines, first_text)
        return None if title == "未命名论文" else title
    finally:
        document.close()


_TABLE_MARKER = re.compile(r"^\s*(?:table|tab\.|表)\s*\d+[A-Za-z]?\b", re.IGNORECASE)
_FORMULA_MARKER = re.compile(
    r"(?:\s[=≈≤≥∑∏√∫∞±]|\b(?:arg\s*min|arg\s*max|softmax|sigmoid|"
    r"relu|loss|objective|gradient|derivative|equation)\b)",
    re.IGNORECASE,
)


def _classify_block(text: str) -> str:
    """Give retrieval a light-weight structural hint without altering evidence text."""

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return "text"
    if any(_TABLE_MARKER.search(line) for line in lines[:2]):
        return "table"
    # Captions are often separated from the rows by PDF layout extraction. A
    # numeric multi-column block is still a useful table candidate.
    if len(lines) >= 2 and sum(
        len(re.findall(r"\d+(?:\.\d+)?%?", line)) >= 2 for line in lines
    ) >= 2:
        return "table"
    if _FORMULA_MARKER.search(text) and (
        "=" in text or any(symbol in text for symbol in "∑∏√∫∞±≤≥")
    ):
        return "formula"
    return "text"


def parse_pdf(pdf_bytes: bytes, max_block_chars: int = 3_000) -> ParsedPaper:
    if not pdf_bytes:
        raise PDFParseError("PDF 文件为空。")

    try:
        document = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as exc:
        raise PDFParseError("无法打开 PDF，请确认文件未损坏且未加密。") from exc

    try:
        if document.page_count == 0:
            raise PDFParseError("PDF 没有可读取的页面。")

        chunks: list[PaperChunk] = []
        warnings: list[str] = []
        first_text = ""
        first_page_lines: list[tuple[str, float]] = []

        for page_index, page in enumerate(document):
            page_number = page_index + 1
            page_chunks = 0
            blocks = page.get_text("dict", sort=True).get("blocks", [])
            for fallback_index, block in enumerate(blocks):
                if block.get("type") != 0:
                    continue
                line_entries: list[tuple[str, PageRect]] = []
                for line in block.get("lines", []):
                    line_text = _normalize_text(
                        "".join(str(span.get("text", "")) for span in line.get("spans", []))
                    )
                    if not line_text:
                        continue
                    # Rotated margin stamps such as arXiv identifiers are not titles.
                    if page_index == 0 and _is_horizontal(line):
                        first_page_lines.append((line_text, _line_font_size(line)))
                    bbox = line.get("bbox")
                    if not bbox or len(bbox) != 4:
                        continue
                    line_entries.append(
                        (
                            line_text,
                            PageRect(
                                x0=float(bbox[0]),
                                y0=float(bbox[1]),
                                x1=float(bbox[2]),
                                y1=float(bbox[3]),
                            ),
                        )
                    )
                text = _normalize_text("\n".join(line_text for line_text, _ in line_entries))
                if len(text) < 2:
                    continue
                line_rects = [rect for _, rect in line_entries]
                if not first_text:
                    first_text = text
                for part_index, part in enumerate(_split_block(text, max_block_chars)):
                    suffix = f"_{part_index + 1}" if len(text) > max_block_chars else ""
                    block_number = int(block.get("number", fallback_index)) + 1
                    chunks.append(
                        PaperChunk(
                            chunk_id=f"p{page_number}_b{block_number}{suffix}",
                            page=page_number,
                            content=part,
                            content_type=_classify_block(text),
                            rects=line_rects,
                        )
                    )
                    page_chunks += 1
            if page_chunks == 0:
                warnings.append(f"第 {page_number} 页未提取到文本。")

        if not chunks:
            raise PDFParseError("PDF 未提取到文本；第一版不支持扫描件。")

        title = _choose_title(document, first_page_lines, first_text)
        return ParsedPaper(
            title=title,
            page_count=document.page_count,
            chunks=chunks,
            warnings=warnings,
        )
    finally:
        document.close()
