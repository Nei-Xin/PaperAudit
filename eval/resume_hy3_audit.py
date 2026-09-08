"""Resume unattempted audits after credential rotation; stop on billing rejection."""
from datetime import datetime, timezone
from threading import Event
from eval import final_hy3_experiment as experiment
from eval.reference_annotation_v2 import read, save

def main():
    out=experiment.OUT
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    interrupted=[]
    # A request log without a result is an interrupted attempt, not a fresh slot.
    for path in sorted(out.glob('run_*/*_requests.json')):
        rid=path.name.removesuffix('_requests.json')
        result=path.with_name(rid+'.json')
        if result.exists():
            continue
        requests=read(path)
        save(result,{'report_id':rid,'repeat':int(path.parent.name.split('_')[1]),
            'status':'error','error_type':'InterruptedDuringServicePause',
            'seconds':sum(q.get('seconds',0) for q in requests),
            'seconds_note':'Lower bound from completed request logs; process was stopped.',
            'requests':requests,'raw_outputs':[],
            'interruption_note':'No completed audit available. Preserve attempt rather than silently re-running.'})
        interrupted.append(str(result.relative_to(out)))
    save(out/'resumptions'/(stamp+'.json'),{
        'timestamp':stamp,'model':'hy3','endpoint':'https://tokenhub.tencentmaas.com/v1',
        'reason':'User supplied a replacement credential; live connectivity test succeeded.',
        'interrupted_attempts_recorded':interrupted,
        'policy':'Preserve completed successes/failures; execute only unattempted slots. Stop new requests on HTTP 402.',
        'runner_sha256':experiment.sha(__import__('pathlib').Path(__file__))})
    stopped=Event()
    original=experiment.Hy3Client
    class GuardedClient(original):
        def __init__(self,settings):
            if stopped.is_set():
                raise RuntimeError('Audit stopped after HTTP 402; no new requests issued')
            super().__init__(settings)
            create=self._client.chat.completions.create
            def guarded(**kwargs):
                if stopped.is_set():
                    raise RuntimeError('Audit stopped after HTTP 402')
                try:
                    return create(**kwargs)
                except Exception as exc:
                    if getattr(exc,'status_code',None)==402:
                        stopped.set()
                    raise
            self._client.chat.completions.create=guarded
    experiment.Hy3Client=GuardedClient
    experiment.audit()
    if stopped.is_set():
        raise RuntimeError('Hy3 billing rejected; downstream analysis not started')

if __name__=='__main__':
    main()
