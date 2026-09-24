import json

import pytest

from paperaudit.audit_rules import apply_citation_review
from paperaudit.config import Settings
from paperaudit.hy3_client import Hy3Client, Hy3ResponseError
from paperaudit.models import (
    AtomicClaim, AutoLabel, CitationReview, ClaimAudit, ClaimCategory, ClaimJudgment,
    EvidenceCandidate, EvidenceErrorType, Severity,
)
from paperaudit.service import AuditService
from test_missing_support import MissingClient, _paper


def candidates():
    return [
        EvidenceCandidate(evidence_id='C1_e1', chunk_id='p1_b1', page=1, score=1,
                          text='Model A needs 27 times less computation than B.'),
        EvidenceCandidate(evidence_id='C1_e2', chunk_id='p1_b2', page=1, score=.5,
                          text='Model    Mult-Adds\nA-224    569\nB    15300'),
        EvidenceCandidate(evidence_id='C1_e3', chunk_id='p1_b3', page=1, score=.2,
                          text='Unrelated architecture details.'),
    ]


def original():
    return ClaimJudgment(claim_id='C1', label='SUPPORTED', evidence_ids=['C1_e1'], explanation='支持。')


def review():
    return CitationReview(
        claim_id='C1', complete=True, evidence_ids=['C1_e1', 'C1_e2'], missing_aspects=[],
        explanation='配置行和比较结果共同支持。',
        aspects=[
            {'aspect': '配置', 'reasoning': '表格明确为224配置。',
             'citations': [{'evidence_id': 'C1_e2', 'quote': 'A-224    569'}]},
            {'aspect': '比较倍数与计算量', 'reasoning': '15300 / 569 约为26.89，四舍五入为27倍。',
             'citations': [{'evidence_id': 'C1_e1', 'quote': candidates()[0].text},
                           {'evidence_id': 'C1_e2', 'quote': 'Model Mult-Adds A-224 569 B 15300'}]},
        ],
    )


def test_explicit_model_selection_adds_configuration_without_appending_all_candidates():
    result = apply_citation_review(original(), candidates(), review())
    assert result.label == AutoLabel.SUPPORTED
    assert result.evidence_ids == ['C1_e1', 'C1_e2']
    assert original().evidence_ids == ['C1_e1']


@pytest.mark.parametrize('fault', [
    'missing', 'wrong_claim', 'unknown_id', 'fabricated_quote', 'joined_quote',
    'wrong_source', 'empty_quote', 'uncited_id', 'unselected_quote', 'no_aspects', 'no_review',
])
def test_incomplete_or_unverifiable_support_abstains(fault):
    data = review().model_dump()
    if fault == 'missing':
        data.update(complete=False, missing_aspects=['输入配置缺失'])
    elif fault == 'wrong_claim':
        data['claim_id'] = 'C2'
    elif fault == 'unknown_id':
        data['evidence_ids'].append('C1_e999')
    elif fault in ('fabricated_quote', 'joined_quote', 'empty_quote'):
        data['aspects'][0]['citations'][0]['quote'] = {
            'fabricated_quote': 'A-224 1', 'joined_quote': 'A-224 B 15300', 'empty_quote': '   ',
        }[fault]
    elif fault == 'wrong_source':
        data['aspects'][0]['citations'][0]['evidence_id'] = 'C1_e1'
    elif fault == 'uncited_id':
        data['evidence_ids'].append('C1_e3')
    elif fault == 'unselected_quote':
        data['evidence_ids'] = ['C1_e1']
    elif fault == 'no_aspects':
        data['aspects'] = []
    result = apply_citation_review(original(), candidates(),
                                   None if fault == 'no_review' else CitationReview.model_validate(data))
    assert result.label == AutoLabel.ABSTAIN
    assert result.evidence_ids == []
    assert result.claim_error_type is None
    assert result.severity == Severity.NONE


def test_legacy_audit_loads_without_review_and_new_record_roundtrips():
    old = dict(claim=AtomicClaim(claim_id='C1', text='A-224约少27倍计算量', query_en='A-224 27 times less computation', category='results'),
               candidates=candidates(), judgment=original())
    assert ClaimAudit(**old).citation_review is None
    audit = ClaimAudit(**old, citation_review=review(), judgment_before_citation_review=original())
    assert ClaimAudit.model_validate_json(audit.model_dump_json()) == audit


@pytest.mark.parametrize('outcome', ['missing', 'schema_failure', 'complete'])
def test_service_checks_support_recovered_by_supplement_once_and_preserves_page_error(outcome):
    class Client(MissingClient):
        coverage_calls = 0

        def review_citation_coverage(self, claim, candidates, judgment):
            self.coverage_calls += 1
            if outcome == 'schema_failure':
                raise Hy3ResponseError('bad schema')
            result = super().review_citation_coverage(claim, candidates, judgment)
            if outcome == 'missing':
                return result.model_copy(update={'complete': False, 'missing_aspects': ['配置']})
            return result

    client = Client(anchor='第999页')
    run = AuditService(Settings(api_base='https://example.invalid', api_key='test', model='fake'), client).audit(
        _paper(), '报告', [ClaimCategory.METHOD])
    audit = run.audits[0]
    assert client.coverage_calls == 1
    assert audit.judgment_before_citation_review.label == AutoLabel.SUPPORTED
    assert audit.judgment.label == (AutoLabel.SUPPORTED if outcome == 'complete' else AutoLabel.ABSTAIN)
    assert audit.judgment.evidence_error_type == EvidenceErrorType.FABRICATED_EVIDENCE
    assert audit.judgment.severity == Severity.HIGH


