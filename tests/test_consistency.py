from __future__ import annotations

from dataclasses import replace
import threading
import time

from fastapi.testclient import TestClient
import pytest

from paperaudit.agents.consistency import ConsistencyOrchestrator
from paperaudit.code_service import CodeLearningService
from paperaudit.hy3_client import Hy3ResponseError, ToolTurn
from paperaudit.models import (
    AuditRuntimeSnapshot,
    ConsistencyCheckpointDraft,
    ConsistencyItemStatus,
    ConsistencyPlanDraft,
    ConsistencyReport,
)
from paperaudit.request_budget import active_budget
from paperaudit.storage import ProjectStore, StorageError
from test_code_investigation import PAPER_QUOTE, SETTINGS, YAML_QUOTE, call, codebase, finding, paper, submit


def draft(topic, question=None, *, quote="We apply dropout with a rate of 0.1", chunk_id="p2_b1"):
    return ConsistencyCheckpointDraft(topic=topic, category="hyperparameter", chunk_id=chunk_id,
                                      quote=quote, question=question or f"{topic} 和代码一致吗？")


class PlannedClient:
    """Stateless per conversation, so parallel investigations cannot interleave."""

    def __init__(self, drafts, *, behaviour=None, delay=0.0, paper_quote=PAPER_QUOTE):
        self.drafts, self.behaviour, self.delay = drafts, behaviour or {}, delay
        self.paper_quote = paper_quote
        self.lock = threading.Lock()
        self.active = self.peak = self.requests = 0
        self.first_messages: dict[str, str] = {}

    def plan_consistency(self, title, chunks, limit):
        active_budget.get().reserve()
        return ConsistencyPlanDraft(checkpoints=self.drafts)

    def tool_turn(self, messages, tools, *, force_tool=None) -> ToolTurn:
        active_budget.get().reserve()
        if any(t["function"]["name"] == "propose_checkpoint" for t in tools):
            turns = sum(m["role"] == "assistant" for m in messages)
            calls = ([call("read_page", page=int(d.chunk_id.split("_")[0][1:])) for d in self.drafts]
                     if turns == 0 and self.drafts else
                     [*[call("propose_checkpoint", **d.model_dump()) for d in self.drafts], call("finish_plan")])
            return ToolTurn(message={"role": "assistant", "content": None, "tool_calls": [
                {"id": c.id, "type": "function", "function": {"name": c.name, "arguments": c.arguments}}
                for c in calls]}, tool_calls=tuple(calls), content="")
        question = messages[1]["content"].split("<untrusted_question>\n")[1].split("\n</untrusted_question>")[0]
        with self.lock:
            self.requests += 1
            self.active += 1
            self.peak = max(self.peak, self.active)
            self.first_messages[question] = messages[1]["content"]
        try:
            time.sleep(self.delay)
            mode = self.behaviour.get(question, "ok")
            if mode == "crash":
                raise RuntimeError("boom")
            if mode == "invalid":
                raise Hy3ResponseError("bad")
            turns = sum(m["role"] == "assistant" for m in messages)
            if mode == "explore" or turns == 0:
                calls = [call("grep_code", text=f"dropout: 0.3 {turns}" if mode == "explore" else "dropout: 0.3")]
            else:
                calls = [submit(findings=[finding("CONSISTENT" if mode == "consistent" else "INCONSISTENT",
                                                  paper=[self.paper_quote])])
                         if mode != "unsure" else submit(status="INSUFFICIENT_EVIDENCE", findings=[])]
            return ToolTurn(message={"role": "assistant", "content": None, "tool_calls": [
                {"id": c.id, "type": "function", "function": {"name": c.name, "arguments": c.arguments}}
                for c in calls]}, tool_calls=tuple(calls), content="")
        finally:
            with self.lock:
                self.active -= 1


def run(client, **options) -> ConsistencyReport:
    return ConsistencyOrchestrator(client, "hy3", **options).run(paper(), codebase(), strategy="one-shot")


def test_each_checkpoint_gets_its_own_investigation_seeded_with_the_paper_passage():
    client = PlannedClient([draft("dropout"), draft("层数"), draft("学习率")],
                           behaviour={"层数 和代码一致吗？": "consistent", "学习率 和代码一致吗？": "unsure"})
    report = run(client)
    assert [item.checkpoint.checkpoint_id for item in report.items] == ["K01", "K02", "K03"]
    assert all(item.status == ConsistencyItemStatus.CHECKED for item in report.items)
    assert report.items[0].checkpoint.paper_anchor.page == 2
    # The planned passage is handed over as readable evidence: it can be cited without a search.
    assert report.items[0].answer.findings[0].paper_citations[0].chunk_id == "p2_b1"
    assert "We apply dropout with a rate of 0.1" in client.first_messages["dropout 和代码一致吗？"]
    assert set(client.first_messages) == {"dropout 和代码一致吗？", "层数 和代码一致吗？", "学习率 和代码一致吗？"}
    summary = report.summary
    assert (summary.checked, summary.inconsistent, summary.consistent, summary.unresolved) == (3, 1, 1, 1)
    assert report.plan_requests == 1 and report.requests == 1 + 3 * 2 and report.planned == 3
    assert ConsistencyReport.model_validate_json(report.model_dump_json()) == report


