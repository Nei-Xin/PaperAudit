from __future__ import annotations

import re
import sqlite3

from .models import CodeCandidate, CodeChunk


_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in",
    "is", "it", "of", "on", "or", "that", "the", "this", "to", "was", "were", "with",
}


def _terms(query: str) -> list[str]:
    values = re.findall(r"[A-Za-z_][A-Za-z0-9_./-]*|\d+(?:\.\d+)?", query)
    return list(
        dict.fromkeys(
            value.lower()
            for value in values
            if value.lower() not in _STOPWORDS and len(value) > 1
        )
    )[:40]


class CodeRetriever:
    def __init__(self, chunks: list[CodeChunk]):
        self._connection = sqlite3.connect(":memory:")
        self._connection.execute(
            "CREATE VIRTUAL TABLE code_chunks USING fts5("
            "chunk_id UNINDEXED, path, symbol, content, tokenize='unicode61 tokenchars _')"
        )
        self._connection.executemany(
            "INSERT INTO code_chunks(chunk_id, path, symbol, content) VALUES (?, ?, ?, ?)",
            [(chunk.chunk_id, chunk.path, chunk.symbol or "", chunk.content) for chunk in chunks],
        )
        self._chunk_map = {chunk.chunk_id: chunk for chunk in chunks}

    def search(self, query: str, limit: int = 8) -> list[CodeCandidate]:
        terms = _terms(query)
        if not terms:
            return []
        fts_query = " OR ".join(f'"{term.replace(chr(34), chr(34) * 2)}"' for term in terms)
        rows = self._connection.execute(
            "SELECT chunk_id, path, symbol, content, bm25(code_chunks, 0.0, 1.8, 2.5, 1.0) "
            "AS rank FROM code_chunks WHERE code_chunks MATCH ? ORDER BY rank LIMIT ?",
            (fts_query, max(limit * 3, limit)),
        ).fetchall()
        ranked: list[tuple[float, CodeChunk]] = []
        for chunk_id, path, symbol, content, rank in rows:
            chunk = self._chunk_map[chunk_id]
            lowered_symbol = str(symbol).lower()
            lowered_path = str(path).lower()
            exact_bonus = sum(
                1.0 if term == lowered_symbol else 0.35 if term in lowered_symbol else 0.0
                for term in terms
            )
            path_bonus = sum(0.2 for term in terms if term in lowered_path)
            ranked.append((-float(rank) + exact_bonus + path_bonus, chunk))
        ranked.sort(key=lambda item: item[0], reverse=True)
        return [
            CodeCandidate(
                chunk_id=chunk.chunk_id,
                path=chunk.path,
                language=chunk.language,
                symbol=chunk.symbol,
                start_line=chunk.start_line,
                end_line=chunk.end_line,
                text=chunk.content,
                score=round(score, 6),
            )
            for score, chunk in ranked[:limit]
        ]

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> "CodeRetriever":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
