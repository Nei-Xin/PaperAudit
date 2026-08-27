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


def _query_terms(values: Iterable[str]) -> list[str]:
    terms: list[str] = []
    for value in values:
        for token in re.findall(r"[A-Za-z][A-Za-z0-9_]*|\d+(?:\.\d+)?", value):
            normalized = token.lower()
            if normalized not in _STOPWORDS and (len(normalized) > 1 or normalized.isdigit()):
                terms.append(normalized)
    return list(dict.fromkeys(terms))[:40]


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
        self._connection = sqlite3.connect(":memory:")
        self._connection.execute(
            "CREATE VIRTUAL TABLE chunks USING fts5("
            "chunk_id UNINDEXED, page UNINDEXED, content, tokenize='unicode61')"
        )
        self._connection.executemany(
            "INSERT INTO chunks(chunk_id, page, content) VALUES (?, ?, ?)",
            [(chunk.chunk_id, chunk.page, chunk.content) for chunk in chunks],
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
            (fts_query, max(limit * 3, limit)),
        ).fetchall()

        ranked: list[tuple[float, str, int, str]] = []
        exact_values = [term for term in terms if any(char.isdigit() for char in term)]
        for chunk_id, page, content, rank in rows:
            lowered = content.lower()
            exact_bonus = sum(0.25 for value in exact_values if value in lowered)
            ranked.append((-float(rank) + exact_bonus, chunk_id, int(page), content))
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

