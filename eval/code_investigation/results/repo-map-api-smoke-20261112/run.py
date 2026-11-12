"""Two real API executions across restart in a separate project store, never live data."""
from pathlib import Path
from dataclasses import replace
import json,time
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from paperaudit.api.main import create_app
from paperaudit.config import Settings
from paperaudit.storage import ProjectStore
from paperaudit.models import ConsistencyCheckpoint,ConsistencyPlan
from paperaudit.consistency_inputs import input_hashes
load_dotenv('/path/to/validation-root/app.env',override=True)
root=Path('/path/to/validation-root')
out=root/'experiments/repo-map-api-smoke-20261112';out.mkdir(exist_ok=False)
source=ProjectStore(root/'library').load_learning_project('1b490443925c72a2')
store=ProjectStore(out/'library');pid=store.save_paper_project(source.pdf_bytes,'mae.pdf',source.paper).project_id
store.save_codebase(pid,source.codebase)
plan=store.save_consistency_plan(pid,ConsistencyPlan(model='manual-smoke',strategy='manual-smoke',target=2,max_requests=40,
    **input_hashes(source.paper,source.codebase),checkpoints=[
        ConsistencyCheckpoint(checkpoint_id='K01',topic='预训练 warmup',category='training',source='user',question='预训练 warmup 的默认值与论文是否一致？请检查表格所属实验设置。'),
        ConsistencyCheckpoint(checkpoint_id='K02',topic='掩码比例',category='training',source='user',question='预训练默认掩码比例与论文一致吗？')]))
settings=replace(Settings.from_env(),repo_map=True,consistency_max_requests=40)
def app():return create_app(storage_root=out/'library',settings_dir=out/'settings',settings=settings)
reports=[]
for n in [1,2]:
 with TestClient(app()) as http:
    response=http.post(f'/api/projects/{pid}/consistency-plans/{plan.plan_id}/execute',json={'privacy_ack':True,'selected_ids':[f'K{n:02d}']})
    response.raise_for_status();job=response.json()
    for _ in range(400):
        job=next(j for j in http.get(f'/api/projects/{pid}/consistency-jobs').json() if j['job_id']==job['job_id'])
        if job['status'] not in ['QUEUED','RUNNING']:break
        time.sleep(1)
    assert job['status']=='SUCCEEDED',job
    report=http.get(f"/api/projects/{pid}/consistency-reports/{job['report_id']}").json()
    (out/f'report-{n}.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');reports.append(report)
    assert report['repo_map'] and report['repo_map']['entries']
    assert report['repo_map_reused']==(n==2)
    assert (1 <= report['repo_map_requests'] <= 4) if n==1 else report['repo_map_requests']==0
    assert all(i['answer']['investigation']['repo_map_used'] for i in report['items'])
    print(json.dumps({'run':n,'requests':report['requests'],'map_requests':report['repo_map_requests'],'summary':report['summary']}),flush=True)
assert store.load_repo_map(pid)
store.save_codebase(pid,source.codebase.model_copy(update={'name':'replacement.zip'}))
assert store.load_repo_map(pid) is None
with TestClient(app()) as http:
 response=http.post(f'/api/projects/{pid}/consistency-plans/{plan.plan_id}/execute',json={'privacy_ack':True,'selected_ids':['K01','K02']})
 assert response.status_code==409
outcome={'project_id':pid,'requests':sum(r['requests'] for r in reports),'tokens':sum(r['tokens'] for r in reports),
 'first_map_requests':reports[0]['repo_map_requests'],'reused_map_requests':reports[1]['repo_map_requests'],
 'restart_reuse':True,'replacement_invalidates_map':True,'stale_plan_http_status':409,'production_store_modified':False}
(out/'outcome.json').write_text(json.dumps(outcome,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(outcome),flush=True)
