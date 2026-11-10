"""Contract tests for grounded lessons, selective repairs and bounded model calls."""
from copy import deepcopy
import json
from types import SimpleNamespace

import httpx
from openai import OpenAI
import pytest

from paperaudit.config import Settings
from paperaudit.hy3_client import Hy3Client, Hy3ResponseError
from paperaudit.learning_generation import (
    LessonDraft, LessonIssue, LessonPatch, LessonPlan, LessonReview,
    LearningQualityError, TopicCoverage, PointUpdate, PointAppend, SectionMetadataUpdate,
    apply_patch, repair_contract, draft_issues, generate_lesson, select_exact_quotes,
)
from paperaudit.models import (
    EvidenceAnchor, ExplanationPoint, LearningReport, LearningSectionType,
    PaperChunk, ParsedPaper, ReportSection,
)
from paperaudit.request_budget import RequestBudget, use_request_budget
from paperaudit.service import AuditService


SETTINGS = Settings(api_base="https://example.invalid/v1", api_key="test", model="fake")


def materials():
    chunks = [PaperChunk(chunk_id=k.value, page=i + 1, content=f"The paper provides evidence about {k.value}.")
              for i, k in enumerate(LearningSectionType)]
    plan = LessonPlan.model_validate({"sections": [
        {"section_type": k, "topics": [{"topic_id": k.value, "title": k.value,
         "learning_goal": "解释原文的方法、条件和结论", "source_chunk_ids": [k.value]}]}
        for k in LearningSectionType
    ]})
    report = LearningReport(paper_title="Paper", one_sentence_summary="论文研究问题与方案。", sections=[
        ReportSection(section_type=k, title=k.value, overview="章节导读", points=[
            ExplanationPoint(title=k.value, explanation="以原文证据解释这一主题。", evidence=[
                EvidenceAnchor(chunk_id=k.value, quote=chunks[i].content),
            ]),
        ]) for i, k in enumerate(LearningSectionType)
    ], suggested_pages=[1, 3, 5])
    draft = LessonDraft(report=report, coverage=[TopicCoverage(topic_id=k.value, point_indices=[0]) for k in LearningSectionType])
    return chunks, plan, draft


def scripted(responses):
    calls = []
    def call(prompt, model):
        calls.append((prompt, model))
        assert len(calls) <= len(responses), "Unexpected extra model call"
        result = responses[len(calls) - 1]
        if isinstance(result, LessonPatch) and issubclass(model, LessonPatch):
            return result.model_copy(deep=True)
        assert isinstance(result, model)
        return result.model_copy(deep=True)
    return call, calls


def run(call, chunks):
    return generate_lesson(call, "Paper", chunks, "\n".join(c.content for c in chunks))


def method_patch(draft, explanation="修补后的完整机制解释。"):
    section = deepcopy(draft.report.sections[2])
    section.points[0].explanation = explanation
    return LessonPatch(point_updates=[PointUpdate(section_type="method", point_index=0, point=section.points[0])], coverage=[draft.coverage[2]])


def test_grounded_report_keeps_more_than_four_method_points_and_legacy_contract():
    chunks, plan, draft = materials()
    for i in range(6):
        point = deepcopy(draft.report.sections[2].points[0])
        point.title = f"方法步骤 {i + 2}"
        draft.report.sections[2].points.append(point)
    call, calls = scripted([plan, draft, LessonReview(issues=[])])
    report = run(call, chunks)
    assert len(calls) == 3
    assert len(report.sections[2].points) == 7
    assert set(report.model_dump()) == {"paper_title", "one_sentence_summary", "sections", "suggested_pages"}
    assert "coverage" not in report.model_dump_json()
    assert LearningReport.model_validate_json(report.model_dump_json()) == report


def test_semantic_gap_is_repaired_once_and_other_sections_are_preserved():
    chunks, plan, draft = materials()
    issue = LessonIssue(section_type="method", point_indices=[0], problem="未解释方法的输入与输出。", source_chunk_ids=["method"])
    patch = method_patch(draft)
    call, calls = scripted([plan, draft, LessonReview(issues=[issue]), patch, LessonReview(issues=[])])
    report = run(call, chunks)
    assert len(calls) == 5
    assert report.sections[2].points[0].explanation == patch.point_updates[0].point.explanation
    assert report.sections[:2] + report.sections[3:] == draft.report.sections[:2] + draft.report.sections[3:]
    assert report.suggested_pages == draft.report.suggested_pages
    assert "未解释方法的输入与输出" in calls[3][0]
    assert patch.point_updates[0].point.explanation in calls[4][0]


