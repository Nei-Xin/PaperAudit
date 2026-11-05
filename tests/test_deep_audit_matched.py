"""Counterfactual arms must consume exactly the same pre-investigation state."""

import pytest

from eval.deep_audit_matched import FreezeService, digest, replay, summarize, verify_sources
from eval.deep_audit_pilot import save
from paperaudit.models import AutoLabel
from test_investigation import CLAIM, PAPER, SEED, SETTINGS, Client, initial


def test_freeze_stops_before_agent_and_replay_cannot_mutate_input():
    client = Client()
    service = FreezeService(SETTINGS, client)
    audit = service._audit_claim(CLAIM, [SEED], initial().judgment, PAPER)
    assert client.plans == 0 and audit.investigation is None
    snapshot = {"audit": audit.model_dump(mode="json"), "trigger": service.trigger}
    fingerprint = digest(snapshot)

    class NeverCall:
        def __getattr__(self, name):
            raise AssertionError(f"Baseline must not call model: {name}")

    baseline = replay(snapshot, PAPER, "no_investigation", NeverCall(), "fake")
    assert baseline == audit
    result = replay(snapshot, PAPER, "agent", Client(), "fake")
    assert result.judgment.label == AutoLabel.SUPPORTED
    assert result.judgment_before_investigation == baseline.judgment
    assert result.investigation.trigger == service.trigger
    assert digest(snapshot) == fingerprint


def test_no_arm_rejudges_a_resolved_frozen_state():
    snapshot = {"audit": initial().model_dump(mode="json"), "trigger": None}
    client = Client()
    for arm in ("no_investigation", "fixed", "agent"):
        assert replay(snapshot, PAPER, arm, client, "fake").investigation is None
    assert client.plans == 0


def test_reference_fields_never_reach_agent(monkeypatch):
    snapshot = {"audit": initial().model_dump(mode="json"), "trigger": "citation_gap"}

    class InspectClient(Client):
        def plan_investigation(self, *args):
            assert "reference_label" not in repr(args)
            assert "reference_evidence" not in repr(args)
            return super().plan_investigation(*args)

    result = replay(snapshot, PAPER, "agent", InspectClient(), "fake")
    assert result.investigation


def test_modified_source_is_rejected(tmp_path):
    source = tmp_path / "source.py"
    source.write_text("changed")
    with pytest.raises(ValueError, match="Frozen source/input changed"):
        verify_sources({"source_sha256": {str(source): "old"}, "input_sha256": {}})


def test_summary_separates_controls_and_does_not_count_errors_as_matches(tmp_path):
    (tmp_path / "frozen").mkdir()
    (tmp_path / "results").mkdir()
    cases = [{"case_id": "A", "group": "natural"}, {"case_id": "B", "group": "removal_control"}]
    for case in cases:
        save(tmp_path / "frozen" / f"{case['case_id']}.json", {
            "case_id": case["case_id"], "status": "ok", "snapshot": {"trigger": "citation_gap"},
            "requests": 1, "tokens": 10,
        })
        row = {**case, "arm": "agent", "status": "ok" if case["case_id"] == "A" else "error",
               "eligible": True, "triggered": True, "reference_match": True,
               "label": "SUPPORTED", "reference_label": "SUPPORTED", "added_evidence": 1,
               "citation_valid": True, "requests": 2, "tokens": 10, "seconds": 1}
        save(tmp_path / "results" / f"{case['case_id']}.json", row)
    result = summarize(tmp_path, {"cases": cases, "repeats": 1})
    assert result["requests"] == 6
    assert result["groups"]["natural"]["arms"]["agent"]["reference_matches"] == 1
    assert result["groups"]["removal_control"]["arms"]["agent"]["reference_matches"] == 0
    assert result["groups"]["removal_control"]["arms"]["agent"]["failures"] == 1
