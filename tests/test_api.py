from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Event
import time

import pymupdf
import pytest
from fastapi.testclient import TestClient

from paperaudit.api.main import create_app
from paperaudit.config import Settings
from paperaudit.models import LearningReport, PaperAnswer, EvidenceAnchor, ReportSection, ExplanationPoint
from paperaudit.storage import ProjectStore


def test_pdf() -> bytes:
    with pymupdf.open() as doc:
        page = doc.new_page()
        page.insert_text((60, 60), "Reading Workflow Test", fontsize=20)
        page.insert_text((60, 100), "We test a method with two groups. The measured accuracy is 95 percent.")
        return doc.tobytes()

# Helper, not a pytest test.
test_pdf.__test__ = False


class FakeService:
    calls = 0

    def generate_learning_report(self, paper):
        self.calls += 1
        anchor = EvidenceAnchor(chunk_id=paper.chunks[-1].chunk_id, page=1, text=paper.chunks[-1].content)
        return LearningReport(paper_title=paper.title, one_sentence_summary="测试论文讲解", suggested_pages=[1], sections=[
            ReportSection(section_type="method", title="方法", overview="测试方法概述", points=[
                ExplanationPoint(title="测试要点", explanation="两组对照实验", evidence=[anchor])])])

    def answer_question(self, paper, question, history, **kwargs):
        return PaperAnswer(question=question, answer=f"已保存回答 {len(history) + 1}", status="ANSWERED",
                           citations=[EvidenceAnchor(chunk_id=paper.chunks[-1].chunk_id, page=1, text="两组对照")])


@pytest.fixture
def setup(tmp_path):
    settings = Settings(api_base="https://example.invalid/v1", api_key="private-test-key", model="fake-model")
    runner = FakeService()
    options = dict(storage_root=tmp_path / "library", settings_dir=tmp_path / "settings", settings=settings,
                   service_factory=lambda _: runner)
    return options, runner


def upload(client, pdf=None):
    return client.post("/api/projects", files={"pdf": ("paper.pdf", pdf or test_pdf(), "application/pdf")},
                       data={"mode": "learn", "privacy_ack": "true"})


def wait_job(client, pid, status="SUCCEEDED", job_id=None):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        jobs = client.get(f"/api/projects/{pid}/jobs").json()["learning"]
        job = next((j for j in jobs if j["job_id"] == job_id), jobs[0])
        if job["status"] == status:
            return job
        time.sleep(0.02)
    raise AssertionError(job)


def test_upload_generate_qa_persist_and_pdf_range(setup):
    options, runner = setup
    data = test_pdf()
    with TestClient(create_app(**options)) as client:
        response = upload(client, data)
        assert response.status_code == 201, response.text
        pid = response.json()["project"]["project_id"]
        wait_job(client, pid)
        assert client.get(f"/api/projects/{pid}/lecture").json()["sections"][0]["title"] == "方法"
        assert client.get(f"/api/projects/{pid}").json()["has_learning_report"]
        assert client.get(f"/api/projects/{pid}/pdf", headers={"Range": "bytes=0-4"}).content == b"%PDF-"
        assert client.get(f"/api/projects/{pid}/pdf", headers={"Range": "bytes=0-4"}).status_code == 206
        assert client.post(f"/api/projects/{pid}/qa", json={"question": "研究方法是什么？"}).status_code == 200
        conversations = client.get(f"/api/projects/{pid}/conversations").json()
        cid = conversations["active_conversation_id"]
        assert client.post(f"/api/projects/{pid}/qa", json={"question": "第二问", "conversation_id": cid}).json()["answer"] == "已保存回答 2"
        duplicate = upload(client, data)
        assert duplicate.json()["project"]["project_id"] == pid
        assert duplicate.json()["job"] is None
        assert runner.calls == 1
        assert client.get(f"/api/projects/{pid}/lecture/export?format=md").status_code == 200
    # Reload using a new app, including old-compatible storage session keys.
    with TestClient(create_app(**options)) as client:
        history = client.get(f"/api/projects/{pid}/conversations").json()["conversations"][0]["paper_history"]
        assert len(history) == 2
        saved = ProjectStore(options["storage_root"]).load_learning_project(pid)
        assert len(saved.paper_history) == 2
        assert saved.report is not None


