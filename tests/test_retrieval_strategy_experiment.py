import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from eval import retrieval_strategy_experiment as experiment
from paperaudit.models import ClaimJudgment, JudgmentBatch


def protocol(tmp_path):
    case = {'case_id': 'paper_C1', 'paper_id': 'paper', 'page_count': 1,
            'claim': {'claim_id': 'C1', 'text': '结果', 'category': 'results', 'query_en': 'result'},
            'reference_label': 'SUPPORTED',
            'candidates': {arm: [{'evidence_id': 'C1_e1', 'chunk_id': 'b', 'page': 1,
                                 'text': 'A verified result.', 'score': 1}] for arm in experiment.ARMS}}
    experiment.save(tmp_path / 'protocol.json', {'source_sha256': {}, 'cases': [case]})
    return case


def test_pilot_validates_references_and_never_persists_credentials(tmp_path, monkeypatch):
    protocol(tmp_path)
    class Client:
        def __init__(self, settings):
            assert settings.api_key == 'test-secret-not-to-be-saved'
            self.raw_outputs = []
            self._client = SimpleNamespace(
                chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **kw: None)),
                close=lambda: None,
            )

        def judge_claims(self, batch, page_count):
            return JudgmentBatch(judgments=[ClaimJudgment(
                claim_id='C1', label='SUPPORTED', evidence_ids=['invented'], explanation='test')])
    monkeypatch.setattr(experiment, 'Hy3Client', Client)
    summary = experiment.run(tmp_path, api_base='https://example.invalid/v1', model='fake',
                             api_key='test-secret-not-to-be-saved', limit=1)
    assert summary['planned_per_arm'] == 1
    assert summary['arms']['plain']['abstain'] == 1
    assert summary['arms']['plain']['invalid_references'] == 1
    assert summary['arms']['plain']['reference_agreement'] == 0
    assert summary['arms']['hybrid']['completed'] == 0
    for path in tmp_path.rglob('*.json'):
        assert 'test-secret-not-to-be-saved' not in path.read_text()


def test_pilot_refuses_changed_source_and_changed_runtime(tmp_path):
    protocol(tmp_path)
    source = tmp_path / 'source.py'
    source.write_text('changed')
    experiment.save(tmp_path / 'protocol.json', {'source_sha256': {str(source): 'not-current'}, 'cases': []})
    with pytest.raises(ValueError, match='Source changed'):
        experiment.run(tmp_path, api_base='https://example.invalid', model='fake', api_key='unused', limit=1)
    protocol(tmp_path)
    experiment.save(tmp_path / 'runtime.json', {'model': 'different'})
    with pytest.raises(ValueError, match='Runtime differs'):
        experiment.run(tmp_path, api_base='https://example.invalid', model='fake', api_key='unused', limit=1)


def test_incomplete_results_remain_visible_in_summary(tmp_path):
    protocol(tmp_path)
    (tmp_path / 'results').mkdir()
    experiment.save(tmp_path / 'results/paper_C1_plain.json', {
        'status': 'error', 'seconds': 1, 'requests': [{'status': 'error', 'http_status': 401}]})
    summary = experiment.summarize(tmp_path)
    assert summary['planned_per_arm'] == 1
    assert summary['arms']['plain']['failed'] == 1
    assert summary['arms']['structural']['completed'] == 0