def test_unresolved_semantic_problem_never_returns_partial_report_or_retries_forever():
    chunks, plan, draft = materials()
    review = LessonReview(issues=[LessonIssue(section_type="method", point_indices=[0], problem="结论仍超出原文支持。")])
    call, calls = scripted([plan, draft, review, method_patch(draft), review, method_patch(draft), review])
    with pytest.raises(LearningQualityError, match="两轮修补上限"):
        run(call, chunks)
    assert len(calls) == 7


@pytest.mark.parametrize("damage", ["quote", "unknown_source", "missing_evidence", "coverage", "index", "empty_explanation", "missing_section", "duplicate_section"])
def test_deterministic_checks_catch_errors_even_when_model_review_passes(damage):
    chunks, plan, valid = materials()
    draft = valid.model_copy(deep=True)
    if damage == "quote": draft.report.sections[2].points[0].evidence[0].quote = "A fabricated supporting sentence."
    elif damage == "unknown_source": draft.report.sections[2].points[0].evidence[0].chunk_id = "not-real"
    elif damage == "missing_evidence": draft.report.sections[2].points[0].evidence = []
    elif damage == "coverage": draft.coverage.pop(2)
    elif damage == "index": draft.coverage[2].point_indices = [9]
    elif damage == "empty_explanation": draft.report.sections[2].points[0].explanation = " "
    elif damage == "missing_section": draft.report.sections.pop(2)
    elif damage == "duplicate_section": draft.report.sections.append(deepcopy(draft.report.sections[2]))
    patch = method_patch(valid)
    if damage in {"coverage", "index"}:
        patch.point_updates = []
    elif damage in {"missing_section", "duplicate_section"}:
        patch.point_updates = []
        patch.sections = [valid.report.sections[2]]
    call, calls = scripted([plan, draft, LessonReview(issues=[]), patch, LessonReview(issues=[])])
    report = run(call, chunks)
    assert len(calls) == 5
    assert len(report.sections) == 7
    assert report.sections[2].points[0].evidence == valid.report.sections[2].points[0].evidence


def test_declared_coverage_without_relevant_evidence_is_rejected():
    chunks, plan, draft = materials()
    draft.report.sections[2].points[0].evidence = deepcopy(draft.report.sections[0].points[0].evidence)
    issues = draft_issues(draft, plan, {c.chunk_id: c for c in chunks})
    assert any("没有引用提纲" in i.problem for i in issues)


def test_theory_paper_may_explicitly_have_no_experiments_or_results():
    chunks, plan, draft = materials()
    for index in [3, 4]:
        plan.sections[index].topics = []
        plan.sections[index].unavailable_reason = "原文为理论推导，未报告实验及实测结果。"
        draft.report.sections[index].points = []
        draft.report.sections[index].overview = plan.sections[index].unavailable_reason
    draft.coverage = [c for c in draft.coverage if c.topic_id not in {"experiments", "results"}]
    call, calls = scripted([plan, draft, LessonReview(issues=[])])
    report = run(call, chunks)
    assert report.sections[3].points == report.sections[4].points == []
    assert len(calls) == 3


@pytest.mark.parametrize("damage", ["unknown_source", "duplicate_topic", "missing_section", "empty_reason"])
def test_invalid_plans_stop_before_spending_on_draft(damage):
    chunks, plan, _ = materials()
    if damage == "unknown_source": plan.sections[0].topics[0].source_chunk_ids = ["fake"]
    elif damage == "duplicate_topic": plan.sections[1].topics[0].topic_id = plan.sections[0].topics[0].topic_id
    elif damage == "missing_section": plan.sections.pop()
    elif damage == "empty_reason": plan.sections[0].topics = []
    call, calls = scripted([plan])
    with pytest.raises(LearningQualityError): run(call, chunks)
    assert len(calls) == 1


