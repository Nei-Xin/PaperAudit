from dataclasses import replace
import time

import pytest
from fastapi.testclient import TestClient

from paperaudit.agents.consistency import ConsistencyOrchestrator
from paperaudit.agents.consistency_planner import ConsistencyPlanner
from paperaudit.api.main import create_app
from paperaudit.code_service import CodeLearningService
from paperaudit.consistency_jobs import ConsistencyJobManager
from paperaudit.models import AuditJobStatus
from paperaudit.request_budget import RequestBudget
from paperaudit.storage import ProjectStore, StorageError
from test_code_investigation import ScriptedClient, call, codebase, paper, SETTINGS
from test_consistency import PlannedClient, draft, make_store, RUNTIME


def proposal(topic="dropout", **kwargs):
    return call("propose_checkpoint", **draft(topic, **kwargs).model_dump())


def test_planner_reads_before_proposing_rejects_bad_quotes_and_duplicates():
    client = ScriptedClient([proposal()], [call("read_page", page=2)],
        [proposal("wrong", quote="dropout with a rate of 0.9"), proposal(), proposal("Dropout ")],
        [call("finish_plan")])
    plan = ConsistencyPlanner(client, "fake").run(paper(), codebase())
    assert [c.topic for c in plan.checkpoints] == ["dropout"]
    assert (plan.proposed, plan.rejected, plan.requests) == (4, 3, 4)
    assert "We apply dropout" not in client.requests[0]["messages"][1]["content"]
    assert len([s for s in plan.steps if s.tool == "propose_checkpoint"]) == 4


def test_exhausted_planner_keeps_accepted_points_and_enforces_tool_limit():
    client = ScriptedClient([call("read_page", page=2)], [proposal()], [call("read_page", page=3)])
    plan = ConsistencyPlanner(client, "fake", budget=RequestBudget(max_requests=3)).run(paper(), codebase())
    assert len(plan.checkpoints) == 1 and plan.stop_reason == "request_limit"
    assert plan.requests == 3
    assert len([s for s in plan.steps if s.tool == "read_page"]) == 1


def test_empty_agent_falls_back_without_exceeding_global_planning_budget():
    class EmptyPlanner(PlannedClient):
        def tool_turn(self, messages, tools, **kwargs):
            return ScriptedClient([call("finish_plan")]).tool_turn(messages, tools, **kwargs)
    client = EmptyPlanner([draft("dropout")])
    plan = ConsistencyOrchestrator(client, "fake", max_requests=2).plan(paper(), codebase(), strategy="agent")
    assert plan.fallback and len(plan.checkpoints) == 1 and plan.requests == 2
    plan = ConsistencyOrchestrator(client, "fake", max_requests=1).plan(paper(), codebase(), strategy="agent")
    assert not plan.checkpoints and plan.requests == 1


def test_planner_extracts_between_reading_batches_and_does_not_repeat_successful_reads():
    client = ScriptedClient(
        [call("read_page", page=2)],
        [call("read_page", page=3), proposal()],  # Reading is unavailable this turn.
        [call("read_page", page=2), call("read_page", page=3)],
        [call("continue_reading", reason="Only hardware and runtime, no checkable new setting.")],
        [call("finish_plan")],
    )
    plan = ConsistencyPlanner(client, "fake").run(paper(), codebase())
    assert len(plan.checkpoints) == 1
    assert [(s.tool, s.arguments) for s in plan.steps if s.tool == "read_page"] == [
        ("read_page", {"page": 2}), ("read_page", {"page": 3})]
    assert "read_page" not in client.requests[1]["tools"]
    assert "read_page" in client.requests[2]["tools"]
    assert "continue_reading" in client.requests[3]["tools"]
    assert any("identical reading call" in r for r in client.tool_results())


def test_planner_bounds_reading_batch_and_reserves_three_requests_for_extraction():
    client = ScriptedClient(
        [call("read_page", page=2), call("list_dir", path=""), call("read_page", page=3),
         call("grep_paper", text="dropout")],
        [proposal("bad", quote="dropout rate of 0.9")],
        [proposal()],
        [call("finish_plan")],
    )
    plan = ConsistencyPlanner(client, "fake", budget=RequestBudget(max_requests=4)).run(paper(), codebase())
    assert plan.requests == 4 and len(plan.checkpoints) == 1 and plan.rejected == 1
    assert len([s for s in plan.steps if s.tool in {"read_page", "list_dir", "grep_paper"}]) == 3
    assert all(set(r["tools"]) == {"propose_checkpoint", "finish_plan"} for r in client.requests[1:])


def test_planner_can_skip_irrelevant_passages_without_fabricating_a_checkpoint():
    client = ScriptedClient([call("read_page", page=3)],
        [call("continue_reading", reason="Only hardware and timing.")],
        [call("read_page", page=2)], [proposal()], [call("finish_plan")])
    plan = ConsistencyPlanner(client, "fake").run(paper(), codebase())
    assert plan.requests == 5 and len(plan.checkpoints) == 1 and plan.rejected == 0


def test_failed_investigations_still_spend_global_budget():
    client = PlannedClient([draft(f"item{i}") for i in range(15)],
        behaviour={f"item{i} 和代码一致吗？": "crash" for i in range(15)})
    report = ConsistencyOrchestrator(client, "fake", max_requests=12, concurrency=3).run(
        paper(), codebase(), strategy="one-shot")
    assert report.requests == client.requests + report.plan_requests
    assert report.requests <= 12 and report.summary.not_checked > 0


