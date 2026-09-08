"""Analyze reliable Luna results without issuing any new audit requests."""
from collections import Counter
from pathlib import Path
import argparse
import csv
import json
from statistics import fmean
from eval import analyze_final_hy3 as common
from eval.luna_reliable_experiment import OUT,ROOT
from eval.reference_annotation_v2 import read,save

def pct(v): return 'N/A' if v is None else f'{v*100:.2f}%'
def number(v): return 'N/A' if v is None else f'{v:.2f}'
def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+
        ['| '+' | '.join(map(str,r))+' |' for r in rows])

def transport():
    rows=[]
    for path in sorted(OUT.glob('run_*/*_checkpoints/*.json')):
        record=read(path);attempts=record['attempts']
        rows.append({'repeat':int(path.parent.parent.name.split('_')[1]),
            'report_id':path.parent.name.removesuffix('_checkpoints'),'request_index':int(path.stem),
            'attempts':len(attempts),'first_success':bool(attempts and attempts[0]['status']=='ok'),
            'eventual_success':bool(record.get('response')),'seconds':sum(a['seconds'] for a in attempts),
            'tokens':sum((a.get('usage') or {}).get('total_tokens',0) for a in attempts),
            'errors':';'.join(a.get('error_type','') for a in attempts if a['status']=='error')})
    summary={'logical_requests':len(rows),'network_attempts':sum(r['attempts'] for r in rows),
        'first_success_rate':fmean(r['first_success'] for r in rows) if rows else None,
        'eventual_success_rate':fmean(r['eventual_success'] for r in rows) if rows else None,
        'retry_attempts':sum(max(0,r['attempts']-1) for r in rows),
        'network_seconds_sum':sum(r['seconds'] for r in rows),'reported_tokens':sum(r['tokens'] for r in rows),
        'note':'Requests cached only within a run; replay does not count as another network request. Durations summed, not wall clock.'}
    save(OUT/'analysis/transport.json',summary)
    common.csv_save(OUT/'analysis/transport.csv',rows)
    return summary