def test_patch_cannot_silently_rewrite_passed_sections():
    chunks, plan, draft = materials()
    patch = method_patch(draft)
    patch.sections.append(draft.report.sections[0])
    review = LessonReview(issues=[LessonIssue(section_type="method", point_indices=[0], problem="缺少机制解释。")])
    call, calls = scripted([plan, draft, review, patch])
    with pytest.raises(LearningQualityError, match="只能替换"):
        run(call, chunks)
    assert len(calls) == 4


def test_review_cannot_validate_against_invented_source():
    chunks, plan, draft = materials()
    review = LessonReview(issues=[LessonIssue(section_type="results", point_indices=[0], problem="补充数值。", source_chunk_ids=["fake"])])
    call, _ = scripted([plan, draft, review])
    with pytest.raises(LearningQualityError, match="不存在的原文"):
        run(call, chunks)


def test_summary_only_repair_preserves_all_sections():
    chunks, plan, draft = materials()
    review = LessonReview(issues=[LessonIssue(problem="总结声称所有任务均提升，应限制到论文测试任务。")])
    patch = LessonPatch(sections=[], coverage=[], one_sentence_summary="仅在测试任务中展示改进。")
    call, _ = scripted([plan, draft, review, patch, LessonReview(issues=[])])
    report = run(call, chunks)
    assert report.sections == draft.report.sections
    assert report.one_sentence_summary == patch.one_sentence_summary


def transport_client(responses):
    requests = []
    def respond(request):
        requests.append(json.loads(request.content))
        content = responses[len(requests) - 1]
        return httpx.Response(200, json={
            "id": "test", "object": "chat.completion", "created": 0, "model": "fake",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        })
    client = Hy3Client(SETTINGS)
    client._client = OpenAI(api_key="test", base_url=SETTINGS.api_base,
                           http_client=httpx.Client(transport=httpx.MockTransport(respond)))
    return client, requests


def test_generation_uses_caller_budget_and_meters_every_stage():
    chunks, plan, draft = materials()
    client, requests = transport_client([x.model_dump_json() for x in [plan, draft, LessonReview(issues=[])]])
    budget = RequestBudget(max_requests=3)
    with use_request_budget(budget):
        report = AuditService(SETTINGS, client=client).generate_learning_report(ParsedPaper(title="Paper", page_count=7, chunks=chunks))
    assert len(requests) == budget.requests == 3
    assert all(r["response_format"] == {"type": "json_object"} for r in requests)
    assert budget.tokens == 6
    assert report.sections[2].points[0].evidence[0].page == 3


def test_short_budget_stops_without_extra_provider_requests():
    chunks, plan, _ = materials()
    client, requests = transport_client([plan.model_dump_json()])
    with use_request_budget(RequestBudget(max_requests=1)):
        with pytest.raises(Hy3ResponseError, match="上限"):
            client.generate_learning_report("Paper", chunks)
    assert len(requests) == 1


def test_json_repair_receives_entire_long_draft_and_counts_towards_budget():
    chunks, plan, draft = materials()
    draft.report.sections[2].points[0].explanation = "解释长段落。" * 3000
    malformed = draft.model_dump_json()[:-1] + " END_OF_LONG_DRAFT"
    client, requests = transport_client([plan.model_dump_json(), malformed, draft.model_dump_json(), LessonReview(issues=[]).model_dump_json()])
    budget = RequestBudget(max_requests=4)
    with use_request_budget(budget):
        client.generate_learning_report("Paper", chunks)
    assert "END_OF_LONG_DRAFT" in requests[2]["messages"][1]["content"]
    assert budget.requests == 4


def test_oversized_or_empty_paper_never_silently_drops_source_or_calls_model():
    client = object.__new__(Hy3Client)
    client.settings = SimpleNamespace(max_paper_chars=10)
    for chunks in [[], [PaperChunk(chunk_id="p1", page=1, content="Long paper content that would lose middle sections.")]]:
        with pytest.raises(Hy3ResponseError): client.generate_learning_report("Paper", chunks)


