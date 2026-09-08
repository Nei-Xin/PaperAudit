"""Offline replay verification; raises before any uncached network call."""
from pathlib import Path
import argparse
from eval.luna_reliable_experiment import ROOT,OUT
from eval.run_luna_experiment import settings
from eval.reference_annotation_v2 import read,save
from eval.durable_requests import DurableRequests
from paperaudit.hy3_client import Hy3Client
from paperaudit.models import ParsedPaper,ClaimCategory
from paperaudit.service import AuditService

class UncachedRequest(Exception): pass

def verify(rid):
    source=ROOT/'eval/hy3_pilot_20260907'
    report=next(r for r in read(source/'blind_inputs.json') if r['report_id']==rid)
    paper=ParsedPaper.model_validate(read(source/'paper_evidence.json'))
    client=Hy3Client(settings());calls=[]
    def offline(**kwargs):
        calls.append(1)
        raise UncachedRequest('No network permitted during replay verification')
    replay=DurableRequests(offline,OUT/'pilot'/(rid+'_checkpoints'))
    # Offline miss must not write an error into authoritative checkpoints.
    def only_cached(**kwargs):
        path=replay.directory/f'{replay.index+1:04d}.json'
        if not path.exists() or not read(path).get('response'):
            raise UncachedRequest('End of saved response prefix')
        return replay(**kwargs)
    client._client.chat.completions.create=only_cached
    complete=False
    try:
        run=AuditService(settings(),client=client).audit(paper,report['report_text'],list(ClaimCategory),mode='luna_reliable_pilot')
        original=read(OUT/'pilot'/(rid+'.json'))
        assert run.model_dump(mode='json')==original['audit'],'Replay differs from saved audit'
        complete=True
    except UncachedRequest:
        pass
    finally:
        client._client.close()
    assert not calls
    result=dict(report_id=rid,replayed_requests=replay.index,full_audit_identical=complete,network_calls=0)
    save(OUT/'verification'/(rid+'_replay.json'),result)
    print(result)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('report_id');args=p.parse_args();verify(args.report_id)
