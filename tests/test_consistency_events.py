import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from paperaudit.api.consistency_routes import event_stream
from paperaudit.api.main import create_app
from paperaudit.consistency_events import read_events, step_fields
from paperaudit.agents.models import CodeInvestigationStep
from paperaudit.agents.consistency import ConsistencyOrchestrator
from paperaudit.code_service import CodeLearningService
from paperaudit.storage import ProjectStore, StorageError
from paperaudit.models import AuditJobStatus
from test_code_investigation import SETTINGS, paper, codebase
from test_consistency import make_store, RUNTIME, PlannedClient, draft
from test_consistency_planner import wait_job


def queued(tmp_path):
    store,pid,_=make_store(tmp_path)
    job=store.create_consistency_job(pid,runtime=RUNTIME)
    return store,pid,job


def read_all(path):
    rows=[];offset=0
    while True:
        batch,offset=read_events(path,offset);rows+=batch
        if len(batch)<128:return rows


def test_parallel_writers_assign_contiguous_ids_and_survive_store_restart(tmp_path):
    store,pid,job=queued(tmp_path)
    def append(n):
        store.append_consistency_event(pid,job.job_id,kind='tool_step',checkpoint_id=f'K{n%4}',outcome=f'step {n}')
    with ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(append,range(240)))
    path=store.consistency_event_path(pid,job.job_id)
    rows=read_all(path)
    assert [r.event_id for r in rows]==list(range(1,241))
    assert len({r.outcome for r in rows})==240
    restarted=ProjectStore(store.storage_root)
    last=restarted.append_consistency_event(pid,job.job_id,kind='planning_finished')
    assert last.event_id==241
    # Complete records remain visible; a torn final write is discarded on the next append.
    with path.open('ab') as f:f.write(b'{"event_id":242,"outcome":"partial')
    assert len(read_all(path))==241
    assert restarted.append_consistency_event(pid,job.job_id,kind='planning_finished').event_id==242
    assert len(read_all(path))==242
    with pytest.raises(StorageError):store.consistency_event_path(pid,'../../escape')
    wrong_pid=store.save_paper_project(b'other','other.pdf',paper()).project_id
    with pytest.raises(StorageError):store.consistency_event_path(wrong_pid,job.job_id)


def test_step_events_do_not_contain_raw_submissions_or_rejected_quotes():
    raw='SECRET_MODEL_OUTPUT'
    for tool in ['submit_answer','propose_checkpoint','unknown']:
        result=step_fields(CodeInvestigationStep(tool=tool,arguments={'raw':raw,'quote':raw,'findings':[raw]},outcome=raw,ok=False))
        assert raw not in json.dumps(result)
    result=step_fields(CodeInvestigationStep(tool='read_file',arguments={'path':'a.py','start_line':1,'end_line':5,'secret':raw},outcome='读取 5 行'))
    assert result['arguments']=={'path':'a.py','start_line':1,'end_line':5}


def test_orchestrator_emits_planning_parallel_steps_review_and_final_verdicts():
    events=[];client=PlannedClient([draft('dropout'),draft('other')],delay=.01)
    report=ConsistencyOrchestrator(client,'fake',on_event=lambda **e:events.append(e)).run(paper(),codebase())
    assert events[0]['kind']=='planning_started'
    assert sum(e['kind']=='checkpoint_accepted' for e in events)==2
    for i in report.items:
        group=[e for e in events if e.get('checkpoint_id')==i.checkpoint.checkpoint_id]
        kinds=[e['kind'] for e in group]
        assert kinds.index('item_queued')<kinds.index('item_started')<kinds.index('tool_step')<kinds.index('verification')<kinds.index('item_finished')
        assert group[-1]['verdicts']==['INCONSISTENT'] and group[-1]['pending_review']==0
    assert report.requests==7


def test_agent_plan_events_arrive_during_planning_and_failed_items_finish():
    events=[];client=PlannedClient([draft('dropout')])
    plan=ConsistencyOrchestrator(client,'fake',on_event=lambda **e:events.append(e)).plan(paper(),codebase(),strategy='agent')
    assert plan.checkpoints and any(e['kind']=='planning_step' for e in events)
    accepted=[e for e in events if e['kind']=='checkpoint_accepted']
    assert len(accepted)==1 and accepted[0]['checkpoint_id']=='K01'
    events=[];client=PlannedClient([draft('bad')],behaviour={'bad 和代码一致吗？':'crash'})
    report=ConsistencyOrchestrator(client,'fake',on_event=lambda **e:events.append(e)).run(paper(),codebase())
    assert report.summary.failed==1
    assert next(e for e in events if e['kind']=='item_finished')['status']=='failed'


def test_api_replay_header_priority_bad_cursors_and_old_jobs(tmp_path):
    store,pid,job=queued(tmp_path)
    for n in range(3):store.append_consistency_event(pid,job.job_id,kind='tool_step',outcome=str(n))
    store.update_consistency_job(pid,job.model_copy(update={'status':AuditJobStatus.SUCCEEDED,'stage':'done'}))
    app=create_app(storage_root=store.storage_root,settings_dir=tmp_path/'settings',settings=SETTINGS)
    with TestClient(app) as http:
        url=f'/api/projects/{pid}/consistency-jobs/{job.job_id}/events'
        response=http.get(url)
        assert response.status_code==200 and response.headers['content-type'].startswith('text/event-stream')
        assert response.headers['cache-control']=='no-store' and response.headers['x-accel-buffering']=='no'
        assert 'id: 1\n' in response.text and 'event: end' in response.text
        resumed=http.get(url+'?after=3',headers={'Last-Event-ID':'2'})
        assert 'id: 1\n' not in resumed.text and 'id: 2\n' not in resumed.text and 'id: 3\n' in resumed.text
        assert http.get(url,headers={'Last-Event-ID':'invalid'}).status_code==422
        assert http.get(url+'?after=-1').status_code==422
        assert http.get(url+'?after=9999').status_code==409
        assert http.get(url.replace(job.job_id,'consistency-job-missing')).status_code==404
        # Legacy terminal tasks can have no event file at all.
        store.consistency_event_path(pid,job.job_id).unlink()
        old=http.get(url)
        assert 'event: end' in old.text and 'event: audit' not in old.text