def test_failed_job_retry_is_explicit_and_secret_free(setup):
    options, runner = setup
    original = runner.generate_learning_report
    runner.generate_learning_report = lambda paper: (_ for _ in ()).throw(RuntimeError("failed private-test-key"))
    with TestClient(create_app(**options)) as client:
        pid = upload(client).json()["project"]["project_id"]
        failed = wait_job(client, pid, "FAILED")
        assert "private-test-key" not in failed["error"]
        assert client.get(f"/api/projects/{pid}/lecture").json() is None
        runner.generate_learning_report = original
        retry = client.post(f"/api/projects/{pid}/lecture/jobs")
        assert retry.status_code == 202
        wait_job(client, pid, job_id=retry.json()["job_id"])


def test_model_settings_never_return_key_and_persist_with_private_mode(setup):
    options, _ = setup
    with TestClient(create_app(**options)) as client:
        assert "private-test-key" not in client.get("/api/settings").text
        body = {"api_base": "https://example.invalid/v1", "model": "updated", "api_key": "new-private-key"}
        response = client.put("/api/settings", json=body)
        assert response.status_code == 200
        assert "private-key" not in response.text
        assert (options["settings_dir"] / "model.json").stat().st_mode & 0o777 == 0o600
        body["api_key"] = ""
        assert client.put("/api/settings", json=body).status_code == 200
        assert client.app.state.api.settings.api_key == "new-private-key"
        body["api_key"] = {"secret": "never-return-this"}
        response = client.put("/api/settings", json=body)
        assert response.status_code == 422 and "never-return-this" not in response.text
    with TestClient(create_app(**options)) as client:
        assert client.get("/api/settings").json()["model"] == "updated"
        assert client.app.state.api.settings.api_key == "new-private-key"


@pytest.mark.parametrize("case", ["no_model", "no_consent", "bad_pdf", "wrong_mode", "code_zip", "oversize"])
def test_upload_validation_has_no_project_side_effects(setup, case, monkeypatch):
    options, _ = setup
    if case == "no_model":
        options["settings"] = replace(options["settings"], api_key="")
    if case == "oversize":
        monkeypatch.setattr("paperaudit.api.main.MAX_PDF_BYTES", 10)
    with TestClient(create_app(**options)) as client:
        data = {"privacy_ack": "false" if case == "no_consent" else "true", "mode": "unknown_mode" if case == "wrong_mode" else "learn"}
        files = {"pdf": ("paper.pdf", b"invalid" if case == "bad_pdf" else test_pdf(), "application/pdf")}
        if case == "code_zip":
            files["code_zip"] = ("code.zip", b"invalid", "application/zip")
        response = client.post("/api/projects", data=data, files=files)
        assert response.status_code in {409, 413, 422}, response.text
        assert client.get("/api/projects").json() == []


def test_reject_cross_origin_writes_and_missing_projects(setup):
    options, _ = setup
    with TestClient(create_app(**options)) as client:
        response = client.post("/api/projects", headers={"Origin": "https://other.example"})
        assert response.status_code == 403
        assert client.get("/api/projects/nonexistent").status_code == 404
        assert client.post("/api/projects/nonexistent/qa", json={"question": "test"}).status_code == 404
        assert client.get("/api/not-a-route").status_code == 404
        assert client.get("/assets/not-a-file.js").status_code == 404


def test_qa_conversation_isolation_validation_and_busy_request(setup):
    options, runner = setup
    with TestClient(create_app(**options)) as client:
        pid = upload(client).json()["project"]["project_id"]
        wait_job(client, pid)
        for body in [{"question": " "}, {"question": "x" * 1001}]:
            assert client.post(f"/api/projects/{pid}/qa", json=body).status_code == 422
        assert client.post(f"/api/projects/{pid}/qa", json={"question": "first"}).status_code == 200
        first = client.get(f"/api/projects/{pid}/conversations").json()["active_conversation_id"]
        assert client.post(f"/api/projects/{pid}/qa", json={"question": "new", "new_conversation": True}).status_code == 200
        assert len(client.get(f"/api/projects/{pid}/conversations").json()["conversations"]) == 2
        assert client.post(f"/api/projects/{pid}/qa", json={"question": "bad", "conversation_id": "missing"}).status_code == 400
        entered, release = Event(), Event()
        original = runner.answer_question
        def delayed(*args, **kwargs):
            entered.set()
            assert release.wait(5)
            return original(*args, **kwargs)
        runner.answer_question = delayed
        with ThreadPoolExecutor() as pool:
            future = pool.submit(client.post, f"/api/projects/{pid}/qa", json={"question": "slow", "conversation_id": first})
            assert entered.wait(5)
            try:
                assert client.post(f"/api/projects/{pid}/qa", json={"question": "overlap"}).status_code == 409
            finally:
                release.set()
            assert future.result().status_code == 200