def test_client_requests_coverage_with_prior_selection_and_repairs_schema(monkeypatch):
    client = Hy3Client(Settings(api_base='https://example.invalid', api_key='test', model='fake'))
    prompts = []
    responses = iter(['{}', json.dumps(review().model_dump())])

    def complete(prompt, effort=None):
        prompts.append(prompt)
        return next(responses)

    monkeypatch.setattr(client, '_complete', complete)
    claim = AtomicClaim(claim_id='C1', text='A-224计算少27倍', query_en='A-224 27 times less computation', category='results')
    assert client.review_citation_coverage(claim, candidates(), original()) == review()
    assert len(prompts) == 2
    assert 'EVERY asserted aspect' in prompts[0]
    assert 'previous_judgment' in prompts[0]
    assert 'A-224' in prompts[0]
    client._client.close()


def test_reconstructed_table_header_is_rejected_even_when_all_words_exist():
    pool = [EvidenceCandidate(evidence_id='C1_e1', chunk_id='p1_b1', page=1, score=1,
                             text='Model\nImageNet\nMillion\nMillion\nAccuracy\nMult-Adds\nParameters')]
    response = CitationReview(claim_id='C1', complete=True, evidence_ids=['C1_e1'],
                              aspects=[{'aspect': '计算单位', 'reasoning': '表头',
                                        'citations': [{'evidence_id': 'C1_e1',
                                                       'quote': 'Million Mult-Adds'}]}],
                              missing_aspects=[], explanation='表头支持。')
    assert apply_citation_review(original(), pool, response).label == AutoLabel.ABSTAIN


def test_semantic_equivalence_does_not_require_literal_claim_words_or_ratio():
    pool = candidates()
    response = review()
    # The local gate validates provenance, not Chinese/English token overlap or arithmetic.
    response.aspects[1].citations = response.aspects[1].citations[1:]
    response.evidence_ids = ['C1_e2']
    result = apply_citation_review(original(), pool, response)
    assert result.label == AutoLabel.SUPPORTED
    assert result.evidence_ids == ['C1_e2']


@pytest.mark.parametrize('label', ['ABSTAIN', 'CONTRADICTED', 'PARTIALLY_SUPPORTED', 'NO_SUPPORT_FOUND'])
def test_non_supported_judgments_do_not_get_promoted_by_coverage_review(label):
    judgment = original().model_copy(update={'label': AutoLabel(label)})
    assert apply_citation_review(judgment, candidates(), review()) == judgment


@pytest.mark.parametrize('outcome', ['repaired', 'still_invalid', 'gap', 'schema_failure'])
def test_local_quote_repair_is_bounded_and_never_weakens_validation(outcome):
    from paperaudit.citation_review import review_supported_citations

    bad = review()
    bad.aspects[0].citations[0].quote = 'Invented quote'

    class Client:
        reviews = repairs = 0

        def review_citation_coverage(self, *args):
            self.reviews += 1
            return bad

        def repair_citation_coverage(self, claim, pool, rejected):
            self.repairs += 1
            assert rejected == bad
            if outcome == 'schema_failure':
                raise Hy3ResponseError('invalid schema')
            if outcome == 'still_invalid':
                return bad
            if outcome == 'gap':
                return review().model_copy(update={'complete': False, 'missing_aspects': ['配置']})
            return review()

    client = Client()
    claim = AtomicClaim(claim_id='C1', text='配置A-224少27倍计算量', category='results', query_en='A-224 computation')
    final, last, first = review_supported_citations(client, claim, candidates(), original())
    assert client.reviews == client.repairs == 1
    assert first == bad
    assert final.label == (AutoLabel.SUPPORTED if outcome == 'repaired' else AutoLabel.ABSTAIN)
    assert (last is None) == (outcome == 'schema_failure')


def test_missing_aspect_is_not_retried_even_if_other_quotes_are_invalid():
    from paperaudit.citation_review import review_supported_citations

    class Client:
        def review_citation_coverage(self, *args):
            return review().model_copy(update={'complete': False, 'missing_aspects': ['configuration']})

        def repair_citation_coverage(self, *args):
            pytest.fail('Evidence gaps must not trigger quotation repair')

    claim = AtomicClaim(claim_id='C1', text='A-224', category='results', query_en='A-224')
    result, _, before = review_supported_citations(Client(), claim, candidates(), original())
    assert result.label == AutoLabel.ABSTAIN
    assert before is None


def test_service_persists_both_reviews_when_quote_repair_is_needed():
    class Client(MissingClient):
        def review_citation_coverage(self, claim, candidates, judgment):
            valid = super().review_citation_coverage(claim, candidates, judgment)
            valid.aspects[0].citations[0].quote = 'Not in the source'
            self.judgment = judgment
            return valid

        def repair_citation_coverage(self, claim, candidates, rejected):
            return super().review_citation_coverage(claim, candidates, self.judgment)

    run = AuditService(Settings(api_base='https://example.invalid', api_key='test', model='fake'), Client()).audit(
        _paper(), '报告', [ClaimCategory.METHOD])
    audit = run.audits[0]
    assert audit.judgment.label == AutoLabel.SUPPORTED
    assert audit.citation_review_before_repair.aspects[0].citations[0].quote == 'Not in the source'
    assert audit.citation_review.aspects[0].citations[0].quote in _paper().chunks[1].content
    assert ClaimAudit.model_validate_json(audit.model_dump_json()) == audit
