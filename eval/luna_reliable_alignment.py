"""Serial blind semantic alignment using bounded durable transport."""
import json
from pathlib import Path
from dotenv import dotenv_values
from openai import OpenAI
from paperaudit.hy3_client import _extract_json
from eval.luna_reliable_experiment import ROOT,OUT
from eval.durable_requests import DurableRequests,write
from eval.reference_annotation_v2 import read
from eval.final_hy3_experiment import sha

SYSTEM=('只做语义对应，不判断事实真伪。将原始事实对齐到系统抽取的claims。full要求选中的claim完整保留原事实主体、关系、数字、条件和结论强度；'
    '仅同主题或同source_id绝不等于完整覆盖。多个claim可以共同完整覆盖一个fact。抽取中丢失数字/限定词/改写过强结论时必须partial。'
    '没有相应内容missing，不确定uncertain。只返回JSON {"matches":[{"fact_id":"...","claim_ids":["..."],"coverage":"full|partial|missing|uncertain","reason":"简短理由"}]}，包含所有fact_id。')

def validate(value,facts,claims):
    matches=value['matches']
    assert len(matches)==len(facts)
    assert {m['fact_id'] for m in matches}=={f['fact_id'] for f in facts}
    for m in matches:
        assert m['coverage'] in {'full','partial','missing','uncertain'}
        assert len(m['claim_ids'])==len(set(m['claim_ids']))
        assert set(m['claim_ids'])<={c['claim_id'] for c in claims}
        assert m['coverage']!='full' or m['claim_ids']

def main():
    env=dotenv_values(ROOT/'.env');protocol=read(OUT/'protocol.json')
    config={'model':env['REFERENCE_MODEL'],'api_base':env['REFERENCE_API_BASE'],'temperature':.2,'workers':1,
        'timeout':240,'transport':'3 attempts per invocation, 6 lifetime; 5/15 seconds backoff',
        'semantic_attempts':2,'blind_fields':'Only original facts and extracted claim text; no judgments or scores',
        'runner_sha256':sha(Path(__file__))}
    cfg=OUT/'alignment/config.json'
    if cfg.exists(): assert read(cfg)==config
    else: write(cfg,config)
    for r in protocol['reports']:
        rid=r['report_id'];blind=read(OUT/'inputs'/('blind_'+rid+'.json'))
        for repeat in range(1,r['repeats']+1):
            path=OUT/f'run_{repeat}'/(rid+'.json')
            assert path.exists(),'Wait for all formal audits before alignment'
            run=read(path)
            if run['status']!='ok': continue
            claims=[{k:a['claim'][k] for k in ('claim_id','text','source_id','source_quote')} for a in run['audit']['audits']]
            for attempt in (1,2):
                target=OUT/'alignment'/f'{rid}_{repeat}_attempt{attempt}.json'
                if target.exists():
                    if read(target)['status']=='ok': break
                    continue
                client=OpenAI(base_url=env['REFERENCE_API_BASE'],api_key=env['REFERENCE_API_KEY'],timeout=240,max_retries=0)
                transport=DurableRequests(client.chat.completions.create,OUT/'alignment_checkpoints'/target.stem)
                payload={'facts':blind['facts'],'claims':claims}
                messages=[{'role':'system','content':SYSTEM},{'role':'user','content':json.dumps(payload,ensure_ascii=False)}]
                write(OUT/'alignment_inputs'/f'{rid}_{repeat}_format{attempt}.json',{'model':env['REFERENCE_MODEL'],'temperature':.2,'messages':messages})
                try:
                    response=transport(model=env['REFERENCE_MODEL'],temperature=.2,messages=messages)
                finally:
                    client.close()
                result={'raw':response.choices[0].message.content or '', 'returned_model':response.model,
                    'response_id':response.id,'usage':response.usage.model_dump() if response.usage else None}
                try:
                    value=_extract_json(result['raw']);validate(value,blind['facts'],claims)
                    result.update(status='ok',value=value)
                except (ValueError,KeyError,AssertionError,TypeError) as exc:
                    result.update(status='error',error_type=type(exc).__name__)
                write(target,result)
                print(target.stem+' '+result['status'],flush=True)
                if result['status']=='ok': break
    paths=sorted((OUT/'alignment').glob('*.json'))+sorted((OUT/'alignment_inputs').glob('*.json'))
    write(OUT/'alignment_freeze.json',{'runner_sha256':sha(Path(__file__)),
        'sha256':{str(p.relative_to(OUT)):sha(p) for p in paths}})

if __name__=='__main__': main()