def test_failed_quality_review_preserves_report_saved_after_submission(tmp_path):
    from time import monotonic, sleep
    from paperaudit.learning_jobs import LearningJobManager
    from paperaudit.models import AuditJobStatus, AuditRuntimeSnapshot
    from paperaudit.storage import ProjectStore, make_conversation

    chunks, plan, draft = materials()
    store = ProjectStore(tmp_path / "library")
    paper = ParsedPaper(title="Paper", page_count=7, chunks=chunks)
    project = store.save_paper_project(b"test-paper", "paper.pdf", paper)
    # Simulate a report saved by another caller
    # after job creation, before execution; failure must still never replace it.
    job = store.create_learning_job(project.project_id, runtime=AuditRuntimeSnapshot(
        model="fake", reasoning_effort="high", retrieval_top_k=5, judge_batch_size=6,
    ))
    store.save_learning_report(project.project_id, draft.report)
    conversation = make_conversation("保留的阅读会话")
    store.save_conversations(project.project_id, [conversation], conversation.conversation_id, keep_empty=True)
    before = {str(p.relative_to(tmp_path)): p.read_bytes() for p in tmp_path.rglob('*.json')}
    issue = LessonReview(issues=[LessonIssue(section_type="method", point_indices=[0], problem="方法机制仍缺少解释。")])
    client, requests = transport_client([x.model_dump_json() for x in [plan, draft, issue, method_patch(draft), issue, method_patch(draft), issue]])
    manager = LearningJobManager(store, service_factory=lambda settings: AuditService(settings, client=client),
                                 mark_interrupted_on_start=False)
    try:
        manager.submit(project.project_id, job.job_id, SETTINGS)
        deadline = monotonic() + 5
        while monotonic() < deadline:
            current = store.load_learning_job(project.project_id, job.job_id)
            if current.status == AuditJobStatus.FAILED:
                break
            sleep(0.01)
        assert current.status == AuditJobStatus.FAILED
        assert "质量检查未通过" in current.error
    finally:
        manager.shutdown()
    saved = store.load_learning_project(project.project_id)
    assert saved.report == draft.report
    assert saved.conversations == [conversation]
    for name, content in before.items():
        if name.endswith('learning-report.json') or name.endswith('session.json'):
            assert (tmp_path / name).read_bytes() == content
    assert len(requests) == 7


def test_standalone_generation_caps_all_five_stages_including_json_repairs():
    chunks, plan, draft = materials()
    review = LessonReview(issues=[LessonIssue(section_type="method", point_indices=[0], problem="解释不充分。")])
    stages = [plan, draft, review, method_patch(draft), LessonReview(issues=[])]
    responses = [text for stage in stages for text in ["invalid json", stage.model_dump_json()]]
    client, requests = transport_client(responses)
    result = client.generate_learning_report("Paper", chunks)
    assert result.sections[2].points[0].explanation == "修补后的完整机制解释。"
    assert len(requests) == 10


def test_empty_repair_is_schema_retried_with_explicit_section_contract():
    chunks, plan, draft = materials()
    review = LessonReview(issues=[LessonIssue(section_type="method", point_indices=[0], problem="补充输入输出。")])
    responses = [x.model_dump_json() for x in [plan, draft, review, LessonPatch(sections=[], coverage=[]), method_patch(draft), LessonReview(issues=[])]]
    client, requests = transport_client(responses)
    report = client.generate_learning_report("Paper", chunks)
    assert report.sections[2].points[0].explanation == "修补后的完整机制解释。"
    assert len(requests) == 6
    repair_prompt = requests[3]["messages"][1]["content"]
    assert '"point_updates": [{"section_type": "method", "point_index": 0}]' in repair_prompt
    assert '"minItems": 1' in repair_prompt


def test_schema_repair_preserves_scope_and_source_when_model_returns_wrong_chapter():
    chunks, plan, draft = materials()
    review = LessonReview(issues=[LessonIssue(section_type="method", point_indices=[0], problem="补充输入输出。")])
    wrong = LessonPatch(sections=[draft.report.sections[0]], coverage=[draft.coverage[2]],
                        one_sentence_summary="不应修改的总结")
    responses = [x.model_dump_json() for x in [plan, draft, review, wrong, method_patch(draft), LessonReview(issues=[])]]
    client, requests = transport_client(responses)
    report = client.generate_learning_report("Paper", chunks)
    assert report.one_sentence_summary == draft.report.one_sentence_summary
    assert report.sections[0] == draft.report.sections[0]
    assert report.sections[2].points[0].explanation == "修补后的完整机制解释。"
    correction = requests[4]["messages"][1]["content"]
    assert '"point_updates": [{"section_type": "method", "point_index": 0}]' in correction
    assert chunks[2].content in correction
    assert "Validation errors:" in correction
    assert "Validation errors:" in correction