def test_restart_marks_interrupted_and_event_stream_terminates(tmp_path):
    store,pid,job=queued(tmp_path)
    app=create_app(storage_root=store.storage_root,settings_dir=tmp_path/'settings',settings=SETTINGS)
    with TestClient(app) as http:
        response=http.get(f'/api/projects/{pid}/consistency-jobs/{job.job_id}/events')
        assert 'INTERRUPTED' in response.text and 'event: end' in response.text
        assert len(read_all(store.consistency_event_path(pid,job.job_id)))==1


class Connection:
    disconnected=False
    async def is_disconnected(self):return self.disconnected


def test_stream_delivers_before_completion_heartbeats_and_cleans_up_disconnect(tmp_path):
    store,pid,job=queued(tmp_path);path=store.consistency_event_path(pid,job.job_id)
    async def check():
        connection=Connection();stream=event_stream(connection,store,pid,job.job_id,path,0,poll_seconds=0,heartbeat_seconds=0)
        assert (await anext(stream)).startswith('retry:')
        store.append_consistency_event(pid,job.job_id,kind='item_started',checkpoint_id='K01')
        assert 'item_started' in await anext(stream)
        assert store.load_consistency_job(pid,job.job_id).status=='QUEUED'
        assert 'keep-alive' in await anext(stream)
        connection.disconnected=True
        with pytest.raises(StopAsyncIteration):await anext(stream)
        # Completion has more than one batch; every final event is delivered before end.
        for _ in range(130):store.append_consistency_event(pid,job.job_id,kind='tool_step')
        store.update_consistency_job(pid,job.model_copy(update={'status':AuditJobStatus.SUCCEEDED}))
        replay=[frame async for frame in event_stream(Connection(),store,pid,job.job_id,path,1,poll_seconds=0)]
        assert sum('event: audit' in f for f in replay)==131
        assert replay[-1].startswith('event: end')
    asyncio.run(check())


def test_background_workflow_persists_events_without_changing_request_usage(tmp_path):
    store,pid,chunk=make_store(tmp_path)
    client=PlannedClient([draft('dropout',chunk_id=chunk)],paper_quote={'chunk_id':chunk,'quote':'dropout with a rate of 0.1'})
    app=create_app(storage_root=store.storage_root,settings_dir=tmp_path/'settings',settings=SETTINGS,
                   code_service_factory=lambda s:CodeLearningService(s,client))
    with TestClient(app) as http:
        created=http.post(f'/api/projects/{pid}/consistency-jobs',json={'privacy_ack':True})
        job=wait_job(http,pid,created.json()['job_id']);assert job['status']=='SUCCEEDED'
        report=http.get(f"/api/projects/{pid}/consistency-reports/{job['report_id']}").json()
        assert report['requests']==4
        response=http.get(f"/api/projects/{pid}/consistency-jobs/{job['job_id']}/events")
        assert 'item_finished' in response.text and 'verification' in response.text
        assert response.text.index('item_finished')<response.text.index('event: end')
        assert 'SECRET_MODEL_OUTPUT' not in response.text


def test_corrupt_journal_does_not_prevent_recovery_or_job_status_reads(tmp_path):
    store,pid,job=queued(tmp_path)
    store.consistency_event_path(pid,job.job_id).write_bytes(b'{corrupt}\n')
    app=create_app(storage_root=store.storage_root,settings_dir=tmp_path/'settings',settings=SETTINGS)
    with TestClient(app) as http:
        assert store.load_consistency_job(pid,job.job_id).status=='INTERRUPTED'
        assert http.get(f'/api/projects/{pid}/consistency-jobs').status_code==200
        assert http.get(f'/api/projects/{pid}/consistency-jobs/{job.job_id}/events').status_code==409


def test_unavailable_event_storage_does_not_lose_audit_result(tmp_path,monkeypatch):
    from paperaudit.consistency_jobs import ConsistencyJobManager
    store,pid,chunk=make_store(tmp_path)
    client=PlannedClient([draft('dropout',chunk_id=chunk)],paper_quote={'chunk_id':chunk,'quote':'dropout with a rate of 0.1'})
    job=store.create_consistency_job(pid,runtime=RUNTIME)
    def unavailable(*args,**kwargs):raise OSError('test disk unavailable')
    monkeypatch.setattr(store,'append_consistency_event',unavailable)
    manager=ConsistencyJobManager(store,service_factory=lambda s:CodeLearningService(s,client),mark_interrupted_on_start=False)
    manager.submit(pid,job.job_id,SETTINGS);manager.shutdown()
    saved=store.load_consistency_job(pid,job.job_id)
    assert saved.status=='SUCCEEDED'
    assert store.load_consistency_report(pid,saved.report_id).requests==4
