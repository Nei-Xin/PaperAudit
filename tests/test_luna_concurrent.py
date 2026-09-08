from threading import Barrier
from concurrent.futures import ThreadPoolExecutor
import pytest
from eval.luna_concurrent import Guard, dispatch
from eval.durable_requests import TransportPaused, write
from eval.luna_reliable_experiment import run_one
from openai.types.chat import ChatCompletion

def test_completed_run_skips_client(tmp_path):
    path=tmp_path/'R1.json'; write(path,{'status':'ok'})
    assert run_one(None,None,None,path,None,None,None)=={'status':'ok'}

def test_concurrent_checkpoints_are_separate(tmp_path):
    gate=Barrier(2); guard=Guard()
    def request(**kwargs):
        gate.wait(timeout=3)
        return ChatCompletion(id=kwargs['model'],created=0,model='test',object='chat.completion',choices=[])
    def job(name): return guard.factory(request,tmp_path/name)(model=name).id
    with ThreadPoolExecutor(2) as pool: assert list(pool.map(job,['A','B']))==['A','B']
    assert (tmp_path/'A/0001.json').exists() and (tmp_path/'B/0001.json').exists()

def test_pause_stops_dispatch_and_drains():
    guard=Guard(); calls=[]
    def job(item):
        calls.append(item); guard.stop.set(); raise TransportPaused('exhausted')
    assert dispatch([1,2,3],1,job,guard)==[1,2,3]
    assert calls==[1]

def test_auth_stops_new_network_requests(tmp_path):
    guard=Guard(); calls=[]
    class Unauthorized(Exception): status_code=401
    def request(**kwargs): calls.append(1); raise Unauthorized()
    for name in ['A','B']:
        with pytest.raises(TransportPaused): guard.factory(request,tmp_path/name)(model='test')
    assert calls==[1] and guard.auth.is_set() and guard.stop.is_set()