def test_invalid_quote_feedback_identifies_exact_quote_and_repeats_source_for_repair():
    chunks, plan, draft = materials()
    valid = deepcopy(draft)
    draft.report.sections[2].points[0].evidence[0].quote = "Incorrectly joined text."
    issues = draft_issues(draft, plan, {c.chunk_id: c for c in chunks})
    assert issues[0].source_chunk_ids == ["method"]
    assert "Incorrectly joined text." in issues[0].problem
    call, calls = scripted([plan, draft, LessonReview(issues=[]), method_patch(valid), LessonReview(issues=[])])
    run(call, chunks)
    assert '<untrusted_repair_sources>' in calls[3][0]
    assert json.dumps({"method": chunks[2].content}, ensure_ascii=False) in calls[3][0]


def test_patch_schema_rejects_unrelated_topic_even_when_coverage_count_matches():
    chunks, plan, draft = materials()
    review = LessonReview(issues=[LessonIssue(section_type="method", point_indices=[0], problem="补充输入输出。")])
    wrong = method_patch(draft)
    wrong.coverage = [draft.coverage[0]]
    client, requests = transport_client([x.model_dump_json() for x in [plan, draft, review, wrong, method_patch(draft), LessonReview(issues=[])]])
    report = client.generate_learning_report("Paper", chunks)
    assert report.sections[2].points[0].explanation == "修补后的完整机制解释。"
    assert len(requests) == 6
    assert '"required_topic_ids": ["method"]' in requests[4]["messages"][1]["content"]
    assert 'coverage.0.topic_id' in requests[4]["messages"][1]["content"]


def test_literal_quote_selection_preserves_source_hyphenation_and_other_content():
    chunks, _, draft = materials()
    chunks[2].content = "The model uses English-\nto-German data and preserves every source character. " * 12
    draft.report.sections[2].points[0].evidence[0].quote = "The model uses English-to-German data."
    original = draft.model_dump_json()
    calls = []
    def choose(prompt, model):
        calls.append(prompt)
        return model.model_validate({"quote_0": 1})
    result = select_exact_quotes(choose, draft, {c.chunk_id: c for c in chunks})
    from paperaudit.evidence import _validated_evidence_quote
    anchor = result.report.sections[2].points[0].evidence[0]
    assert _validated_evidence_quote(anchor.quote, chunks[2].content)
    assert len(anchor.quote) <= 320
    assert draft.model_dump_json() == original
    assert result.report.sections[2].points[0].explanation == draft.report.sections[2].points[0].explanation
    assert len(calls) == 1


def test_literal_quote_selection_can_decline_instead_of_inventing_support():
    chunks, _, draft = materials()
    draft.report.sections[2].points[0].evidence[0].quote = "Unsupported text."
    def decline(prompt, model):
        return model.model_validate({"quote_0": -1})
    with pytest.raises(LearningQualityError, match="未找到支持"):
        select_exact_quotes(decline, draft, {c.chunk_id: c for c in chunks})


def test_quote_selection_is_metered_and_followed_by_semantic_review():
    chunks, plan, draft = materials()
    issue = LessonReview(issues=[LessonIssue(section_type="method", point_indices=[0], problem="解释不充分。")])
    patch = method_patch(draft)
    patch.point_updates[0].point.evidence[0].quote = "Incorrect quote from model."
    responses = [x.model_dump_json() for x in [plan, draft, issue, patch]] + [
        '{"quote_0": 0}', LessonReview(issues=[]).model_dump_json()]
    client, requests = transport_client(responses)
    budget = RequestBudget(max_requests=6)
    with use_request_budget(budget):
        report = client.generate_learning_report("Paper", chunks)
    assert len(requests) == budget.requests == 6
    assert report.sections[2].points[0].evidence[0].quote == chunks[2].content
    assert chunks[2].content in requests[-1]["messages"][1]["content"]


