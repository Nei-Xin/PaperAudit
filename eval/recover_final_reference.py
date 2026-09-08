"""Preserve service failures and retry only their slots before final freeze."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import shutil
from eval.final_hy3_experiment import OUT, sha
from eval.reference_annotation_v2 import annotate, read, save

def main():
    assert not (OUT/'protocol.json').exists(), 'Do not repair labels after experiment freeze'
    assert not read(OUT/'inputs/pending.json'), 'Inputs must be complete'
    def one(p):
        pid=p['paper_id']; old=OUT/'reference'/pid; dest=OUT/'reference_recovery'/pid
        dest.mkdir(parents=True,exist_ok=True)
        copied=[]; retry=[]
        for path in sorted(old.glob('*attempt*.json')):
            value=read(path)
            if value.get('error_type') in {'InternalServerError','APIConnectionError','APITimeoutError','RateLimitError','APIStatusError'}:
                retry.append(str(path.relative_to(OUT)))
                continue
            target=dest/path.name
            if not target.exists():
                shutil.copy2(path,target)
            copied.append({'source':str(path.relative_to(OUT)),'sha256':sha(path)})
        save(dest/'recovery_manifest.json',{'preserved_attempts':copied,'service_failure_slots':retry,
            'policy':'Only failed transport/service slots retried once through original two-attempt workflow. Other attempts reused. Before any Hy3 final predictions.'})
        blind=[read(path) for path in sorted((OUT/'inputs').glob('blind_'+pid+'_*.json'))]
        annotate(OUT,blind,read(OUT/p['evidence_path']),dest,workers=4)
    with ThreadPoolExecutor(max_workers=1) as pool:
        list(pool.map(one,read(OUT/'inputs/papers.json')))
    save(OUT/'reference_selection.json',{'directory':'reference_recovery',
        'reason':'Explicit recovery of server failures before final audit; original reference remains available.'})
    paths=sorted((OUT/'reference_recovery').rglob('*.json'))+sorted((OUT/'reference').rglob('*.json'))+[OUT/'reference_selection.json']
    save(OUT/'reference_freeze.json',{'sha256':{str(p.relative_to(OUT)):sha(p) for p in paths}})

if __name__=='__main__':
    main()