def test_plan_entries_must_quote_the_paper_and_are_deduplicated_and_capped():
    report = run(PlannedClient([
        draft("dropout"),
        draft("Dropout "),                                           # same topic
        draft("编造", quote="We apply dropout with a rate of 0.9"),   # not in the paper
        draft("错片段", chunk_id="p9_b9"),
        draft("太短", quote="0.1"),
        draft("训练资源", quote="Training used eight GPUs", chunk_id="p3_b1"),
        draft("超出上限", quote="for twelve hours", chunk_id="p3_b1"),
    ]), max_checkpoints=2)
    assert [item.checkpoint.topic for item in report.items] == ["dropout", "训练资源"]
    assert (report.planned, report.plan_rejected, report.plan_over_limit) == (7, 4, 1)


def test_investigations_run_in_parallel_up_to_the_configured_width():
    client = PlannedClient([draft(f"要点{i}") for i in range(6)], delay=0.05)
    report = run(client, concurrency=3)
    assert report.summary.checked == 6 and 2 <= client.peak <= 3


def test_total_request_ceiling_is_never_exceeded_and_unstarted_items_are_reported():
    # Every investigation explores until its own budget forces a conclusion.
    behaviour = {f"要点{i} 和代码一致吗？": "explore" for i in range(8)}
    client = PlannedClient([draft(f"要点{i}") for i in range(8)], behaviour=behaviour)
    report = run(client, max_requests=40, concurrency=4)
    assert report.requests <= 40 and client.requests + report.plan_requests == report.requests
    statuses = [item.status for item in report.items]
    assert ConsistencyItemStatus.NOT_CHECKED in statuses and len(statuses) == 8
    assert report.summary.not_checked == statuses.count(ConsistencyItemStatus.NOT_CHECKED)
    assert all(item.note for item in report.items if item.status == ConsistencyItemStatus.NOT_CHECKED)


def test_one_failed_investigation_does_not_lose_the_others():
    client = PlannedClient([draft("会崩"), draft("无效"), draft("正常")],
                           behaviour={"会崩 和代码一致吗？": "crash", "无效 和代码一致吗？": "invalid"})
    report = run(client)
    assert [item.status.value for item in report.items] == ["failed", "failed", "checked"]
    assert "RuntimeError" in report.items[0].note and "模型响应无效" in report.items[1].note
    assert report.summary.failed == 2 and report.summary.inconsistent == 1


def test_empty_plan_yields_an_empty_report_without_investigations():
    client = PlannedClient([])
    report = run(client)
    assert report.items == [] and client.requests == 0 and report.requests == 1


# Jobs, storage and API -----------------------------------------------------------


RUNTIME = AuditRuntimeSnapshot(model="hy3", reasoning_effort="no_think", retrieval_top_k=5, judge_batch_size=6)


def make_store(tmp_path, *, with_code=True):
    import pymupdf
    from paperaudit.pdf_parser import parse_pdf

    document = pymupdf.open()
    document.new_page().insert_text((72, 72), "We apply dropout with a rate of 0.1 to each sub-layer.")
    pdf = document.tobytes()
    parsed = parse_pdf(pdf)
    store = ProjectStore(tmp_path / "library")
    pid = store.save_paper_project(pdf, "paper.pdf", parsed).project_id
    if with_code:
        store.save_codebase(pid, codebase())
    return store, pid, parsed.chunks[0].chunk_id


def test_job_requires_code_and_rejects_a_second_active_job(tmp_path):
    store, pid, _ = make_store(tmp_path, with_code=False)
    with pytest.raises(StorageError, match="代码"):
        store.create_consistency_job(pid, runtime=RUNTIME)
    store.save_codebase(pid, codebase())
    job = store.create_consistency_job(pid, runtime=RUNTIME, max_checkpoints=5)
    with pytest.raises(StorageError, match="正在执行"):
        store.create_consistency_job(pid, runtime=RUNTIME)
    assert store.mark_interrupted_consistency_jobs() == 1
    assert store.load_consistency_job(pid, job.job_id).status == "INTERRUPTED"
    assert store.create_consistency_job(pid, runtime=RUNTIME).max_checkpoints == 20


def test_api_runs_a_consistency_audit_in_the_background_and_serves_the_report(tmp_path):
    from paperaudit.api.main import create_app

    store, pid, chunk_id = make_store(tmp_path)
    quote = "dropout with a rate of 0.1"
    client = PlannedClient([draft("dropout", quote=quote, chunk_id=chunk_id)],
                           paper_quote={"chunk_id": chunk_id, "quote": quote})
    app = create_app(storage_root=tmp_path / "library", settings_dir=tmp_path / "settings", settings=SETTINGS,
                     code_service_factory=lambda settings: CodeLearningService(
                         replace(settings, consistency_concurrency=2), client))
    with TestClient(app) as http:
        assert http.post(f"/api/projects/{pid}/consistency-jobs", json={}).status_code == 422
        created = http.post(f"/api/projects/{pid}/consistency-jobs", json={"privacy_ack": True, "max_checkpoints": 5})
        assert created.status_code == 202
        for _ in range(100):
            job = http.get(f"/api/projects/{pid}/consistency-jobs").json()[0]
            if job["status"] not in {"QUEUED", "RUNNING"}:
                break
            time.sleep(0.02)
        assert job["status"] == "SUCCEEDED" and job["progress"] == 1.0, job
        report = http.get(f"/api/projects/{pid}/consistency-reports/{job['report_id']}").json()
        assert report["summary"]["inconsistent"] == 1 and report["items"][0]["checkpoint"]["topic"] == "dropout"
        assert report["max_checkpoints"] == 5 and report["concurrency"] == 2
        assert http.get(f"/api/projects/{pid}/consistency-reports/consistency-missing").status_code == 404
        assert http.post(f"/api/projects/{pid}/consistency-jobs/{job['job_id']}/retry").status_code == 409
