"""Bounded fact correction preserves the plan and cannot delete difficult facts."""
from copy import deepcopy

import pytest

from paperaudit.hy3_client import Hy3ResponseError
from paperaudit.learning_generation import (
    FactCorrection, PlanFactPatch, LessonReview, LessonIssue, apply_fact_patch,
    LearningQualityError, validate_plan,
)
from paperaudit.request_budget import RequestBudget, use_request_budget
from test_learning_facts import fact_materials
from test_learning_generation import method_patch, transport_client


def damaged():
    chunks, plan, draft = fact_materials()
    good = deepcopy(plan.sections[4].topics[0].facts[0])
    plan.sections[4].topics[0].facts[0].value = "381"
    patch = PlanFactPatch(corrections=[FactCorrection(
        topic_id="results", fact_id="fr", replacement=good)])
    return chunks, plan, draft, patch


def test_fact_correction_preserves_all_other_plan_bytes_and_inputs():
    chunks, plan, _, patch = damaged()
    # A correct fact in the SAME topic must also survive verbatim.
    sibling = patch.corrections[0].replacement.model_copy(update={"fact_id": "sibling"}, deep=True)
    plan.sections[4].topics[0].facts.append(sibling)
    before = plan.model_dump_json()
    result = apply_fact_patch(plan, patch, {c.chunk_id: c for c in chunks})
    expected = deepcopy(plan)
    expected.sections[4].topics[0].facts[0] = deepcopy(patch.corrections[0].replacement)
    assert result.model_dump_json() == expected.model_dump_json()
    result.sections[4].topics[0].facts[0].finding = "later change"
    assert plan.model_dump_json() == before
    assert patch.corrections[0].replacement.finding != "later change"


@pytest.mark.parametrize("damage", ["empty", "duplicate", "other_topic", "other_id", "kind", "residual"])
def test_invalid_fact_patch_cannot_bypass_checks(damage):
    chunks, plan, _, patch = damaged()
    correction = patch.corrections[0]
    if damage == "empty": patch.corrections = []
    elif damage == "duplicate": patch.corrections *= 2
    elif damage == "other_topic": correction.topic_id = "method"
    elif damage == "other_id": correction.replacement.fact_id = "sibling"
    elif damage == "kind": correction.replacement.kind = "mechanism"
    elif damage == "residual": correction.replacement.value = "999"
    before = plan.model_dump_json()
    with pytest.raises(LearningQualityError):
        apply_fact_patch(plan, patch, {c.chunk_id: c for c in chunks})
    assert plan.model_dump_json() == before


def test_split_fact_gets_collision_free_ids_and_is_checked_against_source():
    chunks, plan, _, patch = damaged()
    existing = deepcopy(patch.corrections[0].replacement)
    existing.fact_id = "fr__split_2"
    plan.sections[4].topics[0].facts.append(existing)
    extra = deepcopy(existing)
    extra.fact_id = "fr"  # Provider IDs cannot overwrite existing facts.
    patch.corrections[0].additional_facts = [extra]
    result = apply_fact_patch(plan, patch, {c.chunk_id: c for c in chunks})
    assert [f.fact_id for f in result.sections[4].topics[0].facts] == ["fr", "fr__split_3", "fr__split_2"]
    extra.value = "999"
    with pytest.raises(LearningQualityError):
        apply_fact_patch(plan, patch, {c.chunk_id: c for c in chunks})


def test_conflicting_fact_cannot_silently_lose_its_group_or_status():
    chunks, plan, _, patch = damaged()
    first = plan.sections[4].topics[0].facts[0]
    first.status, first.conflict_group, first.uncertainty = "conflicting", "scores", "来源冲突"
    other = deepcopy(patch.corrections[0].replacement)
    other.fact_id, other.status, other.conflict_group, other.uncertainty = "fr2", "conflicting", "scores", "来源冲突"
    plan.sections[4].topics[0].facts.append(other)
    with pytest.raises(LearningQualityError, match="不能删减"):
        apply_fact_patch(plan, patch, {c.chunk_id: c for c in chunks})
    patch.corrections[0].replacement = first.model_copy(update={"value": "38.1"}, deep=True)
    validate_plan(apply_fact_patch(plan, patch, {c.chunk_id: c for c in chunks}), {c.chunk_id: c for c in chunks})


def test_one_correction_is_metered_and_corrected_plan_reaches_draft_prompt():
    chunks, plan, draft, patch = damaged()
    client, requests = transport_client([x.model_dump_json() for x in [plan, patch, draft, LessonReview(issues=[])]])
    budget = RequestBudget(max_requests=4)
    with use_request_budget(budget):
        report = client.generate_learning_report("Paper", chunks)
    assert budget.requests == len(requests) == 4
    assert report == draft.report
    assert '"value":"38.1"' in requests[2]["messages"][1]["content"]
    assert '"value":"381"' not in requests[2]["messages"][1]["content"]
    assert 'value_not_grounded' in requests[1]["messages"][1]["content"]


def test_failed_correction_stops_before_draft_without_a_second_correction():
    chunks, plan, _, patch = damaged()
    patch.corrections[0].replacement.value = "381"
    client, requests = transport_client([x.model_dump_json() for x in [plan, patch, patch]])
    with pytest.raises(Hy3ResponseError):
        client.generate_learning_report("Paper", chunks)
    assert len(requests) == 3  # One response-repair opportunity, then stop before drafting.


