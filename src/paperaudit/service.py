from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from difflib import SequenceMatcher
import re

from .config import Settings
from .hy3_client import Hy3Client, Hy3ResponseError
from .models import (
    AtomicClaim,
    AnswerConclusion,
    AnswerStatus,
    AuditRun,
    AutoLabel,
    ClaimAudit,
    ClaimCategory,
    ClaimJudgment,
    EvidenceAnchor,
    EvidenceCandidate,
    LearningReport,
    LearningSectionType,
    PageRect,
    PaperAnswer,
    PaperChunk,
    ParsedPaper,
    ReportSection,
    Severity,
)
from .pdf_parser import parse_pdf
from .retrieval import EvidenceRetriever, build_claim_query
from .scoring import build_summary


ProgressCallback = Callable[[str, float], None]

_LOCATION_QUESTION_PATTERN = re.compile(
    r"第\s*几\s*页|哪(?:些|几)?\s*页|在(?:哪|哪里|哪儿)|位于|位置|"
    r"\bwhere\b|\bwhich\s+pages?\b|\bwhat\s+pages?\b",
    re.IGNORECASE,
)
_EXISTENCE_QUESTION_PATTERN = re.compile(
    r"有没有|有无|是否(?:有|包含|存在|提到)|有.+吗|包含.+吗|提到.+吗|"
    r"\bdoes\b.+\bhave\b|\bis\s+there\b|\bcontains?\b",
    re.IGNORECASE,
)
_DOCUMENT_STRUCTURE_TARGETS = (
    (
        "补充材料",
        ("补充材料", "补充内容", "supplementary", "supplemental"),
        ("supplementary material", "supplemental material", "supplementary"),
    ),
    (
        "附录",
        ("附录", "appendix", "appendices"),
        ("appendix", "appendices"),
    ),
    (
        "参考文献",
        ("参考文献", "references", "bibliography"),
        ("references", "bibliography"),
    ),
    (
        "致谢",
        ("致谢", "acknowledgment", "acknowledgement"),
        ("acknowledgments", "acknowledgements", "acknowledgment", "acknowledgement"),
    ),
)
_LOCATION_SECTION_TERMS = (
    (
        LearningSectionType.RESULTS,
        ("实验结果", "结果", "性能", "对比实验", "消融", "results", "performance"),
    ),
    (
        LearningSectionType.EXPERIMENTS,
        (
            "实验内容",
            "实验部分",
            "实验设计",
            "实验设置",
            "实验",
            "数据集",
            "评估设置",
            "experiments",
            "dataset",
            "evaluation setup",
        ),
    ),
    (
        LearningSectionType.METHOD,
        ("方法论", "研究方法", "方法", "框架", "流程", "methodology", "method", "framework"),
    ),
    (
        LearningSectionType.CONTRIBUTIONS,
        ("主要贡献", "贡献", "创新", "contribution", "innovation"),
    ),
    (
        LearningSectionType.RESEARCH_PROBLEM,
        ("研究问题", "研究目标", "research problem", "objective"),
    ),
    (
        LearningSectionType.LIMITATIONS,
        ("研究局限", "局限", "限制", "不足", "limitation"),
    ),
    (
        LearningSectionType.KEY_TERMS,
        ("关键术语", "术语", "概念", "key terms", "terminology"),
    ),
)
_LOCATION_SECTION_NAMES = {
    LearningSectionType.RESEARCH_PROBLEM: "研究问题",
    LearningSectionType.CONTRIBUTIONS: "主要贡献",
    LearningSectionType.METHOD: "研究方法",
    LearningSectionType.EXPERIMENTS: "实验设计",
    LearningSectionType.RESULTS: "实验结果",
    LearningSectionType.LIMITATIONS: "研究局限",
    LearningSectionType.KEY_TERMS: "关键术语",
}
_SECTION_HEADING_TERMS = {
    LearningSectionType.RESEARCH_PROBLEM: ("introduction",),
    LearningSectionType.CONTRIBUTIONS: ("introduction",),
    LearningSectionType.METHOD: ("methodology", "methods", "method", "approach", "framework"),
    LearningSectionType.EXPERIMENTS: ("experiments", "experimental", "evaluation"),
    LearningSectionType.RESULTS: ("results", "experiments", "experimental", "evaluation"),
    LearningSectionType.LIMITATIONS: ("limitations", "discussion", "conclusion"),
    LearningSectionType.KEY_TERMS: (),
}


