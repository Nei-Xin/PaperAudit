"""Stable report boundaries and locally validated claim provenance."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import asdict, dataclass
import re
from typing import Literal

from pydantic import Field

from .models import AtomicClaim, ClaimExtraction, SkippedReportSource, StrictModel


@dataclass(frozen=True)
class ReportSource:
    source_id: str
    text: str
    report_location: str
    section_title: str = ""


_CITATION = re.compile(r"[（(](?:证据|引用|来源)\s*[:：][^）)\n]+[）)]")
_EVALUATION = re.compile(r"(?:评估|评测|实验|evaluate|evaluation|experiment).*(?:数据|任务|基准|dataset|task|benchmark)|(?:数据|任务|dataset|task).*(?:评估|评测|evaluate)", re.I)


def _sentences(line: str) -> list[str]:
    """A citation immediately after sentence punctuation belongs to that sentence."""
    parts = []
    start = 0
    for boundary in re.finditer(r"[。！？!?]|\.(?=\s+[A-Z\u4e00-\u9fff])", line):
        if boundary.start() < start:
            continue
        end = boundary.end()
        while True:
            anchor = _CITATION.match(line, end + len(line[end:]) - len(line[end:].lstrip()))
            if anchor is None:
                break
            end = anchor.end()
        parts.append(line[start:end])
        start = end
    parts.append(line[start:])
    return [part.strip() for part in parts if part.strip()]


class SourcedClaim(AtomicClaim):
    source_quote: str = Field(min_length=1)


class SourceExtraction(StrictModel):
    source_id: str
    claims: list[SourcedClaim]
    skip_reason: Literal["heading", "opinion", "out_of_scope", "non_claim"] | None = None


class SourceExtractionBatch(StrictModel):
    sources: list[SourceExtraction]


def split_report_sources(text: str) -> list[ReportSource]:
    """Keep decimals, qualifiers and enumerations intact; split full sentences."""
    sources: list[ReportSource] = []
    slide = None
    section = ""
    for line_number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        marker = re.fullmatch(r"\s*\[幻灯片\s+(\d+)\]\s*", line)
        if marker:
            slide = marker.group(1)
        heading = re.match(r"^\s*#{1,6}\s+(.+)", line)
        if heading:
            section = heading.group(1).strip()
        # English periods split only before whitespace; 3.2 and v1.0 stay intact.
        sentences = _sentences(line)
        for sentence_number, sentence in enumerate(sentences, 1):
            sentence = sentence.strip()
            if not sentence:
                continue
            location = f"第 {line_number} 行 · 第 {sentence_number} 句"
            if slide:
                location = f"PPT 第 {slide} 页 · {location}"
            sources.append(ReportSource(f"S{len(sources) + 1:04d}", sentence, location, section))
    return sources


def source_batches(sources: Sequence[ReportSource]) -> Iterator[list[ReportSource]]:
    batch: list[ReportSource] = []
    size = 0
    for source in sources:
        if batch and (len(batch) >= 12 or size + len(source.text) > 6000):
            yield batch
            batch, size = [], 0
        batch.append(source)
        size += len(source.text)
    if batch:
        yield batch


def source_payload(sources: Sequence[ReportSource]) -> list[dict[str, str]]:
    return [asdict(source) for source in sources]


def validate_source_extraction(
    response: SourceExtractionBatch, sources: Sequence[ReportSource], scope: Sequence[str]
) -> ClaimExtraction:
    """Reject missing/duplicate units and fabricated quotes before scoring."""
    by_id = {item.source_id: item for item in response.sources}
    if len(by_id) != len(response.sources) or set(by_id) != {s.source_id for s in sources}:
        raise ValueError("每个原文编号必须且只能返回一次，不得遗漏或添加编号。")
    claims: list[AtomicClaim] = []
    skipped: list[SkippedReportSource] = []
    for source in sources:
        item = by_id[source.source_id]
        if bool(item.claims) == bool(item.skip_reason):
            raise ValueError(f"{source.source_id} 必须返回论断或明确的跳过原因。")
        if item.skip_reason:
            if item.skip_reason == "out_of_scope" and "results" in scope and _EVALUATION.search(source.text):
                raise ValueError(f"{source.source_id} 描述在哪些数据或任务上评估方法，属于本次 results 范围；不能因涉及数据集而跳过。请核对并提取。")
            skipped.append(SkippedReportSource(source_id=source.source_id, text=source.text,
                report_location=source.report_location, reason=item.skip_reason))
            continue
        unique: dict[str, AtomicClaim] = {}
        for claim in item.claims:
            if claim.source_quote not in source.text:
                raise ValueError(f"{source.source_id} 的引用必须是该句中连续、逐字的原文。")
            category = claim.category
            if category.value == "dataset_setup" and category.value not in scope and "results" in scope and _EVALUATION.search(source.text):
                # Evaluation coverage is part of results, even when setup is excluded.
                category = type(category).RESULTS
            if category.value not in scope:
                raise ValueError(f"{source.source_id} 的论断超出请求的审计范围。")
            if claim.source_id not in (None, source.source_id):
                raise ValueError(f"{source.source_id} 的论断来源编号不一致。")
            normalized = re.sub(r"\s+", "", claim.text).strip("。.!！?？").casefold()
            if not normalized:
                raise ValueError(f"{source.source_id} 返回了空论断。")
            unique.setdefault(normalized, AtomicClaim(**{
                **claim.model_dump(),
                "source_id": source.source_id,
                "report_location": source.report_location,
                "category": category,
                # Only local report text can provide an original citation.
                "provided_evidence": " ".join(_CITATION.findall(source.text)) or (
                    claim.provided_evidence if claim.provided_evidence and claim.provided_evidence in source.text else None
                ),
            }))
        claims.extend(sorted(unique.values(), key=lambda c: (
            source.text.index(c.source_quote), c.text,
        )))
    return ClaimExtraction(claims=claims, source_count=len(sources), skipped_sources=skipped)