def test_all_optional_stages_and_json_repairs_fit_twelve_request_ceiling():
    chunks, plan, draft = materials()
    issue = LessonReview(issues=[LessonIssue(section_type="method", point_indices=[0], problem="解释不充分。")])
    patch = method_patch(draft)
    patch.point_updates[0].point.evidence[0].quote = "Incorrect quote."
    stages = [x.model_dump_json() for x in [plan, draft, issue, patch]] + [
        '{"quote_0": 0}', LessonReview(issues=[]).model_dump_json()]
    client, requests = transport_client([text for stage in stages for text in ["invalid json", stage]])
    report = client.generate_learning_report("Paper", chunks)
    assert report.sections[2].points[0].evidence[0].quote == chunks[2].content
    assert len(requests) == 12
    assert all(r["response_format"] == {"type": "json_object"} for r in requests)


def test_exact_quote_does_not_override_failed_semantic_review():
    chunks, plan, draft = materials()
    issue = LessonReview(issues=[LessonIssue(section_type="method", point_indices=[0], problem="解释超出原文支持。")])
    patch = method_patch(draft)
    patch.point_updates[0].point.evidence[0].quote = "Incorrect quote."
    client, requests = transport_client([x.model_dump_json() for x in [plan, draft, issue, patch]] + [
        '{"quote_0": 0}', issue.model_dump_json(), patch.model_dump_json(), '{"quote_0": 0}', issue.model_dump_json()])
    with pytest.raises(Hy3ResponseError, match="两轮修补上限"):
        client.generate_learning_report("Paper", chunks)
    assert len(requests) == 9


def test_required_result_value_must_appear_in_linked_explanation_not_just_quote():
    chunks, plan, draft = materials()
    chunks[4].content = "Base model: French BLEU 38.1. Big model: French BLEU 41.8."
    topic = plan.sections[4].topics[0]
    topic.required_values = ["38.1", "41.8"]
    draft.report.sections[4].points[0].evidence[0].quote = chunks[4].content
    draft.report.sections[4].points[0].explanation = "big 英法 BLEU 为41.8；另有138.1这个无关数值。"
    issues = draft_issues(draft, plan, {c.chunk_id: c for c in chunks})
    assert any("缺少关键结果值 38.1" in i.problem for i in issues)
    draft.report.sections[4].points[0].explanation += "base 英法 BLEU 为38.1。"
    assert draft_issues(draft, plan, {c.chunk_id: c for c in chunks}) == []


def test_plan_cannot_require_a_number_absent_from_its_sources():
    chunks, plan, _ = materials()
    plan.sections[4].topics[0].required_values = ["99.9"]
    call, calls = scripted([plan])
    with pytest.raises(LearningQualityError, match="关键数值"):
        run(call, chunks)
    assert len(calls) == 1


def test_required_values_allow_sentence_period_but_not_larger_decimal():
    from paperaudit.learning_generation import validate_plan
    chunks, plan, draft = materials()
    chunks[4].content = "The result is 28.4. Another result is 38.1."
    plan.sections[4].topics[0].required_values = ["28.4"]
    validate_plan(plan, {c.chunk_id: c for c in chunks})
    draft.report.sections[4].points[0].evidence[0].quote = chunks[4].content
    draft.report.sections[4].points[0].explanation = "The result is 28.4."
    assert draft_issues(draft, plan, {c.chunk_id: c for c in chunks}) == []
    plan.sections[4].topics[0].required_values = ["38"]
    with pytest.raises(LearningQualityError, match="关键数值"):
        validate_plan(plan, {c.chunk_id: c for c in chunks})


def test_second_repair_targets_new_defect_without_rewriting_first_fix():
    chunks, plan, draft = materials()
    first_issue = LessonReview(issues=[LessonIssue(section_type="method", point_indices=[0], problem="方法缺少步骤。")])
    later_issue = LessonReview(issues=[LessonIssue(section_type="results", point_indices=[0], problem="主结果漏报。")])
    results = deepcopy(draft.report.sections[4])
    results.points[0].explanation = "补齐主结果及条件。"
    second = LessonPatch(point_updates=[PointUpdate(section_type="results", point_index=0, point=results.points[0])], coverage=[draft.coverage[4]])
    call, calls = scripted([plan, draft, first_issue, method_patch(draft), later_issue, second, LessonReview(issues=[])])
    report = run(call, chunks)
    assert len(calls) == 7
    assert report.sections[2].points[0].explanation == "修补后的完整机制解释。"
    assert report.sections[4].points[0].explanation == "补齐主结果及条件。"
    assert report.sections[0] == draft.report.sections[0]