def test_fact_correction_respects_short_outer_budget():
    chunks, plan, _, _ = damaged()
    client, requests = transport_client([plan.model_dump_json()])
    with use_request_budget(RequestBudget(max_requests=1)):
        with pytest.raises(Hy3ResponseError, match="上限"):
            client.generate_learning_report("Paper", chunks)
    assert len(requests) == 1


def test_json_format_repair_keeps_failed_fact_context_and_exact_scope():
    chunks, plan, draft, patch = damaged()
    client, requests = transport_client([plan.model_dump_json(), PlanFactPatch(corrections=[]).model_dump_json(),
                                       patch.model_dump_json(), draft.model_dump_json(), LessonReview(issues=[]).model_dump_json()])
    assert client.generate_learning_report("Paper", chunks) == draft.report
    assert len(requests) == 5
    prompt = requests[2]["messages"][1]["content"]
    assert 'untrusted_fact_errors' in prompt and 'value_not_grounded' in prompt
    assert chunks[4].content in prompt


def test_new_optional_stage_does_not_raise_eighteen_request_ceiling():
    chunks, plan, draft, correction = damaged()
    issue = LessonReview(issues=[LessonIssue(section_type="method", point_indices=[0], problem="修正机制")])
    patch = method_patch(draft)
    patch.point_updates[0].point.evidence[0].quote = "Incorrect quote."
    stages = [x.model_dump_json() for x in [plan, correction, draft, issue, patch]] + [
        '{"quote_0": 0}', issue.model_dump_json(), patch.model_dump_json(),
        '{"quote_0": 0}', LessonReview(issues=[]).model_dump_json()]
    client, requests = transport_client([s for stage in stages for s in ["invalid json", stage]])
    with pytest.raises(Hy3ResponseError, match="上限"):
        client.generate_learning_report("Paper", chunks)
    assert len(requests) == 18  # Cannot silently spend the theoretical 20 requests.


def test_semantically_invalid_patch_uses_existing_response_repair_with_local_source_feedback():
    chunks, plan, draft, patch = damaged()
    wrong = deepcopy(patch)
    wrong.corrections[0].replacement.sources[0].quote = "A fabricated quotation from another passage."
    client, requests = transport_client([x.model_dump_json() for x in [plan, wrong, patch, draft, LessonReview(issues=[])]])
    assert client.generate_learning_report("Paper", chunks) == draft.report
    assert len(requests) == 5
    prompt = requests[2]["messages"][1]["content"]
    assert 'invalid_fact_source' in prompt
    assert 'source_checks' in prompt and 'actual_chunk_text' in prompt
    assert chunks[4].content in prompt


def test_verified_long_correction_quote_is_split_without_losing_any_source_text():
    from paperaudit.learning_generation import fact_repair_contract
    chunks, plan, _, patch = damaged()
    quote = chunks[4].content + " Supporting continuous context for this finding." * 9
    chunks[4].content = quote
    raw = patch.model_dump(mode="json")
    raw["corrections"][0]["replacement"]["sources"][0]["quote"] = quote
    model, _ = fact_repair_contract(plan, {c.chunk_id: c for c in chunks})
    parsed = model.model_validate(raw)
    anchors = parsed.corrections[0].replacement.sources
    assert len(anchors) > 1 and all(8 <= len(a.quote) <= 320 and a.quote in quote for a in anchors)
    covered = set()
    for offset, anchor in zip(range(0, len(quote), 280), anchors):
        covered.update(range(offset, offset + len(anchor.quote)))
    assert covered == set(range(len(quote)))
    assert raw["corrections"][0]["replacement"]["sources"][0]["quote"] == quote
    # Formatting is not an escape hatch for invented, stitched or unknown text.
    raw["corrections"][0]["replacement"]["sources"][0]["quote"] = quote + " invented ending"
    with pytest.raises(ValueError):
        model.model_validate(raw)


def test_actual_provider_correction_replays_without_editing_facts_or_spending_requests():
    import json
    from pathlib import Path
    from paperaudit.models import PaperChunk
    from paperaudit.learning_generation import LessonPlan, fact_repair_contract
    path = Path(__file__).parent / "fixtures/lecture_facts/provider_snapshots/transformer-fact-correction.json"
    fixture = json.loads(path.read_text())
    plan = LessonPlan.model_validate(fixture["plan"])
    sources = {c["chunk_id"]: PaperChunk.model_validate(c) for c in fixture["sources"]}
    model, errors = fact_repair_contract(plan, sources)
    assert len(errors) == 5
    patch = model.model_validate_json(fixture["patch_response"])
    result = apply_fact_patch(plan, patch, sources)
    old = {f.fact_id: f for s in plan.sections for t in s.topics for f in t.facts}
    new = {f.fact_id: f for s in result.sections for t in s.topics for f in t.facts}
    changed = {f.fact_id for _, f, _ in errors}
    assert len(old) == 30 and len(new) == 32
    assert all(new[fid].model_dump_json() == fact.model_dump_json() for fid, fact in old.items() if fid not in changed)
    assert set(old) <= set(new)
    assert all(a.model_dump(exclude={"facts"}) == b.model_dump(exclude={"facts"})
               for s1, s2 in zip(plan.sections, result.sections) for a, b in zip(s1.topics, s2.topics))
    assert new["me4f2"].metric == "PPL" and new["me4f2__split_2"].metric == "BLEU"
    validate_plan(result, sources)
