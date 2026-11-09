"""Migration backend acceptance against isolated storage; no network/model charges."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from io import BytesIO
from threading import Event
import json
import subprocess
import sys
import time
from zipfile import ZipFile

import pytest
from fastapi.testclient import TestClient

from paperaudit.api.main import create_app
from paperaudit.config import Settings
from paperaudit.models import (PeerReviewReport, ReviewConcern, ReviewDimension, JointAnswer,
    RelatedWorkComparison, AuditRuntimeSnapshot)
from paperaudit.pdf_parser import parse_pdf
from paperaudit.review_progress import action_key
from paperaudit.storage import ProjectStore
from test_api import FakeService, test_pdf
from test_audit_api import AuditRunner


def report():
    return PeerReviewReport(paper_title="Paper", decision="BORDERLINE", overall_score=5,
        summary="Review summary", decision_rationale="Evidence required", top_priorities=["Add experiment"],
        major_concerns=[ReviewConcern(issue_id="issue-a", title="Missing baseline", severity="major",
            description="Need comparison", why_it_matters="Validity", suggestion="Add experiment")],
        dimensions=[ReviewDimension(name="soundness", score=4, rationale="Good")])


class Runner(AuditRunner):
    def __init__(self):
        super().__init__()
        self.review_calls = []
        self.code_calls = []
        self.paper_calls = []
        self.related_calls = []

    def generate_learning_report(self, paper):
        return FakeService().generate_learning_report(paper)

    def generate_peer_review(self, paper, *, venue, rubric_weights):
        self.review_calls.append((venue, rubric_weights))
        self.entered.set()
        assert self.release.wait(5)
        if self.fail:
            raise RuntimeError("failed backend-secret")
        return report()

    def compare_related_work(self, paper, references):
        self.related_calls.append(references)
        if self.fail:
            raise RuntimeError("failed backend-secret")
        return RelatedWorkComparison(references=references, assessment="User supplied comparison", confidence=3)

    def answer_question(self, paper, question, history, **kwargs):
        self.paper_calls.append(kwargs)
        return super().answer_question(paper, question, history, **kwargs)

    def answer(self, paper, codebase, question, **kwargs):
        self.code_calls.append(kwargs)
        self.entered.set()
        assert self.release.wait(5)
        return JointAnswer(question=question, answer="Code answer", scope="joint", status="ANSWERED",
                           selected_code=kwargs.get("selected_code"))


@pytest.fixture
def setup(tmp_path):
    runner = Runner()
    runtime = []
    def factory(settings):
        runtime.append(settings)
        return runner
    options = dict(storage_root=tmp_path / "library", settings_dir=tmp_path / "settings",
        settings=Settings(api_base="https://example.invalid/v1", api_key="backend-secret", model="original"),
        service_factory=factory, code_service_factory=factory)
    store = ProjectStore(options["storage_root"])
    pdf = test_pdf()
    pid = store.save_paper_project(pdf, "paper.pdf", parse_pdf(pdf)).project_id
    return options, runner, store, pid, runtime


def wait(client, pid, kind, job_id):
    for _ in range(250):
        job = next(j for j in client.get(f"/api/projects/{pid}/jobs").json()[kind] if j["job_id"] == job_id)
        if job["status"] not in {"QUEUED", "RUNNING"}:
            return job
        time.sleep(.01)
    raise AssertionError(job)


def generate(client, pid):
    response = client.post(f"/api/projects/{pid}/review-jobs", json={"privacy_ack": True})
    assert response.status_code == 202, response.text
    job = wait(client, pid, "review", response.json()["job_id"])
    assert job["status"] == "SUCCEEDED", job
    return client.get(f"/api/projects/{pid}/review").json()


def code_zip(path="main.py"):
    data = BytesIO()
    with ZipFile(data, "w") as archive:
        archive.writestr(path, "def accuracy():\n    return 0.95\n")
    return data.getvalue()


def test_review_edits_progress_regeneration_and_legacy_reload(setup):
    options, runner, store, pid, _ = setup
    base = f"/api/projects/{pid}"
    with TestClient(create_app(**options)) as client:
        payload = generate(client, pid)
        rid = payload["report"]["run_id"]
        before = (store.projects_dir / pid / "peer-review.json").read_bytes()
        progress = {**payload["progress"], "items": [{"key": action_key("Add experiment"), "done": True}]}
        assert client.put(base + "/review/progress", json=progress).status_code == 200
        assert (store.projects_dir / pid / "peer-review.json").read_bytes() == before
        assert client.get(base + "/review").json()["progress"]["items"][0]["done"]
        edit = client.patch(base + "/review/concerns/0", json={"expected_run_id": rid,
            "human_reviewed": True, "human_decision": "false_positive", "status": "resolved",
            "human_note": "Checked", "severity_level": "P3", "support_type": "fact"})
        assert edit.status_code == 200, edit.text
        concern = edit.json()["report"]["minor_concerns"][0]
        assert concern["ai_severity_level"] == "P1" and concern["human_note"] == "Checked"
        assert concern["severity"] == "minor" and concern["support_type"] == "fact"
        assert client.get(base + "/review/export?format=md").status_code == 200
        assert client.patch(base + "/review/concerns/0", json={"expected_run_id": "old", "status": "open"}).status_code == 409
        fresh = generate(client, pid)
        assert fresh["report"]["run_id"] != rid and fresh["progress"]["items"] == []
        assert client.put(base + "/review/progress", json=progress).status_code == 409
    with TestClient(create_app(**options)) as client:
        assert client.get(base + "/review").json()["report"]["run_id"] == fresh["report"]["run_id"]
        assert len(runner.review_calls) == 2
    assert store.load_peer_review(pid).run_id == fresh["report"]["run_id"]


@pytest.mark.parametrize("change", [
    {"items": [{"key": "unknown", "done": True}]},
    {"items": [{"key": action_key("Add experiment"), "done": True}] * 2},
    {"review_generated_at": "stale"}, {"schema_version": 2},
])
def test_progress_rejects_invalid_or_stale_without_writing(setup, change):
    options, _, store, pid, _ = setup
    with TestClient(create_app(**options)) as client:
        payload = generate(client, pid)
        response = client.put(f"/api/projects/{pid}/review/progress", json={**payload["progress"], **change})
        assert response.status_code in {400, 422}, response.text
        assert not (store.projects_dir / pid / "review-progress.json").exists()


def test_review_running_guards_retry_snapshot_and_failure_redaction(setup):
    options, runner, store, pid, runtime = setup
    base = f"/api/projects/{pid}"
    runner.fail = True
    runner.release.clear()
    with TestClient(create_app(**options)) as client:
        try:
            first = client.post(base + "/review-jobs", json={"privacy_ack": True, "venue": "iclr", "rubric_weights": {"soundness": 1}})
            assert first.status_code == 202, first.text
            assert runner.entered.wait(2)
            assert client.post(base + "/review-jobs", json={"privacy_ack": True}).status_code == 400
            assert client.delete(base).status_code == 400
            assert client.patch(base + "/review/concerns/0", json={"expected_run_id": ""}).status_code == 409
        finally:
            runner.release.set()
        failed = wait(client, pid, "review", first.json()["job_id"])
        assert failed["status"] == "FAILED" and "backend-secret" not in failed["error"]
        runner.fail = False
        client.app.state.api.settings = replace(options["settings"], model="changed")
        retry = client.post(base + f'/review-jobs/{failed["job_id"]}/retry')
        assert retry.status_code == 202
        assert wait(client, pid, "review", retry.json()["job_id"])["status"] == "SUCCEEDED"
        assert runtime[-1].model == "original"
        assert runner.review_calls[0] == runner.review_calls[1]
        assert client.post(base + f'/review-jobs/{failed["job_id"]}/retry').status_code == 409


@pytest.mark.parametrize("body", [{}, {"privacy_ack":True,"venue":"invalid"},
    {"privacy_ack":True,"rubric_weights":{"unknown":1}}, {"privacy_ack":True,"rubric_weights":{"soundness":-1}}])
def test_review_validation_creates_no_jobs(setup, body):
    options, runner, store, pid, _ = setup
    with TestClient(create_app(**options)) as client:
        assert client.post(f"/api/projects/{pid}/review-jobs", json=body).status_code == 422
        assert store.list_peer_review_jobs(pid) == [] and not runner.review_calls


def test_related_work_limits_failure_and_persistence(setup):
    options, runner, store, pid, _ = setup
    with TestClient(create_app(**options)) as client:
        rid = generate(client, pid)["report"]["run_id"]
        url = f"/api/projects/{pid}/review/related-work"
        body = {"expected_run_id":rid,"privacy_ack":True,"references":[{"citation":"Paper B", "url":"https://example.invalid/paper"}]}
        assert client.post(url, json={**body,"references":body["references"]*6}).status_code == 422
        assert client.post(url, json={**body,"privacy_ack":False}).status_code == 422
        runner.fail = True
        response = client.post(url, json=body)
        assert response.status_code == 500 and "backend-secret" not in response.text
        assert store.load_peer_review(pid).related_work_comparison is None
        runner.fail = False
        assert client.post(url, json=body).status_code == 200
    assert store.load_peer_review(pid).related_work_comparison.references[0].citation == "Paper B"


def test_revision_baseline_retry_pdf_and_human_matching(setup):
    options, runner, store, pid, runtime = setup
    base = f"/api/projects/{pid}"
    with TestClient(create_app(**options)) as client:
        original = generate(client, pid)["report"]
        assert client.post(base+"/revisions", data={"privacy_ack":"true"}, files={"pdf":("bad.pdf", b"bad")}).status_code == 422
        assert not store.list_peer_review_revision_jobs(pid)
        runner.fail = True
        first = client.post(base+"/revisions", data={"privacy_ack":"true"}, files={"pdf":("revision.pdf", test_pdf())})
        assert first.status_code == 202, first.text
        failed = wait(client,pid,"revision",first.json()["job_id"])
        assert failed["status"] == "FAILED"
        baseline = store.load_peer_review_revision_input(pid, failed["job_id"])[1]
        store.save_peer_review(pid, baseline.model_copy(update={"summary":"Later change"}))
        client.app.state.api.settings = replace(options["settings"],model="changed")
        runner.fail = False
        response = client.post(base+f'/revision-jobs/{failed["job_id"]}/retry')
        assert response.status_code == 202, response.text
        done = wait(client,pid,"revision",response.json()["job_id"])
        assert done["status"] == "SUCCEEDED", done
        assert runtime[-1].model == "original"
        assert store.load_peer_review_revision_input(pid,done["job_id"])[1] == baseline
        assert store.load_peer_review(pid).summary == "Later change"
        rid = done["revision_id"]
        revision = client.get(base+f"/revisions/{rid}").json()
        assert revision["remaining_issue_ids"] == ["issue-a"]
        assert len(client.get(base+"/revisions").json()) == 1
        ranged = client.get(base+f"/revisions/{rid}/pdf",headers={"Range":"bytes=0-4"})
        assert ranged.status_code == 206 and ranged.content == b"%PDF-"
        patch = client.patch(base+f"/revisions/{rid}",json={"match_confirmed":True,"resolved_issue_ids":["issue-a"],"remaining_issue_ids":[]})
        assert patch.status_code == 200, patch.text
        assert patch.json()["resolved_concerns"] == ["Missing baseline"] and patch.json()["remaining_concerns"] == []
        assert client.patch(base+f"/revisions/{rid}",json={"resolved_issue_ids":["issue-a","issue-a"]}).status_code == 422
        assert client.patch(base+f"/revisions/{rid}",json={"resolved_issue_ids":["other"]}).status_code == 422
        assert client.post(base+f'/revision-jobs/{failed["job_id"]}/retry').status_code == 409
    with TestClient(create_app(**options)) as client:
        assert client.get(base+f"/revisions/{rid}").json()["match_confirmed"]
        assert len(runner.review_calls) == 3


def test_project_conversation_crud_and_empty_restart(setup):
    options, _, store, pid, _ = setup
    base = f"/api/projects/{pid}"
    with TestClient(create_app(**options)) as client:
        assert client.patch(base,json={"title":"Updated title"}).json()["title"] == "Updated title"
        assert client.patch(base,json={"title":"   "}).status_code == 422
        before = client.get(base+"/conversations").json()["active_conversation_id"]
        created = client.post(base+"/conversations",json={"title":"Empty saved"}).json()
        cid = created["active_conversation_id"]
        assert cid != before and len(created["conversations"]) == 2
        client.patch(base+f"/conversations/{before}",json={"activate":True})
        client.patch(base+f"/conversations/{cid}",json={"title":"Renamed"})
    with TestClient(create_app(**options)) as client:
        saved = client.get(base+"/conversations").json()
        assert saved["active_conversation_id"] == before
        assert next(c for c in saved["conversations"] if c["conversation_id"]==cid)["title"] == "Renamed"
        assert client.delete(base+f"/conversations/{before}").json()["active_conversation_id"] == cid
        final = client.delete(base+f"/conversations/{cid}").json()
        assert len(final["conversations"]) == 1 and final["active_conversation_id"] != cid
        assert client.delete(base+"/conversations/missing").status_code == 404
        assert client.delete(base).status_code == 204
        assert client.get(base).status_code == 404
    assert store.list_projects() == []


def test_code_upload_qa_selection_and_separate_histories(setup):
    options, runner, store, pid, _ = setup
    base = f"/api/projects/{pid}"
    with TestClient(create_app(**options)) as client:
        assert client.post(base+"/code/qa",json={"question":"Q"}).status_code == 409
        upload = client.post(base+"/code",files={"code_zip":("code.zip",code_zip())})
        assert upload.status_code == 201, upload.text
        assert client.get(base).json()["has_code"]
        file = client.get(base+"/code/files").json()[0]
        assert client.get(base+"/code/files/"+file["path"]).json()["content"] == file["content"]
        assert client.get(base+"/code/files/unknown.py").status_code == 404
        assert client.post(base+"/qa",json={"question":"Paper?","page_scope":1}).status_code == 200
        cid = client.get(base+"/conversations").json()["active_conversation_id"]
        selection={"path":file["path"],"start_line":2,"end_line":2,"text":"injected","context_text":"injected"}
        answer = client.post(base+"/code/qa",json={"question":"Code?","selected_code":selection,"conversation_id":cid})
        assert answer.status_code == 200, answer.text
        assert runner.code_calls[-1]["selected_code"].text == "    return 0.95"
        assert "injected" not in runner.code_calls[-1]["selected_code"].context_text
        assert client.post(base+"/code/qa",json={"question":"Bad?","selected_code":{**selection,"end_line":100}}).status_code == 422
        assert client.post(base+"/code/qa",json={"question":"Bad?","conversation_id":"missing"}).status_code == 404
        assert client.post(base+"/code/qa",json={"question":"New","new_conversation":True}).status_code == 200
    saved = store.load_learning_project(pid)
    old = next(c for c in saved.conversations if c.conversation_id == cid)
    assert len(old.paper_history) == len(old.joint_history) == 1
    assert len(saved.conversations) == 2
    assert runner.paper_calls[0]["selected_chunk_ids"]


@pytest.mark.parametrize("selection", [{"page_scope":2}, {"selected_chunk_ids":["invalid"]},
    {"selection":{"page":2,"text":"test"}}, {"selection":{"page":1,"text":"test","chunk_ids":["bad"]}}])
def test_paper_selection_rejects_out_of_scope(setup, selection):
    options,runner,_,pid,_ = setup
    with TestClient(create_app(**options)) as client:
        assert client.post(f"/api/projects/{pid}/qa",json={"question":"Q",**selection}).status_code == 422
        assert not runner.paper_calls


def test_code_zip_invalid_and_oversize_no_mutation(setup, monkeypatch):
    options,_,store,pid,_=setup
    with TestClient(create_app(**options)) as client:
        for data in (b"invalid",code_zip("../escape.py")):
            assert client.post(f"/api/projects/{pid}/code",files={"code_zip":("bad.zip",data)}).status_code == 422
        monkeypatch.setattr("paperaudit.api.project_routes.MAX_ZIP_BYTES",10)
        assert client.post(f"/api/projects/{pid}/code",files={"code_zip":("big.zip",code_zip())}).status_code == 413
    assert store.load_learning_project(pid).codebase is None


def test_concurrent_joint_qa_refuses_delete_and_session_mutation(setup):
    options,runner,store,pid,_=setup
    base=f"/api/projects/{pid}"
    with TestClient(create_app(**options)) as client, ThreadPoolExecutor() as pool:
        client.post(base+"/code",files={"code_zip":("code.zip",code_zip())})
        runner.release.clear()
        future=pool.submit(client.post,base+"/code/qa",json={"question":"Q"})
        try:
            assert runner.entered.wait(2)
            assert client.delete(base).status_code == 409
            assert client.post(base+"/conversations",json={}).status_code == 409
            assert client.post(base+"/code/qa",json={"question":"Duplicate"}).status_code == 409
        finally:
            runner.release.set()
        assert future.result().status_code == 200
        assert len(runner.code_calls)==1


@pytest.mark.parametrize("mode,kind",[("learn","learning"),("peer_review","review"),("audit_existing","audit")])
def test_home_upload_modes_preserve_inputs(setup, mode, kind):
    options,runner,store,pid,_=setup
    store.delete_project(pid)
    data={"mode":mode,"privacy_ack":"true"}
    files={"pdf":("paper.pdf",test_pdf())}
    if mode=="learn":
        files["code_zip"]=("code.zip",code_zip())
    if mode=="audit_existing":
        data.update(report_text="The measured accuracy is 95 percent.",scope=["results"])
    if mode=="peer_review":
        data.update(venue="iclr",rubric_weights=json.dumps({"soundness":1}))
    with TestClient(create_app(**options)) as client:
        response=client.post("/api/projects",data=data,files=files)
        assert response.status_code==201,response.text
        created=response.json()
        assert wait(client,created["project"]["project_id"],kind,created["job"]["job_id"])["status"]=="SUCCEEDED"
        if kind=="audit":
            assert created["job"]["scope"]==["results"]
        if kind=="review":
            assert created["job"]["venue"]=="iclr" and created["job"]["rubric_weights"]["soundness"]>.5
        if kind=="learning":
            assert client.get(f'/api/projects/{created["project"]["project_id"]}').json()["has_code"]


def test_lifespan_interrupts_all_four_kinds_without_model_calls(setup):
    options,runner,store,pid,_=setup
    runtime=AuditRuntimeSnapshot(model="original",reasoning_effort="",retrieval_top_k=5,judge_batch_size=6)
    store.save_peer_review(pid,report())
    store.create_learning_job(pid,runtime=runtime)
    store.create_peer_review_job(pid,runtime=runtime)
    store.create_peer_review_revision_job(pid,pdf_bytes=test_pdf(),original_filename="rev.pdf",runtime=runtime)
    store.create_audit_job(pid,report_text="Accuracy is 95 percent.",source_type="uploaded_report",source_label="Test",
        source_filename=None,scope=["results"],audit_mode="audit_existing",runtime=runtime)
    with TestClient(create_app(**options)) as client:
        jobs=client.get(f"/api/projects/{pid}/jobs").json()
        assert all(len(jobs[k])==1 and jobs[k][0]["status"]=="INTERRUPTED" for k in ("learning","review","revision","audit"))
        assert not runner.review_calls and not runner.calls
        response=client.put("/api/settings",json={"api_base":"https://example.invalid/v1","model":"original","reasoning_effort":""})
        assert response.status_code==200 and "backend-secret" not in response.text
    with TestClient(create_app(**options)) as client:
        assert client.get("/api/settings").json()["reasoning_effort"]==""


def test_api_import_is_independent_of_streamlit():
    result=subprocess.run([sys.executable,"-c",
        "from paperaudit.api.main import create_app; import sys; assert 'streamlit' not in sys.modules; create_app().openapi()"],
        capture_output=True,text=True)
    assert result.returncode==0,result.stderr


def test_streamlit_progress_uses_same_file_and_survives_new_session(setup):
    from streamlit.testing.v1 import AppTest
    options,_,store,pid,_=setup
    store.save_peer_review(pid,report().model_copy(update={"run_id":"stable-run","generated_at":"2026-11-09"}))
    source=f'''
from paperaudit.storage import ProjectStore
from paperaudit.ui.peer_review import render_peer_review
store=ProjectStore({str(options["storage_root"])!r})
pid={pid!r}
render_peer_review(store.load_peer_review(pid),
    load_progress=lambda:store.load_review_progress(pid),
    on_save_progress=lambda value:store.save_review_progress(pid,value))
'''
    app=AppTest.from_string(source).run()
    assert not app.exception
    checkbox=next(c for c in app.checkbox if c.key.startswith("peer-review-action-done"))
    checkbox.check().run()
    assert not app.exception
    assert store.load_review_progress(pid)["items"][0]["done"]
    fresh=AppTest.from_string(source).run()
    assert not fresh.exception
    assert next(c for c in fresh.checkbox if c.key.startswith("peer-review-action-done")).value


def test_legacy_history_default_id_stable_and_read_does_not_migrate_files(setup):
    options,_,store,pid,_=setup
    saved=store.load_learning_project(pid)
    answer=FakeService().answer_question(saved.paper,"Legacy question",[])
    store.save_histories(pid,[answer],[])
    path=store.projects_dir/pid/"session.json"
    before=path.read_bytes()
    with TestClient(create_app(**options)) as client:
        first=client.get(f"/api/projects/{pid}/conversations").json()
        second=client.get(f"/api/projects/{pid}/conversations").json()
        assert first==second
        assert first["conversations"][0]["paper_history"][0]["question"]=="Legacy question"
    assert before==path.read_bytes()
