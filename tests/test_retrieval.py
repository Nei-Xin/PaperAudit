from paperaudit.models import AtomicClaim, ClaimCategory, PaperChunk
from paperaudit.retrieval import EvidenceRetriever, build_claim_query, expand_claim_evidence


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


def test_formula_context_recovers_unsearchable_equation_from_legacy_index() -> None:
    chunks = [
        PaperChunk(
            chunk_id="p3_formula",
            page=3,
            content="L = ∑ (y - x)²",
        ),
        PaperChunk(
            chunk_id="p3_text",
            page=3,
            content="The objective is optimized during training.",
        ),
    ]
    with EvidenceRetriever(chunks) as retriever:
        results = retriever.search("equation objective loss", "C006", limit=1)
    assert results[0].chunk_id == "p3_text"
    claim = AtomicClaim(claim_id="C006", text="平方误差目标", category=ClaimCategory.METHOD,
                        query_en="equation objective loss")
    expanded = expand_claim_evidence(claim, chunks, results)
    assert expanded[0] == results[0]
    assert expanded[1].chunk_id == "p3_formula"
    assert expanded[1].text == chunks[0].content
    assert expanded[1].evidence_id == "C006_e2"


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
            content="Ours 91.2 8.8",
            content_type="table",
        ),
        PaperChunk(
            chunk_id="p6_unrelated",
            page=6,
            content="Ablation details are discussed separately.",
        ),
    ]
    with EvidenceRetriever(chunks) as retriever:
        results = retriever.search("Table 2 results", "C007", limit=1)
    claim = AtomicClaim(claim_id="C007", text="表2结果", category=ClaimCategory.RESULTS,
                        query_en="Table 2 results")
    expanded = expand_claim_evidence(claim, chunks, results)
    assert expanded[:len(results)] == results
    assert [result.chunk_id for result in expanded] == ["p4_caption", "p5_row"]
    assert expanded[1].page == 5
    assert expanded[1].text == chunks[1].content


def test_context_is_bounded_deduplicated_and_does_not_join_distant_pages() -> None:
    chunks = [
        PaperChunk(chunk_id=f"p{page}", page=page, content=f"Table {page}: Results")
        for page in (1, 2, 9)
    ]
    claim = AtomicClaim(claim_id="C", text="表1", category=ClaimCategory.RESULTS,
                        query_en="Table 1 results")
    with EvidenceRetriever(chunks) as retriever:
        seed = retriever.search(claim.query_en, "C", limit=1)
    # Appending to IDs with gaps must not create duplicate evidence IDs.
    seed = [seed[0].model_copy(update={"evidence_id": "C_e2"})]
    expanded = expand_claim_evidence(claim, chunks, seed, max_additions=1)
    assert [c.chunk_id for c in expanded] == ["p1", "p2"]
    assert len({c.evidence_id for c in expanded}) == 2
    assert expand_claim_evidence(claim, chunks, expanded) == expanded
    assert expand_claim_evidence(claim, chunks, []) == []
    assert expand_claim_evidence(claim, chunks, seed, max_additions=0) == seed


def test_cross_page_prose_requires_continuation_not_just_proximity() -> None:
    claim = AtomicClaim(claim_id="C", text="收敛前提", category=ClaimCategory.METHOD,
                        query_en="convergence assumptions")
    chunks = [
        PaperChunk(chunk_id="a", page=2, content="The convergence assumptions require"),
        PaperChunk(chunk_id="b", page=3, content="a bounded gradient and smooth loss."),
        PaperChunk(chunk_id="c", page=4, content="Unrelated experiment overview."),
    ]
    with EvidenceRetriever(chunks) as retriever:
        seed = retriever.search(claim.query_en, "C", limit=1)
    expanded = expand_claim_evidence(claim, chunks, seed)
    assert [c.chunk_id for c in expanded] == ["a", "b"]
    assert expand_claim_evidence(claim, chunks, expanded) == expanded


def test_structure_alone_cannot_produce_candidates_for_an_unmatched_query() -> None:
    chunks = [
        PaperChunk(chunk_id="a", page=2, content="L = ∑ (y - x)²", content_type="formula"),
        PaperChunk(chunk_id="b", page=3, content="Table 2: Scores", content_type="table"),
    ]
    with EvidenceRetriever(chunks) as retriever:
        assert retriever.search("constraint quaternion", "C") == []


def test_budget_preserves_whole_passages_deduplicates_and_backfills():
    from paperaudit.models import EvidenceCandidate
    from paperaudit.retrieval import budget_claim_evidence
    def candidate(cid, text):
        return EvidenceCandidate(evidence_id='old', chunk_id=cid, page=3, text=text, score=1)
    a, b, c = candidate('a', '1234'), candidate('b', 'long passage'), candidate('c', '5678')
    result = budget_claim_evidence('C', [a, a, b, c], max_candidates=2, max_chars=8)
    assert [r.chunk_id for r in result] == ['a', 'c']
    assert [r.evidence_id for r in result] == ['C_e1', 'C_e2']
    assert [r.text for r in result] == ['1234', '5678']
    assert a.evidence_id == 'old'


