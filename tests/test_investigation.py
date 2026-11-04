"""Exercise the real graph, retrieval and citation gates without paid API calls."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import httpx
from openai import OpenAI
from pydantic import ValidationError
import pytest

from paperaudit.agents.investigator import EvidenceInvestigator
from paperaudit.agents.models import InvestigationAction
from paperaudit.agents.tools import append_evidence, execute_tool
from paperaudit.config import Settings
from paperaudit.hy3_client import Hy3Client, Hy3ResponseError
from paperaudit.models import (
    AtomicClaim, AutoLabel, ClaimAudit, ClaimCategory, ClaimExtraction, ClaimJudgment,
    CitationReview, EvidenceCandidate, JudgmentBatch, PaperChunk, ParsedPaper,
)
from paperaudit.request_budget import BudgetExceeded, RequestBudget, active_budget, use_request_budget
from paperaudit.service import AuditService


SETTINGS = Settings("https://example.invalid/v1", "test-secret", "fake", deep_audit=True)
CLAIM = AtomicClaim(claim_id="C001", text="Dataset A score is 90.",
                    category=ClaimCategory.RESULTS, query_en="Dataset A score")
PAPER = ParsedPaper(title="Test", page_count=3, chunks=[
    PaperChunk(chunk_id="intro", page=1, content="We describe a model."),
    PaperChunk(chunk_id="result", page=2, content="Dataset A score is 90."),
    PaperChunk(chunk_id="config", page=3, content="The batch size is 32."),
])
SEED = EvidenceCandidate(evidence_id="C001_e1", chunk_id="intro", page=1,
                         text=PAPER.chunks[0].content, score=1)


def unresolved():
    return ClaimJudgment(claim_id=CLAIM.claim_id, label=AutoLabel.ABSTAIN,
                         explanation="Need experiment evidence.")


def initial():
    return ClaimAudit(claim=CLAIM, candidates=[SEED], judgment=unresolved())


def action(tool="read_page", **kwargs):
    return InvestigationAction(tool=tool, reason="核对实验设置", missing_aspects=["实验结果"], **kwargs)


class Client:
    def __init__(self, actions=None, *, invalid_quote=False, always_abstain=False):
        self.actions = list(actions or [action(page=2)])
        self.plans = 0
        self.invalid_quote = invalid_quote
        self.always_abstain = always_abstain

    def count(self):
        budget = active_budget.get()
        if budget:
            budget.reserve()

    def plan_investigation(self, *args):
        self.count()
        self.plans += 1
        return self.actions[min(self.plans - 1, len(self.actions) - 1)]

    def extract_claims(self, *args):
        return ClaimExtraction(claims=[CLAIM])

    def judge_claims(self, claims, page_count):
        return JudgmentBatch(judgments=[unresolved()])

    def adjudicate_claim(self, claim, candidates, page_count):
        self.count()
        relevant = next((c for c in candidates if c.chunk_id == "result"), None)
        judgment = unresolved()
        if relevant and not self.always_abstain:
            judgment = ClaimJudgment(claim_id=claim.claim_id, label=AutoLabel.SUPPORTED,
                                    evidence_ids=[relevant.evidence_id], explanation="Exact result.")
        return JudgmentBatch(judgments=[judgment])

    def review_citation_coverage(self, claim, candidates, judgment):
        self.count()
        relevant = next(c for c in candidates if c.evidence_id in judgment.evidence_ids)
        return CitationReview(
            claim_id=claim.claim_id, reviewed_label=judgment.label.value, complete=True,
            evidence_ids=judgment.evidence_ids, missing_aspects=[], explanation="Checked.",
            aspects=[{"aspect": "result", "reasoning": "Exact text",
                      "citations": [{"evidence_id": relevant.evidence_id,
                                     "quote": "fabricated text" if self.invalid_quote else relevant.text}]}],
        )

    def repair_citation_coverage(self, claim, candidates, review, judgment):
        return self.review_citation_coverage(claim, candidates, judgment)


def run(client=None, *, audit=None, budget=None):
    return EvidenceInvestigator(client or Client(), PAPER, "fake", budget=budget).run(
        audit or initial(), "unresolved_judgment",
    )


def test_graph_recovers_missing_evidence_only_after_quote_gate():
    result = run()
    assert result.judgment.label == AutoLabel.SUPPORTED
    assert result.investigation.stop_reason == "verified"
    assert result.investigation.requests == 3
    assert result.investigation.missing_aspects == []
    assert result.judgment_before_investigation.label == AutoLabel.ABSTAIN
    assert result.candidates[0] == SEED
    assert result.citation_review.aspects[0].citations[0].quote == PAPER.chunks[1].content
    assert ClaimAudit.model_validate_json(result.model_dump_json()) == result
    assert len(result.investigation.paper_hash) == 64


def test_false_quote_cannot_become_support():
    result = run(Client(invalid_quote=True))
    assert result.judgment.label == AutoLabel.ABSTAIN
    assert result.investigation.stop_reason != "verified"


@pytest.mark.parametrize(("actions", "reason"), [
    ([action(page=2), action(page=3)], "round_limit"),
    ([action(page=2), action(page=2)], "repeated_action"),
    ([action(page=1)], "no_new_evidence"),
    ([action(page=99)], "invalid_tool_arguments"),
    ([action("expand_context", chunk_id="unknown")], "invalid_tool_arguments"),
    ([action("finish")], "model_finished"),
])
def test_bounded_termination(actions, reason):
    client = Client(actions, always_abstain=True)
    result = run(client)
    assert result.investigation.stop_reason == reason
    assert result.judgment.label == AutoLabel.ABSTAIN
    assert client.plans <= 2
    assert result.investigation.missing_aspects


@pytest.mark.parametrize("limit, reason", [(1, "request_limit"), (0, "request_limit")])
def test_request_budget_returns_trace_without_unverified_support(limit, reason):
    result = run(budget=RequestBudget(max_requests=limit))
    assert result.investigation.requests == limit
    assert result.investigation.stop_reason == reason
    assert result.judgment.label == AutoLabel.ABSTAIN
    assert active_budget.get() is None


def test_expired_deadline_makes_no_request():
    result = run(budget=RequestBudget(max_seconds=0))
    assert result.investigation.stop_reason == "time_limit"
    assert result.investigation.requests == 0


def test_budget_stops_before_quote_gate_without_accepting_proposal():
    result = run(budget=RequestBudget(max_requests=2))
    assert result.investigation.stop_reason == "request_limit"
    assert result.judgment.label == AutoLabel.ABSTAIN


def test_forged_evidence_and_wrong_claim_fail_closed():
    class WrongClient(Client):
        def adjudicate_claim(self, claim, candidates, page_count):
            return JudgmentBatch(judgments=[ClaimJudgment(
                claim_id="other", label=AutoLabel.SUPPORTED,
                evidence_ids=["invented"], explanation="bad",
            )])
    result = run(WrongClient())
    assert result.investigation.stop_reason == "invalid_model_response"
    assert result.judgment.label == AutoLabel.ABSTAIN


def test_tools_preserve_whole_text_and_existing_ids_under_shared_budget():
    found = execute_tool(action("expand_context", chunk_id="intro"), PAPER, CLAIM, [SEED])
    candidates, added = append_evidence(CLAIM.claim_id, [SEED], found,
                                        max_candidates=2, max_chars=100)
    assert candidates[0] == SEED
    assert len(candidates) == 2 and len(added) == 1
    assert candidates[1].text == PAPER.chunks[1].content
    assert candidates[1].page == PAPER.chunks[1].page
    candidates, added = append_evidence(CLAIM.claim_id, [SEED], found,
                                        max_candidates=24, max_chars=len(SEED.text))
    assert candidates == [SEED] and added == []
    result = run(audit=initial().model_copy(update={
        "candidates": [SEED.model_copy(update={"text": "x" * 18000})],
    }))
    assert result.investigation.stop_reason == "evidence_budget"
    assert result.investigation.requests == 0


def test_search_only_returns_current_paper_chunks():
    found = execute_tool(action("search_paper", query="Dataset A score"), PAPER, CLAIM, [SEED])
    assert "result" in {c.chunk_id for c in found}
    assert {c.chunk_id for c in found} <= {c.chunk_id for c in PAPER.chunks}


@pytest.mark.parametrize("payload", [
    {"tool": "shell", "query": "pwd"}, {"tool": "read_page", "page": 0},
    {"tool": "read_page", "page": True}, {"tool": "read_page", "page": 1, "query": "x"},
    {"tool": "search_paper", "query": " "}, {"tool": "finish", "page": 1},
])
def test_schema_rejects_unsupported_actions(payload):
    with pytest.raises(ValidationError):
        InvestigationAction.model_validate({**payload, "reason": "test"})


def test_full_service_uses_agent_and_keeps_standard_mode_unchanged(monkeypatch):
    monkeypatch.setattr("paperaudit.service.retrieve_claim_evidence", lambda *a, **kw: [SEED])
    client = Client()
    deep = AuditService(SETTINGS, client).audit(PAPER, "report", [ClaimCategory.RESULTS])
    assert deep.deep_audit and deep.audits[0].investigation.stop_reason == "verified"
    standard_client = Client()
    standard = AuditService(replace(SETTINGS, deep_audit=False), standard_client).audit(
        PAPER, "report", [ClaimCategory.RESULTS],
    )
    assert not standard.deep_audit and standard_client.plans == 0
    assert standard.audits[0].investigation is None


def test_service_skips_resolved_claims_and_invalid_initial_responses():
    client = Client()
    service = AuditService(SETTINGS, client)
    candidates = [SEED, EvidenceCandidate(evidence_id="C001_e2", chunk_id="result", page=2,
                                          text=PAPER.chunks[1].content, score=1)]
    supported = client.adjudicate_claim(CLAIM, candidates, 3).judgments[0]
    result = service._audit_claim(CLAIM, candidates, supported, PAPER)
    assert result.judgment.label == AutoLabel.SUPPORTED and client.plans == 0

    class BrokenClient(Client):
        def adjudicate_claim(self, *args):
            raise Hy3ResponseError("invalid schema")
    broken = BrokenClient()
    result = AuditService(SETTINGS, broken)._audit_claim(CLAIM, [SEED], None, PAPER)
    assert result.investigation is None and broken.plans == 0


def test_budget_counts_json_repair_and_disables_hidden_sdk_retries():
    requests = []

    def respond(request):
        requests.append(request)
        content = "invalid json" if len(requests) == 1 else action("finish").model_dump_json()
        return httpx.Response(200, json={
            "id": "test", "object": "chat.completion", "created": 0, "model": "fake",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": content},
                         "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        })

    client = Hy3Client(SETTINGS)
    client._client = OpenAI(api_key="test", base_url=SETTINGS.api_base,
                            http_client=httpx.Client(transport=httpx.MockTransport(respond)))
    budget = RequestBudget(max_requests=2)
    with use_request_budget(budget):
        assert client._json_call("test", InvestigationAction).tool == "finish"
        with pytest.raises(BudgetExceeded):
            client._json_call("again", InvestigationAction)
    assert budget.requests == 2 and budget.tokens == 4 and len(requests) == 2

    requests.clear()
    def unavailable(request):
        requests.append(request)
        return httpx.Response(500, json={"error": {"message": "offline"}})
    client._client = OpenAI(api_key="test", base_url=SETTINGS.api_base,
                            http_client=httpx.Client(transport=httpx.MockTransport(unavailable)))
    result = run(client)
    assert result.investigation.stop_reason == "provider_error"
    assert len(requests) == result.investigation.requests == 1


def test_concurrent_claim_budgets_do_not_leak():
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda limit: run(budget=RequestBudget(max_requests=limit)), [1, 3]))
    assert [r.investigation.requests for r in results] == [1, 3]
    assert [r.investigation.stop_reason for r in results] == ["request_limit", "verified"]
    assert active_budget.get() is None


def test_service_investigates_semantic_citation_gap_but_not_schema_failure():
    class GapClient(Client):
        def review_citation_coverage(self, claim, candidates, judgment):
            if len(candidates) == 1:
                return CitationReview(claim_id=claim.claim_id, complete=False,
                                      evidence_ids=[], aspects=[], missing_aspects=["实验结果"],
                                      explanation="Need result table.")
            return super().review_citation_coverage(claim, candidates, judgment)

    supported = ClaimJudgment(claim_id=CLAIM.claim_id, label=AutoLabel.SUPPORTED,
                              evidence_ids=[SEED.evidence_id], explanation="Initial support.")
    result = AuditService(SETTINGS, GapClient())._audit_claim(CLAIM, [SEED], supported, PAPER)
    assert result.investigation.trigger == "citation_gap"
    assert result.judgment.label == AutoLabel.SUPPORTED

    class BrokenReview(Client):
        def review_citation_coverage(self, *args):
            raise Hy3ResponseError("invalid schema")
    broken = BrokenReview()
    result = AuditService(SETTINGS, broken)._audit_claim(CLAIM, [SEED], supported, PAPER)
    assert result.investigation is None and broken.plans == 0


def test_no_candidates_can_be_recovered_and_local_page_error_is_preserved():
    claim = CLAIM.model_copy(update={"provided_evidence": "论文第99页"})
    result = AuditService(SETTINGS, Client())._audit_claim(claim, [], None, PAPER)
    assert result.investigation.trigger == "no_candidates"
    assert result.investigation.stop_reason == "verified"
    assert result.judgment.evidence_error_type.value == "fabricated_evidence"
    assert result.judgment.severity.value == "high"


def test_investigation_panel_renders_evidence_and_outcome():
    from streamlit.testing.v1 import AppTest

    def render_panel():
        import streamlit as st
        from paperaudit.models import ClaimAudit
        from paperaudit.ui.investigation import render_investigation
        render_investigation(ClaimAudit.model_validate(st.session_state["fixture"]))

    app = AppTest.from_function(render_panel)
    app.session_state["fixture"] = run().model_dump(mode="json")
    app.run()
    assert not app.exception
    assert any("Dataset A score is 90." in item.value for item in app.text)
    assert any("新判断已通过引用校验" in item.value for item in app.markdown)
