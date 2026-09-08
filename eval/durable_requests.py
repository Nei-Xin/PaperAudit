"""Per-run ordered response checkpoints and bounded transport retries."""
import hashlib
import json
from pathlib import Path
import time
from openai.types.chat import ChatCompletion

class TransportPaused(RuntimeError):
    pass

def write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    temporary.replace(path)

class DurableRequests:
    def __init__(self,create,directory,sleep=time.sleep,before_attempt=None):
        self.create=create;self.directory=Path(directory);self.sleep=sleep;self.index=0
        self.before_attempt=before_attempt

    def __call__(self,**kwargs):
        self.index+=1
        path=self.directory/f'{self.index:04d}.json'
        digest=hashlib.sha256(json.dumps(kwargs,sort_keys=True,ensure_ascii=False,default=str).encode()).hexdigest()
        record=json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'request_sha256':digest,'attempts':[]}
        if record['request_sha256']!=digest:
            raise RuntimeError('Checkpoint request mismatch; refuse replay')
        if record.get('response'):
            return ChatCompletion.model_validate(record['response'])
        if len(record['attempts'])>=6:
            raise TransportPaused('Lifetime request attempt limit reached')
        for local in range(min(3,6-len(record['attempts']))):
            if self.before_attempt: self.before_attempt()
            start=time.monotonic()
            try:
                response=self.create(**kwargs)
            except Exception as exc:
                code=getattr(exc,'status_code',None)
                retryable=code in {408,409,429,500,502,503,504} or type(exc).__name__ in {'APIConnectionError','APITimeoutError'}
                record['attempts'].append({'status':'error','error_type':type(exc).__name__,'http_status':code,
                    'seconds':time.monotonic()-start})
                write(path,record)
                if not retryable:
                    if code in {401,402,403}:
                        raise TransportPaused('Authentication/billing rejection') from exc
                    raise
                if local==2 or len(record['attempts'])>=6:
                    raise TransportPaused('Transient service failure exhausted bounded retries') from exc
                self.sleep((5,15)[local])
            else:
                record['response']=response.model_dump(mode='json')
                record['attempts'].append({'status':'ok','seconds':time.monotonic()-start,
                    'usage':response.usage.model_dump() if response.usage else None})
                write(path,record)
                return response
        raise TransportPaused('Request retry budget exhausted')
