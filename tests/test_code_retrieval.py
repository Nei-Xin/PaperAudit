from __future__ import annotations

from paperaudit.code_retrieval import CodeRetriever
from paperaudit.models import CodeChunk


def test_code_retrieval_prefers_symbol_match() -> None:
    chunks = [
        CodeChunk(
            chunk_id="c1",
            path="agents/director.py",
            language="python",
            symbol="DirectorAgent.select_mode",
            start_line=20,
            end_line=40,
            content="def select_mode(self, poem): return self.mode_selector(poem)",
        ),
        CodeChunk(
            chunk_id="c2",
            path="README.md",
            language="markdown",
            symbol="Usage",
            start_line=1,
            end_line=10,
            content="The director agent is described in the documentation.",
        ),
    ]

    with CodeRetriever(chunks) as retriever:
        results = retriever.search("DirectorAgent select_mode", 2)

    assert results[0].chunk_id == "c1"
    assert results[0].path == "agents/director.py"
    assert results[0].start_line == 20
