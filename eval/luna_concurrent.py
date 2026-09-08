"""Amended task concurrency; application requests and frozen inputs unchanged."""
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from threading import Event, Lock
from datetime import datetime, timezone
from dataclasses import asdict
import json
import msvcrt
from eval import luna_reliable_experiment as base
from eval.durable_requests import DurableRequests, TransportPaused, write
from eval.reference_annotation_v2 import read
from eval.final_hy3_experiment import sha

OUT=base.OUT
REV=OUT/'amendments/concurrency2'

class Guard:
    def __init__(self):
        self.stop=Event(); self.auth=Event(); self.lock=Lock(); self.rate_count=0
    def factory(self,create,directory):
        def guarded(**kwargs):
            try: result=create(**kwargs)
            except Exception as exc:
                code=getattr(exc,'status_code',None)
                with self.lock:
                    self.rate_count=self.rate_count+1 if code==429 else 0
                    if code in (401,402,403): self.auth.set(); self.stop.set()
                    if self.rate_count>=2: self.stop.set()
                raise
            with self.lock: self.rate_count=0
            return result
        def before_attempt():
            if self.auth.is_set(): raise TransportPaused('Authentication/billing circuit open')
        durable=DurableRequests(guarded,directory,before_attempt=before_attempt)
        def request(**kwargs):
            try: return durable(**kwargs)
            except TransportPaused:
                self.stop.set(); raise
        return request

def dispatch(jobs,workers,job,guard):
    pending=list(jobs); interrupted=[]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        active={}
        while active or (pending and not guard.stop.is_set()):
            while pending and len(active)<workers and not guard.stop.is_set():
                item=pending.pop(0); active[pool.submit(job,item)]=item
            if not active: break
            done,_=wait(active,return_when=FIRST_COMPLETED)
            for future in done:
                item=active.pop(future)
                try: future.result()
                except TransportPaused:
                    guard.stop.set(); interrupted.append(item)
                except BaseException:
                    guard.stop.set(); raise
    return interrupted+pending

def main():
    OUT.mkdir(exist_ok=True)
    with (OUT/'concurrent.lock').open('a+b') as lock:
        lock.seek(0); lock.write(b'0'); lock.flush(); lock.seek(0)
        msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        execute()

def execute():
    global REV
    p=read(OUT/'protocol.json'); amendment=read(REV/'amendment.json')
    assert sha(OUT/'protocol.json')==sha(REV/'protocol.original.json')
    upgrade=OUT/'amendments/concurrency4/amendment.json'
    workers=2; fallback_workers=1
    if upgrade.exists():
        amended=read(upgrade)
        amendment=dict(amendment,source_sha256=dict(amendment['source_sha256'],**amended['source_sha256']),observation_tasks=amended['observation_tasks'])
        REV=upgrade.parent; workers=4; fallback_workers=2
        for name,h in amended['preserved_results'].items(): assert sha(OUT/name)==h,name
    for name,h in p['source_sha256'].items():
        expected=amendment['source_sha256'].get(name.replace('\\','/'),h)
        assert sha(base.ROOT/name)==expected,name
    for name,h in amendment['source_sha256'].items(): assert sha(base.ROOT/name)==h,name
    for name,h in p['input_sha256'].items(): assert sha(OUT/name)==h,name
    for name,h in read(OUT/'reference_freeze.json')['sha256'].items(): assert sha(OUT/name)==h,name
    runtime=asdict(base.previous.settings()); runtime.pop('api_key'); assert runtime==p['runtime']
    papers={r['paper_id']:base.ParsedPaper.model_validate(read(OUT/r['evidence_path'])) for r in read(OUT/'inputs/papers.json')}
    jobs=[(r,i) for i in (1,2,3) for r in p['reports'] if i<=r['repeats'] and not (OUT/f'run_{i}'/(r['report_id']+'.json')).exists()]
    loglock=Lock()
    def run_phase(items,workers,phase):
        guard=Guard()
        def job(item):
            r,i=item; rid=r['report_id']; path=OUT/f'run_{i}'/(rid+'.json')
            started=datetime.now(timezone.utc).isoformat()
            checkpoints=path.parent/(path.stem+'_checkpoints')
            baseline={c.name:len(read(c)['attempts']) for c in checkpoints.glob('*.json')}
            outcome='paused'
            try:
                result=base.run_one(papers[r['paper_id']],(OUT/r['report_path']).read_text(encoding='utf-8'),
                    [base.ClaimCategory(c) for c in p['scope']],path,'luna_reliable_formal',rid,i,guard.factory)
                outcome=result['status']
            finally:
                attempts=[a for c in checkpoints.glob('*.json') for a in read(c)['attempts'][baseline.get(c.name,0):]]
                with loglock:
                    with (REV/'execution.jsonl').open('a',encoding='utf-8') as stream:
                        stream.write(json.dumps(dict(report_id=rid,repeat=i,phase=phase,workers=workers,started_at=started,
                            finished_at=datetime.now(timezone.utc).isoformat(),status=outcome,
                            network_attempts=len(attempts),successful_attempts=sum(a['status']=='ok' for a in attempts),
                            network_seconds=sum(a['seconds'] for a in attempts)))+'\n')
                print(rid+'/'+str(i)+' '+outcome,flush=True)
        base.status('auditing_amended',workers=workers,phase=phase)
        left=dispatch(items,workers,job,guard)
        return left,guard
    state=read(REV/'scheduler.json') if (REV/'scheduler.json').exists() else {'fallback_used':False}
    if state.get('terminal_pause'):
        raise TransportPaused('Stopped after bounded fallback; explicit recovery required')
    if state['fallback_used']:
        left,guard=run_phase(jobs,fallback_workers,f'fallback{fallback_workers}')
    else:
        observation=set(amendment['observation_tasks'])
        first=[j for j in jobs if j[0]['report_id']+'/'+str(j[1]) in observation]
        later=[j for j in jobs if j not in first]
        left,guard=run_phase(first,workers,f'observation_parallel{workers}')
        if not guard.stop.is_set(): left,guard=run_phase(later,workers,f'parallel{workers}')
        else: left+=later
        if guard.stop.is_set() and not guard.auth.is_set():
            state={'fallback_used':True,'at':datetime.now(timezone.utc).isoformat()}; write(REV/'scheduler.json',state)
            left,guard=run_phase(left,fallback_workers,f'fallback{fallback_workers}')
    if guard.auth.is_set() or left or guard.stop.is_set():
        write(REV/'scheduler.json',dict(state,terminal_pause=True))
        base.status('paused_amended',auth=guard.auth.is_set(),remaining=len(left)); return
    base.status('audits_complete_analysis_pending')
    marker=OUT/'amendments/concurrency2/downstream.json'
    if marker.exists(): return
    write(marker,{'stage':'alignment_started','at':datetime.now(timezone.utc).isoformat()})
    from eval.luna_reliable_alignment import main as align
    from eval import luna_reliable_analysis as analysis
    align()
    write(marker,{'stage':'analysis_started'})
    analysis.common.OUT=OUT; analysis.common.summarize(); analysis.report()
    write(marker,{'stage':'complete'})
    base.status('analysis_complete_pdf_pending')

if __name__=='__main__': main()
