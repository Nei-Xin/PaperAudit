import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from eval import evidence_gap_experiment as experiment
from paperaudit.models import ClaimJudgment, JudgmentBatch


def protocol(tmp_path):
    case = {'case_id': 'NEW01', 'claim': {'claim_id': 'NEW01', 'text': 'result',
            'category': 'results', 'query_en': 'result'}, 'page_count': 1,
            'reference_label': 'CONTRADICTED', 'control_chunks': None,
            'candidates': [{'evidence_id': 'NEW01_e1', 'chunk_id': 'p1_b1', 'page': 1,
                            'text': 'Table 1: measured error is 42.7%.', 'score': 1}]}
    experiment.save(tmp_path/'protocol.json', {'cases': [case], 'input_sha256': {}})


def run(tmp_path):
    return experiment.run(tmp_path, 'baseline', 'https://example.invalid', 'fake', 'never-save-secret')


def test_baseline_replay_is_not_billed_again_and_does_not_save_credentials(tmp_path, monkeypatch):
    protocol(tmp_path)
    class Client:
        calls = 0
        def __init__(self, settings):
            assert settings.api_key == 'never-save-secret'
            self.raw_outputs = []
            self._client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **kwargs: None)), close=lambda: None)

        def judge_claims(self, pairs, page_count):
            Client.calls += 1
            return JudgmentBatch(judgments=[ClaimJudgment(claim_id='NEW01', label='CONTRADICTED',
                evidence_ids=['NEW01_e1'], explanation='错误率不一致。',claim_error_type='numeric_or_metric_mismatch')])

    monkeypatch.setattr(experiment, 'Hy3Client', Client)
    first = run(tmp_path)
    assert first['reference_agreement'] == 1
    assert first['false_support'] == 0
    assert run(tmp_path) == first
    assert Client.calls == 1
    for p in tmp_path.rglob('*.json'):
        assert 'never-save-secret' not in p.read_text()


def test_interrupted_request_and_modified_runtime_require_explicit_recovery(tmp_path):
    protocol(tmp_path)
    (tmp_path/'baseline/results').mkdir(parents=True)
    experiment.save(tmp_path/'baseline/results/NEW01.requests.json', [{'status':'started'}])
    with pytest.raises(ValueError, match='Interrupted request'):
        run(tmp_path)
    experiment.save(tmp_path/'baseline/runtime.json', {'model':'changed'})
    with pytest.raises(ValueError, match='runtime or source changed'):
        run(tmp_path)


def test_modified_inputs_are_refused_before_any_api_call(tmp_path):
    p=tmp_path/'source.json'
    p.write_text('changed')
    experiment.save(tmp_path/'protocol.json', {'cases':[], 'input_sha256':{str(p):'old'}})
    with pytest.raises(ValueError, match='Frozen input changed'):
        run(tmp_path)
