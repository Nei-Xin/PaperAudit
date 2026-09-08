"""Activate only after the legacy process has exited at a report boundary."""
from datetime import datetime, timezone
import shutil
from eval.luna_concurrent import OUT, REV, main
from eval.luna_reliable_experiment import ROOT
from eval.reference_annotation_v2 import read
from eval.durable_requests import write
from eval.final_hy3_experiment import sha

def activate():
    held=REV/'P04_high.boundary.md'
    if held.exists(): held.replace(OUT/'reports/P04_high.md')
    protocol=read(OUT/'protocol.json')
    assert sha(OUT/'protocol.json')==sha(REV/'protocol.original.json')
    for name,digest in protocol['input_sha256'].items(): assert sha(OUT/name)==digest,name
    paths=[OUT/f'run_{i}'/(r['report_id']+'.json') for i in (1,2,3) for r in protocol['reports'] if i<=r['repeats']]
    completed=[p for p in paths if p.exists()]
    pending=[p.parent.name+'/'+p.stem for p in paths if not p.exists()]
    requests=[read(p) for p in OUT.glob('run_*/*_checkpoints/*.json')]
    attempts=[a for r in requests for a in r['attempts']]
    source_names=['eval/luna_reliable_experiment.py','eval/durable_requests.py','eval/luna_concurrent.py',
        'eval/activate_luna_concurrency.py','eval/luna_reliable_analysis.py','eval/package_luna_report.py']
    target=REV/'amendment.json'
    assert not target.exists(),'Already activated; use existing amended runner'
    write(target,dict(created_at=datetime.now(timezone.utc).isoformat(),workers_before=1,workers_after=2,
        old_protocol_sha256=sha(REV/'protocol.original.json'),
        source_sha256={name:sha(ROOT/name) for name in source_names},
        preserved_results={str(p.relative_to(OUT)):sha(p) for p in completed},affected_tasks=pending,
        observation_tasks=[p.stem+'/'+p.parent.name.split('_')[1] for p in paths if not p.exists()][:4],
        baseline_transport=dict(network_attempts=len(attempts),successful_attempts=sum(a['status']=='ok' for a in attempts),network_seconds=sum(a['seconds'] for a in attempts)),
        transition='Old downstream waiter stopped. Next report file temporarily held until old process exited before run_one; restored with original hash. Current in-flight report allowed to finish. No audit response discarded.',
        policy='4 formal tasks observe concurrency2; then continue2. Consecutive429 or exhausted retries stop dispatch, drain tasks, fallback1 once. Auth/billing stops new network requests. No automatic infinite recovery.'))
    for name in source_names:
        snapshot=REV/'sources'/name; snapshot.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(ROOT/name,snapshot)
    main()

if __name__=='__main__': activate()
