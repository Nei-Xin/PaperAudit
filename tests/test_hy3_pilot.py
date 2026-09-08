import json

from eval.annotate_hy3_pilot import Labels, validate_labels
from eval import run_hy3_pilot as pilot


def test_reference_checks_ids_and_quotes():
    import pytest
    item={'fact_id':'F01','label':'SUPPORTED','error_type':None,'severity':'none',
          'citation_status':'valid','evidence':[{'chunk_id':'p1_b1','quote':'actual finding'}],
          'explanation':'原文支持'}
    labels=Labels.model_validate({'facts':[item]})
    assert validate_labels(labels,[{'fact_id':'F01'}],{'p1_b1':{'content':'An actual finding.'}})=={}
    assert 'F01' in validate_labels(labels,[{'fact_id':'F01'}],{'p1_b1':{'content':'Unrelated.'}})
    with pytest.raises(ValueError,match='IDs'):
        validate_labels(labels,[{'fact_id':'F02'}],{})


def test_missing_or_abstained_sources_do_not_count_as_agreement(tmp_path,monkeypatch):
    monkeypatch.setattr(pilot,'OUT',tmp_path)
    reports=[{'report_id':rid,'tier':tier} for rid,tier in [('A','high'),('B','medium'),('C','low')]]
    pilot.save(tmp_path/'protocol.json',{'reports':reports})
    pilot.save(tmp_path/'blind_inputs.json',[{'report_id':r['report_id'],'facts':[{'fact_id':'F01','source_id':'S1'}]} for r in reports])
    for report in reports:
        for i in range(1,4):
            audits=[] if report['report_id']=='B' else [{'claim':{'source_id':'S1'},'judgment':{'label':'ABSTAIN' if report['report_id']=='C' else 'SUPPORTED'}}]
            pilot.save(tmp_path/f'run_{i}'/(report['report_id']+'.json'),{
                'status':'ok','seconds':1,'requests':[{'usage':{'total_tokens':10}}],
                'audit':{'audits':audits,'summary':{'total_score':90 if report['report_id']=='A' else 50}}})
    pilot.summarize()
    summary=json.loads((tmp_path/'summary.json').read_text(encoding='utf-8'))
    assert [r['source_label_agreement'] for r in summary['reports']]==[1,0,0]
    assert summary['strict_tier_order'] is False  # ties are not a successful ordering
    assert summary['projected_96_audit_tokens']==960


def test_partial_runs_have_no_stability_or_budget_projection(tmp_path,monkeypatch):
    monkeypatch.setattr(pilot,'OUT',tmp_path)
    reports=[{'report_id':rid,'tier':tier} for rid,tier in [('A','high'),('B','medium'),('C','low')]]
    pilot.save(tmp_path/'protocol.json',{'reports':reports})
    pilot.save(tmp_path/'blind_inputs.json',[{'report_id':r['report_id'],'facts':[]} for r in reports])
    pilot.summarize()
    summary=pilot.read(tmp_path/'summary.json')
    assert summary['complete'] is False
    assert summary['strict_tier_order'] is None
    assert summary['projected_96_audit_tokens'] is None
    assert all(r['score_std'] is None for r in summary['reports'])
