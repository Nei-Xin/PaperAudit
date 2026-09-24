import json
from types import SimpleNamespace

import pytest

from eval import citation_coverage_experiment as experiment
from paperaudit.models import CitationReview


def protocol(tmp_path):
    case = {'case_id': 'P_C1', 'claim': {'claim_id': 'C1', 'text': 'result', 'category': 'results', 'query_en': 'result'},
            'candidates': [{'evidence_id': 'C1_e1', 'chunk_id': 'b1', 'page': 1, 'text': 'Verified result.', 'score': 1}],
            'judgment': {'claim_id': 'C1', 'label': 'SUPPORTED', 'evidence_ids': ['C1_e1'], 'explanation': 'supported'},
            'reference_label': 'SUPPORTED', 'control': False}
    experiment.save(tmp_path / 'protocol.json', {'sha256': {}, 'cases': [case]})


def run(tmp_path):
    return experiment.run(tmp_path, 'https://example.invalid', 'fake', 'secret-not-to-save')


def test_replay_runs_local_validator_and_resume_does_not_repeat_api(tmp_path, monkeypatch):
    protocol(tmp_path)
    class Client:
        calls = 0

        def __init__(self, settings):
            self.raw_outputs = []
            self._client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **kw: None)), close=lambda: None)

        def review_citation_coverage(self, claim, candidates, judgment):
            Client.calls += 1
            return CitationReview(claim_id='C1', complete=True, evidence_ids=['C1_e1'],
                                  aspects=[{'aspect': 'result', 'reasoning': 'claimed support',
                                            'citations': [{'evidence_id': 'C1_e1', 'quote': 'fabricated text'}]}],
                                  missing_aspects=[], explanation='supported')

        def repair_citation_coverage(self, claim, candidates, rejected):
            return rejected

    monkeypatch.setattr(experiment, 'Hy3Client', Client)
    result = run(tmp_path)
    assert result['invalid_complete_reviews'] == 1
    assert result['after_reference_agreement'] == 0
    assert run(tmp_path) == result
    assert Client.calls == 1
    assert all('secret-not-to-save' not in path.read_text() for path in tmp_path.rglob('*.json'))


def test_interrupted_request_and_changed_runtime_are_not_silently_replayed(tmp_path):
    protocol(tmp_path)
    (tmp_path / 'results').mkdir()
    experiment.save(tmp_path / 'results/P_C1.requests.json', [{'status': 'started'}])
    with pytest.raises(ValueError, match='Interrupted request'):
        run(tmp_path)
    experiment.save(tmp_path / 'runtime.json', {'model': 'changed'})
    with pytest.raises(ValueError, match='Runtime changed'):
        run(tmp_path)


def test_changed_frozen_inputs_are_rejected_before_api(tmp_path):
    file = tmp_path / 'source'
    file.write_text('modified')
    experiment.save(tmp_path / 'protocol.json', {'sha256': {str(file): 'old'}, 'cases': []})
    with pytest.raises(ValueError, match='Frozen input/source changed'):
        run(tmp_path)
