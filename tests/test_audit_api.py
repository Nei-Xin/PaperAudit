from dataclasses import replace
from io import BytesIO
from threading import Event
import time

import pytest
from fastapi.testclient import TestClient
from pptx import Presentation

from paperaudit.api.main import create_app
from paperaudit.config import Settings
from paperaudit.models import AuditRuntimeSnapshot, ClaimCategory
from paperaudit.pdf_parser import parse_pdf
from paperaudit.storage import ProjectStore
from paperaudit.ui.demo_data import get_demo_audit_run
from test_api import FakeService, test_pdf


class AuditRunner(FakeService):
    def __init__(self):
        self.calls = []
        self.fail = False
        self.entered, self.release = Event(), Event()
        self.release.set()

    def audit(self, paper, text, scope, *, mode, progress=None):
        self.calls.append((text, scope, mode))
        self.entered.set()
        assert self.release.wait(5)
        if self.fail:
            raise RuntimeError("audit failed secret-audit-test")
        if progress:
            progress("正在核对论断", .6)
        return get_demo_audit_run().model_copy(update={"paper_title":paper.title,"report_text":text,"scope":scope,"mode":mode})


@pytest.fixture
def setup(tmp_path):
    runner = AuditRunner()
    options = dict(storage_root=tmp_path/'library', settings_dir=tmp_path/'settings',
                   settings=Settings(api_base='https://example.invalid/v1', api_key='secret-audit-test', model='fake-audit'),
                   service_factory=lambda _: runner)
    store = ProjectStore(options['storage_root'])
    pdf = test_pdf()
    pid = store.save_paper_project(pdf, 'audit-paper.pdf', parse_pdf(pdf)).project_id
    return options, runner, store, pid


def wait_job(client, pid, job_id):
    for _ in range(200):
        job = next(j for j in client.get(f'/api/projects/{pid}/jobs').json()['audit'] if j['job_id']==job_id)
        if job['status'] not in {'QUEUED','RUNNING'}:
            return job
        time.sleep(.02)
    raise AssertionError(job)


def submit(client, pid, **extra):
    return client.post(f'/api/projects/{pid}/audit-jobs', data={'privacy_ack':'true','report_text':'论文中方法的准确率为95%。','scope':['results'],**extra})


def test_audit_submit_results_exports_and_duplicate_guard(setup):
    options, runner, store, pid = setup
    runner.release.clear()
    with TestClient(create_app(**options)) as client:
        response = submit(client,pid)
        assert response.status_code==202, response.text
        assert runner.entered.wait(2)
        assert submit(client,pid).status_code==400
        runner.release.set()
        job = wait_job(client,pid,response.json()['job_id'])
        assert job['status']=='SUCCEEDED'
        aid=job['audit_id']
        assert len(client.get(f'/api/projects/{pid}/audits').json())==1
        assert client.get(f'/api/projects/{pid}/audits/{aid}').json()['run']['report_text']=='论文中方法的准确率为95%。'
        for fmt in ['md','json']:
            exported=client.get(f'/api/projects/{pid}/audits/{aid}/export?format={fmt}')
            assert exported.status_code==200 and len(exported.content)>100
        assert client.post(f'/api/projects/{pid}/audit-jobs/{job["job_id"]}/retry').status_code==409
        assert len(runner.calls)==1


def test_failure_retry_preserves_snapshot_and_rejects_old_retries(setup):
    options,runner,store,pid=setup
    runner.fail=True
    with TestClient(create_app(**options)) as client:
        first=submit(client,pid).json()
        failed=wait_job(client,pid,first['job_id'])
        assert failed['status']=='FAILED' and 'secret-audit-test' not in failed['error']
        client.app.state.api.settings=replace(options['settings'],model='different',deep_audit=True)
        runner.fail=False
        response=client.post(f'/api/projects/{pid}/audit-jobs/{first["job_id"]}/retry')
        assert response.status_code==202
        retry=response.json()
        assert retry['runtime']==first['runtime']
        assert retry['scope']==first['scope'] and retry['report_text']==first['report_text']
        assert wait_job(client,pid,retry['job_id'])['status']=='SUCCEEDED'
        assert client.post(f'/api/projects/{pid}/audit-jobs/{first["job_id"]}/retry').status_code==409


