from __future__ import annotations

import re
import sqlite3
from collections.abc import Iterable

from .models import AtomicClaim, EvidenceCandidate, PaperChunk
from .pdf_parser import _classify_block


_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "was",
    "were",
    "with",
}
_ATTRIBUTION_TERMS = {
    "author",
    "authors",
    "propose",
    "proposed",
    "introduce",
    "introduced",
    "team",
    "developed",
    "designed",
    "invented",
    "created",
}
_METRIC_TERMS = {"error", "accuracy", "precision", "recall", "bleu", "f1", "score", "improvement"}
_RESOURCE_TERMS = {
    "gpu",
    "gpus",
    "cpu",
    "memory",
    "v100",
    "hours",
    "hour",
    "days",
    "day",
    "batch",
    "training",
    "inference",
}
_CONCRETE_RESOURCE_TERMS = {
    "gpu",
    "gpus",
    "cpu",
    "memory",
    "v100",
    "hours",
    "hour",
    "days",
    "day",
    "batch",
}
_CONFIG_TERMS = {
    "base",
    "large",
    "small",
    "medium",
    "xl",
    "model",
    "variant",
    "configuration",
    "config",
}
_SPECIFIC_CONFIG_TERMS = {"base", "large", "small", "medium", "xl", "variant"}
_TABLE_HEADER_TERMS = {
    "model",
    "complexity",
    "accuracy",
    "error",
    "err",
    "score",
    "metric",
    "dataset",
    "baseline",
    "approach",
    "data",
    "type",
    "reduction",
}


def _normalize_for_search(text: str) -> str:
    """Make PDF line-break hyphenation and common ligatures searchable."""

    normalized = text.casefold().replace("ﬁ", "fi").replace("ﬂ", "fl").replace("×", "x")
    return re.sub(r"-\s*", "", normalized)


def _query_terms(values: Iterable[str]) -> list[str]:
    terms: list[str] = []
    for value in values:
        tokens = re.findall(
            r"[A-Za-z][A-Za-z0-9_]*|\d+(?:\.\d+)?", _normalize_for_search(value)
        )
        for token in tokens:
            normalized = token.lower()
            if normalized not in _STOPWORDS and (len(normalized) > 1 or normalized.isdigit()):
                terms.append(normalized)
    return list(dict.fromkeys(terms))[:40]


def _content_terms(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[A-Za-z][A-Za-z0-9_]*|\d+(?:\.\d+)?", text)
        if token not in _STOPWORDS and (len(token) > 1 or token.isdigit())
    }


def _search_text(text: str) -> str:
    normalized = _normalize_for_search(text)
    compounds = re.findall(r"\b([a-z]+)(\d+)\b", normalized)
    expanded = " ".join(" ".join(parts) for parts in compounds)
    return f"{normalized} {expanded}".strip()


def _term_matches(term: str, content_terms: set[str]) -> bool:
    """Match exact terms and simple morphology-independent variants."""

    variants = {term}
    if term.endswith("s") and len(term) > 2:
        variants.add(term[:-1])
    elif len(term) > 2:
        variants.add(term + "s")
    return bool(variants & content_terms)


def _has_metric_number_anchor(content: str, terms: set[str], content_terms: set[str]) -> bool:
    """Prefer a reported metric value over an unrelated exact number."""

    metric_terms = terms & _METRIC_TERMS
    if not metric_terms:
        return False
    for number_match in re.finditer(r"\d+(?:\.\d+)?\s*%", content):
        window_start = max(0, number_match.start() - 80)
        window_end = min(len(content), number_match.end() + 80)
        window = content[window_start:window_end]
        if any(re.search(rf"\b{re.escape(metric)}\b", window) for metric in metric_terms):
            return True
    return False


def _has_resource_anchor(terms: set[str], content_terms: set[str]) -> bool:
    """Prefer matching hardware/training-resource statements for resource queries."""

    query_resources = terms & _CONCRETE_RESOURCE_TERMS or terms & _RESOURCE_TERMS
    if not query_resources:
        return False
    return any(_term_matches(term, content_terms) for term in query_resources)


