"""Join independently produced reference labels with completed pilot audits.

This is a source-position diagnostic, not a semantic fact-alignment evaluator.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from statistics import fmean

from eval.run_hy3_pilot import OUT, read, save, summarize


def ratio(values):
    return fmean(values) if values else None


def percent(value):
    return f'{value*100:.2f}%' if value is not None else 'N/A'


def main():
    summarize()
    config=read(OUT/'protocol.json')
    reference_dir=OUT/'reference'
    if not (reference_dir/'labels.json').exists():
        raise SystemExit('Independent annotation has not finished.')
    reference_files=sorted(reference_dir.rglob('*.json'))
    fingerprint={str(p.relative_to(reference_dir)):hashlib.sha256(p.read_bytes()).hexdigest() for p in reference_files}
    freeze=OUT/'reference_freeze.json'
    if freeze.exists() and read(freeze)!=fingerprint:
        raise ValueError('Reference files changed after joining with Hy3 results.')
    save(freeze,fingerprint)
    base=read(OUT/'summary.json')
    labels=read(reference_dir/('effective_labels.json' if (reference_dir/'effective_labels.json').exists() else 'labels.json'))
    effective_rounds=read(reference_dir/'effective_rounds.json') if (reference_dir/'effective_rounds.json').exists() else {}
    blind={r['report_id']:r for r in read(OUT/'blind_inputs.json')}
    raw_rounds=[]
    round_agreement=[]
    for rid in blind:
        a=read(reference_dir/effective_rounds.get(f'{rid}_1',f'{rid}_round_1.json'))
        b=read(reference_dir/effective_rounds.get(f'{rid}_2',f'{rid}_round_2.json'))
        raw_rounds.extend([a,b])
        if a['status']!='ok' or b['status']!='ok':
            continue
        other={f['fact_id']:f for f in b['labels']['facts']}
        for f in a['labels']['facts']:
            round_agreement.append({k:f[k]==other[f['fact_id']][k]
                                    for k in ('label','error_type','severity','citation_status')})
    rows=[]
    for item in labels:
        if 'fact_id' not in item:
            continue
        fact=next(f for f in blind[item['report_id']]['facts'] if f['fact_id']==item['fact_id'])
        observations=[]
        for repeat in range(1,4):
            path=OUT/f'run_{repeat}'/(item['report_id']+'.json')
            run=read(path) if path.exists() else None
            extracted=[a for a in run['audit']['audits'] if a['claim']['source_id']==item['source_id']] if run and run['status']=='ok' else []
            observations.append({
                'repeat':repeat, 'run_status':run['status'] if run else 'not_run',
                'extracted_count':len(extracted), 'extracted_texts':[a['claim']['text'] for a in extracted],
                'labels':[a['judgment']['label'] for a in extracted],
                'error_types':[a['judgment']['claim_error_type'] for a in extracted],
                'severities':[a['judgment']['severity'] for a in extracted],
                'citations':[a['claim']['provided_evidence'] for a in extracted],
                'evidence_errors':[a['judgment']['evidence_error_type'] for a in extracted],
                'explanations':[a['judgment']['explanation'] for a in extracted],
                'group_label_match': bool(extracted) and all(a['judgment']['label']==item['reference']['label'] for a in extracted) if item['status']=='resolved' else None,
                'high_risk_error_detected':any(a['judgment']['label'] in {'PARTIALLY_SUPPORTED','CONTRADICTED','NO_SUPPORT_FOUND'} and a['judgment']['severity'] in {'high','critical'} for a in extracted),
                'any_high_risk':any(a['judgment']['severity'] in {'high','critical'} for a in extracted),
            })
        rows.append({'report_id':item['report_id'],'fact_id':item['fact_id'],'source_id':item['source_id'],
                     'text':fact['text'],'reference_status':item['status'],'reference':item['reference'],
                     'observations':observations})
    resolved=[r for r in rows if r['reference_status']=='resolved']
    supported=[r for r in resolved if r['reference']['label']=='SUPPORTED' and r['reference']['citation_status']!='invalid']
    high=[r for r in resolved if r['reference']['label'] not in {'SUPPORTED','ABSTAIN'} and r['reference']['severity'] in {'high','critical'}]
    complete=base['complete']
    metrics={
        'reference_resolved':len(resolved),'reference_uncertain':sum(r['reference_status']!='resolved' for r in rows),
        'reference_failed_reports':sum(x['status']=='annotation_failed' for x in labels),
        'reference_label_round_agreement':ratio([r['label'] for r in round_agreement]),
        'reference_round_comparable_facts':len(round_agreement),
        'reference_full_signature_agreement':ratio([all(r.values()) for r in round_agreement]),
        'reference_initial_rounds_evidence_issue_count':sum(len(r.get('evidence_issues',{})) for r in raw_rounds),
        'source_group_label_agreement':ratio([o['group_label_match'] for r in resolved for o in r['observations']]) if complete else None,
        'source_group_comparison_observations':len(resolved)*3,
        'source_high_risk_majority_recall':ratio([sum(o['high_risk_error_detected'] for o in r['observations'])>=2 for r in high]) if complete else None,
        'reference_high_risk_source_count':len(high),
        'supported_source_high_risk_rate':ratio([o['any_high_risk'] for r in supported for o in r['observations']]) if complete else None,
        'supported_source_observations':len(supported)*3,
    }
    calls=[read(p) for p in reference_dir.rglob('*.json') if '_round_' in p.stem or '_adjudication' in p.stem]
    usage={'reference_requests':len(calls),
           'reference_reported_tokens':sum((r.get('usage') or {}).get('total_tokens',0) for r in calls),
           'reference_requests_without_usage':sum(not r.get('usage') for r in calls),
           'reference_request_seconds':sum(r.get('seconds',0) for r in calls),
           'hy3_reported_tokens':base['reported_total_tokens']}
    result={'scope':'steps_1_2_development_pilot','hy3':base,'reference_metrics':metrics,
            'usage':usage,'cases':rows,'limitations':[
                'Reference labels are model-assisted, not human ground truth.',
                'Historical controlled reports: 1 paper, 30 fact occurrences with repeated content, not independent samples.',
                'Comparisons group extracted subclaims by source position, without independent semantic alignment.',
                'Invalid reference quotations remain uncertain; no reference labels changed based on Hy3 results.',
                'No currency estimate without verified provider billing; formal reports are longer than these pilot reports.',
            ]}
    save(OUT/'pilot_results.json',result)
    lines=['# Hy3 开发试点结果（步骤一、二）','',
           '本轮使用旧 DeepFM 论文及三份受控报告，仅用于验证实验流程，不作为正式独立验收。', '',
           '## 模型与流程','',
           '- 被测应用：TokenHub `hy3`，应用调用参数和源代码哈希见 `protocol.json`。',
           '- 参考标注：独立接口 `gpt-5.6-luna`；两次盲标、实质分歧裁决、原文引文校验。',
           '- 标注请求不包含档位、历史金标或 Hy3 输出。标注完成后记录参考文件哈希，再与审计结果汇合。',
           '- 参考标注由模型辅助生成与复核，不等于人工金标。','',
           '## 三档报告与重复结果','',
           '| 报告 | 档位 | 完成次数 | 三次得分 | 平均分 | 分数标准差 |',
           '| --- | --- | ---: | --- | ---: | ---: |']
    for r in base['reports']:
        lines.append(f"| {r['report_id']} | {r['tier']} | {r['completed']}/3 | {r['scores']} | {r['mean_score']} | {r['score_std']} |")
    lines.extend(['',f"9 次审计完整完成：{complete}；三档严格排序：{base['strict_tier_order']}。",'',
        '## 参考标注和来源分组检查','',
        f"- 参考标注已确定 {len(resolved)} 个事实出现位置；不确定 {metrics['reference_uncertain']} 个；标注失败报告 {metrics['reference_failed_reports']} 份。",
        f"- 两次盲标标签一致率 {percent(metrics['reference_label_round_agreement'])}；标签、错误类型、风险和引用状态全部一致的比例 {percent(metrics['reference_full_signature_agreement'])}。",
        f"- 上述一致率仅覆盖两轮结构均有效的 {len(round_agreement)} 个事实位置，包含引文待核验项；不能当作最终标注正确率。",
        f"- 两轮有效标注累计 {metrics['reference_initial_rounds_evidence_issue_count']} 个事实标注出现引文校验问题，进入裁决，不静默接受。",
        f"- Hy3 与参考标注的来源分组标签一致率：{percent(metrics['source_group_label_agreement'])}（{metrics['source_group_comparison_observations']} 次预期观察）。",
        f"- 高风险来源多数运行检出率：{percent(metrics['source_high_risk_majority_recall'])}（参考高风险来源 {len(high)} 个）。",
        f"- 参考支持且无已知无效引用的来源，被判高风险的比例：{percent(metrics['supported_source_high_risk_rate'])}（{metrics['supported_source_observations']} 次预期观察）。",
        '', '以上按原报告来源位置聚合，不是独立语义对齐后的原子论断准确率。拆分成多个子论断时，只有全部标签等于参考标签才算该来源匹配。原句被抽取也不证明句内事实全部覆盖。', '',
        '## 用量与预算','',
        f"- Hy3：{base['request_count']} 次底层请求，已报告 {base['reported_total_tokens']:,} tokens；累计审计耗时 {base['audit_wall_seconds']/60:.1f} 分钟。",
        f"- 参考标注与裁决：{usage['reference_requests']} 次请求，已报告 {usage['reference_reported_tokens']:,} tokens；累计请求耗时 {usage['reference_request_seconds']/60:.1f} 分钟。",
        f"- 按同等报告长度粗略外推 96 次审计：{base['projected_96_audit_tokens']} tokens，不包含生成、标注、复核与裁决。",
        '- 试点报告仅约 600 字，正式报告计划更长，不能直接视为正式预算。未核实计费单价，暂不报告金额。', '',
        '## 实际暴露的失败','',
        '- R002 第二轮返回损坏 JSON；额外一次格式修复只保留部分事实，仍未通过完整性校验。原始失败与修复响应均保留，该报告不进入参考一致性计算。',
        '- 多个引文未通过当前 Chunk 子串检查。已核对的部分原因是 PDF 跨行断词，例如 `simulta-\\nneously` 与模型引用的 `simultaneously`；不能把所有校验失败都解释为伪造引文。',
        '- 下一版需加入可追溯的断词/连字规范化与小批量标注；保留此轮原结果后另开开发验证，不回写本轮标签。','',
        '## 后续边界','',
        '当前仅完成旧论文试点。尚未挑选六篇新论文或构造正式数据。正式数据仍需解决原子事实语义对齐、数字关系校验与不确定样本处理，不能直接把来源位置统计称为事实准确率。', '',
        '逐来源诊断、引用和原始判断见 `pilot_results.json`、`reference/` 与 `run_*/`。'])
    (OUT/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'complete':complete,'reference':metrics,'usage':usage},ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
