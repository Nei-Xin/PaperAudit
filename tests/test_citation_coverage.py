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