def test_two_repairs_with_quote_selection_and_json_repairs_use_at_most_eighteen_requests():
    chunks, plan, draft = materials()
    issue = LessonReview(issues=[LessonIssue(section_type="method", point_indices=[0], problem="解释不充分。")])
    patch = method_patch(draft)
    patch.point_updates[0].point.evidence[0].quote = "Incorrect quote."
    stages = [x.model_dump_json() for x in [plan, draft, issue, patch]] + [
        '{"quote_0": 0}', issue.model_dump_json(), patch.model_dump_json(),
        '{"quote_0": 0}', LessonReview(issues=[]).model_dump_json()]
    client, requests = transport_client([text for stage in stages for text in ["invalid json", stage]])
    report = client.generate_learning_report("Paper", chunks)
    assert report.sections[2].points[0].evidence[0].quote == chunks[2].content
    assert len(requests) == 18


def test_point_patch_preserves_siblings_and_input_bytes_and_shared_coverage():
    chunks, plan, draft = materials()
    sibling = deepcopy(draft.report.sections[2].points[0])
    sibling.title = "已经正确的第二步"
    draft.report.sections[2].points.append(sibling)
    other = plan.sections[2].topics[0].model_copy(update={"topic_id": "other"}, deep=True)
    shared = other.model_copy(update={"topic_id": "shared"}, deep=True)
    plan.sections[2].topics.extend([other, shared])
    untouched = TopicCoverage(topic_id="other", point_indices=[1])
    shared_mapping = TopicCoverage(topic_id="shared", point_indices=[0, 1])
    draft.coverage.extend([untouched, shared_mapping])
    before = draft.model_dump_json()
    issues = [LessonIssue(section_type="method", point_indices=[0], problem="修正第一步")]
    patch = method_patch(draft)
    patch.coverage.append(shared_mapping)
    result = apply_patch(draft, patch, plan, issues)
    assert draft.model_dump_json() == before
    assert result.report.sections[2].points[1].model_dump_json() == sibling.model_dump_json()
    assert next(c for c in result.coverage if c.topic_id == "other") == untouched
    assert next(c for c in result.coverage if c.topic_id == "shared").point_indices == [0, 1]
    assert draft_issues(result, plan, {c.chunk_id: c for c in chunks}) == []
    # Returned objects must not retain aliases to either the draft or patch.
    result.report.sections[2].points[0].title = "later mutation"
    result.report.sections[2].points[1].title = "another mutation"
    assert draft.model_dump_json() == before
    assert patch.point_updates[0].point.title != "later mutation"


def test_append_then_second_round_repair_uses_new_index_without_shifting_old_points():
    chunks, plan, draft = materials()
    point = deepcopy(draft.report.sections[2].points[0])
    point.title = "缺失的第二步"
    append = LessonPatch(appended_points=[PointAppend(section_type="method", points=[point])],
                         coverage=[TopicCoverage(topic_id="method", point_indices=[0, 1])])
    issue = LessonReview(issues=[LessonIssue(section_type="method", append_points=True, problem="补充第二步")])
    point.explanation = "第二步更正后的条件。"
    fix = LessonPatch(point_updates=[PointUpdate(section_type="method", point_index=1, point=point)], coverage=append.coverage)
    later = LessonReview(issues=[LessonIssue(section_type="method", point_indices=[1], problem="第二步条件有误")])
    call, calls = scripted([plan, draft, issue, append, later, fix, LessonReview(issues=[])])
    result = run(call, chunks)
    assert len(calls) == 7
    assert result.sections[2].points[0] == draft.report.sections[2].points[0]
    assert len(result.sections[2].points) == 2
    assert result.sections[2].points[1].explanation == "第二步更正后的条件。"
    assert '"point_index": 1' in calls[5][0]


