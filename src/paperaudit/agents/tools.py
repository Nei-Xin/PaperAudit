"""Read-only tools bound to one parsed paper; all locators come from the index."""

import re

from paperaudit.models import AtomicClaim, EvidenceCandidate, ParsedPaper
from paperaudit.retrieval import EvidenceRetriever, _cited_table_candidates, _is_table_fragment, build_claim_query

from .models import InvestigationAction


def _row_context(chunks, ranked, candidates):
    """Recover separately parsed labels beside observed, compact numeric rows.

    Geometry only prioritizes original blocks for review; it never constructs
    a synthetic table or establishes that a label belongs to a value.
    """
    observed = {c.chunk_id for c in candidates}
    indexed = {c.chunk_id: c for c in chunks}
    result, seen = [], set(observed)
    for hit in ranked:
        row = indexed[hit.chunk_id]
        if row.chunk_id not in observed or not row.rects or not _is_table_fragment(row.content):
            continue
        top, bottom = min(r.y0 for r in row.rects), max(r.y1 for r in row.rects)
        if bottom - top > 20 or not re.search(r"\d", row.content):
            continue
        left, right = min(r.x0 for r in row.rects), max(r.x1 for r in row.rects)
        for chunk in chunks:
            if chunk.chunk_id in seen or not chunk.rects or len(chunk.content) > 200:
                continue
            ctop, cbottom = min(r.y0 for r in chunk.rects), max(r.y1 for r in chunk.rects)
            cleft, cright = min(r.x0 for r in chunk.rects), max(r.x1 for r in chunk.rects)
            overlap = min(bottom, cbottom) - max(top, ctop)
            horizontal_gap = max(left - cright, cleft - right, 0)
            if (0 < cbottom - ctop <= 20 and overlap >= .7 * min(bottom - top, cbottom - ctop)
                    and horizontal_gap <= 100):
                result.append(EvidenceCandidate(evidence_id="pending", chunk_id=chunk.chunk_id,
                                                page=chunk.page, text=chunk.content, score=hit.score))
                seen.add(chunk.chunk_id)
                if len(result) == 3:
                    return result
    return result


def execute_tool(action: InvestigationAction, paper: ParsedPaper, claim: AtomicClaim,
                 candidates: list[EvidenceCandidate]) -> list[EvidenceCandidate]:
    if action.tool == "search_paper":
        with EvidenceRetriever(paper.chunks) as retriever:
            return retriever.search(action.query.strip(), claim.claim_id, limit=12)
    if action.tool == "read_page":
        if action.page > paper.page_count:
            raise ValueError("Page outside current paper")
        chunks = [chunk for chunk in paper.chunks if chunk.page == action.page]
        # A page can contain dozens of blocks. Spend the five-new-block budget
        # on relevant rows/headers rather than the first blocks in PDF order.
        # Keep every original block as fallback; ranking is never evidence of
        # support and does not change the quoted text or its location.
        with EvidenceRetriever(chunks) as retriever:
            ranked = retriever.search(build_claim_query(claim), claim.claim_id, len(chunks))
        table = _cited_table_candidates(
            claim, chunks, ranked, {candidate.chunk_id for candidate in candidates},
        )
        fallback = [EvidenceCandidate(evidence_id="pending", chunk_id=chunk.chunk_id,
                                      page=chunk.page, text=chunk.content, score=0)
                    for chunk in chunks]
        return _row_context(chunks, ranked, candidates) + table + ranked + fallback
    elif action.tool == "expand_context":
        if action.chunk_id not in {candidate.chunk_id for candidate in candidates}:
            raise ValueError("Only observed chunks can be expanded")
        index = next((i for i, chunk in enumerate(paper.chunks)
                      if chunk.chunk_id == action.chunk_id), None)
        if index is None:
            raise ValueError("Unknown chunk")
        chunks = paper.chunks[max(0, index - 2):index + 3]
    else:
        raise ValueError("Not a read tool")
    return [EvidenceCandidate(evidence_id="pending", chunk_id=chunk.chunk_id,
                              page=chunk.page, text=chunk.content, score=0)
            for chunk in chunks]


def append_evidence(claim_id: str, current: list[EvidenceCandidate],
                    found: list[EvidenceCandidate], *, max_candidates: int,
                    max_chars: int) -> tuple[list[EvidenceCandidate], list[str]]:
    """Add at most five whole passages without changing earlier IDs or text."""
    result = list(current)
    seen = {item.chunk_id for item in current}
    ids = {item.evidence_id for item in current}
    chars = sum(len(item.text) for item in current)
    added = []
    index = 1
    for item in found:
        if len(result) >= max_candidates or len(added) >= 5:
            break
        if item.chunk_id in seen or chars + len(item.text) > max_chars:
            continue
        while f"{claim_id}_agent_e{index}" in ids:
            index += 1
        evidence_id = f"{claim_id}_agent_e{index}"
        result.append(item.model_copy(update={"evidence_id": evidence_id}))
        added.append(evidence_id)
        seen.add(item.chunk_id)
        ids.add(evidence_id)
        chars += len(item.text)
    return result, added
