from __future__ import annotations

import re
import sqlite3
from collections.abc import Iterable

from .models import AtomicClaim, EvidenceCandidate, PaperChunk


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
