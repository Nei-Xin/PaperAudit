import json
from dataclasses import replace

import httpx
from openai import OpenAI
import pytest

from paperaudit.agents.code_investigator import CodeInvestigator
from paperaudit.agents.consistency import summarize
from paperaudit.agents.finding_verifier import VerificationBatch, verify_answer
from paperaudit.hy3_client import Hy3Client, Hy3ResponseError
from paperaudit.models import (AnswerScope, CodeCitation, ConsistencyCheckpoint, ConsistencyItem,
    EvidenceAnchor, EvidenceContext, JointAnswer, PaperCodeFinding)
from paperaudit.request_budget import RequestBudget, active_budget, use_request_budget
from paperaudit.code_service import CodeLearningService
from test_code_investigation import ScriptedClient, SETTINGS, call, codebase, paper, submit


def answer(verdict="CONSISTENT"):
    return JointAnswer(question="默认 warmup 是否一致？", answer="SECRET_SUMMARY: 一致", scope="joint", status="ANSWERED",
        relation="IMPLEMENTS", findings=[PaperCodeFinding(text="默认 warmup 均为 20，论文与代码一致。", verdict=verdict,
            paper_citations=[EvidenceAnchor(chunk_id="p11_b1", page=11,
                text="Pre-training settings\nwarmup epochs [20] 40\noptimizer AdamW", quote="warmup epochs [20] 40")],
            code_citations=[CodeCitation(chunk_id="c1", path="main.py", start_line=1, end_line=2,
                text="parser.add_argument('--warmup_epochs', type=int, default=20)\n# default pretraining")])])


def review_result(passed=False, finding_id=0):
    return dict(finding_id=finding_id, paper_statement="论文预训练 warmup 为 40 epochs，[20] 是引用编号。",
                code_statement="命令行默认 warmup 为 20 epochs。", supports_verdict=passed,
                reason="40 与 20 不同，不支持一致判定。" if not passed else "证据支持该判定。")


class Reviewer(ScriptedClient):
    def __init__(self, *turns, results=None, error=None):
        super().__init__(*turns)
        self.results = results if results is not None else [review_result()]
        self.error = error
        self.payloads = []

    def verify_findings(self, payload):
        active_budget.get().reserve()
        active_budget.get().tokens += 17
        self.payloads.append(payload)
        if self.error:
            raise self.error
        return VerificationBatch(results=self.results)


def test_rejection_keeps_original_verdict_and_evidence_but_removes_confirmed_count():
    original = answer()
    client = Reviewer()
    with use_request_budget(RequestBudget(max_requests=1)):
        checked = verify_answer(client, original)
    finding = checked.findings[0]
    assert finding.verdict == original.findings[0].verdict and finding.text == original.findings[0].text
    assert finding.paper_citations == original.findings[0].paper_citations
    assert finding.verification.status == "failed" and finding.needs_review
    assert "40" in finding.verification.paper_statement
    assert "SECRET_SUMMARY" not in checked.answer and "原判定：一致" in checked.answer
    assert checked.relation is None
    item = ConsistencyItem(checkpoint=ConsistencyCheckpoint(checkpoint_id="K01", topic="warmup",
        category="hyperparameter", question="warmup?"), status="checked", answer=checked)
    summary = summarize([item])
    assert summary.checked == 1 and summary.pending_review == 1 and summary.consistent == 0
    payload = client.payloads[0][0]
    assert payload["paper"][0]["text"] == original.findings[0].paper_citations[0].text
    assert payload["code"][0]["text"] == original.findings[0].code_citations[0].text
    assert "question" not in payload and "SECRET_SUMMARY" not in json.dumps(payload)


@pytest.mark.parametrize("results", [[], [review_result(finding_id=9)], [review_result(), review_result()]])
def test_missing_extra_or_duplicate_ids_fail_closed_without_losing_findings(results):
    with use_request_budget(RequestBudget(max_requests=1)):
        checked = verify_answer(Reviewer(results=results), answer())
    assert checked.findings[0].verification.status == "not_reviewed"
    assert checked.findings[0].needs_review and checked.relation is None


def test_budget_exhaustion_and_malformed_response_are_pending_not_passed():
    for budget, client in [(RequestBudget(max_requests=0), Reviewer()),
                           (RequestBudget(max_requests=1), Reviewer(error=Hy3ResponseError("bad")))]:
        with use_request_budget(budget):
            checked = verify_answer(client, answer())
        assert checked.findings[0].needs_review
        assert budget.requests <= budget.max_requests


def test_mixed_batch_skips_not_located_and_preserves_passed_findings():
    original = answer()
    original.findings += [answer("NOT_LOCATED").findings[0], answer("INCONSISTENT").findings[0]]
    client = Reviewer(results=[review_result(True, 2), review_result(False, 0)])
    with use_request_budget(RequestBudget(max_requests=1)):
        checked = verify_answer(client, original)
    assert [f.verification.status for f in checked.findings] == ["failed", "not_reviewed", "passed"]
    assert [p["finding_id"] for p in client.payloads[0]] == [0, 2]
    assert not checked.findings[1].needs_review
    client = Reviewer()
    with use_request_budget(RequestBudget(max_requests=1)):
        verify_answer(client, answer("NOT_LOCATED"))
    assert not client.payloads


