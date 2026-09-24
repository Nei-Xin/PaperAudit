import json

import pytest

from paperaudit.audit_rules import apply_citation_review
from paperaudit.citation_review import review_citations
from paperaudit.config import Settings
from paperaudit.hy3_client import Hy3Client, Hy3ResponseError
from paperaudit.models import (
    AtomicClaim, AutoLabel, CitationReview, ClaimAudit, ClaimExtraction,
    ClaimJudgment, EvidenceCandidate, JudgmentBatch, PaperChunk, ParsedPaper,
)
from paperaudit.service import AuditService
from paperaudit.ui.components import build_review_status_html
from paperaudit.reporting import _render_review


def claim():
    return AtomicClaim(claim_id='C1', text='Model A在Dataset R上的错误率为8%。',
                       query_en='Model A Dataset R error 8', category='results')


def pool():
    return [EvidenceCandidate(evidence_id='C1_e1', chunk_id='caption', page=1, score=1,
                              text='Table 2: Model A error on Dataset R.'),
            EvidenceCandidate(evidence_id='C1_e2', chunk_id='row', page=1, score=1,
                              text='Model Error (%)\nA 12\nB 8')]


def judgment():
    return ClaimJudgment(claim_id='C1', label='CONTRADICTED', evidence_ids=['C1_e1'],
                         explanation='错误率为12%，与8%冲突。', suggestion='改为12%。',
                         claim_error_type='numeric_or_metric_mismatch', severity='high')


def review():
    return CitationReview(claim_id='C1', reviewed_label='CONTRADICTED', complete=True,
        evidence_ids=['C1_e1', 'C1_e2'], missing_aspects=[], explanation='同一配置下12与8冲突。',
        suggestion_verified=True,
        aspects=[dict(aspect='主体和设置', reasoning='同一数据集的模型A。',
                      citations=[dict(evidence_id='C1_e1', quote=pool()[0].text)]),
                 dict(aspect='冲突指标与数值', reasoning='错误率是12%，而非8%。',
                      citations=[dict(evidence_id='C1_e2', quote=pool()[1].text)])])


@pytest.mark.parametrize('fault', ['missing_row', 'wrong_label', 'wrong_claim', 'wrong_quote',
                                  'unknown_id', 'no_review', 'empty_aspects', 'uncited_id'])
def test_unverifiable_conflict_clears_accusation_and_corrected_value(fault):
    result = review()
    if fault == 'missing_row':
        result = result.model_copy(update={'complete': False, 'missing_aspects': ['数值行']})
    elif fault == 'wrong_label':
        result.reviewed_label = 'SUPPORTED'
    elif fault == 'wrong_claim':
        result.claim_id = 'other'
    elif fault == 'wrong_quote':
        result.aspects[1].citations[0].quote = 'A 15'
    elif fault == 'unknown_id':
        result.aspects[1].citations[0].evidence_id = 'other_claim_e1'
    elif fault == 'no_review':
        result = None
    elif fault == 'empty_aspects':
        result.aspects = []
    elif fault == 'uncited_id':
        result.evidence_ids = ['C1_e1']
    final = apply_citation_review(judgment(), pool(), result)
    assert final.label == AutoLabel.ABSTAIN
    assert final.evidence_ids == []
    assert final.severity.value == 'none'
    assert final.claim_error_type is None and final.evidence_error_type is None
    assert final.suggestion is None and '12' not in final.explanation


def test_verified_conflict_keeps_label_and_explicitly_selects_required_row():
    final = apply_citation_review(judgment(), pool(), review())
    assert final.label == AutoLabel.CONTRADICTED
    assert final.evidence_ids == ['C1_e1', 'C1_e2']
    assert final.suggestion == judgment().suggestion


def test_contradiction_with_unverified_correction_abstains():
    unverified = review().model_copy(update={
        'suggestion_verified': False,
        'suggestion_missing_aspects': ['对照模型的纠正数值'],
    })
    final = apply_citation_review(judgment(), pool(), unverified)
    assert final.label == AutoLabel.ABSTAIN
    assert final.suggestion is None


def test_contradiction_requires_explicit_suggestion_verification_for_new_reviews():
    legacy_shape = review().model_copy(update={'suggestion_verified': None})
    final = apply_citation_review(judgment(), pool(), legacy_shape)
    assert final.label == AutoLabel.ABSTAIN


def test_service_does_not_duplicate_candidate_gap_review_for_contradiction():
    class Client:
        def extract_claims(self, *args):
            return ClaimExtraction(claims=[claim().model_copy(update={'numbers': ['8', '12']})])

        def judge_claims(self, batch, *args):
            c, candidates = batch[0]
            return JudgmentBatch(judgments=[judgment().model_copy(update={
                'claim_id': c.claim_id,
                'evidence_ids': [candidates[0].evidence_id],
            })])

        def review_candidate_gap(self, *args):
            pytest.fail('contradictions should go directly to citation coverage review')

        def review_citation_coverage(self, c, candidates, j):
            return CitationReview(
                claim_id=c.claim_id, reviewed_label='CONTRADICTED', complete=True,
                evidence_ids=[x.evidence_id for x in candidates[:2]],
                missing_aspects=[], explanation='复核原文。', suggestion_verified=True,
                aspects=[dict(aspect='冲突', reasoning='同一配置下数值冲突。', citations=[
                    dict(evidence_id=x.evidence_id, quote=x.text) for x in candidates[:2]
                ])],
            )

    paper = ParsedPaper(title='Test', page_count=1,
                        chunks=[PaperChunk(chunk_id=c.chunk_id, page=c.page, content=c.text)
                                for c in pool()])
    run = AuditService(Settings(api_base='https://example.invalid', api_key='test', model='fake'), Client()).audit(
        paper, claim().text, [claim().category])
    assert run.audits[0].judgment.label == AutoLabel.CONTRADICTED


