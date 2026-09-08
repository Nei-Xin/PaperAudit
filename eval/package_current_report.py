"""Package existing results only; no network calls and no audit reruns."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import zipfile
from dotenv import dotenv_values
from eval.final_hy3_experiment import ROOT, OUT, sha
from eval.reference_annotation_v2 import read, save

def main():
    summary=read(OUT/'analysis/summary.json')
    assert summary['attempted_audits']==96 and summary['successful_audits']==39
    for frozen in ('reference_freeze','alignment_freeze'):
        for name,expected in read(OUT/(frozen+'.json'))['sha256'].items():
            assert sha(OUT/name)==expected,name
    protocol=read(OUT/'protocol.json')
    for name,expected in protocol['source_sha256'].items():
        assert sha(ROOT/name)==expected,name
    for name,expected in protocol['input_sha256'].items():
        assert sha(OUT/name)==expected,name
    output=ROOT/'output/PaperAudit_Hy3_existing_results.zip'
    files=[(p,'data/'+p.relative_to(OUT).as_posix()) for p in OUT.rglob('*') if p.is_file()]
    sources=set(protocol['source_sha256'])|{
        'eval/write_final_hy3_report.py','eval/render_final_report_pdf.py','eval/package_current_report.py',
        'eval/recover_final_reference.py','eval/resume_hy3_audit.py','eval/continue_final_experiment.py',
        'eval/annotate_hy3_pilot.py','eval/__init__.py','pyproject.toml'}
    files.extend((ROOT/name,'code/'+name.replace('\\','/')) for name in sorted(sources) if (ROOT/name).is_file())
    files.append((ROOT/'output/pdf/PaperAudit_Hy3_experiment_report.pdf','PaperAudit_Hy3_experiment_report.pdf'))
    secrets=[v.encode() for k,v in dotenv_values(ROOT/'.env').items() if v and ('KEY' in k or 'PASSWORD' in k) and len(v)>8]
    manifest={}
    with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for path,name in files:
            data=path.read_bytes()
            assert not any(secret in data for secret in secrets),'Secret found; do not package '+name
            manifest[name]=hashlib.sha256(data).hexdigest()
            archive.writestr(name,data)
        archive.writestr('manifest_sha256.json',json.dumps(manifest,ensure_ascii=False,indent=2))
        archive.writestr('README.txt',
            'PaperAudit Hy3 本轮数据报告\n'
            '本轮不补跑。96条任务记录：39成功、57失败。PDF为现有数据分析稿，不代表完整有效性验证通过。\n'
            '先阅读PaperAudit_Hy3_experiment_report.pdf。data/analysis保存CSV和JSON明细；data/保存论文、输入、参考标注和真实响应。\n'
            'code/保存冻结实验源码及报告生成工具。密钥不包含在包内。manifest_sha256.json用于完整性校验。\n'
            '无需再次调用模型即可阅读全部现有结果。重算统计可在原项目中执行python -m eval.analyze_final_hy3 summarize。\n')
    with zipfile.ZipFile(output) as archive:
        assert archive.testzip() is None
    print(json.dumps({'archive':str(output),'files':len(files),'bytes':output.stat().st_size},ensure_ascii=False))

if __name__=='__main__':
    main()
