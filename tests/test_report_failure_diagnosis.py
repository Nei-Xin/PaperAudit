import hashlib
import json

import pytest

from eval.diagnose_report_failures import (
    Inputs, aggregate_prediction, evidence_overlap, extraction_quote_issues,
    outcome, quote_matches, review_responses,
)


def test_aggregation_retains_failed_partial_and_abstained_denominators():
    assert outcome(False, True, "audit_failed", None, "SUPPORTED") == "audit_failed"
    assert outcome(True, False, "full", "SUPPORTED", None) == "reference_unresolved"
    assert outcome(True, True, "partial", None, "SUPPORTED") == "extraction_partial"
    assert outcome(True, True, "full", None, "SUPPORTED") == "abstain"
    audits = {"C1": {"judgment": {"label": "SUPPORTED"}}, "C2": {"judgment": {"label": "CONTRADICTED"}}}
    match = {"coverage": "full", "claim_ids": ["C1", "C2"]}
    assert aggregate_prediction(match, audits)[0] == "CONTRADICTED"
    audits["C2"]["judgment"]["label"] = "ABSTAIN"
    assert aggregate_prediction(match, audits)[0] is None
    match["coverage"] = "partial"
    audits["C2"]["judgment"]["label"] = "SUPPORTED"
    assert aggregate_prediction(match, audits)[0] is None


@pytest.mark.parametrize("claim_ids", [["C1", "C1"], ["unknown"]])
def test_corrupt_alignment_does_not_silently_change_denominator(claim_ids):
    with pytest.raises(ValueError, match="claim IDs"):
        aggregate_prediction({"coverage": "full", "claim_ids": claim_ids}, {"C1": {}})


def test_evidence_overlap_requires_actual_quote_not_just_chunk_id():
    reference = {"evidence": [{"chunk_id": "p1", "quote": "exact source text"}]}
    chunks = {"p1": {"content": "The exact source text is here."}}
    selected = [{"candidates": [{"chunk_id": "p1", "text": "truncated text"}]}]
    assert evidence_overlap(reference, selected, chunks)["status"] == "none"
    selected[0]["candidates"][0]["text"] = chunks["p1"]["content"]
    assert evidence_overlap(reference, selected, chunks)["status"] == "all"
    reference["evidence"].append({"chunk_id": "p2", "quote": "a second passage"})
    chunks["p2"] = {"content": "a second passage"}
    assert evidence_overlap(reference, selected, chunks)["status"] == "some"
    reference["evidence"][1]["quote"] = "fabricated"
    assert evidence_overlap(reference, selected, chunks)["status"] == "invalid_reference_quote"


def test_reference_quote_normalization_does_not_remove_semantic_hyphens():
    assert quote_matches("parameter efficiency", "param-\neter efﬁciency")
    assert quote_matches("state-of-the-art", "state-of-the-art")
    assert not quote_matches("stateoftheart", "state-of-the-art")
    assert not quote_matches("", "source")


def test_review_repair_uses_last_response_and_preserves_raw_index():
    run = {"raw_outputs": ["unparseable", json.dumps({"evidence_sufficient": True,
        "judgment": {"claim_id": "C1", "label": "SUPPORTED"}}),
        json.dumps({"evidence_sufficient": True,
        "judgment": {"claim_id": "C1", "label": "SUPPORTED", "evidence_ids": ["C1_e1"]}})]}
    reviews = review_responses(run)["C1"]
    assert reviews[0]["evidence_ids"] == []
    assert reviews[-1]["evidence_ids"] == ["C1_e1"]
    assert reviews[-1]["raw_output_index"] == 3


def test_failed_extraction_reports_nonliteral_quotes_without_calling_model():
    sources = {"S1": "recall提升18.83%、ndcg提升14.14%"}
    run = {"raw_outputs": [json.dumps({"sources": [{"source_id": "S1", "claims": [
        {"claim_id": "C1", "source_quote": "recall提升18.83%"},
        {"claim_id": "C2", "source_quote": "平均ndcg提升14.14%"},
    ]}]})]}
    issues = extraction_quote_issues(run, sources)
    assert len(issues) == 1
    assert issues[0]["claim_id"] == "C2"


def test_input_hashes_accept_windows_paths_and_reject_tampered_consumed_files(tmp_path):
    (tmp_path / "inputs").mkdir()
    target = tmp_path / "inputs/data.json"
    target.write_text('{"value": 1}')
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    (tmp_path / "protocol.json").write_text(json.dumps({"input_sha256": {"inputs\\data.json": digest}}))
    for name in ("reference_freeze", "alignment_freeze"):
        (tmp_path / f"{name}.json").write_text('{"sha256": {}}')
    inputs = Inputs(tmp_path)
    assert inputs.read("inputs\\data.json") == {"value": 1}
    assert inputs.verify_frozen_inputs()["matched_consumed_files"] == 1
    target.write_text('{"value": 2}')
    inputs = Inputs(tmp_path)
    inputs.read("inputs/data.json")
    with pytest.raises(ValueError, match="hash mismatch"):
        inputs.verify_frozen_inputs()
    with pytest.raises(ValueError, match="escapes"):
        inputs.read("../outside.json")