@pytest.mark.parametrize('mode', ['caption_only', 'valid', 'schema_failure', 'repair_failure'])
def test_service_routes_conflicts_through_gate_and_persists_provenance(mode):
    class Client:
        reviews = repairs = 0

        def extract_claims(self, *args):
            return ClaimExtraction(claims=[claim()])

        def judge_claims(self, batch, *args):
            c, candidates = batch[0]
            return JudgmentBatch(judgments=[judgment().model_copy(update={
                'claim_id': c.claim_id, 'evidence_ids': [candidates[0].evidence_id]})])

        def review_citation_coverage(self, c, candidates, j):
            self.reviews += 1
            assert j.label == AutoLabel.CONTRADICTED
            if mode == 'schema_failure':
                raise Hy3ResponseError('bad schema')
            row = next((x for x in candidates if x.chunk_id == 'row'), None)
            caption = next(x for x in candidates if x.chunk_id == 'caption')
            refs = [caption] + ([row] if row else [])
            return CitationReview(claim_id=c.claim_id, reviewed_label='CONTRADICTED',
                complete=row is not None, evidence_ids=[x.evidence_id for x in refs],
                missing_aspects=[] if row else ['数值行'], explanation='复核原文。',
                suggestion_verified=True if row else False,
                aspects=[dict(aspect='冲突', reasoning='核对同一配置。', citations=[dict(
                    evidence_id=x.evidence_id, quote='invented' if mode == 'repair_failure' else x.text)
                    for x in refs])])

        def repair_citation_coverage(self, *args):
            self.repairs += 1
            raise Hy3ResponseError('bad schema')

    chunks = pool()[:1] if mode == 'caption_only' else pool()
    paper = ParsedPaper(title='Test', page_count=1, chunks=[PaperChunk(
        chunk_id=c.chunk_id, page=c.page, content=c.text) for c in chunks])
    client = Client()
    run = AuditService(Settings(api_base='https://example.invalid', api_key='test', model='fake'), client).audit(
        paper, claim().text, [claim().category])
    audit = run.audits[0]
    assert audit.judgment.label == (AutoLabel.CONTRADICTED if mode == 'valid' else AutoLabel.ABSTAIN)
    assert client.reviews == 1 and client.repairs == (mode == 'repair_failure')
    assert audit.judgment_before_citation_review.label == AutoLabel.CONTRADICTED
    assert ClaimAudit.model_validate_json(audit.model_dump_json()) == audit
    if mode == 'repair_failure':
        assert '未通过' in build_review_status_html(audit)
        assert '未通过' in '\n'.join(_render_review(audit))


def test_client_reviews_conflict_without_borrowing_other_claims_or_prior_corrections(monkeypatch):
    client = Hy3Client(Settings(api_base='https://example.invalid', api_key='test', model='fake'))
    prompts = []
    monkeypatch.setattr(client, '_complete', lambda prompt, *args: (prompts.append(prompt) or review().model_dump_json()))
    try:
        result = client.review_citation_coverage(claim(), pool(), judgment())
        client.repair_citation_coverage(claim(), pool(), result)
        assert 'SAME subject' in prompts[0]
        assert 'a caption alone never proves a numeric conflict' in prompts[0]
        assert 'other claims from a batch' in prompts[0]
        assert 'reviewed_label=CONTRADICTED' in prompts[1]
    finally:
        client._client.close()


def test_review_type_mismatch_cannot_be_repaired_into_a_contradiction():
    class Client:
        def review_citation_coverage(self, *args):
            return review().model_copy(update={'reviewed_label': 'SUPPORTED'})
        def repair_citation_coverage(self, *args):
            pytest.fail('Wrong verdict type is not a quote formatting error')
    final, _, before = review_citations(Client(), claim(), pool(), judgment())
    assert final.label == AutoLabel.ABSTAIN and before is None


@pytest.mark.parametrize('repair_outcome', ['valid', 'invalid', 'wrong_verdict', 'gap'])
def test_contradiction_quote_repair_runs_once_and_never_changes_verdict_target(repair_outcome):
    class Client:
        reviews = repairs = 0
        def review_citation_coverage(self, *args):
            self.reviews += 1
            bad = review()
            bad.aspects[1].citations[0].quote = 'A 12.0'
            return bad
        def repair_citation_coverage(self, c, candidates, previous):
            self.repairs += 1
            assert previous.reviewed_label == 'CONTRADICTED'
            fixed = review()
            if repair_outcome == 'invalid':
                return previous
            if repair_outcome == 'wrong_verdict':
                fixed.reviewed_label = 'SUPPORTED'
            if repair_outcome == 'gap':
                fixed.complete = False
                fixed.missing_aspects = ['指标对应关系']
            return fixed
    client = Client()
    final, last, first = review_citations(client, claim(), pool(), judgment())
    assert client.reviews == client.repairs == 1
    assert first is not None and last is not None
    assert final.label == (AutoLabel.CONTRADICTED if repair_outcome == 'valid' else AutoLabel.ABSTAIN)


def test_failed_schema_review_is_visible_in_ui_and_export():
    audit = ClaimAudit(claim=claim(), candidates=pool(),
                       judgment=apply_citation_review(judgment(), pool(), None),
                       judgment_before_citation_review=judgment())
    assert '未获得有效' in build_review_status_html(audit)
    assert '未获得有效' in '\n'.join(_render_review(audit))
