"""Continue the frozen experiment after reference recovery, with durable progress."""
import argparse
from datetime import datetime, timezone
import subprocess
import sys
import time
from eval.final_hy3_experiment import OUT, ROOT
from eval.reference_annotation_v2 import save

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--wait-reference',action='store_true')
    args=parser.parse_args()
    def status(stage,**extra):
        save(OUT/'workflow_status.json',dict(stage=stage,updated_at=datetime.now(timezone.utc).isoformat(),**extra))
        print(stage,flush=True)
    if args.wait_reference:
        status('waiting_for_reference_freeze')
        deadline=time.monotonic()+7200
        while not (OUT/'reference_freeze.json').exists():
            if time.monotonic()>deadline:
                status('blocked',reason='Reference recovery did not finish within two hours')
                raise SystemExit(1)
            time.sleep(10)
    phases=[]
    if not (OUT/'protocol.json').exists():
        phases.append(('freeze','eval.final_hy3_experiment','freeze'))
    phases.extend([('auditing','eval.resume_hy3_audit',None),
        ('aligning','eval.analyze_final_hy3','align'),('summarizing','eval.analyze_final_hy3','summarize'),
        ('writing_report','eval.write_final_hy3_report',None)])
    for stage,module,phase in phases:
        status(stage)
        command=[sys.executable,'-X','utf8','-m',module]+([phase] if phase else [])
        log=OUT/(stage+'.log')
        with log.open('a',encoding='utf-8') as output:
            result=subprocess.run(command,cwd=ROOT,stdout=output,stderr=subprocess.STDOUT)
        if result.returncode:
            status('failed',failed_stage=stage,exit_code=result.returncode,log=str(log.relative_to(OUT)))
            raise SystemExit(result.returncode)
    status('data_and_markdown_complete_pdf_review_pending')

if __name__=='__main__':
    main()