@dataclass(frozen=True)
class _PaperSectionLocation:
    number: str
    title: str
    start_page: int
    end_page: int
    heading_chunk: PaperChunk


@dataclass(frozen=True)
class _DocumentStructureTarget:
    name: str
    heading_terms: tuple[str, ...]


@dataclass(frozen=True)
class LearningPagePoint:
    section_type: LearningSectionType
    section_title: str
    title: str
    explanation: str
    evidence: tuple[EvidenceAnchor, ...]


@dataclass(frozen=True)
class LearningPageContext:
    page: int
    paper_section: str | None
    report_section: str | None
    relation: str | None
    points: tuple[LearningPagePoint, ...]
    suggested_questions: tuple[str, ...]

    @property
    def chunk_ids(self) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(
                anchor.chunk_id
                for point in self.points
                for anchor in point.evidence
            )
        )


@dataclass(frozen=True)
class LearningLogicNode:
    role: str
    title: str
    explanation: str
    evidence: tuple[EvidenceAnchor, ...]


def _noop_progress(_: str, __: float) -> None:
    return None


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


def _paper_sections(paper: ParsedPaper) -> list[_PaperSectionLocation]:
    numbered = [
        (number, title, chunk)
        for chunk in paper.chunks
        if (heading := _numbered_heading(chunk)) is not None
        for number, title in [heading]
    ]
    top_level = [item for item in numbered if "." not in item[0]]
    top_level.sort(key=lambda item: (item[2].page, int(item[0])))
    sections: list[_PaperSectionLocation] = []
    for index, (number, title, chunk) in enumerate(top_level):
        subsection_pages = [
            item_chunk.page
            for item_number, _, item_chunk in numbered
            if item_number.startswith(f"{number}.")
        ]
        next_start = (
            top_level[index + 1][2].page
            if index + 1 < len(top_level)
            else paper.page_count + 1
        )
        end_page = max(
            [chunk.page, next_start - 1, *subsection_pages],
        )
        end_page = min(end_page, paper.page_count)
        sections.append(
            _PaperSectionLocation(
                number=number,
                title=title,
                start_page=chunk.page,
                end_page=end_page,
                heading_chunk=chunk,
            )
        )
    return sections


def _document_structure_target(question: str) -> _DocumentStructureTarget | None:
    normalized = question.lower()
    for name, question_terms, heading_terms in _DOCUMENT_STRUCTURE_TARGETS:
        if any(term in normalized for term in question_terms):
            return _DocumentStructureTarget(name=name, heading_terms=heading_terms)
    return None


def _find_document_heading(
    paper: ParsedPaper,
    target: _DocumentStructureTarget,
) -> PaperChunk | None:
    for chunk in paper.chunks:
        lines = [line.strip() for line in chunk.content.splitlines() if line.strip()]
        if not lines:
            continue
        first_line = re.sub(r"\s+", " ", lines[0]).strip(" :.-").lower()
        if any(
            first_line == term or first_line.startswith(f"{term} ")
            for term in target.heading_terms
        ):
            return chunk
    return None


def _document_structure_answer(
    question: str,
    paper: ParsedPaper,
) -> PaperAnswer | None:
    target = _document_structure_target(question)
    is_location = bool(_LOCATION_QUESTION_PATTERN.search(question))
    is_existence = bool(_EXISTENCE_QUESTION_PATTERN.search(question))
    if target is None or not (is_location or is_existence):
        return None

    heading_chunk = _find_document_heading(paper, target)
    if heading_chunk is not None:
        if is_location:
            answer = f"{target.name}从第 {heading_chunk.page} 页开始。"
        else:
            answer = f"当前 PDF 中识别到{target.name}，从第 {heading_chunk.page} 页开始。"
        return PaperAnswer(
            question=question,
            answer=answer,
            status=AnswerStatus.ANSWERED,
            citations=[
                EvidenceAnchor(
                    chunk_id=heading_chunk.chunk_id,
                    page=heading_chunk.page,
                    text=heading_chunk.content.splitlines()[0].strip(),
                    context_text=heading_chunk.content,
                    rects=heading_chunk.rects[:1],
                )
            ],
        )

    mentions_by_page: dict[int, PaperChunk] = {}
    for chunk in paper.chunks:
        lowered = chunk.content.lower()
        if any(term in lowered for term in target.heading_terms):
            mentions_by_page.setdefault(chunk.page, chunk)
    if mentions_by_page:
        pages = "、".join(str(page) for page in sorted(mentions_by_page))
        return PaperAnswer(
            question=question,
            answer=(
                f"未识别到独立的{target.name}章节，但全文文本在第 {pages} 页出现了相关提及。"
            ),
            status=AnswerStatus.ANSWERED,
            citations=[
                EvidenceAnchor(
                    chunk_id=chunk.chunk_id,
                    page=page,
                    text=chunk.content,
                    rects=chunk.rects,
                )
                for page, chunk in sorted(mentions_by_page.items())
            ],
        )

    return PaperAnswer(
        question=question,
        answer=f"当前 PDF 的章节标题和全文文本索引中未检索到{target.name}。",
        status=AnswerStatus.ANSWERED,
    )


