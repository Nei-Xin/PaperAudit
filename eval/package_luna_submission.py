"""Build and verify the final offline submission bundle."""
from pathlib import Path
import hashlib
import json
import re
import zipfile
from dotenv import dotenv_values

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'eval/luna_reliable_20260907'
def sha(data): return hashlib.sha256(data).hexdigest()

def main():
    checks=json.loads((OUT/'verification/submission_checks.json').read_text(encoding='utf-8'))
    assert checks['tasks']==96 and checks['aligned_successful_runs']==93
    paths=[p for p in OUT.rglob('*') if p.is_file() and p.suffix not in {'.log','.tmp','.lock','.pyc'} and '__pycache__' not in p.parts]
    paths += list((ROOT/'src/paperaudit').rglob('*.py'))+list((ROOT/'eval').glob('*.py'))+list((ROOT/'tests').glob('*.py'))
    paths += [ROOT/n for n in ['pyproject.toml','uv.lock','README.md','output/pdf/PaperAudit_Luna_experiment_report.pdf'] if (ROOT/n).is_file()]
    secrets=[v.encode() for k,v in dotenv_values(ROOT/'.env').items() if v and ('KEY' in k or 'PASSWORD' in k) and len(v)>8]
    archive=ROOT/'output/PaperAudit_Luna_results.zip'; manifest={}
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for path in sorted(set(paths)):
            data=path.read_bytes(); name=path.relative_to(ROOT).as_posix()
            assert not any(secret in data for secret in secrets),'Secret in '+name
            assert not re.search(rb'sk-[A-Za-z0-9_-]{20,}',data),'Potential API key in '+name
            manifest[name]=sha(data); z.writestr(name,data)
        readme=('PaperAudit Luna 实验提交包\n\n'
            '结果：96次正式任务，93成功、3失败；93份成功结果完成语义对齐。\n'
            '报告：output/pdf/PaperAudit_Luna_experiment_report.pdf；Markdown位于eval/luna_reliable_20260907/submission_report.md。\n'
            '参考标注与对齐同样使用Luna，是同模型参考，不是人工金标或独立验证。主办方接受替代模型依据用户确认。\n'
            '历史Hy3和早期Luna探索实验仍保留在原项目，未混入本包正式统计。\n\n'
            '离线复现（无需API，不要运行联网审计命令）：\n'
            '1. 解压到独立目录，执行 uv sync。\n'
            '2. uv run python -m eval.luna_reliable_analysis summarize\n'
            '3. uv pip install matplotlib==3.11.1 reportlab==5.0.1\n'
            '4. uv run --no-sync python eval/finalize_luna_submission.py\n'
            '5. uv run --no-sync python eval/render_final_report_pdf.py --source eval/luna_reliable_20260907/submission_report.md --output output/pdf/PaperAudit_Luna_experiment_report.pdf --model Luna\n'
            '图表使用Microsoft YaHei，PDF使用C:/Windows/Fonts/simsun.ttc；其他系统需替换为可用中文字体。\n'
            '检查analysis/concurrency_phases_final.csv，旧concurrency_phases.csv仅保留追溯。网络耗时总和不等于墙钟运行时间。\n'
            '协议包含原始代码字节散列，复现源码须保留包内换行格式；使用重新检出的Git CRLF文件可能触发散列差异。\n\n'
            '原始protocol.json及amendments目录不修改。正式输入、响应、请求检查点、失败及恢复记录均保留。\n'
            '本包不含API密钥；不要删除失败结果后重跑并冒充原实验记录。\n'
            'manifest_sha256.json覆盖所有打包内容（除该清单自身），可离线逐文件校验。\n')
        data=readme.encode('utf-8');z.writestr('SUBMISSION_README.txt',data);manifest['SUBMISSION_README.txt']=sha(data)
        z.writestr('manifest_sha256.json',json.dumps(manifest,ensure_ascii=False,indent=2))
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        assert len(z.namelist())==len(set(z.namelist()))
        for name,h in manifest.items(): assert sha(z.read(name))==h,name
    print(json.dumps(dict(archive=str(archive),files=len(manifest),bytes=archive.stat().st_size,sha256=sha(archive.read_bytes())),ensure_ascii=False))

if __name__=='__main__': main()
