"""Reject ineffective corrections before spending on another semantic review."""
from copy import deepcopy
import pytest
from pydantic import ValidationError
from paperaudit.learning_generation import (LessonPatch,PointUpdate,LessonReview,draft_issues,
    validated_repair_contract,repair_coverage_excerpts)
from test_learning_facts import fact_materials
from test_learning_generation import transport_client


def test_stale_excerpt_is_repaired_only_with_same_point_passing_all_checks():
    chunks, plan, draft = fact_materials()
    original = draft.report.model_dump_json()
    draft.coverage[4].fact_mentions[0].excerpt = 'old text'
    result = repair_coverage_excerpts(draft, plan)
    assert result.report.model_dump_json() == original
    assert result.coverage[4].fact_mentions[0].excerpt == draft.report.sections[4].points[0].explanation
    assert draft.coverage[4].fact_mentions[0].excerpt == 'old text'
    draft.report.sections[4].points[0].explanation = 'Atlas base 在法语测试集上的 BLEU 为138.1。'
    assert repair_coverage_excerpts(draft, plan).coverage[4].fact_mentions[0].excerpt == 'old text'


def test_excerpt_repair_does_not_borrow_value_from_sibling_or_add_evidence():
    _, plan, draft = fact_materials()
    draft.report.sections[4].points.append(deepcopy(draft.report.sections[4].points[0]))
    draft.report.sections[4].points[0].explanation = '未说明数值'
    result = repair_coverage_excerpts(draft,plan)
    assert result.coverage == draft.coverage
    draft.report.sections[4].points[0] = deepcopy(draft.report.sections[4].points[1])
    draft.report.sections[4].points[0].evidence = []
    draft.coverage[4].fact_mentions[0].excerpt = 'old text'
    assert repair_coverage_excerpts(draft,plan).coverage == draft.coverage


def test_ineffective_patch_is_rejected_by_response_contract():
    chunks, plan, draft = fact_materials()
    sources = {c.chunk_id:c for c in chunks}
    valid = deepcopy(draft)
    draft.report.sections[4].points[0].explanation = 'Atlas base 在法语测试集上的 BLEU 为138.1。'
    draft.coverage[4].fact_mentions[0].excerpt = draft.report.sections[4].points[0].explanation
    issues = draft_issues(draft,plan,sources)
    model,_ = validated_repair_contract(draft,plan,issues,sources)
    bad = LessonPatch(point_updates=[PointUpdate(section_type='results',point_index=0,point=draft.report.sections[4].points[0])],coverage=[draft.coverage[4]])
    with pytest.raises(ValidationError,match='missing_value'):
        model.model_validate(bad.model_dump(mode='json'))
    good = LessonPatch(point_updates=[PointUpdate(section_type='results',point_index=0,point=valid.report.sections[4].points[0])],coverage=[valid.coverage[4]])
    assert model.model_validate(good.model_dump(mode='json')).point_updates[0].point.explanation == valid.report.sections[4].points[0].explanation
    client, requests = transport_client([x.model_dump_json() for x in [plan,draft,LessonReview(issues=[]),bad,good,LessonReview(issues=[])]])
    assert client.generate_learning_report('Paper',chunks) == valid.report
    assert len(requests) == 6
    assert 'missing_value' in requests[4]['messages'][1]['content']


def test_uncertainty_failure_includes_required_text_for_response_repair():
    chunks, plan, draft = fact_materials()
    fact = plan.sections[4].topics[0].facts[0]
    fact.uncertainty = '原文两处结果有冲突，不能任选一个。'
    sources = {c.chunk_id:c for c in chunks}
    issues = draft_issues(draft, plan, sources)
    assert any(fact.uncertainty in i.problem for i in issues)
    model,_ = validated_repair_contract(draft,plan,issues,sources)
    patch = LessonPatch(point_updates=[PointUpdate(section_type='results',point_index=0,point=draft.report.sections[4].points[0])],coverage=[draft.coverage[4]])
    # A wording mismatch is deferred to independent review, never silently waived.
    model.model_validate(patch.model_dump(mode='json'))
    assert any(i.fact_code == 'uncertainty_hidden' for i in draft_issues(draft, plan, sources))
    patch.point_updates[0].point = patch.point_updates[0].point.model_copy(deep=True)
    patch.point_updates[0].point.explanation += fact.uncertainty
    assert model.model_validate(patch.model_dump(mode='json')).coverage[0].fact_mentions[0].excerpt.endswith(fact.uncertainty)


