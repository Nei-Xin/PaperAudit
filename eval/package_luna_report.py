"""Package the completed reliable Luna experiment without model calls."""
import hashlib
import json
import zipfile
from dotenv import dotenv_values
from eval.luna_reliable_experiment import ROOT, OUT
from eval.reference_annotation_v2 import read
from eval.final_hy3_experiment import sha


def main():
    summary=read(OUT/'analysis/summary.json')
    assert summary['attempted_audits']==summary['expected_audits']==96
    protocol=read(OUT/'protocol.json')
    revision=OUT/'amendments/concurrency2/amendment.json'
    amendments=read(revision)['source_sha256'] if revision.exists() else {}
    for frozen in ('reference_freeze','alignment_freeze'):
        for name,expected in read(OUT/(frozen+'.json'))['sha256'].items():
            assert sha(OUT/name)==expected,name
    for name,expected in protocol['source_sha256'].items():
        assert sha(ROOT/name)==amendments.get(name.replace('\\','/'),expected),name
    if revision.exists():
        for name,expected in read(revision)['preserved_results'].items(): assert sha(OUT/name)==expected,name
    for name,expected in protocol['input_sha256'].items():
        assert sha(OUT/name)==expected,name
    pdf=ROOT/'output/pdf/PaperAudit_Luna_experiment_report.pdf'
    assert pdf.is_file()
    files=[(p,'eval/'+OUT.name+'/'+p.relative_to(OUT).as_posix())
           for p in OUT.rglob('*') if p.is_file() and p.suffix not in {'.tmp','.log'}]
    sources=set(protocol['source_sha256'])
    sources.update(str(p.relative_to(ROOT)) for p in (ROOT/'eval').glob('*.py'))
    sources.update(str(p.relative_to(ROOT)) for p in (ROOT/'tests').glob('test_*luna*.py'))
    sources.update({'tests/test_durable_requests.py','pyproject.toml','uv.lock','README.md'})
    files.extend((ROOT/name,name.replace('\\','/')) for name in sorted(sources) if (ROOT/name).is_file())
    files.append((pdf,'output/pdf/'+pdf.name))
    secrets=[v.encode() for k,v in dotenv_values(ROOT/'.env').items()
             if v and ('KEY' in k or 'PASSWORD' in k) and len(v)>8]
    output=ROOT/'output/PaperAudit_Luna_results.zip'
    manifest={}
    with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for path,name in files:
            data=path.read_bytes()
            assert not any(secret in data for secret in secrets),'Secret found in '+name
            manifest[name]=hashlib.sha256(data).hexdigest()
            archive.writestr(name,data)
        archive.writestr('manifest_sha256.json',json.dumps(manifest,ensure_ascii=False,indent=2))
        archive.writestr('README.txt',
            'PaperAudit Luna 实验提交数据包\n'
            f'计划96次，完成记录96次，成功{summary["successful_audits"]}次。失败与重试保留。\n'
            '主办方接受替代模型（用户确认）。参考标注与语义对齐同样使用Luna，不能当作人工金标或独立验证。\n'
            '先阅读output/pdf/PaperAudit_Luna_experiment_report.pdf。实验数据在eval/luna_reliable_20260907。\n'
            '历史Hy3和早期Luna试跑未混入本包正式统计，原项目内仍保留。\n'
            '离线复现：解压后在根目录执行uv sync，再执行uv run python -m eval.luna_reliable_analysis summarize。无需API密钥。\n'
            '联网恢复需在本地.env配置HY3_API_BASE、HY3_API_KEY、HY3_MODEL=gpt-5.6-luna；'
            '对齐使用REFERENCE_API_BASE、REFERENCE_API_KEY、REFERENCE_MODEL=gpt-5.6-luna。\n'
            '审计命令：python -m eval.luna_reliable_experiment all；对齐命令：python -m eval.luna_reliable_alignment。'
            '完整结果已存在时不会重新审计，不应删除冻结结果后冒充本轮原始数据。\n'
            'PDF重建：python eval/render_final_report_pdf.py --source eval/luna_reliable_20260907/submission_report.md '
            '--output output/pdf/PaperAudit_Luna_experiment_report.pdf --model Luna（额外需要reportlab和Windows宋体）。\n'
            'manifest_sha256.json提供文件完整性校验；未包含API密钥。\n')
    with zipfile.ZipFile(output) as archive:
        assert archive.testzip() is None
        for name,digest in manifest.items():
            assert hashlib.sha256(archive.read(name)).hexdigest()==digest,name
    print(json.dumps({'archive':str(output),'files':len(files),'bytes':output.stat().st_size},ensure_ascii=False))


if __name__=='__main__': main()
