from openai.types.chat import ChatCompletion
import pytest
from eval.durable_requests import DurableRequests,TransportPaused

def response():
    return ChatCompletion(id='test',created=0,model='test',object='chat.completion',choices=[])

class APITimeoutError(Exception):
    pass

def test_retry_and_replay_without_network(tmp_path):
    calls=[]
    def request(**kwargs):
        calls.append(kwargs)
        if len(calls)==1: raise APITimeoutError()
        return response()
    assert DurableRequests(request,tmp_path,sleep=lambda _:None)(model='test').id=='test'
    assert len(calls)==2
    assert DurableRequests(request,tmp_path)(model='test').id=='test'
    assert len(calls)==2
    with pytest.raises(RuntimeError,match='mismatch'):
        DurableRequests(request,tmp_path)(model='different')

def test_billing_never_retried(tmp_path):
    class Billing(Exception): status_code=402
    calls=[]
    def request(**kwargs):
        calls.append(1);raise Billing()
    with pytest.raises(TransportPaused): DurableRequests(request,tmp_path)(model='test')
    assert len(calls)==1

def test_retry_budget_survives_resume(tmp_path):
    calls=[]
    def request(**kwargs): calls.append(1);raise APITimeoutError()
    for _ in range(3):
        with pytest.raises(TransportPaused): DurableRequests(request,tmp_path,sleep=lambda _:None)(model='test')
    assert len(calls)==6


def test_resume_replays_prefix_and_continues_interrupted_request(tmp_path):
    calls=[]
    def interrupted(**kwargs):
        calls.append(kwargs['model'])
        if kwargs['model']=='second': raise APITimeoutError()
        return response()
    initial=DurableRequests(interrupted,tmp_path,sleep=lambda _:None)
    initial(model='first')
    with pytest.raises(TransportPaused): initial(model='second')
    resumed_calls=[]
    def healthy(**kwargs):
        resumed_calls.append(kwargs['model'])
        return response()
    resumed=DurableRequests(healthy,tmp_path,sleep=lambda _:None)
    resumed(model='first')
    resumed(model='second')
    resumed(model='third')
    assert calls==['first','second','second','second']
    assert resumed_calls==['second','third']
