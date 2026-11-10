"""Fixed empirical/theory/survey examples plus live-orchestration contract checks."""
from copy import deepcopy

import pytest

from paperaudit.learning_facts import FactMention, LessonFact, contains_label, contains_quantity, quantity, validate_fact
from paperaudit.learning_generation import (
    LessonPlan, LessonPatch, PointUpdate, LessonReview, LearningQualityError, draft_issues, validate_plan,
)
from scripts.check_lecture_facts import SUITE, evaluate_artifact, evaluate_case, load_case
from test_learning_generation import materials, run, scripted, transport_client


@pytest.mark.parametrize("path", sorted(SUITE.glob("*.json")), ids=lambda p: p.stem)
def test_fixed_ledger_cases(path):
    result = evaluate_case(path)
    assert result["passed"], result


@pytest.mark.parametrize("filename", ["transformer.json", "theory.json", "survey.json"])
def test_real_provider_plan_snapshots_replay_without_model_calls(filename):
    _, sources, _ = load_case(SUITE / filename)
    plan = LessonPlan.model_validate_json((SUITE / "provider_snapshots" / (filename + ".plan.json")).read_text())
    validate_plan(plan, sources)
    facts = [f for s in plan.sections for t in s.topics for f in t.facts]
    assert facts
    if filename == "transformer.json":
        assert {"27.3", "38.1", "28.4", "41.8", "41.0"} <= {f.value for f in facts}
        assert any(f.kind == "cost" and f.value is None and f.status == "ambiguous" for f in facts)
    elif filename == "theory.json":
        assert any(f.source_value == "O(1/T)" for f in facts)
        assert any(s.section_type == "experiments" and not s.topics and s.unavailable_reason for s in plan.sections)


@pytest.mark.parametrize("source,rendered,equal", [
    ("3.3e18", "3.3 × 10^18", True),
    ("3.3e18", "3.3×10¹⁸", True),
    ("3.3e18", "3.3×10^19", False),
    ("0.1", "1e-1", True),
    ("0.1", "10%", False),
    ("38.1", "138.1", False),
    ("38.1", "-38.1", False),
    ("38.1", "38.10", True),
    ("38.1", "38.1e2", False),
    ("3.3e18", "3.3 · 1018", False),
])
def test_quantity_equivalence_keeps_scale_sign_and_exponent(source, rendered, equal):
    assert contains_quantity(f"数值为{rendered}。", source) is equal


def fact_materials():
    chunks, plan, draft = materials()
    chunks[4].content = "Atlas base scores 38.1 BLEU on the French test split."
    fact = LessonFact(fact_id="fr", kind="result", subject="Atlas base", dataset="法语", metric="BLEU",
                      finding="法语测试结果", conditions=["测试集"], value="38.1", source_value="38.1",
                      sources=[{"chunk_id": "results", "quote": chunks[4].content}])
    plan.sections[4].topics[0].facts = [fact]
    point = draft.report.sections[4].points[0]
    point.explanation = "Atlas base 在法语测试集上的 BLEU 为38.1。"
    point.evidence[0].quote = chunks[4].content
    draft.coverage[4].fact_mentions = [FactMention(fact_id="fr", point_index=0, excerpt=point.explanation)]
    return chunks, plan, draft


def test_ledger_survives_generation_without_changing_persisted_report_schema():
    chunks, plan, draft = fact_materials()
    client, requests = transport_client([x.model_dump_json() for x in [plan, draft, LessonReview(issues=[])]])
    report = client.generate_learning_report("Paper", chunks)
    assert len(requests) == 3
    assert '"fact_id": "fr"' in requests[1]["messages"][1]["content"] or '"fact_id":"fr"' in requests[1]["messages"][1]["content"]
    assert "fact_mentions" not in report.model_dump_json()
    assert report.sections[4].points[0].explanation == draft.report.sections[4].points[0].explanation