def _paper_location_answer(
    question: str,
    paper: ParsedPaper,
) -> PaperAnswer | None:
    if not _LOCATION_QUESTION_PATTERN.search(question):
        return None
    normalized = question.lower()
    section_type = next(
        (
            candidate_type
            for candidate_type, terms in _LOCATION_SECTION_TERMS
            if any(term in normalized for term in terms)
        ),
        None,
    )
    if section_type is None:
        return PaperAnswer(
            question=question,
            answer="请说明需要定位研究问题、主要贡献、研究方法、实验或研究局限中的哪一部分。",
            status=AnswerStatus.INSUFFICIENT_EVIDENCE,
        )

    sections = _paper_sections(paper)
    section = next(
        (
            candidate
            for heading_term in _SECTION_HEADING_TERMS[section_type]
            for candidate in sections
            if heading_term in candidate.title.lower()
        ),
        None,
    )
    if section is None:
        section_name = _LOCATION_SECTION_NAMES[section_type]
        return PaperAnswer(
            question=question,
            answer=f"未在 PDF 中识别到独立的{section_name}章节标题，暂时无法可靠定位。",
            status=AnswerStatus.INSUFFICIENT_EVIDENCE,
        )

    if section.start_page == section.end_page:
        page_text = f"第 {section.start_page} 页"
    else:
        page_text = f"第 {section.start_page}—{section.end_page} 页"
    section_name = _LOCATION_SECTION_NAMES[section_type]
    heading_rects = section.heading_chunk.rects[:2]
    heading_text = f"{section.number} {section.title}"
    return PaperAnswer(
        question=question,
        answer=(
            f"{section_name}相关内容位于“{section.title}”章节（{page_text}），"
            f"章节从第 {section.start_page} 页开始。"
        ),
        status=AnswerStatus.ANSWERED,
        citations=[
            EvidenceAnchor(
                chunk_id=section.heading_chunk.chunk_id,
                page=section.start_page,
                text=heading_text,
                context_text=section.heading_chunk.content,
                rects=heading_rects,
            )
        ],
    )


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


def _quote_rects(chunk: PaperChunk, quote: str | None) -> list[PageRect]:
    if not quote:
        return chunk.rects
    lines = [re.sub(r"\s+", " ", line).strip() for line in chunk.content.splitlines()]
    lines = [line for line in lines if line]
    if not lines or len(lines) != len(chunk.rects):
        return chunk.rects
    joined = " ".join(lines)
    start = joined.casefold().find(quote.casefold())
    if start < 0:
        return chunk.rects
    end = start + len(quote)
    selected_rects: list[PageRect] = []
    cursor = 0
    for line, rect in zip(lines, chunk.rects, strict=True):
        line_start = cursor
        line_end = cursor + len(line)
        if line_start < end and line_end > start:
            selected_rects.append(rect)
        cursor = line_end + 1
    return selected_rects or chunk.rects


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