def _has_config_resource_pair(content: str, terms: set[str]) -> bool:
    """Match a requested model/configuration entity to nearby resource information."""

    # Generic words such as "model" or "configuration" are too common to anchor a pair;
    # require a distinguishing configuration entity when one is present in the query.
    query_configs = terms & _SPECIFIC_CONFIG_TERMS
    query_resources = terms & _CONCRETE_RESOURCE_TERMS or terms & _RESOURCE_TERMS
    if not query_configs or not query_resources:
        return False
    normalized = _normalize_for_search(content)
    def _pattern(term: str) -> str:
        suffix = "s?" if len(term) > 2 and not term.endswith("s") else ""
        return rf"\b{re.escape(term)}{suffix}\b"

    config_patterns = [_pattern(term) for term in query_configs]
    resource_patterns = [_pattern(term) for term in query_resources]
    config_positions = [
        match.start()
        for pattern in config_patterns
        for match in re.finditer(pattern, normalized)
    ]
    resource_positions = [
        match.start()
        for pattern in resource_patterns
        for match in re.finditer(pattern, normalized)
    ]
    return any(abs(config - resource) <= 240 for config in config_positions for resource in resource_positions)


def _looks_like_author_block(text: str) -> bool:
    if len(text) > 180 or any(marker in text.lower() for marker in ("abstract", "http", "@")):
        return False
    return sum(bool(re.search(r"\b[A-Z][a-z]+\s+[A-Z][A-Za-z-]+\b", line)) for line in text.splitlines()) > 0


def _abstract_chunk_ids(chunks: list[PaperChunk]) -> set[str]:
    """Locate substantive abstract blocks without relying on paper-specific terms."""

    abstract_ids: set[str] = set()
    in_abstract = False
    for chunk in chunks:
        if chunk.page != 1:
            continue
        normalized = _normalize_for_search(chunk.content).strip()
        if re.match(r"^\d*\s*(introduction|background)\b", normalized):
            in_abstract = False
        if normalized.startswith("abstract"):
            in_abstract = True
        if in_abstract and len(normalized.split()) >= 8:
            abstract_ids.add(chunk.chunk_id)
    return abstract_ids


def build_claim_query(claim: AtomicClaim) -> str:
    values = [claim.query_en, *claim.entities, *claim.numbers]
    if claim.metric:
        values.append(claim.metric)
    if claim.dataset:
        values.append(claim.dataset)
    return " ".join(values)


def report_evidence_pages(anchor: str | None) -> set[int]:
    """Recognize explicit paper page references, never slide provenance."""
    text = anchor or ""
    pages: set[int] = set()

    def add_expression(expression: str) -> None:
        for first, last in re.findall(r"(\d+)(?:\s*[-–~至]\s*(\d+))?", expression):
            start = int(first)
            end = int(last) if last else start
            if 1 <= start <= end and end - start <= 100:
                pages.update(range(start, end + 1))

    for expression in re.findall(
        r"第\s*([0-9][0-9、,，\s\-–~至]*)\s*页", text, re.I
    ):
        add_expression(expression)
    for expression in re.findall(r"\b(?:pages?|p\.?)[ \t]*([0-9]+)", text, re.I):
        add_expression(expression)
    return pages


def _continues_across_pages(left: PaperChunk, right: PaperChunk) -> bool:
    """Recognize a likely text continuation; page proximity alone is not enough."""
    if right.page != left.page + 1:
        return False
    before, after = left.content.strip(), right.content.strip()
    return (
        len(before) >= 20 and len(after) >= 20
        and not re.search(r'[.!?。！？:：]["”）)]?$', before)
        and bool(re.match(r"[a-z]", after))
    )


