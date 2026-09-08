"""Real application smoke audit after the user-authorized Luna migration."""
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
import time
from eval.reference_annotation_v2 import read, save
from paperaudit.config import Settings
from paperaudit.hy3_client import Hy3Client
from paperaudit.models import ClaimCategory, ParsedPaper
from paperaudit.service import AuditService

ROOT = Path(__file__).resolve().parents[1]

def main():
    settings = Settings.from_env()
    assert settings.model == 'gpt-5.6-luna'
    dest = ROOT/'eval/luna_migration_smoke'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    runtime = asdict(settings)
    runtime.pop('api_key')
    save(dest/'config.json', {'runtime': runtime, 'purpose': 'Migration smoke, not formal evaluation',
        'reference_limitation': 'Existing Luna annotations are same-model references, not independent-model validation.'})
    paper = ParsedPaper.model_validate(read(ROOT/'eval/hy3_final_20260907/inputs/P03_paper.json'))
    report = '# 方法核查\n\n- DenseNet用特征拼接而非求和实现密集连接。（证据：论文第2页）\n\n- DenseNet用逐元素求和而非特征拼接实现密集连接。（证据：论文第2页）\n'
    save(dest/'input.json', {'report_text': report, 'paper_path': 'eval/hy3_final_20260907/inputs/P03_paper.json'})
    client = Hy3Client(settings)
    client._client.max_retries = 0
    start = time.monotonic()
    result = {}
    try:
        run = AuditService(settings, client=client).audit(paper, report, [ClaimCategory.METHOD],
            mode='luna_migration_smoke', progress=lambda message, value: print(message, flush=True))
        result.update(status='ok', audit=run.model_dump(mode='json'))
    except Exception as exc:
        result.update(status='error', error_type=type(exc).__name__, http_status=getattr(exc,'status_code',None))
    finally:
        result.update(seconds=time.monotonic()-start, raw_outputs=client.raw_outputs)
        save(dest/'result.json',result)
        client._client.close()
    print('Smoke status: '+result['status']+'; output: '+str(dest), flush=True)
    if result['status'] != 'ok':
        raise SystemExit(1)

if __name__ == '__main__':
    main()
