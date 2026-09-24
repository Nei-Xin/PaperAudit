from __future__ import annotations
from collections.abc import Sequence
import re
from .models import EvidenceAnchor, LearningReport, PaperChunk, ParsedPaper, ReportSection


def _numbered_heading(chunk: PaperChunk) -> tuple[str, str] | None:
    lines = [line.strip() for line in chunk.content.splitlines() if line.strip()]
    if not lines:
        return None
    number = ""
    title = ""
    if re.fullmatch(r"\d+(?:\.\d+)*\.?", lines[0]) and len(lines) > 1:
        number, title = lines[0].rstrip("."), lines[1]
    else:
        match = re.fullmatch(r"(\d+(?:\.\d+)*)\.?\s+(.+)", lines[0])
        if match:
            number, title = match.groups()
    if (
        not number
        or not re.search(r"[A-Za-z]", title)
        or len(title) > 100
        or title.rstrip().endswith("?")
    ):
        return None
    return number, title


def _neighbor_context(
    chunk_id: str,
    chunks: list[PaperChunk],
    chunk_positions: dict[str, int],
) -> str | None:
    """Return immediate same-page context without changing the cited evidence block."""
    index = chunk_positions[chunk_id]
    current = chunks[index]
    context_parts: list[str] = []
    for neighbor_index, label in ((index - 1, "前文"), (index + 1, "后文")):
        if 0 <= neighbor_index < len(chunks):
            neighbor = chunks[neighbor_index]
            if neighbor.page == current.page:
                context_parts.append(
                    f"{label} · {neighbor.chunk_id}\n{neighbor.content}"
                )
    return "\n\n".join(context_parts) or None


def refresh_learning_report_evidence(
    report: LearningReport,
    paper: ParsedPaper,
) -> LearningReport:
    """Rebuild every report anchor from the local PDF, including legacy projects."""

    refreshed_sections: list[ReportSection] = []
    for section in report.sections:
        refreshed_points = []
        for point in section.points:
            refreshed_anchors = refresh_evidence_anchors(point.evidence, paper)
            refreshed_points.append(point.model_copy(update={"evidence": refreshed_anchors}))
        refreshed_sections.append(section.model_copy(update={"points": refreshed_points}))
    return report.model_copy(
        update={"paper_title": paper.title, "sections": refreshed_sections}
    )


def refresh_evidence_anchors(
    evidence: Sequence[EvidenceAnchor],
    paper: ParsedPaper,
) -> list[EvidenceAnchor]:
    """Rebuild citation metadata from the trusted local PDF index."""

    chunk_map = {chunk.chunk_id: chunk for chunk in paper.chunks}
    chunk_positions = {chunk.chunk_id: index for index, chunk in enumerate(paper.chunks)}
    refreshed: list[EvidenceAnchor] = []
    seen: set[str] = set()
    for anchor in evidence:
        chunk = chunk_map.get(anchor.chunk_id)
        if chunk is None or chunk.chunk_id in seen:
            continue
        seen.add(chunk.chunk_id)
        quote = (
            _validated_evidence_quote(anchor.quote, chunk.content)
            if anchor.quote
            else None
        )
        refreshed.append(
            EvidenceAnchor(
                chunk_id=chunk.chunk_id,
                page=chunk.page,
                text=chunk.content,
                quote=quote,
                locator=_evidence_locator(
                    chunk.chunk_id,
                    paper.chunks,
                    chunk_positions,
                ),
                context_text=_neighbor_context(
                    chunk.chunk_id,
                    paper.chunks,
                    chunk_positions,
                ),
                rects=_quote_rects(chunk, quote),
            )
        )
    return refreshed


_FIGURE_TABLE_CAPTION_PATTERN = re.compile(
    r"^\s*(Figure|Fig\.?|Table)\s*(\d+(?:[A-Za-z]|\([A-Za-z]\))?)"
    r"\s*(?=[:.]|\s|$)",
    re.IGNORECASE,
)