@pytest.mark.parametrize("damage", ["missing", "duplicate", "wrong_topic", "wrong_point", "fake_excerpt", "wrong_dataset"])
def test_coverage_mapping_cannot_hide_bad_fact(damage):
    chunks, plan, draft = fact_materials()
    coverage = draft.coverage[4]
    if damage == "missing": coverage.fact_mentions = []
    elif damage == "duplicate": coverage.fact_mentions *= 2
    elif damage == "wrong_topic": coverage.fact_mentions[0].fact_id = "unrelated"
    elif damage == "wrong_point": coverage.fact_mentions[0].point_index = 999
    elif damage == "fake_excerpt": draft.report.sections[4].points[0].explanation = "另一个解释。"
    elif damage == "wrong_dataset":
        point = draft.report.sections[4].points[0]
        point.explanation = point.explanation.replace("法语", "德语")
        coverage.fact_mentions[0].excerpt = point.explanation
    assert draft_issues(draft, plan, {c.chunk_id: c for c in chunks})


def test_fact_defect_triggers_selective_repair_even_if_reviewer_misses_it():
    chunks, plan, valid = fact_materials()
    draft = deepcopy(valid)
    draft.report.sections[4].points[0].explanation = "Atlas base 在法语测试集上的 BLEU 未说明。"
    draft.coverage[4].fact_mentions[0].excerpt = draft.report.sections[4].points[0].explanation
    patch = LessonPatch(point_updates=[PointUpdate(section_type="results", point_index=0, point=valid.report.sections[4].points[0])], coverage=[valid.coverage[4]])
    call, calls = scripted([plan, draft, LessonReview(issues=[]), patch, LessonReview(issues=[])])
    result = run(call, chunks)
    assert result == valid.report
    assert len(calls) == 5
    # Re-review sees the concrete defect, rather than starting from a fresh standard.
    assert "missing_value" in calls[4][0]
    assert "untrusted_previous_issues" in calls[4][0]


@pytest.mark.parametrize("damage", ["unknown_source", "wrong_quote", "wrong_exponent", "wrong_source_value", "duplicate_id", "empty_subject"])
def test_bad_fact_ledger_stops_before_draft_generation(damage):
    chunks, plan, _ = fact_materials()
    fact = plan.sections[4].topics[0].facts[0]
    if damage == "unknown_source": fact.sources[0].chunk_id = "missing"
    elif damage == "wrong_quote": fact.sources[0].quote = "Fabricated quotation here."
    elif damage == "wrong_exponent": fact.value = "38.1e2"
    elif damage == "wrong_source_value": fact.source_value = fact.value = "8.1"
    elif damage == "duplicate_id": plan.sections[2].topics[0].facts.append(deepcopy(fact))
    elif damage == "empty_subject": fact.subject = " "
    with pytest.raises(LearningQualityError):
        validate_plan(plan, {c.chunk_id: c for c in chunks})


def test_flattened_exponent_cannot_be_normalized_by_guessing():
    case, sources, facts = load_case(SUITE / "transformer.json")
    cost = facts["base_cost"].model_copy(update={"value": "3.3e18"})
    assert any(e.code == "value_not_grounded" for e in validate_fact(cost, sources))
    assert quantity("3.3 · 1018") is None


def test_raw_source_value_remains_literal_while_rendered_value_may_be_equivalent():
    _, sources, facts = load_case(SUITE / "scientific.json")
    fact = facts["cost_exact"].model_copy(update={"source_value": "3.3e18"})
    assert any(e.code == "source_value_absent" for e in validate_fact(fact, sources))


def test_assignment_is_not_a_license_to_pick_any_number_from_source():
    _, sources, facts = load_case(SUITE / "transformer.json")
    fact = facts["warmup_assignment"]
    assert validate_fact(fact, sources) == []
    wrong = fact.model_copy(update={"source_value": "linearly for the first warmup_steps training steps,", "value": "4000"})
    assert any(e.code == "value_not_grounded" for e in validate_fact(wrong, sources))


