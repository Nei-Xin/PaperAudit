from paperaudit.models import AtomicClaim, ClaimCategory, PaperChunk
from paperaudit.retrieval import EvidenceRetriever, build_claim_query


def test_retrieval_finds_numeric_evidence() -> None:
    chunks = [
        PaperChunk(chunk_id="p1_b1", page=1, content="The introduction presents the problem."),
        PaperChunk(
            chunk_id="p3_b2",
            page=3,
            content="On Dataset A, our method improves F1 by 3.2 points over the baseline.",
        ),
    ]
    claim = AtomicClaim(
        claim_id="C001",
        text="该方法在 Dataset A 上将 F1 提升了 3.2 个点。",
        category=ClaimCategory.RESULTS,
        key_claim=True,
        query_en="Dataset A method improves F1 3.2 points",
        entities=["Dataset A"],
        numbers=["3.2"],
        metric="F1",
        dataset="Dataset A",
    )

    with EvidenceRetriever(chunks) as retriever:
        results = retriever.search(build_claim_query(claim), claim.claim_id, limit=1)

    assert len(results) == 1
    assert results[0].chunk_id == "p3_b2"
    assert results[0].page == 3

