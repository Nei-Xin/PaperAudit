import pytest
from paperaudit.evidence_gap import candidate_gap_trigger, recheck_candidate_gap
from paperaudit.hy3_client import Hy3ResponseError
from paperaudit.models import AtomicClaim, AutoLabel, CandidateGapReview, ClaimJudgment, EvidenceCandidate


def claim(numbers=['42']):
    return AtomicClaim(claim_id='C1', text='结果42', query_en='result 42', category='results', numbers=numbers)

def pool(text='Table 1\nModel 42 7.2'):
    return [EvidenceCandidate(evidence_id='C1_e1', chunk_id='p1_b1', page=1, text=text, score=1)]

def negative():
    return ClaimJudgment(claim_id='C1', label='NO_SUPPORT_FOUND', explanation='缺少证据', claim_error_type='external_hallucination')

def test_trigger_requires_numeric_claim_and_structured_candidate():
    assert candidate_gap_trigger(claim(), pool())
    assert candidate_gap_trigger(claim(), pool('a 42 7\nb 41 6'))
    assert not candidate_gap_trigger(claim([]), pool())
    assert not candidate_gap_trigger(claim(), pool('ordinary prose with no values'))

def test_recheck_promotes_only_when_review_is_relevant_and_ids_are_valid():
    class Client:
        def review_candidate_gap(self, *args):
            return CandidateGapReview(claim_id='C1', evidence_relevant=True,
                judgment=ClaimJudgment(claim_id='C1', label='SUPPORTED', evidence_ids=['C1_e1'], explanation='表格直接支持'),
                explanation='候选表格含目标数值。')
    final, review = recheck_candidate_gap(Client(), claim(), pool(), negative(), 1)
    assert final.label == AutoLabel.SUPPORTED
    assert final.evidence_ids == ['C1_e1']
    assert review is not None

@pytest.mark.parametrize('bad', ['wrong_claim', 'irrelevant', 'invalid_id', 'api_error'])
def test_recheck_fails_closed(bad):
    class Client:
        def review_candidate_gap(self, *args):
            if bad == 'api_error': raise Hy3ResponseError('bad')
            return CandidateGapReview(claim_id='C2' if bad == 'wrong_claim' else 'C1',
                evidence_relevant=bad != 'irrelevant',
                judgment=ClaimJudgment(claim_id='C1', label='SUPPORTED', evidence_ids=['bad'] if bad == 'invalid_id' else ['C1_e1'], explanation='x'),
                explanation='x')
    final, _ = recheck_candidate_gap(Client(), claim(), pool(), negative(), 1)
    assert final.label == AutoLabel.NO_SUPPORT_FOUND

def test_existing_positive_judgment_skips_gap_call():
    class Client:
        def review_candidate_gap(self, *args): pytest.fail('must skip')
    positive=negative().model_copy(update={'label':AutoLabel.SUPPORTED,'evidence_ids':['C1_e1']})
    final, review = recheck_candidate_gap(Client(),claim(),pool(),positive,1)
    assert final == positive and review is None


def test_partial_recheck_does_not_relabel_evidence_gap_as_contradiction():
    class Client:
        def review_candidate_gap(self, *args):
            return CandidateGapReview(claim_id='C1', evidence_relevant=True,
                judgment=ClaimJudgment(claim_id='C1', label='PARTIALLY_SUPPORTED',
                    evidence_ids=['C1_e1'], explanation='数值行缺失', claim_error_type='numeric_or_metric_mismatch'),
                explanation='只确认了定性关系。')
    final, _ = recheck_candidate_gap(Client(), claim(), pool(), negative(), 1)
    assert final.label == AutoLabel.NO_SUPPORT_FOUND