def build_learning_logic_chain(report: LearningReport) -> tuple[LearningLogicNode, ...]:
    """Build a compact, evidence-backed paper logic chain from existing report points."""

    sections = {section.section_type: section for section in report.sections}

    def evidenced_points(section_type: LearningSectionType):
        section = sections.get(section_type)
        if section is None:
            return []
        return [point for point in section.points if point.evidence]

    nodes: list[LearningLogicNode] = []
    problem_points = evidenced_points(LearningSectionType.RESEARCH_PROBLEM)
    if problem_points:
        point = problem_points[0]
        nodes.append(
            LearningLogicNode(
                role="问题",
                title=point.title,
                explanation=point.explanation,
                evidence=tuple(point.evidence),
            )
        )
    if len(problem_points) > 1:
        point = problem_points[1]
        nodes.append(
            LearningLogicNode(
                role="原因与约束",
                title=point.title,
                explanation=point.explanation,
                evidence=tuple(point.evidence),
            )
        )

    solution_points = evidenced_points(LearningSectionType.CONTRIBUTIONS)
    if not solution_points:
        solution_points = evidenced_points(LearningSectionType.METHOD)
    if solution_points:
        point = solution_points[0]
        nodes.append(
            LearningLogicNode(
                role="作者方案",
                title=point.title,
                explanation=point.explanation,
                evidence=tuple(point.evidence),
            )
        )

    verification_points = evidenced_points(LearningSectionType.RESULTS)
    if not verification_points:
        verification_points = evidenced_points(LearningSectionType.EXPERIMENTS)
    if verification_points:
        point = verification_points[0]
        nodes.append(
            LearningLogicNode(
                role="验证证据",
                title=point.title,
                explanation=point.explanation,
                evidence=tuple(point.evidence),
            )
        )
    return tuple(nodes)


def _report_section_for_paper_heading(title: str) -> LearningSectionType | None:
    normalized = title.casefold()
    keyword_map = (
        (LearningSectionType.RESULTS, ("result", "analysis")),
        (LearningSectionType.EXPERIMENTS, ("experiment", "evaluation", "dataset")),
        (LearningSectionType.METHOD, ("method", "approach", "framework", "system")),
        (LearningSectionType.LIMITATIONS, ("limitation", "discussion", "conclusion")),
        (LearningSectionType.RESEARCH_PROBLEM, ("introduction", "background")),
    )
    return next(
        (
            section_type
            for section_type, keywords in keyword_map
            if any(keyword in normalized for keyword in keywords)
        ),
        None,
    )


def build_learning_page_context(
    report: LearningReport,
    paper: ParsedPaper,
    page: int,
) -> LearningPageContext:
    """Resolve a page to existing report knowledge without making a model call."""

    if not 1 <= page <= paper.page_count:
        raise ValueError("PDF 页码超出范围。")

    paper_section = next(
        (
            section
            for section in _paper_sections(paper)
            if section.start_page <= page <= section.end_page
        ),
        None,
    )
    paper_section_label = (
        f"§{paper_section.number} {paper_section.title}"
        if paper_section is not None
        else None
    )

    page_points: list[LearningPagePoint] = []
    for section in report.sections:
        for point in section.points:
            page_evidence = tuple(anchor for anchor in point.evidence if anchor.page == page)
            if not page_evidence:
                continue
            page_points.append(
                LearningPagePoint(
                    section_type=section.section_type,
                    section_title=section.title,
                    title=point.title,
                    explanation=point.explanation,
                    evidence=page_evidence,
                )
            )

    report_section = None
    if page_points:
        mapped_type = page_points[0].section_type
    elif paper_section is not None:
        mapped_type = _report_section_for_paper_heading(paper_section.title)
    else:
        mapped_type = None
    mapped_section = next(
        (section for section in report.sections if section.section_type == mapped_type),
        None,
    )
    relation = None
    if mapped_section is not None:
        report_section = mapped_section.title
        if paper_section_label:
            relation = (
                f"本页位于论文“{paper_section_label}”，对应讲解中的“{mapped_section.title}”。"
                f"{mapped_section.overview}"
            )
        else:
            relation = f"本页对应讲解中的“{mapped_section.title}”。{mapped_section.overview}"

    questions: list[str] = []
    if page_points:
        questions.append(f'“{page_points[0].title}”在第 {page} 页由哪些原文证据支持？')
    if paper_section is not None:
        questions.append(
            f'请结合第 {page} 页解释“{paper_section.title}”在论文整体方法中的作用。'
        )
    if mapped_section is not None:
        questions.append(f'第 {page} 页的内容如何支撑“{mapped_section.title}”？')
    if not questions:
        questions.append(f"请解释论文第 {page} 页的主要内容，并指出可验证的原文依据。")

    return LearningPageContext(
        page=page,
        paper_section=paper_section_label,
        report_section=report_section,
        relation=relation,
        points=tuple(page_points),
        suggested_questions=tuple(dict.fromkeys(questions))[:3],
    )