def test_response_repair_instructions_allow_only_explicit_coverage_fixes():
    chunks, plan, draft = fact_materials()
    valid = deepcopy(draft)
    draft.report.sections[4].points[0].explanation = 'Atlas base 在法语测试集上的 BLEU 未说明。'
    draft.coverage[4].fact_mentions[0].excerpt = draft.report.sections[4].points[0].explanation
    bad = LessonPatch(point_updates=[PointUpdate(section_type='results',point_index=0,point=draft.report.sections[4].points[0])],coverage=[draft.coverage[4]])
    good = LessonPatch(point_updates=[PointUpdate(section_type='results',point_index=0,point=valid.report.sections[4].points[0])],coverage=[valid.coverage[4]])
    client, requests = transport_client([x.model_dump_json() for x in [plan,draft,LessonReview(issues=[]),bad,good,LessonReview(issues=[])]])
    assert client.generate_learning_report('Paper',chunks) == valid.report
    prompt = requests[4]['messages'][1]['content']
    assert 'including factual coverage constraints' in prompt
    assert 'Fix formatting and schema errors only.' not in prompt


def test_wording_review_requires_exact_excerpt_and_never_waives_values():
    from paperaudit.learning_generation import wording_review_contract
    chunks, plan, draft = fact_materials()
    fact = plan.sections[4].topics[0].facts[0]
    fact.conditions = ['使用独立测试划分']
    draft.report.sections[4].points[0].explanation = 'Atlas base 在法语测试集上的 BLEU 为38.1；评估使用未参与训练的独立测试集。'
    draft.coverage[4].fact_mentions[0].excerpt = draft.report.sections[4].points[0].explanation
    issues = draft_issues(draft,plan,{c.chunk_id:c for c in chunks})
    model, payload, candidates = wording_review_contract(draft,plan,issues)
    assert len(payload) == 1
    verdict = {'issues':[], 'fact_checks':[{'check_id':payload[0]['check_id'],'equivalent':True,
        'explanation_excerpt':'并不存在的原句','reason':'unsupported'}]}
    with pytest.raises(ValidationError,match='实际解释'):
        model.model_validate(verdict)
    verdict['fact_checks'][0]['explanation_excerpt'] = '评估使用未参与训练的独立测试集。'
    assert model.model_validate(verdict).fact_checks[0].equivalent
    draft.report.sections[4].points[0].explanation = 'Atlas base 在法语测试集上的 BLEU 为138.1。'
    draft.coverage[4].fact_mentions[0].excerpt = draft.report.sections[4].points[0].explanation
    issues = draft_issues(draft,plan,{c.chunk_id:c for c in chunks})
    _,_,candidates = wording_review_contract(draft,plan,issues)
    numeric = {i for i,issue in enumerate(issues) if issue.fact_code == 'missing_value'}
    assert numeric and numeric.isdisjoint(i for i,_ in candidates)


@pytest.mark.parametrize('equivalent',[True,False])
def test_independent_wording_verdict_controls_whether_content_is_repaired(equivalent):
    from paperaudit.learning_generation import generate_lesson
    chunks,plan,draft = fact_materials()
    plan.sections[4].topics[0].facts[0].conditions = ['使用独立测试划分']
    draft.report.sections[4].points[0].explanation += '评估使用未参与训练的独立测试集。'
    draft.coverage[4].fact_mentions[0].excerpt = draft.report.sections[4].points[0].explanation
    calls = []
    def call(prompt,model):
        calls.append(model.__name__)
        if len(calls)==1:return plan
        if len(calls)==2:return draft
        if model.__name__=='LessonReviewWithWording':
            import json
            checks = json.loads(prompt.split('<untrusted_wording_checks>')[1].split('</untrusted_wording_checks>')[0])
            return model.model_validate({'issues':[], 'fact_checks':[{
                'check_id':c['check_id'], 'equivalent':equivalent,
                'explanation_excerpt':'评估使用未参与训练的独立测试集。',
                'reason':'所引原句说明同一划分' if equivalent else '不能确认测试划分相同'} for c in checks]})
        if model.__name__=='RequiredLessonPatch':
            point = deepcopy(draft.report.sections[4].points[0])
            point.explanation += '使用独立测试划分。'
            patch = LessonPatch(point_updates=[PointUpdate(section_type='results',point_index=0,point=point)],coverage=[draft.coverage[4]])
            return model.model_validate(patch.model_dump(mode='json'))
        return LessonReview(issues=[])
    result=generate_lesson(call,'Paper',chunks,'all source')
    assert len(calls)==(3 if equivalent else 5)
    assert result.sections[4].points[0].explanation.endswith('独立测试集。' if equivalent else '独立测试划分。')


