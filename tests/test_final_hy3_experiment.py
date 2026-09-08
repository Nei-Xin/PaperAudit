import json
from pathlib import Path
import pytest
from eval import final_hy3_experiment as experiment
from eval import analyze_final_hy3 as analysis

def test_incomplete_inputs_cannot_freeze(tmp_path,monkeypatch):
    monkeypatch.setattr(experiment,'OUT',tmp_path)
    (tmp_path/'reference_freeze.json').write_text('{}')
    (tmp_path/'inputs').mkdir()
    (tmp_path/'inputs/pending.json').write_text('[{"paper_id":"P03"}]')
    with pytest.raises(AssertionError,match='Inputs incomplete'):
        experiment.freeze()
    assert not (tmp_path/'protocol.json').exists()

def test_report_assembly_preserves_fact_source_and_citation(tmp_path,monkeypatch):
    monkeypatch.setattr(experiment,'OUT',tmp_path)
    facts=[{'text':f'第{i}条待核查内容。','page':i} for i in range(1,13)]
    result=experiment.build_report('P01','high',facts)
    blind=json.loads((tmp_path/'inputs/blind_P01_high.json').read_text(encoding='utf-8'))
    assert len({f['source_id'] for f in blind['facts']})==12
    assert '（证据：论文第12页）' in blind['report_text']
    assert result['repeats']==3

def test_empty_metric_denominator_is_not_zero_success():
    assert analysis.ratio(0,0) is None
    assert analysis.ratio(0,10)==0