def _expand_question_candidates(
    candidates: list[EvidenceCandidate],
    chunks: list[PaperChunk],
    limit: int = 10,
) -> list[EvidenceCandidate]:
    """Add immediate same-page neighbors so broad answers and table rows retain context."""
    positions = {chunk.chunk_id: index for index, chunk in enumerate(chunks)}
    expanded: list[tuple[PaperChunk, float]] = []
    seen: set[str] = set()
    for candidate in candidates:
        index = positions.get(candidate.chunk_id)
        if index is None:
            continue
        for neighbor_index, score_offset in ((index, 0.0), (index - 1, -0.1), (index + 1, -0.1)):
            if not 0 <= neighbor_index < len(chunks):
                continue
            chunk = chunks[neighbor_index]
            if chunk.page != candidate.page or chunk.chunk_id in seen:
                continue
            seen.add(chunk.chunk_id)
            expanded.append((chunk, candidate.score + score_offset))
            if len(expanded) >= limit:
                break
        if len(expanded) >= limit:
            break
    return [
        EvidenceCandidate(
            evidence_id=f"Q_e{index + 1}",
            chunk_id=chunk.chunk_id,
            page=chunk.page,
            text=chunk.content,
            score=round(score, 6),
        )
        for index, (chunk, score) in enumerate(expanded)
    ]


def _normalize_selected_text(value: str) -> str:
    value = re.sub(r"(?<=[A-Za-z])-\s+(?=[a-z])", "", value)
    return re.sub(r"\s+", " ", value).strip().casefold()


def match_selected_chunks(
    paper: ParsedPaper,
    page: int,
    selected_text: str,
    selected_rects: Sequence[PageRect] = (),
    limit: int = 3,
) -> list[PaperChunk]:
    """Match browser-selected PDF text back to same-page local paper chunks."""
    normalized_selection = _normalize_selected_text(selected_text)
    if len(normalized_selection) < 4:
        return []

    selected_tokens = set(re.findall(r"[a-z0-9]+", normalized_selection))
    scored: list[tuple[float, int, PaperChunk]] = []
    for index, chunk in enumerate(paper.chunks):
        if chunk.page != page:
            continue
        normalized_chunk = _normalize_selected_text(chunk.content)
        if not normalized_chunk:
            continue
        overlap_area = 0.0
        selected_area = sum(
            max(rect.x1 - rect.x0, 0.0) * max(rect.y1 - rect.y0, 0.0)
            for rect in selected_rects
        )
        if selected_area and chunk.rects:
            overlap_area = sum(
                max(min(selected.x1, source.x1) - max(selected.x0, source.x0), 0.0)
                * max(min(selected.y1, source.y1) - max(selected.y0, source.y0), 0.0)
                for selected in selected_rects
                for source in chunk.rects
            )
        if overlap_area > 0:
            score = 5.0 + min(overlap_area / selected_area, 1.0)
        elif normalized_selection in normalized_chunk:
            score = 3.0 + len(normalized_selection) / max(len(normalized_chunk), 1)
        elif normalized_chunk in normalized_selection:
            score = 2.0 + len(normalized_chunk) / max(len(normalized_selection), 1)
        else:
            chunk_tokens = set(re.findall(r"[a-z0-9]+", normalized_chunk))
            token_overlap = len(selected_tokens & chunk_tokens) / max(
                min(len(selected_tokens), len(chunk_tokens)), 1
            )
            similarity = SequenceMatcher(
                None,
                normalized_selection[:1600],
                normalized_chunk[:1600],
                autojunk=False,
            ).ratio()
            score = token_overlap * 0.65 + similarity * 0.35
            if score < 0.28:
                continue
        scored.append((score, -index, chunk))
    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [item[2] for item in scored[: max(1, limit)]]


def _merge_question_candidates(
    selected_chunk_ids: Sequence[str],
    retrieved: list[EvidenceCandidate],
    chunks: list[PaperChunk],
    limit: int,
) -> list[EvidenceCandidate]:
    chunk_map = {chunk.chunk_id: chunk for chunk in chunks}
    selected_candidates = [
        EvidenceCandidate(
            evidence_id=f"S_e{index + 1}",
            chunk_id=chunk.chunk_id,
            page=chunk.page,
            text=chunk.content,
            score=2.0 - index * 0.01,
        )
        for index, chunk_id in enumerate(dict.fromkeys(selected_chunk_ids))
        if (chunk := chunk_map.get(chunk_id)) is not None
    ]
    seeded = _expand_question_candidates(selected_candidates, chunks, limit=limit)
    expanded = _expand_question_candidates(retrieved, chunks, limit=limit)
    merged: list[EvidenceCandidate] = []
    seen: set[str] = set()
    for candidate in [*seeded, *expanded]:
        if candidate.chunk_id in seen:
            continue
        seen.add(candidate.chunk_id)
        merged.append(
            candidate.model_copy(update={"evidence_id": f"Q_e{len(merged) + 1}"})
        )
        if len(merged) >= limit:
            break
    return merged