def expand_claim_evidence(
    claim: AtomicClaim,
    chunks: list[PaperChunk],
    candidates: list[EvidenceCandidate],
    *,
    max_additions: int = 5,
) -> list[EvidenceCandidate]:
    """Append bounded structural context without displacing ranked evidence.

    Every addition retains its original page, text and chunk ID. Structure is a
    retrieval hint, never proof that a row belongs to a particular table.
    """
    positions = {chunk.chunk_id: index for index, chunk in enumerate(chunks)}
    seen = {candidate.chunk_id for candidate in candidates}
    used_ids = {candidate.evidence_id for candidate in candidates}
    result = list(candidates)
    next_id = len(candidates) + 1

    def kind(chunk: PaperChunk) -> str:
        # Old saved indexes have only "text"; infer hints without rewriting them.
        return _classify_block(chunk.content) if chunk.content_type == "text" else chunk.content_type

    for candidate in candidates:
        if len(result) - len(candidates) >= max_additions:
            break
        index = positions.get(candidate.chunk_id)
        if index is None:
            continue
        current = chunks[index]
        for neighbor_index in (index - 1, index + 1):
            if not 0 <= neighbor_index < len(chunks):
                continue
            neighbor = chunks[neighbor_index]
            if neighbor.chunk_id in seen or abs(neighbor.page - current.page) > 1:
                continue
            current_kind, neighbor_kind = kind(current), kind(neighbor)
            structured = {current_kind, neighbor_kind} & {"formula", "table"}
            if current.page == neighbor.page:
                related = bool(structured)
            else:
                left, right = (neighbor, current) if neighbor_index < index else (current, neighbor)
                related = _continues_across_pages(left, right) or (
                    bool(structured) and current_kind == neighbor_kind
                )
            if not related or not re.search(r"[A-Za-z\u0370-\u03ff\u4e00-\u9fff=∑∫]", neighbor.content):
                continue
            while f"{claim.claim_id}_e{next_id}" in used_ids:
                next_id += 1
            evidence_id = f"{claim.claim_id}_e{next_id}"
            next_id += 1
            used_ids.add(evidence_id)
            seen.add(neighbor.chunk_id)
            result.append(EvidenceCandidate(
                evidence_id=evidence_id, chunk_id=neighbor.chunk_id,
                page=neighbor.page, text=neighbor.content,
                score=candidate.score,
            ))
            if len(result) - len(candidates) >= max_additions:
                break
    return result


def _is_table_caption(text: str) -> bool:
    # "Table 5 compares ..." is prose, not the beginning of a table.
    return bool(re.match(r"^\s*(?:table|tab\.|表)\s*\d+[A-Za-z]?(?:\s*[:：.]|\s*$)", text, re.I))