def _validated_evidence_quote(requested: str, source: str) -> str | None:
    quote = re.sub(r"\s+", " ", requested).strip(" \t\r\n\"'“”‘’…")
    normalized_source = re.sub(r"\s+", " ", source).strip()
    if len(quote) < 8 or len(quote) > 320:
        return None
    if quote.casefold() not in normalized_source.casefold():
        return None
    return quote


def _quote_rects(chunk: PaperChunk, quote: str | None) -> list[dict[str, float]]:
    """Return PDF rectangles in a form accepted by strict Pydantic models.

    Parsed chunks expose ``PageRect`` model instances, while ``EvidenceAnchor``
    is built with strict validation.  Passing those instances through directly
    fails on rerender (and made the UI appear inconsistently across layouts), so
    normalize them to plain dictionaries at this boundary.
    """
    source_rects = [rect.model_dump() for rect in chunk.rects]
    if not quote:
        return source_rects
    lines = [re.sub(r"\s+", " ", line).strip() for line in chunk.content.splitlines()]
    lines = [line for line in lines if line]
    if not lines or len(lines) != len(source_rects):
        return source_rects
    joined = " ".join(lines)
    start = joined.casefold().find(quote.casefold())
    if start < 0:
        return source_rects
    end = start + len(quote)
    selected_rects: list[dict[str, float]] = []
    cursor = 0
    for line, rect in zip(lines, source_rects, strict=True):
        line_start = cursor
        line_end = cursor + len(line)
        if line_start < end and line_end > start:
            selected_rects.append(rect)
        cursor = line_end + 1
    return selected_rects or source_rects


def _evidence_locator(
    chunk_id: str,
    chunks: list[PaperChunk],
    chunk_positions: dict[str, int],
) -> str | None:
    index = chunk_positions[chunk_id]
    current = chunks[index]
    parts: list[str] = []
    for heading_index in range(index, -1, -1):
        heading = _numbered_heading(chunks[heading_index])
        if heading is not None:
            parts.append(f"§{heading[0]} {heading[1]}")
            break

    paragraph_number = _paragraph_number(index, chunks)
    if paragraph_number is not None:
        parts.append(f"第 {paragraph_number} 段")

    nearby_texts = [current.content]
    for neighbor_index in (index - 1, index + 1):
        if 0 <= neighbor_index < len(chunks) and chunks[neighbor_index].page == current.page:
            nearby_texts.append(chunks[neighbor_index].content)
    object_match = next(
        (
            match
            for nearby_text in nearby_texts
            for line in nearby_text.splitlines()
            if (match := _FIGURE_TABLE_CAPTION_PATTERN.match(line)) is not None
        ),
        None,
    )
    if object_match:
        object_kind = "Table" if object_match.group(1).lower().startswith("table") else "Figure"
        object_number = object_match.group(2).replace("(", "").replace(")", "")
        parts.append(f"{object_kind} {object_number}")
    return " · ".join(parts) or None


def _paragraph_number(index: int, chunks: list[PaperChunk]) -> int | None:
    """Return a best-effort paragraph ordinal within the nearest numbered section."""

    current = chunks[index]
    if _numbered_heading(current) is not None:
        return None
    if any(
        _FIGURE_TABLE_CAPTION_PATTERN.match(line)
        for line in current.content.splitlines()
    ):
        return None

    section_start: int | None = None
    for candidate_index in range(index - 1, -1, -1):
        if _numbered_heading(chunks[candidate_index]) is not None:
            section_start = candidate_index + 1
            break
    if section_start is None:
        return None

    body_indices = [
        candidate_index
        for candidate_index in range(section_start, index + 1)
        if _numbered_heading(chunks[candidate_index]) is None
        and not any(
            _FIGURE_TABLE_CAPTION_PATTERN.match(line)
            for line in chunks[candidate_index].content.splitlines()
        )
    ]
    try:
        return body_indices.index(index) + 1
    except ValueError:
        return None