def test_restart_marks_pending_job_interrupted_without_replay(setup):
    options, runner = setup
    from paperaudit.models import AuditRuntimeSnapshot
    from paperaudit.pdf_parser import parse_pdf
    store = ProjectStore(options["storage_root"])
    data = test_pdf()
    pid = store.save_paper_project(data, "paper.pdf", parse_pdf(data)).project_id
    store.create_learning_job(pid, runtime=AuditRuntimeSnapshot(model="fake", reasoning_effort="low", retrieval_top_k=5, judge_batch_size=6))
    with TestClient(create_app(**options)) as client:
        assert client.get(f"/api/projects/{pid}/jobs").json()["learning"][0]["status"] == "INTERRUPTED"
        assert runner.calls == 0


def test_regeneration_preserves_old_until_success_and_archives_it(setup):
    options, runner = setup
    with TestClient(create_app(**options)) as client:
        pid = upload(client).json()["project"]["project_id"]
        wait_job(client, pid)
        store = ProjectStore(options["storage_root"])
        old = store.load_learning_project(pid).report
        release, entered = Event(), Event()
        def regenerate(paper):
            entered.set()
            assert release.wait(5)
            return old.model_copy(update={"one_sentence_summary": "详细版已完成"})
        runner.generate_learning_report = regenerate
        path = f"/api/projects/{pid}/lecture/jobs"
        assert client.post(path, json={"regenerate": True}).status_code == 400
        response = client.post(path, json={"regenerate": True, "privacy_ack": True})
        assert response.status_code == 202, response.text
        job = response.json()
        try:
            assert entered.wait(2)
            assert client.get(f"/api/projects/{pid}/lecture").json()["one_sentence_summary"] == old.one_sentence_summary
            assert client.post(path, json={"regenerate": True, "privacy_ack": True}).status_code == 400
        finally:
            release.set()
        wait_job(client, pid, job_id=job["job_id"])
        assert client.get(f"/api/projects/{pid}/lecture").json()["one_sentence_summary"] == "详细版已完成"
        archive = store._project_dir(pid) / "learning-history" / (job["job_id"] + ".json")
        assert LearningReport.model_validate_json(archive.read_text()) == old


def test_regeneration_failure_retry_and_stale_report_protection(setup):
    options, runner = setup
    with TestClient(create_app(**options)) as client:
        pid = upload(client).json()["project"]["project_id"]
        wait_job(client, pid)
        store = ProjectStore(options["storage_root"])
        old = store.load_learning_project(pid).report
        original = runner.generate_learning_report
        runner.generate_learning_report = lambda _: (_ for _ in ()).throw(RuntimeError("质量检查失败"))
        path = f"/api/projects/{pid}/lecture/jobs"
        failed = client.post(path, json={"regenerate": True, "privacy_ack": True}).json()
        wait_job(client, pid, "FAILED", failed["job_id"])
        assert store.load_learning_project(pid).report == old
        client.put("/api/settings", json={"model": "changed-model"})
        runner.generate_learning_report = original
        retry = client.post(path + "/" + failed["job_id"] + "/retry")
        assert retry.status_code == 202, retry.text
        assert retry.json()["runtime"] == failed["runtime"]
        assert retry.json()["regenerate"]
        wait_job(client, pid, job_id=retry.json()["job_id"])
        # Another writer updates the report while a generation is in flight.
        updated = old.model_copy(update={"one_sentence_summary": "其他操作保存的版本"})
        def concurrent(paper):
            store.save_learning_report(pid, updated)
            return old.model_copy(update={"one_sentence_summary": "过期后台结果"})
        runner.generate_learning_report = concurrent
        stale = client.post(path, json={"regenerate": True, "privacy_ack": True}).json()
        wait_job(client, pid, "FAILED", stale["job_id"])
        assert store.load_learning_project(pid).report == updated
        assert client.post(path + "/" + stale["job_id"] + "/retry").status_code == 400