def pptx_bytes():
    deck=Presentation();slide=deck.slides.add_slide(deck.slide_layouts[1])
    slide.shapes.title.text='实验结果'
    slide.placeholders[1].text='准确率为95%，延迟25毫秒。'
    buffer=BytesIO();deck.save(buffer);return buffer.getvalue()


@pytest.mark.parametrize('filename,data',[('report.txt','准确率95%。'.encode()),('report.md','# 结果\n准确率95%。'.encode()),('report.pptx',pptx_bytes())])
def test_preview_and_file_submission(setup,filename,data):
    options,runner,store,pid=setup
    with TestClient(create_app(**options)) as client:
        files={'report_file':(filename,data)}
        preview=client.post('/api/report-files/parse',files=files)
        assert preview.status_code==200 and preview.json()['character_count']>0
        assert not store.list_audit_jobs(pid) and not runner.calls
        response=client.post(f'/api/projects/{pid}/audit-jobs',files=files,data={'privacy_ack':'true'})
        assert response.status_code==202,response.text
        job=wait_job(client,pid,response.json()['job_id'])
        assert job['status']=='SUCCEEDED' and job['source_filename']==filename


@pytest.mark.parametrize('data,files,status',[
    ({'report_text':'hello'},None,422),
    ({'privacy_ack':'true'},None,422),
    ({'privacy_ack':'true','report_text':'   '},None,422),
    ({'privacy_ack':'true','report_text':'x'*100001},None,422),
    ({'privacy_ack':'true','report_text':'a','scope':'invalid'},None,422),
    ({'privacy_ack':'true'}, {'report_file':('x.exe',b'bad')},422),
    ({'privacy_ack':'true'}, {'report_file':('x.pptx',b'bad')},422),
    ({'privacy_ack':'true','report_text':'a'}, {'report_file':('x.txt',b'b')},422),
    ({'privacy_ack':'true','source':'lecture'},None,409),
])
def test_invalid_audit_has_no_side_effects(setup,data,files,status):
    options,runner,store,pid=setup
    with TestClient(create_app(**options)) as client:
        response=client.post(f'/api/projects/{pid}/audit-jobs',data=data,files=files)
        assert response.status_code==status,response.text
        assert not store.list_audit_jobs(pid) and not runner.calls


def test_lecture_source_and_home_upload_and_restart(setup):
    options,runner,store,pid=setup
    store.save_learning_report(pid,FakeService().generate_learning_report(store.load_learning_project(pid).paper))
    with TestClient(create_app(**options)) as client:
        response=client.post(f'/api/projects/{pid}/audit-jobs',data={'source':'lecture','privacy_ack':'true'})
        job=wait_job(client,pid,response.json()['job_id'])
        assert job['status']=='SUCCEEDED' and job['audit_mode']=='audit_generated'
        assert job['source_type']=='generated_learning_report' and '测试要点' in job['report_text']
        response=client.post('/api/projects',files={'pdf':('new.pdf',test_pdf())},data={'mode':'audit_existing','privacy_ack':'true','report_text':'论文准确率为95%。'})
        assert response.status_code==201,response.text
        newpid=response.json()['project']['project_id']
        assert wait_job(client,newpid,response.json()['job']['job_id'])['status']=='SUCCEEDED'
        count=len(runner.calls)
    with TestClient(create_app(**options)) as client:
        assert len(client.get(f'/api/projects/{pid}/audits').json())>=1
        assert len(runner.calls)==count


def test_restart_interrupts_queued_audit_without_call(setup):
    options,runner,store,pid=setup
    job=store.create_audit_job(pid,report_text='test',source_type='uploaded_report',source_label='test',source_filename=None,
         scope=[ClaimCategory.RESULTS],audit_mode='audit_existing',runtime=AuditRuntimeSnapshot(model='fake',reasoning_effort='low',retrieval_top_k=5,judge_batch_size=6))
    with TestClient(create_app(**options)) as client:
        assert wait_job(client,pid,job.job_id)['status']=='INTERRUPTED'
        assert not runner.calls
