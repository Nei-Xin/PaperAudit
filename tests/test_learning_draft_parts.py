"""Large fact ledgers use smaller responses without dropping paper context."""
from copy import deepcopy

import pytest
from pydantic import ValidationError

from paperaudit.learning_generation import LessonDraftPart, LessonReview, generate_lesson
from paperaudit.hy3_client import Hy3ResponseError
from paperaudit.learning_facts import FactMention
from paperaudit.request_budget import RequestBudget, use_request_budget
from test_learning_facts import fact_materials
from test_learning_generation import transport_client


def large_materials():
    chunks, plan, draft = fact_materials()
    topic = plan.sections[4].topics[0]
    fact = topic.facts[0]
    topic.facts = [fact.model_copy(update={"fact_id": f"result_{i}"}, deep=True) for i in range(16)]
    draft.coverage[4].fact_mentions = [FactMention(fact_id=f.fact_id, point_index=0,
        excerpt=draft.report.sections[4].points[0].explanation) for f in topic.facts]
    first = LessonDraftPart(sections=draft.report.sections[:3], coverage=draft.coverage[:3],
        one_sentence_summary=draft.report.one_sentence_summary, suggested_pages=draft.report.suggested_pages)
    second = LessonDraftPart(sections=draft.report.sections[3:], coverage=draft.coverage[3:])
    return chunks, plan, draft, first, second


def test_large_draft_assembles_all_sections_and_globally_reviews_every_part():
    chunks, plan, draft, first, second = large_materials()
    client, requests = transport_client([x.model_dump_json() for x in [plan, first, second, LessonReview(issues=[])]])
    budget = RequestBudget(max_requests=4)
    with use_request_budget(budget):
        assert client.generate_learning_report("Paper", chunks) == draft.report
    assert len(requests) == budget.requests == 4
    for index in [1, 2, 3]:
        prompt = requests[index]["messages"][1]["content"]
        assert all(c.content in prompt for c in chunks)
    assert 'untrusted_previous_part' in requests[2]["messages"][1]["content"]
    assert 'result_15' in requests[3]["messages"][1]["content"]
    assert all(s.title in requests[3]["messages"][1]["content"] for s in draft.report.sections)


@pytest.mark.parametrize("damage", ["chapter", "topic", "summary"])
def test_part_contract_rejects_cross_part_rewrites(damage):
    chunks, plan, _, first, second = large_materials()
    wrong = deepcopy(second)
    if damage == "chapter": wrong.sections[0] = first.sections[0]
    elif damage == "topic": wrong.coverage[0] = first.coverage[0]
    else: wrong.one_sentence_summary = "overwrite"
    responses = [plan, first, wrong]
    def call(prompt, model):
        return model.model_validate(responses.pop(0).model_dump(mode="json"))
    with pytest.raises(ValidationError):
        generate_lesson(call, "Paper", chunks, "all paper")


def test_failure_or_budget_exhaustion_in_second_part_never_returns_first_part():
    chunks, plan, _, first, _ = large_materials()
    client, requests = transport_client([plan.model_dump_json(), first.model_dump_json()])
    with use_request_budget(RequestBudget(max_requests=2)):
        with pytest.raises(Hy3ResponseError, match="上限"):
            client.generate_learning_report("Paper", chunks)
    assert len(requests) == 2


def test_part_schema_repair_cannot_merge_chapters_to_meet_length():
    chunks, plan, draft, first, second = large_materials()
    wrong = deepcopy(first)
    wrong.sections = [first.sections[0]] * 3
    client, requests = transport_client([x.model_dump_json() for x in [plan, wrong, first, second, LessonReview(issues=[])]])
    assert client.generate_learning_report("Paper", chunks) == draft.report
    assert len(requests) == 5
    assert 'literal_error' in requests[2]["messages"][1]["content"]


def test_complete_misnested_chapters_are_moved_losslessly_without_touching_input():
    chunks, plan, draft, first, second = large_materials()
    raw = second.model_dump(mode="json")
    sections = raw["sections"]
    raw["sections"] = sections[:1]
    for section in sections[1:]:
        raw[section["section_type"]] = section
    before = deepcopy(raw)
    assert LessonDraftPart.model_validate(raw).model_dump() == second.model_dump()
    assert raw == before
    responses = [plan.model_dump(mode="json"), first.model_dump(mode="json"), raw, {"issues": []}]
    def call(prompt, model):
        return model.model_validate(responses.pop(0))
    assert generate_lesson(call, "Paper", chunks, "all paper") == draft.report


def test_misnesting_normalizer_does_not_hide_duplicate_or_mismatched_chapters():
    _, _, _, _, second = large_materials()
    raw = second.model_dump(mode="json")
    raw["results"] = raw["sections"][0]
    with pytest.raises(ValidationError):
        LessonDraftPart.model_validate(raw)
    raw["results"] = raw["sections"][1]
    parsed = LessonDraftPart.model_validate(raw)
    assert len(parsed.sections) == 5  # Dynamic exact chapter schema must reject duplicates.


def test_large_repairs_are_batched_and_globally_reviewed_only_after_both_merge():
    from paperaudit.learning_generation import LessonIssue, LessonPatch, PointUpdate
    from test_learning_generation import materials
    chunks, plan, draft = materials()
    issues = [LessonIssue(section_type=s.section_type, point_indices=[0], problem="修正条件") for s in draft.report.sections]
    calls = []
    def call(prompt, model):
        calls.append(model.__name__)
        if len(calls) == 1: return plan
        if len(calls) == 2: return draft
        if len(calls) == 3: return LessonReview(issues=issues)
        if len(calls) in [4, 5]:
            indices = range(3) if len(calls) == 4 else range(3, 7)
            updates = []
            for index in indices:
                point = deepcopy(draft.report.sections[index].points[0])
                point.explanation = f"修正后的第 {index} 章解释。"
                updates.append(PointUpdate(section_type=draft.report.sections[index].section_type, point_index=0, point=point))
            patch = LessonPatch(point_updates=updates, coverage=[draft.coverage[i] for i in indices])
            return model.model_validate(patch.model_dump(mode="json"))
        assert len(calls) == 6
        assert all(f"修正后的第 {i} 章解释。" in prompt for i in range(7))
        return LessonReview(issues=[])
    result = generate_lesson(call, "Paper", chunks, "all source")
    assert len(calls) == 6
    assert all(s.points[0].explanation == f"修正后的第 {i} 章解释。" for i, s in enumerate(result.sections))
    assert all(s.points[0].explanation == "以原文证据解释这一主题。" for s in draft.report.sections)