def test_repaired_excerpt_keeps_wording_question_for_independent_review():
    chunks, plan, draft = fact_materials()
    plan.sections[4].topics[0].facts[0].uncertainty = '表中与正文的报告存在差异。'
    draft.report.sections[4].points[0].explanation += '正文与表中结果不一致。'
    draft.coverage[4].fact_mentions[0].excerpt = 'old sentence'
    fixed = repair_coverage_excerpts(draft,plan)
    assert fixed.coverage[4].fact_mentions[0].excerpt == fixed.report.sections[4].points[0].explanation
    issues = draft_issues(fixed,plan,{c.chunk_id:c for c in chunks})
    assert any(i.fact_code == 'uncertainty_hidden' for i in issues)
    assert not any(i.fact_code == 'excerpt_not_in_explanation' for i in issues)


def test_long_draft_quotes_split_losslessly_but_stitched_quotes_are_not_fixed():
    from paperaudit.learning_generation import normalize_draft_quotes
    chunks, plan, draft = fact_materials()
    text = 'This is continuous source text that must remain intact. ' * 8
    chunks[0].content = text
    point = draft.report.sections[0].points[0]
    point.evidence[0].quote = text
    original = draft.model_dump_json()
    fixed = normalize_draft_quotes(draft,{c.chunk_id:c for c in chunks})
    assert len(fixed.report.sections[0].points[0].evidence)>1
    assert all(len(a.quote)<=320 and a.quote in text for a in fixed.report.sections[0].points[0].evidence)
    assert draft.model_dump_json()==original
    point.evidence[0].quote = text + ' invented text'
    bad = normalize_draft_quotes(draft,{c.chunk_id:c for c in chunks})
    assert bad.report.sections[0].points[0].evidence == point.evidence


def test_precise_review_point_never_gets_moved_by_unrelated_topic_id():
    from paperaudit.learning_generation import LessonIssue
    from test_learning_generation import materials,method_patch
    chunks,plan,draft=materials()
    review=LessonReview(issues=[LessonIssue(section_type='method',point_indices=[0],topic_ids=['results'],problem='方法缺少步骤')])
    client,requests=transport_client([x.model_dump_json() for x in [plan,draft,review,method_patch(draft),LessonReview(issues=[])]])
    result=client.generate_learning_report('Paper',chunks)
    assert result.sections[4]==draft.report.sections[4]
    assert result.sections[2].points[0].explanation=='修补后的完整机制解释。'
    assert '"required_topic_ids": ["method"]' in requests[3]['messages'][1]['content']


def test_wording_review_rejects_out_of_range_point_before_response_repair():
    from paperaudit.learning_generation import wording_review_contract
    chunks,plan,draft=fact_materials()
    plan.sections[4].topics[0].facts[0].conditions=['独立测试划分']
    issues=draft_issues(draft,plan,{c.chunk_id:c for c in chunks})
    model,payload,_=wording_review_contract(draft,plan,issues)
    value={'issues':[{'section_type':'results','point_indices':[1],'problem':'wrong index'}],
        'fact_checks':[{'check_id':payload[0]['check_id'],'equivalent':False,'explanation_excerpt':'','reason':'未说明划分'}]}
    with pytest.raises(ValidationError,match='越界'):
        model.model_validate(value)