def test_symbolic_theorem_does_not_require_a_fabricated_empirical_value():
    _, sources, facts = load_case(SUITE / "theory.json")
    bound = facts["symbolic_bound"]
    assert validate_fact(bound, sources) == []
    assert validate_fact(bound.model_copy(update={"value": None}), sources) == []
    assert any(e.code == "value_not_grounded" for e in validate_fact(bound.model_copy(update={"value": "0.01"}), sources))


def test_canonical_labels_do_not_accept_different_named_model_or_optimizer():
    assert not contains_label("采用 AdamW。", "Adam")
    assert not contains_label("在 Set-AB 上测试。", "Set-A")
    assert contains_label("Transformer base 的结果为38.1BLEU。", "Transformer base")
    assert contains_label("结果为38.1BLEU。", "BLEU")


def test_fixed_gold_prevents_model_from_redefining_wrong_bindings_or_omitting_facts():
    path = SUITE / "scientific.json"
    case, _, facts = load_case(path)
    mentions = []
    for fact in facts.values():
        positive = next(e for e in case["examples"] if e["fact_id"] == fact.fact_id and not e["expected_codes"])
        mentions.append({"fact_id": fact.fact_id, "explanation": positive["explanation"],
                         "excerpt": positive["excerpt"], "cited_chunk_ids": [s.chunk_id for s in fact.sources]})
    artifact = {"facts": [f.model_dump() for f in facts.values()], "mentions": mentions}
    assert evaluate_artifact(path, artifact)["passed"]
    wrong = deepcopy(artifact)
    wrong["facts"][0]["dataset"] = "Set-B"
    assert not evaluate_artifact(path, wrong)["passed"]
    missing = deepcopy(artifact)
    missing["facts"].pop()
    assert not evaluate_artifact(path, missing)["passed"]
    assert not evaluate_artifact(path, {"facts": [], "mentions": []})["passed"]


def test_rejected_full_paper_provider_facts_remain_rejected_without_rewriting_response():
    import json
    from paperaudit.models import PaperChunk
    snapshot = json.loads((SUITE / "provider_snapshots/transformer-rejected-facts.json").read_text())
    assert len(snapshot["cases"]) == 5
    for case in snapshot["cases"]:
        sources = {c["chunk_id"]: PaperChunk.model_validate(c) for c in case["sources"]}
        fact = LessonFact.model_validate(case["fact"])
        assert sorted({e.code for e in validate_fact(fact, sources)}) == case["expected_codes"]


@pytest.mark.parametrize("expression", ["1/√dk", "O(n2 · d)", "O(n × d)", "1/√d_k"])
def test_verbatim_symbolic_operators_are_retained_without_interpreting_typography(expression):
    from paperaudit.models import PaperChunk
    quote = f"The literal expression is {expression}."
    sources = {"math": PaperChunk(chunk_id="math", page=1, content=quote)}
    fact = LessonFact(fact_id="math", kind="mechanism", subject="公式", finding="按原文保留表达式",
                      source_value=expression, value=expression, sources=[{"chunk_id": "math", "quote": quote}])
    assert validate_fact(fact, sources) == []
    mention = FactMention(fact_id="math", point_index=0, excerpt=f"公式保留为 {expression}。")
    from paperaudit.learning_facts import check_mention
    assert check_mention(fact, mention, mention.excerpt, {"math"}) == []


def test_symbolic_operator_support_does_not_reconstruct_a_missing_fraction_bar():
    from paperaudit.models import PaperChunk
    quote = "The factor is 1\n√dk in the extracted text."
    sources = {"math": PaperChunk(chunk_id="math", page=1, content=quote)}
    fact = LessonFact(fact_id="math", kind="mechanism", subject="公式", finding="抽取的表达式",
                      source_value="1\n√dk", value="1/√dk", sources=[{"chunk_id": "math", "quote": quote}])
    assert {e.code for e in validate_fact(fact, sources)} == {"value_not_grounded"}
    fact.source_value = "1/√dk"
    assert {e.code for e in validate_fact(fact, sources)} == {"source_value_absent"}