def test_metadata_and_summary_repair_do_not_authorize_points_or_coverage():
    _, plan, draft = materials()
    issues = [LessonIssue(section_type="method", edit_metadata=True, problem="导读有误"), LessonIssue(problem="总结有误")]
    patch = LessonPatch(metadata_updates=[SectionMetadataUpdate(section_type="method", title="方法", overview="限定后的导读")],
                        one_sentence_summary="限定后的总结")
    result = apply_patch(draft, patch, plan, issues)
    assert result.report.sections[2].points == draft.report.sections[2].points
    assert result.coverage == draft.coverage
    assert result.report.sections[2].overview == "限定后的导读"
    assert result.report.one_sentence_summary == "限定后的总结"
    patch.point_updates = method_patch(draft).point_updates
    with pytest.raises(LearningQualityError, match="只能替换"):
        apply_patch(draft, patch, plan, issues)


@pytest.mark.parametrize("damage", ["sibling", "duplicate", "append", "metadata", "whole_section", "summary", "coverage", "missing_point"])
def test_patch_rejects_changes_outside_exact_point_scope(damage):
    _, plan, draft = materials()
    draft.report.sections[2].points.append(deepcopy(draft.report.sections[2].points[0]))
    issues = [LessonIssue(section_type="method", point_indices=[0], problem="修正第一点")]
    patch = method_patch(draft)
    if damage == "sibling": patch.point_updates[0].point_index = 1
    elif damage == "duplicate": patch.point_updates *= 2
    elif damage == "append": patch.appended_points = [PointAppend(section_type="method", points=[draft.report.sections[2].points[0]])]
    elif damage == "metadata": patch.metadata_updates = [SectionMetadataUpdate(section_type="method", title="篡改", overview="篡改")]
    elif damage == "whole_section": patch.sections = [draft.report.sections[2]]
    elif damage == "summary": patch.one_sentence_summary = "篡改"
    elif damage == "coverage": patch.coverage = [draft.coverage[0]]
    elif damage == "missing_point": patch.point_updates = []
    before = draft.model_dump_json()
    with pytest.raises(LearningQualityError, match="只能替换"):
        apply_patch(draft, patch, plan, issues)
    assert draft.model_dump_json() == before


@pytest.mark.parametrize("scope", [
    {}, {"point_indices": [-1]}, {"point_indices": [1]}, {"point_indices": [0, 0]},
    {"topic_ids": ["results"]}, {"topic_ids": ["unknown"]},
])
def test_ambiguous_or_invalid_review_scope_stops_before_patch_call(scope):
    chunks, plan, draft = materials()
    review = LessonReview(issues=[LessonIssue(section_type="method", problem="错误范围", **scope)])
    call, calls = scripted([plan, draft, review])
    with pytest.raises(LearningQualityError):
        run(call, chunks)
    assert len(calls) == 3


def test_mapping_only_repair_preserves_every_explanation_and_removes_unknown_ids():
    chunks, plan, draft = materials()
    draft.coverage.append(TopicCoverage(topic_id="unknown", point_indices=[99]))
    issues = draft_issues(draft, plan, {c.chunk_id: c for c in chunks})
    model, contract = repair_contract(draft, plan, issues)
    assert contract["point_updates"] == contract["structural_sections"] == []
    assert not contract["summary_requires_repair"]
    patch = LessonPatch(coverage=[draft.coverage[0]])
    result = apply_patch(draft, patch, plan, issues)
    assert result.report.model_dump_json() == draft.report.model_dump_json()
    assert len(result.coverage) == 7
    assert draft_issues(result, plan, {c.chunk_id: c for c in chunks}) == []


def test_disproven_omission_can_keep_text_without_forcing_invented_append():
    chunks, plan, draft = materials()
    issue = LessonReview(issues=[LessonIssue(section_type="method", append_points=True, problem="误报缺失")])
    patch = LessonPatch(appended_points=[PointAppend(section_type="method", points=[])], coverage=[draft.coverage[2]])
    call, calls = scripted([plan, draft, issue, patch, LessonReview(issues=[])])
    assert run(call, chunks) == draft.report
    assert len(calls) == 5


def test_summary_issue_cannot_smuggle_point_permission():
    _, plan, draft = materials()
    with pytest.raises(LearningQualityError, match="总结问题"):
        repair_contract(draft, plan, [LessonIssue(point_indices=[0], problem="总结有误")])