def report():
    s=read(OUT/'analysis/summary.json'); p=read(OUT/'protocol.json'); t=transport()
    def csvrows(name):
        with (OUT/'analysis'/name).open(encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))
    runs=csvrows('runs.csv'); facts=csvrows('facts.csv')
    eligible=[r for r in s['rankings'] if all(r[k] is not None for k in ('high','medium','low'))]
    labels={'controlled':'控制组','natural':'自然组','adversarial':'对抗组'}
    examples=[]
    refdir=read(OUT/'reference_selection.json')['directory']
    seen=set()
    for f in facts:
        key=f['reference_label']
        if key in seen or f['reference_status']!='resolved' or f['correct']=='True' or not f['prediction_label']: continue
        seen.add(key)
        blind=read(OUT/'inputs'/('blind_'+f['report_id']+'.json'))
        original=next(x for x in blind['facts'] if x['fact_id']==f['fact_id'])
        ref=next(x for x in read(OUT/refdir/f['paper_id']/'labels.json') if x['report_id']==f['report_id'] and x['fact_id']==f['fact_id'])
        examples.append(f'### {f["report_id"]} / 第{f["repeat"]}次 / {f["fact_id"]}\n\n'
            f'原事实：{original["text"]}\n\n参考为{key}，系统为{f["prediction_label"]}。参考依据：{ref["reference"]["explanation"]}。'
            '该案例是参考分歧，不能仅依据参考标签断言系统错误；原始系统解释和证据见对应运行JSON。')
    lines=['# PaperAudit：Luna 论文报告审计实验数据报告',
        '本轮模型为gpt-5.6-luna。根据用户确认，主办方接受其他模型。实验目录：luna_reliable_20260907。',
        '## 摘要',
        f'本轮对6篇论文的36份报告计划96个完整审计任务，已记录{s["attempted_audits"]}次，成功{s["successful_audits"]}次，失败{s["attempted_audits"]-s["successful_audits"]}次。'
        f'具备高、中、低各三次完整结果的论文为{len(eligible)}/6，严格排序交付通过率为{pct(s["ranking_rate"])}。'
        f'控制组重复分数标准差均值为{number(s["controlled_mean_score_std"])}；标签两两重复一致率为{pct(s["controlled_label_repeat_agreement"])}。',
        '参考标注同样来自Luna，属于同模型参考一致性，不是人工金标或独立模型验证。主办方接受替代模型不消除这一测量限制。',
        '## 场景与方法',
        '用户将中文论文讲解报告与原论文一起输入，系统抽取带原文位置的事实，检索PDF文本证据，判断支持状态、错误类别及风险，再由规则计算六维分数。该任务评估报告是否忠实于论文，不是复现论文的训练结果。',
        '六维为：事实支持度、原引用正确性、关键事实引用完整性、数字与指标一致性、六类内容覆盖度、结论边界。支持=100、部分支持=50、矛盾/无支持=0；弃权不进入部分维度均值。总分为非空维度等权均值，不能解释为正确概率。规则源码和详细协议随包提供。',
        '## 数据与冻结协议',
        table(['组别','报告数','重复次数','任务数'],[['控制组',18,3,54],['自然组',6,1,6],['对抗组',12,3,36]]),
        '六篇论文为ALBERT、XLNet、DenseNet、MobileNets、LightGCN、NGCF，固定arXiv v1 PDF及散列。控制组每篇三档，各12个预定义事实单元；中档替换2个条件/范围主张，低档替换4个主要错误主张。自然报告沿用原Hy3生成文本，不改称Luna生成。对抗组各4份填充、错误页码、指令注入。',
        '这些数据已有前期Hy3及Luna试跑，不能再称全新未见留出集。原始数据不修改，本轮重新执行所有审计；历史结果不并入。开发门槛使用另外三份历史DeepFM报告，仅要求完整流程成功，不按分数调整方法。',
        '参考标签在前期正式审计前冻结：Luna两轮盲请求，分歧裁决，核查原文引用子串。最终参考758条可用、14条不确定。自然组事实拆分更细，组间差异不可直接归因于报告质量。',
        '## 可靠执行与资源开销',
        '单并发、240秒单次超时；SDK自动重试关闭。临时连接/超时/408/429/部分5xx最多三次尝试，等待5、15秒；跨恢复生命周期最多六次。401/402/403立即暂停。每个任务的成功请求按调用序号与请求散列保存，恢复只回放该任务的响应，不跨重复共享。',
        table(['项目','观测值'],[['逻辑请求数',t['logical_requests']],['实际网络尝试数',t['network_attempts']],['首次请求成功率',pct(t['first_success_rate'])],['重试后请求完成率',pct(t['eventual_success_rate'])],['重试次数',t['retry_attempts']],['审计接口报告tokens',t['reported_tokens']]]),
        '网络超时的请求即使未收到响应也可能在服务端执行或计费；缺失用量未估算。总网络耗时不是墙钟时间，连接诊断、开发检查与标注/对齐用量需分别计入。',
        table(['最终审计失败原因','任务数'],list(Counter(f['error_type'] for f in s['failures']).items())) if s['failures'] else '本轮无最终审计失败；被重试恢复的网络错误仍保留在transport.csv中。',
        '## 判别力与稳定性',
        table(['论文','高档均分','中档均分','低档均分','排序'],[[r['paper_id'],number(r['high']),number(r['medium']),number(r['low']),'无法判定' if r not in eligible else ('通过' if r['correct'] else '未通过')] for r in s['rankings']]),
        '均分只有三次均成功时计算。缺失计为排序交付目标未通过，但不是实际排序错误。项目目标为至少5/6篇严格排序、整体分数标准差均值≤3、标签重复一致性≥90%；不是主办方官方数值门槛。',
        '## 事实级结果',
        table(['组别','参考观测分母','端到端标签一致率','已判定一致率','语义事实召回','非弃权覆盖'],[[labels[k],g['resolved_reference_observations'],pct(g['end_to_end_label_accuracy']),pct(g['decided_label_accuracy']),pct(g['semantic_fact_recall']),pct(g['nonabstain'])] for k,g in s['groups'].items()]),
        table(['组别','高风险分母','高风险告警召回','支持事实分母','高风险告警比例','引用保留'],[[labels[k],g['high_risk_denominator'],pct(g['high_risk_recall']),g['supported_denominator'],pct(g['supported_high_risk_false_positive']),pct(g['original_citation_retention'])] for k,g in s['groups'].items()]),
        '端到端口径保留整次失败、漏抽取和弃权；已判定口径仅含完整语义对齐且非弃权子集。不确定参考不计准确率分母。高风险指标只比较告警等级，没有要求原因完全一致；对抗组支持事实可能带错误引用，因此高风险告警不能全部解释为误报。',
        '已判定一致率存在成功子集选择偏差：较难抽取、无法对齐或被弃权的事实被排除，不能将该比例推广到全部输入；需结合端到端一致率与覆盖率阅读。',
        '语义对齐只看原事实和抽取文本，不看标签或分数。完整覆盖需保留数字、条件、主张强度；同source_id不算覆盖证明。多个抽取共同覆盖时取最差已判定标签，任一弃权则事实未决。',
        '## 对抗实验',
        table(['报告','类型','基础均分','攻击均分','差值'],[[r['report_id'],r['attack'],number(r['base_mean']),number(r['attack_mean']),number(r['delta'])] for r in s['attacks']]),
        '填充和注入内容作为应用输入保留。错误引用应影响证据维度，不能以分数不变判为正确鲁棒性；差值不能单独证明攻击识别。',
        '## 典型分歧', '\n\n'.join(examples) or '没有满足固定选择规则的已判定分歧。',
        '案例按CSV原顺序选择每种参考标签的首个已判定分歧，不依事后好坏挑选。',
        '## 局限与交付',
        '只有6篇机器学习论文；重复观测相关，不按独立事实计算显著性。模型可能在预训练接触论文，参考模型参与构造/标注/对齐，存在共同偏差。研究基于PDF文本，不恢复图表视觉语义。渠道自报模型名并不证明实际权重身份。',
        '原始失败、重试请求、检查点、数据散列及协议全部保留。对比历史Hy3时，模型、并发、超时和重试策略同时改变，不作单一模型因果归因。最终结论限于本轮样本和已报告指标，未达标指标保留。',
        '复现：在项目环境运行python -m eval.luna_reliable_experiment all恢复审计；python -m eval.luna_reliable_analysis summarize仅重算现有统计；不得更改冻结输入后复用检查点。API密钥通过本地.env设置，不包含在提交包中。']
    revision=OUT/'amendments/concurrency2'
    if (revision/'amendment.json').exists():
        amendment=read(revision/'amendment.json')
        events=[json.loads(line) for line in (revision/'execution.jsonl').read_text(encoding='utf-8').splitlines()] if (revision/'execution.jsonl').exists() else []
        phases=[]
        for phase in ['original_serial','observation_parallel2','parallel2','fallback_serial']:
            if phase=='original_serial':
                values=amendment['baseline_transport']
            else:
                selected=[e for e in events if e['phase']==phase]
                if not selected: continue
                values={k:sum(e[k] for e in selected) for k in ['network_attempts','successful_attempts','network_seconds']}
            phases.append([phase,values['network_attempts'],pct(values['successful_attempts']/values['network_attempts']) if values['network_attempts'] else 'N/A',number(values['network_seconds'])])
        lines.extend(['## 并发执行协议修订',
            '修订时间：'+amendment['created_at']+'。原冻结协议未覆盖，旧源码及修订散列保存在amendments/concurrency2。'
            '原单并发任务完成后，接下来的4个正式任务以并发2观察，随后维持2；连续429或重试耗尽时停止派发，排空在途任务后最多降回单并发一次。认证/余额拒绝立即停止新增请求。'
            '模型、提示词、评分、输入、重复次数及240秒超时不变；语义对齐保持单并发。下表为各阶段网络尝试成功比例和网络耗时总和，包含失败尝试；不是任务准确率或墙钟加速比。',
            table(['阶段','网络尝试','尝试成功率','网络耗时总和（秒）'],phases)])
        common.csv_save(OUT/'analysis/concurrency_phases.csv',[dict(phase=r[0],network_attempts=r[1],attempt_success_rate=r[2],network_seconds=r[3]) for r in phases])
        lines=[line.replace('单并发、240秒单次超时；SDK自动重试关闭。','初始单并发，随后按修订改为任务并发2（见协议修订章节）；240秒单次超时；SDK自动重试关闭。') for line in lines]
    (OUT/'submission_report.md').write_text('\n\n'.join(lines)+'\n',encoding='utf-8')

def main():
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['align','summarize']);args=p.parse_args()
    common.OUT=OUT
    if args.phase=='align':
        from eval.luna_reliable_alignment import main as align
        align()
    else:
        common.summarize();report()

if __name__=='__main__': main()
