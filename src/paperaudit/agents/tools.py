"""Read-only tools bound to one parsed paper; all locators come from the index."""

from paperaudit.models import AtomicClaim, EvidenceCandidate, ParsedPaper
from paperaudit.retrieval import EvidenceRetriever

from .models import InvestigationAction


def execute_tool(action: InvestigationAction, paper: ParsedPaper, claim: AtomicClaim,
                 candidates: list[EvidenceCandidate]) -> list[EvidenceCandidate]:
    if action.tool == "search_paper":
        with EvidenceRetriever(paper.chunks) as retriever:
            return retriever.search(action.query.strip(), claim.claim_id, limit=12)
    if action.tool == "read_page":
        if action.page > paper.page_count:
            raise ValueError("Page outside current paper")
        chunks = [chunk for chunk in paper.chunks if chunk.page == action.page]
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
