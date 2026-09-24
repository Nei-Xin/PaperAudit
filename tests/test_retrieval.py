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


def test_retrieval_prioritizes_context_for_wrong_numeric_value() -> None:
    chunks = [
        PaperChunk(chunk_id="p1_b4", page=1, content="On ImageNet, our residual nets achieve 3.57% error."),
        PaperChunk(chunk_id="p1_b5", page=1, content="On COCO, we obtain a 28% relative improvement."),
    ]
    with EvidenceRetriever(chunks) as retriever:
        results = retriever.search("ResNet ImageNet error 28 percent", "C001", limit=1)
    assert results[0].chunk_id == "p1_b4"


def test_retrieval_includes_author_block_for_attribution_query() -> None:
    chunks = [
        PaperChunk(chunk_id="p1_b1", page=1, content="Transformer"),
        PaperChunk(chunk_id="p1_b2", page=1, content="Ashish Vaswani\nNoam Shazeer"),
        PaperChunk(chunk_id="p1_b3", page=1, content="Abstract\nThe model is based on attention."),
    ]
    with EvidenceRetriever(chunks) as retriever:
        results = retriever.search("Transformer proposed by BERT team", "C002", limit=1)
    assert results[0].chunk_id == "p1_b2"


def test_retrieval_prioritizes_substantive_abstract_evidence() -> None:
    chunks = [
        PaperChunk(chunk_id="p1_b1", page=1, content="Abstract"),
        PaperChunk(
            chunk_id="p1_b2",
            page=1,
            content="We evaluate the method on seven games and outperform prior approaches on six.",
        ),
        PaperChunk(chunk_id="p1_b3", page=1, content="1 Introduction"),
        PaperChunk(
            chunk_id="p4_b1",
            page=4,
            content="Prior approaches use several handcrafted features for the games.",
        ),
    ]
    with EvidenceRetriever(chunks) as retriever:
        results = retriever.search(
            "method outperforms prior approaches on all seven games", "C003", limit=1
        )
    assert results[0].chunk_id == "p1_b2"


def test_retrieval_prioritizes_matching_resource_configuration() -> None:
    chunks = [
        PaperChunk(chunk_id="p2_b1", page=2, content="The model achieves strong accuracy."),
        PaperChunk(
            chunk_id="p4_b1",
            page=4,
            content="We train the LARGE model on 128 V100 GPUs over 2.3 days.",
        ),
    ]
    with EvidenceRetriever(chunks) as retriever:
        results = retriever.search("LARGE model training GPU resources", "C004", limit=1)
    assert results[0].chunk_id == "p4_b1"


def test_retrieval_matches_configuration_entity_to_nearby_resource() -> None:
    chunks = [
        PaperChunk(
            chunk_id="p4_b1",
            page=4,
            content="The BASE model uses 64 V100 GPUs. The LARGE model uses 128 V100 GPUs.",
        ),
        PaperChunk(
            chunk_id="p5_b1",
            page=5,
            content="The LARGE model has 24 blocks and 16 attention heads.",
        ),
    ]
    with EvidenceRetriever(chunks) as retriever:
        results = retriever.search("LARGE model training GPU", "C005", limit=1)
    assert results[0].chunk_id == "p4_b1"


def test_retrieval_boosts_formula_blocks_for_equation_queries() -> None:
    chunks = [
        PaperChunk(
            chunk_id="p3_formula",
            page=3,
            content="The objective loss L = sum_i (y_i - f(x_i))^2.",
            content_type="formula",
        ),
        PaperChunk(
            chunk_id="p3_text",
            page=3,
            content="The objective is optimized during training.",
        ),
    ]
    with EvidenceRetriever(chunks) as retriever:
        results = retriever.search("equation objective loss", "C006", limit=1)
    assert results[0].chunk_id == "p3_formula"


def test_retrieval_recovers_cross_page_table_continuation() -> None:
    chunks = [
        PaperChunk(
            chunk_id="p4_caption",
            page=4,
            content="Table 2 Results",
            content_type="table",
        ),
        PaperChunk(
            chunk_id="p5_row",
            page=5,
            content="Ours 91.2 accuracy on Dataset Z",
            content_type="table",
        ),
        PaperChunk(
            chunk_id="p6_unrelated",
            page=6,
            content="Ablation details are discussed separately.",
        ),
    ]
    with EvidenceRetriever(chunks) as retriever:
        results = retriever.search("Table 2 Dataset Z accuracy", "C007", limit=2)
    assert {result.chunk_id for result in results} == {"p4_caption", "p5_row"}
