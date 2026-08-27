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
                            rects=line_rects,
                        )
                    )
                    page_chunks += 1
            if page_chunks == 0:
                warnings.append(f"第 {page_number} 页未提取到文本。")

        if not chunks:
            raise PDFParseError("PDF 未提取到文本；第一版不支持扫描件。")

        metadata_title = _normalize_text(document.metadata.get("title", ""))
        first_block_title = " ".join(first_text.splitlines())[:160].strip()
        title = (
            first_block_title
            if not metadata_title or _looks_truncated_title(metadata_title)
            else " ".join(metadata_title.splitlines())[:160].strip()
        ) or "未命名论文"
        return ParsedPaper(
            title=title,
            page_count=document.page_count,
            chunks=chunks,
            warnings=warnings,
        )
    finally:
        document.close()
