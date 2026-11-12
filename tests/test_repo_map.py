from dataclasses import replace
import json

import pytest
from pydantic import ValidationError

from paperaudit.agents.repo_mapper import build_repo_map, usable_map
from paperaudit.agents.code_investigator import CodeInvestigator
from paperaudit.consistency_inputs import index_hash
from paperaudit.models import RepoMap, RepoMapEntry, JointAnswer
from paperaudit.storage import ProjectStore, StorageError
from paperaudit.hy3_client import Hy3ResponseError
from paperaudit.request_budget import RequestBudget
from test_code_investigation import codebase, paper, ScriptedClient, call, submit, SETTINGS
from test_consistency import PlannedClient, draft, run

ENTRY=dict(path='configs/base.yaml',start_line=1,end_line=3,role='模型默认配置的位置')


def memory():
    return RepoMap(code_hash=index_hash(codebase()),model='fake',entries=[RepoMapEntry(**ENTRY)],stop_reason='finished',requests=2,tokens=30)


def mapper():
    return ScriptedClient([call('read_file',path=ENTRY['path'],start_line=1,end_line=3)],
                          [call('submit_repo_map',entries=[ENTRY])])


def test_map_submission_requires_read_sources_and_rejects_other_tools():
    client=ScriptedClient([call('grep_code',text='dropout'),call('submit_repo_map',entries=[ENTRY])],
        [call('read_file',path=ENTRY['path'],start_line=1,end_line=3)], [call('submit_repo_map',entries=[ENTRY])])
    result=build_repo_map(client,codebase(),'fake')
    assert result.entries==[RepoMapEntry(**ENTRY)] and result.requests==3
    assert not result.steps[0].ok and not result.steps[1].ok
    assert 'Unread source' in result.steps[1].outcome
    assert all(set(r['tools']) <= {'list_dir','find_symbol','read_file','submit_repo_map'} for r in client.requests)
    assert RepoMap.model_validate_json(result.model_dump_json())==result


def test_mapper_forces_final_submission_and_failure_keeps_usage():
    client=ScriptedClient(*[[call('list_dir',path='')] for _ in range(4)])
    result=build_repo_map(client,codebase(),'fake')
    assert not result.entries and result.requests==4
    assert client.requests[-1]['force']=='submit_repo_map' and client.requests[-1]['tools']==['submit_repo_map']
    assert not result.steps[-1].ok
    failed=build_repo_map(ScriptedClient(Hy3ResponseError('invalid')),codebase(),'fake')
    assert failed.requests==1 and failed.stop_reason=='invalid_model_response'
    with pytest.raises(ValidationError):
        RepoMap(code_hash='x',model='fake',stop_reason='finished',entries=[RepoMapEntry(**{**ENTRY,'role':'x'*160,'path':'x'*300})]*4)


def test_map_is_untrusted_navigation_and_does_not_authorize_citations():
    client=ScriptedClient([submit()],[submit()])
    result,trace=CodeInvestigator(client,paper(),codebase(),'fake',repo_map=memory()).run(
        'dropout?','joint',selected_paper_chunk_ids=['p2_b1'])
    assert trace.repo_map_used and (result is None or not result.findings)
    assert 'never returned by a tool' in ' '.join(trace.first_rejections).lower()
    task=client.requests[0]['messages'][1]['content']
    assert '<untrusted_repo_map>' in task and 'never evidence' in task and ENTRY['path'] in task
    stale=memory().model_copy(update={'code_hash':'old'})
    client=ScriptedClient([submit(status='INSUFFICIENT_EVIDENCE',findings=[])])
    _,trace=CodeInvestigator(client,paper(),codebase(),'fake',repo_map=stale).run('q','joint')
    assert not trace.repo_map_used and '<untrusted_repo_map>' not in client.requests[0]['messages'][1]['content']


def test_cache_survives_restart_rejects_stale_write_and_invalidates_on_replacement(tmp_path):
    store=ProjectStore(tmp_path)
    metadata=store.save_paper_project(b'paper','paper.pdf',paper())
    pid=metadata.project_id;store.save_codebase(pid,codebase());store.save_repo_map(pid,memory())
    assert ProjectStore(tmp_path).load_repo_map(pid)==memory()
    changed=codebase().model_copy(update={'name':'replacement.zip'})
    store.save_codebase(pid,changed)
    assert store.load_repo_map(pid) is None
    with pytest.raises(StorageError):store.save_repo_map(pid,memory())
    assert not usable_map(memory(),changed)
    directory=store._require_project_dir(pid);(directory/'repo-map.json').write_text('{invalid')
    assert store.load_repo_map(pid) is None


class MapClient(PlannedClient):
    def __init__(self, fail=False):
        super().__init__([draft('dropout'),draft('layers')]);self.mapper=mapper() if not fail else ScriptedClient(Hy3ResponseError('bad'))
    def tool_turn(self,messages,tools,*,force_tool=None):
        if any(t['function']['name']=='submit_repo_map' for t in tools):
            return self.mapper.tool_turn(messages,tools,force_tool=force_tool)
        return super().tool_turn(messages,tools,force_tool=force_tool)