def wait_job(http, pid, jid):
    for _ in range(200):
        job = next(j for j in http.get(f"/api/projects/{pid}/consistency-jobs").json() if j["job_id"] == jid)
        if job["status"] not in {"QUEUED", "RUNNING"}:
            return job
        time.sleep(.01)
    raise AssertionError("job did not finish")


@pytest.mark.parametrize("strategy", ["one-shot", "agent"])
def test_plan_survives_restart_selected_execution_and_duplicate_submission(tmp_path, strategy):
    store, pid, chunk = make_store(tmp_path)
    client = PlannedClient([draft("dropout", chunk_id=chunk), draft("其他", chunk_id=chunk)],
                           paper_quote={"chunk_id": chunk, "quote": "dropout with a rate of 0.1"})
    settings = replace(SETTINGS, consistency_max_requests=60, consistency_concurrency=2)
    def app():
        return create_app(storage_root=tmp_path / "library", settings_dir=tmp_path / "settings",
                          settings=settings, code_service_factory=lambda s: CodeLearningService(s, client))
    with TestClient(app()) as http:
        response = http.post(f"/api/projects/{pid}/consistency-jobs",
                             json={"privacy_ack": True, "mode": "plan", "max_checkpoints": 5,
                                   **({"planning_strategy": strategy} if strategy == "agent" else {})})
        assert response.status_code == 202
        job = wait_job(http, pid, response.json()["job_id"])
        assert job["status"] == "SUCCEEDED" and not job["report_id"]
        assert job["planning_strategy"] == strategy
        plan_id = job["plan_id"]
    with TestClient(app()) as http:
        plan = http.get(f"/api/projects/{pid}/consistency-plans/{plan_id}").json()
        assert len(plan["checkpoints"]) == 2 and plan["code_hash"] and plan["max_requests"] == 60
        assert plan["strategy"] == ("one-shot-v1" if strategy == "one-shot" else "agent-planner-v2")
        endpoint = f"/api/projects/{pid}/consistency-plans/{plan_id}/execute"
        assert http.post(endpoint, json={"privacy_ack": True, "selected_ids": ["K99"]}).status_code == 409
        assert http.post(endpoint, json={"privacy_ack": True}).status_code == 409
        body = {"privacy_ack": True, "selected_ids": ["K02"], "extra_questions": ["配置文件在哪里？"]}
        response = http.post(endpoint, json=body)
        assert response.status_code == 202
        jid = response.json()["job_id"]
        assert http.post(endpoint, json=body).json()["job_id"] == jid
        job = wait_job(http, pid, jid)
        assert job["status"] == "SUCCEEDED", job
        report = http.get(f"/api/projects/{pid}/consistency-reports/{job['report_id']}").json()
        assert [i["checkpoint"]["checkpoint_id"] for i in report["items"]] == ["K02", "U01"]
        assert report["items"][1]["checkpoint"]["paper_anchor"] is None
        assert report["plan_unselected"] == 1 and report["plan_over_limit"] == 0
        assert http.post(endpoint, json=body).json()["job_id"] == jid
        changed = codebase().model_copy(update={"name": "changed"})
        store.save_codebase(pid, changed)
        response = http.post(endpoint, json=body)
        assert response.status_code == 409 and "变化" in response.text


def test_retry_preserves_saved_planning_strategy_and_rejects_invalid_strategy(tmp_path):
    store, pid, chunk = make_store(tmp_path)
    failed = store.create_consistency_job(pid, runtime=RUNTIME, kind="plan", planning_strategy="agent")
    # Old jobs without the new field must retain their original agent behavior.
    from paperaudit.models import ConsistencyJob
    old = failed.model_dump()
    old.pop("planning_strategy")
    failed = ConsistencyJob.model_validate(old).model_copy(update={"status": AuditJobStatus.FAILED})
    store.update_consistency_job(pid, failed)
    client = PlannedClient([draft("dropout", chunk_id=chunk)])
    app = create_app(storage_root=tmp_path / "library", settings_dir=tmp_path / "settings",
                     settings=SETTINGS, code_service_factory=lambda s: CodeLearningService(s, client))
    with TestClient(app) as http:
        endpoint = f"/api/projects/{pid}/consistency-jobs"
        assert http.post(endpoint, json={"privacy_ack": True, "planning_strategy": "typo"}).status_code == 422
        response = http.post(f"{endpoint}/{failed.job_id}/retry")
        assert response.status_code == 202 and response.json()["planning_strategy"] == "agent"
        job = wait_job(http, pid, response.json()["job_id"])
        assert job["status"] == "SUCCEEDED"
        plan = http.get(f"/api/projects/{pid}/consistency-plans/{job['plan_id']}").json()
        assert plan["strategy"] == "agent-planner-v2"


def test_queued_execution_rechecks_input_version_before_any_model_call(tmp_path):
    store, pid, chunk = make_store(tmp_path)
    saved = store.load_learning_project(pid)
    plan = ConsistencyOrchestrator(PlannedClient([draft("dropout", chunk_id=chunk)]), "fake").plan(
        saved.paper, saved.codebase, strategy="one-shot")
    plan = store.save_consistency_plan(pid, plan)
    job = store.create_consistency_job(pid, runtime=RUNTIME, kind="execute",
                                       plan_id=plan.plan_id, selected_ids=["K01"])
    store.save_codebase(pid, codebase().model_copy(update={"name": "new"}))
    manager = ConsistencyJobManager(store, mark_interrupted_on_start=False,
                                    service_factory=lambda _: object())
    manager.submit(pid, job.job_id, SETTINGS)
    manager.shutdown()
    result = store.load_consistency_job(pid, job.job_id)
    assert result.status == AuditJobStatus.FAILED and "变化" in result.error