def test_all_strategies_have_equal_caps_and_keep_ranked_seeds():
    from paperaudit.models import EvidenceCandidate
    from paperaudit.retrieval import retrieve_claim_evidence
    # Lexical results alternate with unsearchable formulas in document order.
    chunks = []
    for index in range(12):
        chunks.extend([
            PaperChunk(chunk_id=f't{index}', page=2, content=f'Model result {index}.'),
            PaperChunk(chunk_id=f'f{index}', page=2, content='L = ∑ (y - x)²'),
        ])
    ranked = [EvidenceCandidate(evidence_id=f'C_e{i+1}', chunk_id=f't{i}', page=2,
                               text=chunks[i*2].content, score=1-i/100) for i in range(12)]
    class Retriever:
        def search(self, query, claim_id, limit):
            return ranked[:limit]
    claim = AtomicClaim(claim_id='C', text='结果', category=ClaimCategory.RESULTS, query_en='result')
    pools = {arm: retrieve_claim_evidence(Retriever(), claim, chunks, strategy=arm)
             for arm in ('plain', 'structural', 'hybrid')}
    for pool in pools.values():
        assert pool[:5] == ranked[:5]
        assert len(pool) == len({c.chunk_id for c in pool}) == 10
        assert [c.evidence_id for c in pool] == [f'C_e{i}' for i in range(1, 11)]
    assert all(c.chunk_id.startswith('t') for c in pools['plain'])
    assert all(c.chunk_id.startswith('f') for c in pools['structural'][5:])
    assert [c.chunk_id for c in pools['hybrid'][:8]] == [f't{i}' for i in range(8)]
    assert all(c.chunk_id.startswith('f') for c in pools['hybrid'][8:])


def test_cited_page_retrieval_finds_comparison_row_without_displacing_seeds():
    from paperaudit.retrieval import retrieve_claim_evidence
    chunks = [PaperChunk(chunk_id=f'd{i}', page=1, content='The ModelZ DatasetR comparison overview.') for i in range(16)]
    chunks += [
        PaperChunk(chunk_id='caption', page=3, content='Table 2: ModelZ 82.4 on DatasetR, compared with BaseA.'),
        PaperChunk(chunk_id='row', page=3, content='BaseA\n73.2\n71.4'),
        PaperChunk(chunk_id='header', page=3, content='DatasetR accuracy'),
    ]
    claim = AtomicClaim(claim_id='C', text='结果比较', category=ClaimCategory.RESULTS,
                        query_en='ModelZ DatasetR compared BaseA 82.4 73.2', provided_evidence='论文第3页表2')
    with EvidenceRetriever(chunks) as retriever:
        baseline = retrieve_claim_evidence(retriever, claim, chunks, strategy='plain')
        result = retrieve_claim_evidence(retriever, claim, chunks, strategy='cited')
    assert result[:5] == baseline[:5]
    assert 'row' not in {c.chunk_id for c in baseline}
    assert 'row' in {c.chunk_id for c in result}
    assert len(result) <= 10
    assert len({c.chunk_id for c in result}) == len(result)
    assert [c.evidence_id for c in result] == [f'C_e{i+1}' for i in range(len(result))]
    source = {c.chunk_id: c for c in chunks}
    assert all(c.page == source[c.chunk_id].page and c.text == source[c.chunk_id].content for c in result)


def test_invalid_absent_or_unmatched_citation_does_not_replace_global_evidence():
    from paperaudit.retrieval import retrieve_claim_evidence
    chunks = [PaperChunk(chunk_id=f'd{i}', page=2, content=f'Gradient training settings {i}.') for i in range(12)]
    chunks.append(PaperChunk(chunk_id='unrelated', page=3, content='zebra habitat'))
    claim = AtomicClaim(claim_id='C', text='训练', category=ClaimCategory.METHOD, query_en='Gradient training settings')
    with EvidenceRetriever(chunks) as retriever:
        baseline = retrieve_claim_evidence(retriever, claim, chunks, strategy='plain')
        for anchor in (None, '第999页', 'Table 3', '第3页'):
            changed = claim.model_copy(update={'provided_evidence': anchor})
            assert retrieve_claim_evidence(retriever, changed, chunks, strategy='cited') == baseline


def test_wrong_cited_page_is_only_a_hint_and_budget_remains_shared():
    from paperaudit.retrieval import retrieve_claim_evidence
    chunks = [PaperChunk(chunk_id=f't{i}', page=2, content=f'Optimization learning algorithm exact result {i}.') for i in range(10)]
    chunks += [PaperChunk(chunk_id=f'c{i}', page=3, content=f'Historical optimization proposal {i}.') for i in range(4)]
    claim = AtomicClaim(claim_id='C', text='优化方法', category=ClaimCategory.METHOD,
                        query_en='Optimization learning algorithm exact result', provided_evidence='第3页')
    with EvidenceRetriever(chunks) as retriever:
        baseline = retrieve_claim_evidence(retriever, claim, chunks, strategy='plain')
        result = retrieve_claim_evidence(retriever, claim, chunks, strategy='cited')
        bounded = retrieve_claim_evidence(retriever, claim, chunks, strategy='cited', max_chars=230)
    assert result[:5] == baseline[:5]
    assert sum(c.page == 3 for c in result) <= 3
    assert sum(len(c.text) for c in bounded) <= 230