def _is_table_fragment(text: str) -> bool:
    """Recognize compact headers/rows, including one numeric cell per line."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines or len(text) > 600 or any(len(line.split()) > 12 for line in lines):
        return False
    normalized = _normalize_for_search(text)
    header_hits = len(set(re.findall(r"[a-z]+", normalized)) & _TABLE_HEADER_TERMS)
    numbers = re.findall(r"\d+(?:\.\d+)?", text)
    # Long prose lines are not rows even if the parser marked them as tables.
    short_lines = sum(len(line.split()) <= 6 for line in lines)
    # Task headers may consist entirely of abbreviations unknown to retrieval.
    header = not numbers and len(lines) >= 3 and short_lines == len(lines)
    return (header or header_hits >= 2 or len(numbers) >= 2) and short_lines >= len(lines) * .7


def _table_fragments(chunks: list[PaperChunk], index: int) -> list[PaperChunk]:
    """Find a bounded table above or below its caption, respecting PDF columns."""
    caption = chunks[index]

    def bounds(chunk):
        return (min(r.x0 for r in chunk.rects), min(r.y0 for r in chunk.rects),
                max(r.x1 for r in chunk.rects), max(r.y1 for r in chunk.rects))

    if caption.rects:
        box = bounds(caption)
        aligned = []
        for chunk in chunks:
            if chunk.page != caption.page or not chunk.rects:
                continue
            other = bounds(chunk)
            overlap = max(0, min(box[2], other[2]) - max(box[0], other[0]))
            if overlap >= .7 * min(box[2] - box[0], other[2] - other[0]):
                aligned.append(chunk)
        aligned.sort(key=lambda c: bounds(c)[1])
        at = next(i for i, c in enumerate(aligned) if c.chunk_id == caption.chunk_id)
    else:
        aligned, at = chunks, index

    sides = []
    for direction in (1, -1):
        fragments = []
        distance = None
        previous = caption
        for offset in range(1, 13):
            pos = at + direction * offset
            if not 0 <= pos < len(aligned):
                break
            chunk = aligned[pos]
            if chunk.page != caption.page or _is_table_caption(chunk.content) or not _is_table_fragment(chunk.content):
                break
            if caption.rects:
                current_box, previous_box = bounds(chunk), bounds(previous)
                gap = (current_box[1] - previous_box[3] if direction == 1
                       else previous_box[1] - current_box[3])
                if gap < -2 or gap > 36:
                    break
                if distance is None:
                    distance = max(0, gap)
            fragments.append(chunk)
            previous = chunk
        if fragments:
            if direction == -1:
                fragments.reverse()
            # Without geometry preserve caption-first behavior when both sides
            # look plausible. With geometry prefer the nearer table boundary.
            sides.append((distance if distance is not None else (direction == -1), fragments))
    return min(sides, key=lambda side: (side[0], -len(side[1])))[1] if sides else []


def _cited_table_candidates(
    claim: AtomicClaim,
    cited_chunks: list[PaperChunk],
    local: list[EvidenceCandidate],
    global_seed_ids: set[str],
) -> list[EvidenceCandidate]:
    """Reserve at most three slots for a matching caption, header and ranked rows."""
    positions = {chunk.chunk_id: index for index, chunk in enumerate(cited_chunks)}
    requested_tables = set(re.findall(r"(?:\btable|\btab\.|表)\s*(\d+[A-Za-z]?)", claim.provided_evidence or "", re.I))

    def explicitly_cited(hit):
        number = re.match(r"\s*(?:table|tab\.|表)\s*(\d+[A-Za-z]?)", hit.text, re.I)
        return bool(number and number.group(1).casefold() in {n.casefold() for n in requested_tables})

    for hit in sorted(local, key=lambda c: not explicitly_cited(c)):
        if not _is_table_caption(hit.text):
            continue
        index = positions[hit.chunk_id]
        fragments = _table_fragments(cited_chunks, index)
        if not fragments:
            continue
        with EvidenceRetriever(fragments) as table_retriever:
            rows = table_retriever.search(build_claim_query(claim), claim.claim_id, len(fragments))
        # The first fragment is a header only if it has no numeric values.
        # Ranking rows separately avoids preferring the first model/config in
        # a table, and also retrieves counter-evidence for incorrect values.
        header = fragments[0] if not re.search(r"\d", fragments[0].content) else None
        ordered = [hit]
        if header is not None:
            ordered.append(EvidenceCandidate(
                evidence_id=f"{claim.claim_id}_context", chunk_id=header.chunk_id,
                page=header.page, text=header.content, score=hit.score,
            ))
        ordered.extend(rows)
        ordered.extend(local)
        additions: list[EvidenceCandidate] = []
        seen = set(global_seed_ids)
        for candidate in ordered:
            if candidate.chunk_id not in seen:
                additions.append(candidate)
                seen.add(candidate.chunk_id)
            if len(additions) == 3:
                break
        return additions
    return [candidate for candidate in local if candidate.chunk_id not in global_seed_ids][:3]


def budget_claim_evidence(
    claim_id: str, candidates: Iterable[EvidenceCandidate], *,
    max_candidates: int = 10, max_chars: int = 18_000,
) -> list[EvidenceCandidate]:
    """Keep whole local passages under one shared count and text budget."""
    if max_candidates < 1 or max_chars < 1:
        raise ValueError("Candidate count and character budgets must be positive.")
    result: list[EvidenceCandidate] = []
    seen: set[str] = set()
    chars = 0
    for candidate in candidates:
        if candidate.chunk_id in seen:
            continue
        seen.add(candidate.chunk_id)
        if chars + len(candidate.text) > max_chars:
            continue
        result.append(candidate.model_copy(update={"evidence_id": f"{claim_id}_e{len(result) + 1}"}))
        chars += len(candidate.text)
        if len(result) == max_candidates:
            break
    return result


def retrieve_claim_evidence(
    retriever: EvidenceRetriever, claim: AtomicClaim, chunks: list[PaperChunk], *,
    strategy: str, seed_limit: int = 5, max_chars: int = 18_000,
) -> list[EvidenceCandidate]:
    """Compare lexical, structural-first and mixed expansion with equal caps.

    All strategies start with the same ranked seed. Structural takes up to five
    neighbors before lexical backfill; hybrid reserves three of those five
    additional slots for lexical results and two for neighbors. No gold data is
    involved in selection.
    """
    if strategy not in {"plain", "structural", "hybrid", "cited"}:
        raise ValueError(f"Unknown retrieval strategy: {strategy}")
    if seed_limit < 1:
        raise ValueError("seed_limit must be positive")
    ranked = retriever.search(build_claim_query(claim), claim.claim_id, seed_limit + 5)
    seeds = ranked[:seed_limit]
    if strategy == "plain":
        ordered = ranked
    elif strategy == "cited":
        # A report citation is a search hint, never proof of support. Keep the
        # global seed even when the report points at an unrelated/invalid page.
        pages = report_evidence_pages(claim.provided_evidence)
        cited_chunks = [chunk for chunk in chunks if chunk.page in pages]
        additions: list[EvidenceCandidate] = []
        if cited_chunks:
            seed_ids = {candidate.chunk_id for candidate in seeds}
            with EvidenceRetriever(cited_chunks) as cited_retriever:
                local = cited_retriever.search(
                    build_claim_query(claim), claim.claim_id, seed_limit + 3
                )
            # A table caption/header often wins lexical ranking while its row
            # carries the value needed by the claim. Complete cited-page
            # table regions first so ordinary prose cannot consume the local
            # expansion budget.
            additions = _cited_table_candidates(
                claim,
                cited_chunks,
                local,
                seed_ids,
            )
        ordered = seeds + additions + ranked[seed_limit:]
    elif strategy == "structural":
        ordered = expand_claim_evidence(claim, chunks, seeds) + ranked[seed_limit:]
    else:
        lexical = ranked[:seed_limit + 3]
        # Expand original seeds; ignore neighbors already included lexically.
        neighbors = expand_claim_evidence(claim, chunks, seeds, max_additions=10)[len(seeds):]
        lexical_ids = {candidate.chunk_id for candidate in lexical}
        additions = [candidate for candidate in neighbors if candidate.chunk_id not in lexical_ids][:2]
        ordered = lexical + additions + ranked[seed_limit + 3:]
    return budget_claim_evidence(
        claim.claim_id, ordered, max_candidates=seed_limit + 5, max_chars=max_chars,
    )


def supplement_claim_evidence(
    claim: AtomicClaim, chunks: list[PaperChunk], candidates: list[EvidenceCandidate],
) -> list[EvidenceCandidate]:
    """Add at most five local chunks, preserving all existing evidence IDs."""
    existing = {item.chunk_id for item in candidates}
    pages = report_evidence_pages(claim.provided_evidence)
    cited = [chunk for chunk in chunks if chunk.page in pages and chunk.chunk_id not in existing]
    additions = []
    if cited:
        with EvidenceRetriever(cited) as retriever:
            additions = retriever.search(claim.query_en, claim.claim_id, 5)
    # Search beyond the original top-k; do not simply rejudge the same pool.
    remaining = [chunk for chunk in chunks if chunk.chunk_id not in existing | {c.chunk_id for c in additions}]
    if len(additions) < 5 and remaining:
        with EvidenceRetriever(remaining) as retriever:
            additions.extend(retriever.search(claim.query_en, claim.claim_id, 5 - len(additions)))
    return candidates + [item.model_copy(update={
        "evidence_id": f"{claim.claim_id}_e{len(candidates) + index + 1}",
    }) for index, item in enumerate(additions)]


class EvidenceRetriever:
    def __init__(self, chunks: list[PaperChunk]):
        self._chunks = chunks
        self._abstract_chunk_ids = _abstract_chunk_ids(chunks)
        self._connection = sqlite3.connect(":memory:")
        self._connection.execute(
            "CREATE VIRTUAL TABLE chunks USING fts5("
            "chunk_id UNINDEXED, page UNINDEXED, content UNINDEXED, search_text, "
            "tokenize='unicode61')"
        )
        self._connection.executemany(
            "INSERT INTO chunks(chunk_id, page, content, search_text) VALUES (?, ?, ?, ?)",
            [
                (chunk.chunk_id, chunk.page, chunk.content, _search_text(chunk.content))
                for chunk in chunks
            ],
        )

    def close(self) -> None:
        self._connection.close()

    def search(self, query: str, claim_id: str, limit: int = 5) -> list[EvidenceCandidate]:
        terms = _query_terms([query])
        if not terms:
            return []

        fts_query = " OR ".join(f'"{term.replace(chr(34), chr(34) * 2)}"' for term in terms)
        rows = self._connection.execute(
            "SELECT chunk_id, page, content, bm25(chunks) AS rank "
            "FROM chunks WHERE chunks MATCH ? ORDER BY rank LIMIT ?",
            # Keep a broad first-stage pool: long abstract blocks can have a poor
            # BM25 rank even when they contain the exact evidence sentence.
            (fts_query, max(limit * 50, 500)),
        ).fetchall()

        query_term_set = set(terms)
        if query_term_set & _ATTRIBUTION_TERMS:
            row_ids = {str(row[0]) for row in rows}
            abstract_seen = False
            for chunk in self._chunks:
                if chunk.page != 1:
                    continue
                if "abstract" in chunk.content.casefold():
                    abstract_seen = True
                if not abstract_seen and _looks_like_author_block(chunk.content) and chunk.chunk_id not in row_ids:
                    rows.append((chunk.chunk_id, chunk.page, chunk.content, 0.0))
        row_ids = {str(row[0]) for row in rows}
        for chunk in self._chunks:
            if chunk.chunk_id in self._abstract_chunk_ids and chunk.chunk_id not in row_ids:
                rows.append((chunk.chunk_id, chunk.page, chunk.content, 0.0))

        ranked: list[tuple[float, str, int, str]] = []
        exact_values = [term for term in terms if any(char.isdigit() for char in term)]
        query_text = _normalize_for_search(query)
        bm25_scores = [-float(row[3]) for row in rows]
        bm25_min = min(bm25_scores, default=0.0)
        bm25_max = max(bm25_scores, default=0.0)
        for chunk_id, page, content, rank in rows:
            normalized_content = _normalize_for_search(content)
            content_terms = _content_terms(normalized_content)
            coverage = sum(_term_matches(term, content_terms) for term in set(terms)) / max(
                len(set(terms)), 1
            )
            exact_ratio = (
                sum(1 for value in exact_values if value in normalized_content) / len(exact_values)
                if exact_values
                else 0.0
            )
            bm25_value = -float(rank)
            bm25_ratio = (
                (bm25_value - bm25_min) / (bm25_max - bm25_min)
                if bm25_max > bm25_min
                else 1.0
            )
            phrase_bonus = 1.0 if query_text and query_text in normalized_content else 0.0
            context_terms = [term for term in terms if term not in exact_values]
            context_hits = sum(_term_matches(term, content_terms) for term in set(context_terms))
            context_anchor = 1.0 if context_hits >= 2 else 0.0
            metric_number_anchor = (
                1.0
                if _has_metric_number_anchor(normalized_content, query_term_set, content_terms)
                else 0.0
            )
            resource_anchor = 1.0 if _has_resource_anchor(query_term_set, content_terms) else 0.0
            config_resource_pair = 1.0 if _has_config_resource_pair(normalized_content, query_term_set) else 0.0
            front_matter_bonus = 0.0
            if query_term_set & _ATTRIBUTION_TERMS and int(page) == 1 and _looks_like_author_block(content):
                front_matter_bonus = 0.6
            abstract_bonus = 0.4 if chunk_id in self._abstract_chunk_ids else 0.0
            score = (
                coverage * 0.55
                + exact_ratio * 0.1
                + context_anchor * 0.25
                + metric_number_anchor * 0.25
                + resource_anchor * 0.2
                + config_resource_pair * 0.3
                + bm25_ratio * 0.05
                + phrase_bonus * 0.05
                + front_matter_bonus
                + abstract_bonus
            )
            ranked.append((score, chunk_id, int(page), content))
        ranked.sort(key=lambda item: item[0], reverse=True)

        return [
            EvidenceCandidate(
                evidence_id=f"{claim_id}_e{index + 1}",
                chunk_id=chunk_id,
                page=page,
                text=content,
                score=round(score, 6),
            )
            for index, (score, chunk_id, page, content) in enumerate(ranked[:limit])
        ]

    def __enter__(self) -> "EvidenceRetriever":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