def test_orchestrator_builds_once_before_parallel_work_and_cached_usage_is_zero():
    client=MapClient();saved=[]
    report=run(client,enable_repo_map=True,on_repo_map=saved.append,max_requests=29)
    assert len(saved)==1 and report.repo_map_requests==2 and not report.repo_map_reused
    assert report.requests==report.plan_requests+report.repo_map_requests+sum(i.answer.investigation.requests for i in report.items)
    assert report.requests<=report.max_requests and all(i.answer.investigation.repo_map_used for i in report.items)
    client=MapClient()
    reused=run(client,enable_repo_map=True,repo_map=saved[0],max_requests=25)
    assert reused.repo_map_reused and reused.repo_map_requests==0 and not client.mapper.requests
    assert reused.requests==1+sum(i.answer.investigation.requests for i in reused.items)
    assert all('<untrusted_repo_map>' in m for m in client.first_messages.values())


def test_failed_map_does_not_block_investigations_and_small_budget_skips_build():
    report=run(MapClient(fail=True),enable_repo_map=True,max_requests=29)
    assert report.repo_map_requests==1 and report.repo_map.stop_reason=='invalid_model_response'
    assert report.summary.checked==2 and not any(i.answer.investigation.repo_map_used for i in report.items)
    client=MapClient();report=run(client,enable_repo_map=True,max_requests=13)
    assert report.repo_map is None and not client.mapper.requests and report.requests<=13


def test_map_flag_is_frozen_with_job_settings():
    from paperaudit.workflows import runtime_snapshot
    from paperaudit.models import AuditRuntimeSnapshot
    raw=runtime_snapshot(replace(SETTINGS,repo_map=True)).model_dump()
    assert AuditRuntimeSnapshot.model_validate(raw).repo_map
    del raw['repo_map']
    assert not AuditRuntimeSnapshot.model_validate(raw).repo_map


def test_background_execution_persists_map_and_reuses_it_after_restart(tmp_path):
    from fastapi.testclient import TestClient
    from paperaudit.api.main import create_app
    from paperaudit.code_service import CodeLearningService
    from test_consistency import make_store
    from test_consistency_planner import wait_job
    store,pid,chunk=make_store(tmp_path)
    client=MapClient()
    client.drafts=[draft('dropout',chunk_id=chunk),draft('layers',chunk_id=chunk)]
    client.paper_quote={'chunk_id':chunk,'quote':'dropout with a rate of 0.1'}
    settings=replace(SETTINGS,repo_map=True)
    def app():
        return create_app(storage_root=tmp_path/'library',settings_dir=tmp_path/'settings',settings=settings,
            code_service_factory=lambda s:CodeLearningService(s,client))
    with TestClient(app()) as http:
        response=http.post(f'/api/projects/{pid}/consistency-jobs',json={'privacy_ack':True,'mode':'plan'})
        job=wait_job(http,pid,response.json()['job_id']);assert job['status']=='SUCCEEDED'
        assert not client.mapper.requests and store.load_repo_map(pid) is None
        endpoint=f"/api/projects/{pid}/consistency-plans/{job['plan_id']}/execute"
        response=http.post(endpoint,json={'privacy_ack':True,'selected_ids':['K01']})
        job=wait_job(http,pid,response.json()['job_id']);assert job['status']=='SUCCEEDED',job
        report=http.get(f"/api/projects/{pid}/consistency-reports/{job['report_id']}").json()
        assert report['repo_map_requests']==2 and store.load_repo_map(pid)
    with TestClient(app()) as http:
        response=http.post(endpoint,json={'privacy_ack':True,'selected_ids':['K02']})
        job=wait_job(http,pid,response.json()['job_id']);assert job['status']=='SUCCEEDED',job
        report=http.get(f"/api/projects/{pid}/consistency-reports/{job['report_id']}").json()
        assert report['repo_map_reused'] and report['repo_map_requests']==0
        assert len(client.mapper.requests)==2


def test_followup_uses_cached_map_only_when_enabled_and_still_reads_evidence():
    from paperaudit.code_service import CodeLearningService
    for enabled in (False,True):
        client=ScriptedClient([call('read_page',page=2),call('read_file',path='configs/base.yaml',start_line=1,end_line=3)], [submit()])
        result=CodeLearningService(replace(SETTINGS,repo_map=enabled),client).answer(
            paper(),codebase(),'论文的 dropout 与代码一致吗？',investigate=True,repo_map=memory())
        assert result.investigation.repo_map_used==enabled
        assert result.findings and result.investigation.requests==2
        assert ('<untrusted_repo_map>' in client.requests[0]['messages'][1]['content'])==enabled
