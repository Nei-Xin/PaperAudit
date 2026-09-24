import json

import pytest

from eval.unseen_e2e_experiment import score_sources, verify, sha


def test_source_scoring_keeps_omissions_and_split_failures_in_denominator():
    report = {'facts': [dict(case_id=f'C{i}', source_id=f'S{i}', reference_label=label,
                             reference_evidence=[])
                         for i, label in enumerate(['SUPPORTED', 'SUPPORTED', 'CONTRADICTED'])]}
    audits = [dict(claim={'source_id': sid}, judgment={'label': label}, candidates=[])
              for sid, label in [('S1', 'SUPPORTED'), ('S1', 'ABSTAIN'), ('S2', 'SUPPORTED')]]
    rows = score_sources(report, audits)
    assert len(rows) == 3
    assert rows[0]['missed_support'] and not rows[0]['extracted']
    assert rows[1]['missed_support'] and not rows[1]['exact_agreement']
    assert rows[2]['false_support']


def test_abstention_is_safe_withholding_but_not_exact_reference_agreement():
    report = {'facts': [dict(case_id='C', source_id='S', reference_label='NO_SUPPORT_FOUND',
                             reference_evidence=[])]}
    audits = [dict(claim={'source_id': 'S'}, judgment={'label': 'ABSTAIN'}, candidates=[])]
    row = score_sources(report, audits)[0]
    assert row['safe_withholding'] and not row['exact_agreement']
    assert row['all_reference_chunks_retrieved'] is None


def test_changed_frozen_input_is_rejected(tmp_path):
    source = tmp_path / 'report.txt'
    source.write_text('original')
    protocol = {'input_sha256': {str(source): sha(source)}, 'source_sha256': {}}
    (tmp_path / 'protocol.json').write_text(json.dumps(protocol))
    assert verify(tmp_path) == protocol
    source.write_text('changed')
    with pytest.raises(ValueError, match='Frozen input/source changed'):
        verify(tmp_path)