def test_old_findings_load_as_unreviewed_without_retroactive_downgrade():
    raw = answer().model_dump()
    del raw["findings"][0]["verification"]
    loaded = JointAnswer.model_validate(raw)
    assert loaded.findings[0].verification.status == "not_reviewed" and not loaded.findings[0].needs_review


def test_caption_provenance_survives_storage_and_is_sent_separately_to_reviewer():
    original = answer()
    anchor = original.findings[0].paper_citations[0]
    anchor.source_context = [EvidenceContext(chunk_id="p11_caption", page=11,
        text="Table 8. Pre-training setting.")]
    restored = JointAnswer.model_validate_json(original.model_dump_json())
    client = Reviewer()
    with use_request_budget(RequestBudget(max_requests=1)):
        checked = verify_answer(client, restored)
    sent = client.payloads[0][0]["paper"][0]
    assert sent["text"] == anchor.text and sent["chunk_id"] == anchor.chunk_id
    assert sent["source_context"] == [anchor.source_context[0].model_dump(mode="json")]
    assert checked.findings[0].paper_citations[0] == anchor
    old = original.model_dump()
    del old["findings"][0]["paper_citations"][0]["source_context"]
    assert JointAnswer.model_validate(old).findings[0].paper_citations[0].source_context == []


def test_investigator_reserves_and_accounts_for_one_verification_request():
    client = Reviewer([call("read_page", page=2), call("read_file", path="configs/base.yaml", start_line=1,end_line=3)],
                      [submit()], results=[review_result(True)])
    checked, trace = CodeInvestigator(client, paper(), codebase(), "fake",
        budget=RequestBudget(max_requests=3), verify_findings=True).run("dropout?", AnswerScope.JOINT)
    assert checked.findings[0].verification.status == "passed"
    assert trace.requests == 3 and trace.tokens == 17
    assert client.requests[-1]["force"] == "submit_answer"
    assert trace.steps[-1].tool == "verify_findings"


def test_disabled_verification_and_invalid_citations_do_not_call_reviewer():
    client = Reviewer([call("read_page", page=2),call("read_file",path="configs/base.yaml",start_line=1,end_line=3)], [submit()])
    result, trace = CodeInvestigator(client,paper(),codebase(),"fake").run("dropout?",AnswerScope.JOINT)
    assert result and not client.payloads and trace.requests == 2
    client = Reviewer([submit()], [submit()])
    result, trace = CodeInvestigator(client,paper(),codebase(),"fake",verify_findings=True).run("dropout?",AnswerScope.JOINT)
    assert result.status == "INSUFFICIENT_EVIDENCE" and not client.payloads


def test_follow_up_setting_enables_verifier_and_roundtrips_pending_evidence():
    client = Reviewer([call("read_page", page=2), call("read_file", path="configs/base.yaml", start_line=1,end_line=3)],
                      [submit()])
    result = CodeLearningService(replace(SETTINGS, code_verification=True), client).answer(
        paper(), codebase(), "论文的 dropout 与代码一致吗？", investigate=True)
    assert client.payloads and result.findings[0].needs_review
    restored = JointAnswer.model_validate_json(result.model_dump_json())
    assert restored == result and restored.findings[0].verification.required


@pytest.mark.parametrize("unavailable", [False, True])
def test_consistency_report_preserves_downgraded_finding_and_charged_review(unavailable):
    from test_consistency import PlannedClient, draft, run
    class RejectingClient(PlannedClient):
        def verify_findings(self, payload):
            result = super().verify_findings(payload)
            if unavailable:
                raise Hy3ResponseError("bad response")
            return VerificationBatch(results=[r.model_copy(update={"supports_verdict": False}) for r in result.results])
    client = RejectingClient([draft("dropout")])
    report = run(client)
    assert report.summary.pending_review == 1 and report.summary.inconsistent == 0
    assert report.summary.checked == 1 and report.summary.failed == 0
    assert report.requests == 4 and report.items[0].answer.findings[0].verdict == "INCONSISTENT"
    assert report.items[0].answer.investigation.stop_reason == "verification_pending"


@pytest.mark.parametrize("mode", ["ok", "invalid", "provider_error"])
def test_wire_request_is_isolated_tool_free_and_never_retried(mode):
    sent=[]
    def respond(request):
        sent.append(json.loads(request.content))
        if mode == "provider_error":
            return httpx.Response(503,json={"error":{"message":"unavailable"}})
        content=json.dumps({"results":[review_result()]}) if mode == "ok" else '{"results": "bad"}'
        return httpx.Response(200,json={"id":"x","object":"chat.completion","created":0,"model":"fake",
            "usage":{"prompt_tokens":12,"completion_tokens":8,"total_tokens":20},
            "choices":[{"index":0,"message":{"role":"assistant","content":content},"finish_reason":"stop"}]})
    client=Hy3Client(SETTINGS)
    client._client=OpenAI(api_key="test",base_url=SETTINGS.api_base,max_retries=2,
                         http_client=httpx.Client(transport=httpx.MockTransport(respond)))
    budget=RequestBudget(max_requests=1)
    with use_request_budget(budget):
        checked=verify_answer(client,answer())
    assert len(sent)==1 and budget.requests==1 and checked.findings[0].needs_review
    assert "tools" not in sent[0] and len(sent[0]["messages"])==2
    assert "SECRET_SUMMARY" not in json.dumps(sent[0])
    assert checked.findings[0].verification.status == ("failed" if mode=="ok" else "not_reviewed")
    assert budget.tokens == (0 if mode=="provider_error" else 20)