class AuditService:
    def __init__(self, settings: Settings, client: Hy3Client | None = None):
        self.settings = settings
        self.client = client or Hy3Client(settings)

    def parse(self, pdf_bytes: bytes) -> ParsedPaper:
        return parse_pdf(pdf_bytes)

    def generate_report(self, paper: ParsedPaper) -> str:
        return self.client.generate_report(paper.title, paper.chunks)

    def generate_learning_report(self, paper: ParsedPaper) -> LearningReport:
        generated = self.client.generate_learning_report(paper.title, paper.chunks)
        required_sections = list(LearningSectionType)
        section_map: dict[LearningSectionType, ReportSection] = {}
        for section in generated.sections:
            if section.section_type in section_map:
                raise Hy3ResponseError(f"Hy3 重复生成了章节：{section.section_type.value}。")
            section_map[section.section_type] = section

        missing = [section.value for section in required_sections if section not in section_map]
        if missing:
            raise Hy3ResponseError(f"Hy3 讲解缺少必要章节：{', '.join(missing)}。")

        chunk_map = {chunk.chunk_id: chunk for chunk in paper.chunks}
        chunk_positions = {chunk.chunk_id: index for index, chunk in enumerate(paper.chunks)}
        invalid_key_points: list[str] = []
        enriched_sections: list[ReportSection] = []
        total_key_points = 0
        for section_type in required_sections:
            section = section_map[section_type]
            enriched_points = []
            section_key_points = 0
            for point in section.points:
                is_key_point = (
                    point.key_point
                    and section_key_points < 2
                    and total_key_points < 14
                )
                anchors: list[EvidenceAnchor] = []
                seen: set[str] = set()
                for anchor in point.evidence:
                    chunk = chunk_map.get(anchor.chunk_id)
                    if chunk is None or chunk.chunk_id in seen:
                        continue
                    seen.add(chunk.chunk_id)
                    quote = (
                        _validated_evidence_quote(anchor.quote, chunk.content)
                        if anchor.quote
                        else None
                    )
                    anchors.append(
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
                            rects=_quote_rects(chunk, quote),
                            context_text=_neighbor_context(
                                chunk.chunk_id,
                                paper.chunks,
                                chunk_positions,
                            ),
                        )
                    )
                if is_key_point and not anchors:
                    invalid_key_points.append(point.title)
                if is_key_point:
                    section_key_points += 1
                    total_key_points += 1
                enriched_points.append(
                    point.model_copy(
                        update={"key_point": is_key_point, "evidence": anchors}
                    )
                )
            enriched_sections.append(section.model_copy(update={"points": enriched_points}))

        if invalid_key_points:
            names = "、".join(invalid_key_points[:5])
            raise Hy3ResponseError(f"关键知识点缺少有效原文证据：{names}。")

        suggested_pages = list(
            dict.fromkeys(page for page in generated.suggested_pages if 1 <= page <= paper.page_count)
        )
        if len(suggested_pages) > 5:
            page_weights = Counter(
                anchor.page
                for section in enriched_sections
                for point in section.points
                if point.key_point
                for anchor in point.evidence
                if anchor.page is not None
            )
            original_order = {page: index for index, page in enumerate(suggested_pages)}
            selected_pages = set(
                sorted(
                    suggested_pages,
                    key=lambda page: (-page_weights[page], original_order[page]),
                )[:5]
            )
            suggested_pages = [page for page in suggested_pages if page in selected_pages]
        return generated.model_copy(
            update={
                "paper_title": paper.title,
                "sections": enriched_sections,
                "suggested_pages": suggested_pages,
            }
        )

    def answer_question(
        self,
        paper: ParsedPaper,
        question: str,
        history: Sequence[PaperAnswer] = (),
        selected_chunk_ids: Sequence[str] = (),
        selected_text: str | None = None,
    ) -> PaperAnswer:
        normalized_question = question.strip()
        if not normalized_question:
            raise ValueError("追问内容不能为空。")
        if len(normalized_question) > 1000:
            raise ValueError("追问内容过长，请控制在 1000 个字符以内。")
        normalized_selection = selected_text.strip()[:2000] if selected_text else None

        structure_answer = _document_structure_answer(normalized_question, paper)
        if structure_answer is not None:
            return structure_answer

        location_answer = _paper_location_answer(normalized_question, paper)
        if location_answer is not None:
            return location_answer

        query = self.client.plan_question(paper.title, normalized_question, history)
        retrieval_query = " ".join(
            value
            for value in [query.query_en, *query.entities, *query.numbers]
            if value.strip()
        )
        with EvidenceRetriever(paper.chunks) as retriever:
            candidates = retriever.search(
                retrieval_query,
                "Q",
                self.settings.retrieval_top_k,
            )

        candidates = _merge_question_candidates(
            selected_chunk_ids,
            candidates,
            paper.chunks,
            limit=min(max(self.settings.retrieval_top_k * 2, 8), 12),
        )

        if not candidates:
            return PaperAnswer(
                question=normalized_question,
                answer="当前论文中未检索到足够相关的原文证据，暂时无法可靠回答。",
                status=AnswerStatus.INSUFFICIENT_EVIDENCE,
            )

        draft = self.client.answer_question(
            normalized_question,
            candidates,
            history,
            normalized_selection,
        )
        if draft.status == AnswerStatus.INSUFFICIENT_EVIDENCE:
            expanded_limit = min(max(self.settings.retrieval_top_k * 4, 16), 24)
            with EvidenceRetriever(paper.chunks) as retriever:
                expanded_retrieved = retriever.search(
                    retrieval_query,
                    "QX",
                    expanded_limit,
                )
            expanded_candidates = _merge_question_candidates(
                selected_chunk_ids,
                expanded_retrieved,
                paper.chunks,
                limit=expanded_limit,
            )
            if {item.chunk_id for item in expanded_candidates} != {
                item.chunk_id for item in candidates
            }:
                candidates = expanded_candidates
                draft = self.client.answer_question(
                    normalized_question,
                    candidates,
                    history,
                    normalized_selection,
                )
        candidate_map = {candidate.chunk_id: candidate for candidate in candidates}
        chunk_map = {chunk.chunk_id: chunk for chunk in paper.chunks}
        chunk_positions = {chunk.chunk_id: index for index, chunk in enumerate(paper.chunks)}
        citations_by_id: dict[str, EvidenceAnchor] = {}

        def build_anchor(
            chunk_id: str,
            requested_quote: str | None = None,
        ) -> EvidenceAnchor | None:
            candidate = candidate_map.get(chunk_id)
            chunk = chunk_map.get(chunk_id)
            if candidate is None or chunk is None:
                return None
            quote = None
            if requested_quote is not None:
                quote = _validated_evidence_quote(requested_quote, chunk.content)
                if quote is None:
                    return None
            chunk = chunk_map[chunk_id]
            anchor = EvidenceAnchor(
                chunk_id=chunk_id,
                page=candidate.page,
                text=candidate.text,
                quote=quote,
                locator=_evidence_locator(
                    chunk_id,
                    paper.chunks,
                    chunk_positions,
                ),
                rects=_quote_rects(chunk, quote),
                context_text=_neighbor_context(
                    chunk_id,
                    paper.chunks,
                    chunk_positions,
                ),
            )
            existing = citations_by_id.get(chunk_id)
            if existing is None or (existing.quote is None and quote is not None):
                citations_by_id[chunk_id] = anchor
            return anchor

        for chunk_id in draft.citation_chunk_ids:
            build_anchor(chunk_id)

        conclusions: list[AnswerConclusion] = []
        for conclusion in draft.conclusions[:4]:
            conclusion_text = conclusion.text.strip()
            if not conclusion_text:
                continue
            conclusion_citations: list[EvidenceAnchor] = []
            conclusion_seen: set[str] = set()
            for evidence in conclusion.evidence[:2]:
                if evidence.chunk_id in conclusion_seen:
                    continue
                anchor = build_anchor(evidence.chunk_id, evidence.quote)
                if anchor is not None:
                    conclusion_seen.add(evidence.chunk_id)
                    conclusion_citations.append(anchor)
            if conclusion_citations:
                conclusions.append(
                    AnswerConclusion(
                        text=conclusion_text,
                        support_type=conclusion.support_type,
                        citations=conclusion_citations,
                    )
                )

        citations = list(citations_by_id.values())

        if draft.status == AnswerStatus.ANSWERED and not conclusions:
            return PaperAnswer(
                question=normalized_question,
                answer="模型返回的结论缺少可在本地 PDF 中核验的原文摘录，本次回答已转为证据不足。",
                status=AnswerStatus.INSUFFICIENT_EVIDENCE,
            )
        if draft.status == AnswerStatus.ANSWERED and not citations:
            return PaperAnswer(
                question=normalized_question,
                answer="模型未返回可验证的有效原文引用，本次回答已转为证据不足。",
                status=AnswerStatus.INSUFFICIENT_EVIDENCE,
            )
        if draft.status == AnswerStatus.INSUFFICIENT_EVIDENCE:
            citations = []

        verified_answer = draft.answer
        if conclusions:
            verified_answer = "\n".join(conclusion.text for conclusion in conclusions)
        return PaperAnswer(
            question=normalized_question,
            answer=verified_answer,
            status=draft.status,
            citations=citations,
            conclusions=conclusions,
        )

    def audit(
        self,
        paper: ParsedPaper,
        report_text: str,
        scope: Sequence[ClaimCategory],
        mode: str = "audit_existing",
        progress: ProgressCallback | None = None,
    ) -> AuditRun:
        notify = progress or _noop_progress
        notify("正在拆分原子论断", 0.1)
        extraction = self.client.extract_claims(report_text, [category.value for category in scope])
        claims = [
            claim.model_copy(update={"claim_id": f"C{index + 1:03d}"})
            for index, claim in enumerate(extraction.claims)
        ]
        if not claims:
            raise ValueError("报告中未提取到可审计的事实论断。")

        notify("正在检索候选证据", 0.25)
        candidates_by_claim: dict[str, list] = {}
        with EvidenceRetriever(paper.chunks) as retriever:
            for claim in claims:
                candidates_by_claim[claim.claim_id] = retriever.search(
                    build_claim_query(claim),
                    claim.claim_id,
                    self.settings.retrieval_top_k,
                )

        judgments: dict[str, ClaimJudgment] = {}
        auditable = [claim for claim in claims if candidates_by_claim[claim.claim_id]]
        batch_size = max(1, self.settings.judge_batch_size)
        for start in range(0, len(auditable), batch_size):
            batch = auditable[start : start + batch_size]
            progress_value = 0.35 + 0.5 * min((start + len(batch)) / max(len(auditable), 1), 1.0)
            notify("正在判断证据支持关系", progress_value)
            response = self.client.judge_claims(
                [(claim, candidates_by_claim[claim.claim_id]) for claim in batch],
                paper.page_count,
            )
            for judgment in response.judgments:
                judgments[judgment.claim_id] = judgment

        audits: list[ClaimAudit] = []
        for claim in claims:
            candidates = candidates_by_claim[claim.claim_id]
            judgment = judgments.get(claim.claim_id)
            if not candidates:
                judgment = ClaimJudgment(
                    claim_id=claim.claim_id,
                    label=AutoLabel.ABSTAIN,
                    explanation="本地检索未返回候选证据，暂时无法可靠判断。",
                    severity=Severity.NONE,
                )
            elif judgment is None:
                judgment = ClaimJudgment(
                    claim_id=claim.claim_id,
                    label=AutoLabel.ABSTAIN,
                    explanation="Hy3 未返回该论断的结构化判断。",
                    severity=Severity.NONE,
                )
            else:
                allowed_ids = {candidate.evidence_id for candidate in candidates}
                returned_ids = set(judgment.evidence_ids)
                requires_evidence = judgment.label in {
                    AutoLabel.SUPPORTED,
                    AutoLabel.PARTIALLY_SUPPORTED,
                    AutoLabel.CONTRADICTED,
                }
                if not returned_ids.issubset(allowed_ids) or (requires_evidence and not returned_ids):
                    judgment = judgment.model_copy(
                        update={
                            "label": AutoLabel.ABSTAIN,
                            "evidence_ids": [],
                            "explanation": "Hy3 返回的证据编号无效，已转为人工复核。",
                            "claim_error_type": None,
                            "evidence_error_type": None,
                            "severity": Severity.NONE,
                        }
                    )
            audits.append(ClaimAudit(claim=claim, candidates=candidates, judgment=judgment))

        notify("正在生成审计摘要", 0.95)
        summary = build_summary(audits, list(scope))
        notify("审计完成", 1.0)
        return AuditRun(
            paper_title=paper.title,
            page_count=paper.page_count,
            mode=mode,
            scope=list(scope),
            report_text=report_text,
            audits=audits,
            summary=summary,
            parse_warnings=paper.warnings,
        )
