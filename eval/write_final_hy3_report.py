"""Write the submission report from completed, frozen experiment artifacts."""
from __future__ import annotations
import csv
from datetime import datetime
import html
from pathlib import Path
from statistics import fmean
from eval.final_hy3_experiment import OUT,ROOT,sha
from eval.reference_annotation_v2 import read,save

def pct(value):
    return f'{value*100:.2f}%' if value is not None else 'N/A'

def num(value):
    return f'{value:.2f}' if value is not None else 'N/A'

def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+
        ['| '+' | '.join(str(v) for v in row)+' |' for row in rows])+'\n'

def main():
    s=read(OUT/'analysis/summary.json'); protocol=read(OUT/'protocol.json');papers=read(OUT/'inputs/papers.json')
    assert s['attempted_audits']==96,'Do not publish unfinished experiment as final'
    with (OUT/'analysis/reports.csv').open(encoding='utf-8-sig',newline='') as f:
        reports=list(csv.DictReader(f))
    with (OUT/'analysis/facts.csv').open(encoding='utf-8-sig',newline='') as f:
        facts=list(csv.DictReader(f))
    with (OUT/'analysis/runs.csv').open(encoding='utf-8-sig',newline='') as f:
        runs=list(csv.DictReader(f))
    successful={(r['report_id'],r['repeat']) for r in runs if r['status']=='ok'}
    group_names={'controlled':'控制组','natural':'自然组','adversarial':'对抗组'}
    def fraction(rows,key):
        return sum(r[key]=='True' for r in rows)/len(rows) if rows else None
    subset=[]
    for kind,name in group_names.items():
        planned=[r for r in runs if r['kind']==kind]
        done=[r for r in planned if r['status']=='ok']
        fs=[f for f in facts if f['kind']==kind and (f['report_id'],f['repeat']) in successful]
        ref=[f for f in fs if f['reference_status']=='resolved']
        high=[f for f in ref if f['reference_severity'] in {'high','critical'}]
        supported=[f for f in ref if f['reference_label']=='SUPPORTED']
        subset.append(dict(kind=kind,name=name,planned=len(planned),successful=len(done),facts=len(fs),
            semantic_recall=fraction(fs,'semantic_full'),reference_count=len(ref),reference_agreement=fraction(ref,'correct'),
            nonabstain=fraction(fs,'nonabstain'),high_count=len(high),high_recall=fraction(high,'prediction_high_risk'),
            supported_count=len(supported),high_false_positive=fraction(supported,'prediction_high_risk')))
    eligible=[r for r in s['rankings'] if all(r[t] is not None for t in ('high','medium','low'))]
    complete_reports=[r for r in reports if r['kind']=='controlled' and r['score_std']!='']
    save(OUT/'analysis/successful_subset.json',{'analysis_type':'Post hoc descriptive successful-run subset; not replacement for preregistered denominators',
        'groups':subset,'rankable_papers':len(eligible),'complete_control_reports':len(complete_reports)})
    c=s['groups']['controlled'];runtime=protocol['runtime']
    checks=[('严格等级排序',s['ranking_rate'],5/6,False),('分数标准差均值',s['controlled_mean_score_std'],3,True),
        ('标签重复一致性',s['controlled_label_repeat_agreement'],.9,False),('语义事实召回',c['semantic_fact_recall'],.95,False),
        ('高风险召回',c['high_risk_recall'],.8,False),('支持事实高风险误报',c['supported_high_risk_false_positive'],.05,True),
        ('非弃权覆盖',c['nonabstain'],.8,False),('原始引用保留',c['original_citation_retention'],.95,False)]
    verdict=lambda v,t,lower:'无法判定' if v is None else ('达到' if (v<=t if lower else v>=t) else '未达到')
    passed=sum(verdict(v,t,l)=='达到' for _,v,t,l in checks)
    # Deterministic examples: first observed mismatch of each reference label, not best-looking cases.
    examples=[]; seen=set()
    for row in facts:
        if row['reference_status']!='resolved' or row['correct']=='True' or (row['report_id'],row['repeat']) not in successful:
            continue
        category=row['reference_label']
        if category in seen:
            continue
        seen.add(category)
        blind=read(OUT/'inputs'/('blind_'+row['report_id']+'.json'))
        fact=next(f for f in blind['facts'] if f['fact_id']==row['fact_id'])
        run=read(OUT/('run_'+row['repeat'])/(row['report_id']+'.json'))
        claims=[a for a in run.get('audit',{}).get('audits',[]) if a['claim']['claim_id'] in row['claim_ids'].split(';')]
        refdir=read(OUT/'reference_selection.json')['directory'] if (OUT/'reference_selection.json').exists() else 'reference'
        ref=next(f for f in read(OUT/refdir/row['paper_id']/'labels.json') if f['report_id']==row['report_id'] and f['fact_id']==row['fact_id'])
        examples.append(f'### 案例：{row["report_id"]}/运行{row["repeat"]}/{row["fact_id"]}\n\n原事实：{fact["text"]}\n\n'
            f'参考标签：{category}；系统聚合标签：{row["prediction_label"] or "未决"}；语义覆盖：{row["coverage"]}。\n\n'
            f'参考解释：{ref["reference"]["explanation"]}\n\n系统解释：'+('；'.join(a['judgment']['explanation'] for a in claims) or '无完整可对应的已判定论断。')+
            '\n\n归因边界：这是一次可追溯的参考分歧，需结合原文判断是检索、抽取、判断还是参考标注问题；不能只因参考标签不同就认定系统错误。')
    lines=['# PaperAudit：基于 Hy3 的论文讲解报告审计实验数据报告',
        '实验编号：HY3-FINAL-20260907｜对象：方向一应用评测｜数据版本：冻结协议与文件散列见随附数据包。',
        '## 摘要',
        f'本实验以6篇公开论文为证据源，准备18份控制报告、6份Hy3自然报告和12份对抗变体。96个计划审计任务均已有结果记录，其中{s["successful_audits"]}次成功，{96-s["successful_audits"]}次因接口错误、超时或停止保护未完成。成功率为{pct(s["successful_audits"]/96)}。用户决定本轮不补跑失败任务。'
        f'仅{len(eligible)}/6篇论文具备高、中、低各三次成功审计的完整排序数据，整体重复分数波动为{num(s["controlled_mean_score_std"])}。因此本轮不能完成原计划的完整判别力和稳定性论证。'
        f'控制组包含服务失败的端到端参考标签一致率为{pct(c["end_to_end_label_accuracy"])}；该值反映整个流程交付能力，不能直接解释为模型事实判断准确率。',
        '本报告为本轮数据归档与分析稿，包含现有样本、冻结方法、所有运行记录与失败分析；它不宣称任务要求的有效性验证已全部达成。成功子集统计属于事后描述，可能有选择偏差，不能替代原计划样本。',
        '参考标注由独立模型gpt-5.6-luna辅助生成并经两轮独立请求、分歧裁决和本地证据检查；本实验没有人工标注或人工复核。结果衡量系统与冻结参考标注的一致性，不能视为人工金标正确率。',
        '## 1. 任务与系统',
        '任务为对照论文PDF审计中文讲解报告中的事实、数字、引用与结论边界。系统解析PDF文本，将报告拆成带原文位置的原子论断，通过FTS5检索证据，由Hy3判断支持状态、错误类型与风险，再执行引用规则校验和六维评分。全部重复运行从报告重新抽取开始，未复用上次固定论断。',
        '六个评分维度为事实支持度、证据正确性、证据完整性、数字与指标一致性、内容覆盖度、结论边界。各维度0–100分，总分为可计算维度等权均值。弃权不参与部分维度平均，因此总分必须结合事实召回和非弃权覆盖解读。该分数不表示事实正确概率。具体可执行定义及阈值口径见数据包README与冻结评分源码。',
        '## 2. 数据与实验设计',
        table(['论文ID','论文','领域','固定版本','PDF页数'],[[p['paper_id'],p['title'],p['area'],p['arxiv_version'],p['pages']] for p in papers]),
        '已对仓库历史评测文件做论文身份检索并排除旧样本，检查记录保存在inputs/historical_isolation.json。该检查不能排除模型预训练已接触论文，也不等于时间外推测试。PDF页码均为本地文件物理页。',
        table(['样本组','报告数','每份重复','计划审计数','目的'],[
            ['控制组','18','3','54','同论文高/中/低目标等级的判别力与稳定性'],
            ['自然组','6','1','6','Hy3直接生成、未经修订的真实输入'],
            ['对抗组','12','3','36','填充文本、伪造引用、注入命令各4份']]),
        '控制报告每份12条预定义事实，按研究问题、贡献、方法、实验设置、结果、局限组织。中档替换2条条件或范围相关主张，低档替换4条主要结果、归属、外部事实或方法相关主张。生成及修改动机保存于construction目录；质量档位是构造目标，独立参考标注才用于事实级比较。部分生成请求失败或拒绝时保留记录；DenseNet负样本由Codex按原文构造并明确标记其负样本用途。',
        '自然报告保留Hy3原始文字，实际长度可能超出提示词建议范围；不为满足长度或分数目标改写。控制组预定义事实单元按句划分，部分包含紧密关联的多个主张；自然组拆分更细，故两组分别统计，不直接将准确率差异归因为输入质量。对抗报告基于中档报告，伪造引用将前4处页码改为999页；其引用真值因此改变。填充和命令不作为新增事实参考项，但仍进入应用完整审计。',
        '## 3. 参考标注与冻结',
        '每个小批次最多3条事实，Luna收到完整论文证据、报告和该批事实。两轮互不共享判断，不提供质量档位、修改动机或Hy3审计结果。标签、错误类型、风险、原引用状态存在分歧时，再依据原文裁决；证据缺失、未匹配或未能解决时保留为不确定。证据子串匹配兼容空白、Unicode连字和物理行末断词，并保留原始证据。子串出现不是语义充分性的自动证明。',
        '参考状态计数：'+str(s['reference_fact_counts'])+'。它按报告事实出现次数计算，攻击报告与基础报告存在复用，不代表同等数量的独立知识点。',
        '参考文件在正式审计之前冻结，输入、应用代码和配置在protocol.json中记录散列。审计后仅进行盲语义对齐与统计，不据结果改参考标签。语义对齐请求只看原事实和系统抽取文字，不看任何标签或分数。它检查主体、关系、数字、条件与结论强度是否完整保留，不能用source_id相同代替。',
        '## 4. 模型与执行设置',
        table(['设置','实际值'],[[k,str(v)] for k,v in runtime.items() if k in {'model','api_base','temperature','top_p','reasoning_effort','retrieval_top_k','batch_size','timeout_seconds','max_context_chars'}]),
        '被测模型请求名为hy3，参考请求名为gpt-5.6-luna。调用第三方兼容接口，返回模型名称为接口自报，未独立验证实际部署权重身份。审计并发4；SDK自动重试关闭，应用既有格式/证据重试保留。失败审计不静默重跑，所有底层请求用量、错误类型、响应和耗时保存。',
        '正式审计通过tokenhub.tencentmaas.com接口执行，发生多次HTTP 402后按用户提供的新凭据恢复，只继续未完成任务槽位；成功和失败结果均保留。前5份自然报告由旧接口生成，DenseNet由新接口生成。Luna迁移连通测试不计入本轮Hy3结果。参考服务故障在正式审计前通过reference_recovery恢复并冻结。',
        '## 执行完成度与服务失败',
        table(['样本组','计划任务','成功','未完成'],[[g['name'],g['planned'],g['successful'],g['planned']-g['successful']] for g in subset]),
        '失败构成为22次APIStatusError、29次APITimeoutError及6次RuntimeError。接口错误日志对应HTTP 402；停止保护触发后，正在进行的任务可能以RuntimeError结束。超时阈值为120秒，本轮没有调整该阈值。以上属于执行失败，不能直接当作模型事实错误案例。故障记录及更换凭据后的恢复记录均随数据保留。',
        '## 5. 控制实验结果',
        table(['论文','高档均分','中档均分','低档均分','严格排序'],[[r['paper_id'],num(r['high']),num(r['medium']),num(r['low']),('无法判定' if any(r[t] is None for t in ('high','medium','low')) else ('通过' if r['correct'] else '未通过'))] for r in s['rankings']]),
        f'均分仅在该报告三次均成功时计算。18份控制报告中仅{len(complete_reports)}份具备完整三次分数。冻结脚本将缺失数据记为排序目标未通过，因此下表排序值为“目标交付通过率”，不等于模型实际排序错误率。N/A表示缺少规定数据，不能按0分解释。',
        table(['指标','观测值','项目目标','结果'],[[name,num(v) if '标准差' in name else pct(v),('≤' if lower else '≥')+(num(t) if '标准差' in name else pct(t)),verdict(v,t,lower)] for name,v,t,lower in checks]),
        '以上目标由项目预设，并非任务PDF的官方数值门槛。分数稳定不自动说明判断正确；高排序也可能来自引用或覆盖维度，需结合事实标签指标。',
        '## 6. 事实级结果与失败口径',
        table(['样本组','事实观测数','可用参考观测','端到端标签一致率','已判定标签一致率','语义召回','非弃权覆盖'],
            [[kind,g['fact_observations'],g['resolved_reference_observations'],pct(g['end_to_end_label_accuracy']),pct(g['decided_label_accuracy']),pct(g['semantic_fact_recall']),pct(g['nonabstain'])] for kind,g in s['groups'].items()]),
        table(['样本组','高风险参考分母','高风险召回','支持参考分母','高风险误报','带原引用分母','原引用保留'],
            [[kind,g['high_risk_denominator'],pct(g['high_risk_recall']),g['supported_denominator'],pct(g['supported_high_risk_false_positive']),g['original_citation_denominator'],pct(g['original_citation_retention'])] for kind,g in s['groups'].items()]),
        '端到端标签一致率分母包含已解决参考项对应的全部计划运行，漏抽取、对齐失败及弃权不计正确；已判定标签一致率只含完整对齐且非弃权子集。不确定参考项不进入准确率、高风险召回或误报分母，但仍进入语义召回与覆盖统计。多条系统论断共同对应一个事实时采用最差已判定标签；任一对应论断弃权则该事实未决。',
        '重复一致性对同一事实三次结果做两两比较，完整对齐且非弃权、标签相同才计一致。攻击复制的事实和多次运行高度相关；本报告不把重复观测当作独立样本计算置信区间或显著性。',
        '## 成功审计子集：事后描述',
        table(['样本组','成功任务','事实观测','可用参考','标签一致率','语义召回','非弃权覆盖'],[
            [g['name'],g['successful'],g['facts'],g['reference_count'],pct(g['reference_agreement']),pct(g['semantic_recall']),pct(g['nonabstain'])] for g in subset]),
        table(['样本组','高风险分母','高风险召回','支持分母','高风险误报'],[
            [g['name'],g['high_count'],pct(g['high_recall']),g['supported_count'],pct(g['high_false_positive'])] for g in subset]),
        '该子集排除整次审计失败，仍把成功审计中的语义漏抽取和弃权计为未命中；标签一致率分母为其中已解决参考事实。数据不足的组显示N/A。服务失败可能偏向耗时较长或较复杂的报告，故成功子集并非随机样本，其表现不能外推至全部96个任务。原端到端误报率也会被大量无输出任务压低，不宜仅据低误报率宣称安全。',
        '高风险指标仅比较参考风险等级与系统是否输出high/critical，没有进一步要求错误原因完全一致；因此属于高风险告警覆盖。对抗组包含伪造引用，事实本身SUPPORTED但引用错误时，系统高风险告警可能合理。此处“支持事实高风险误报”只是对事实标签的统计代理，不能把其全部视为错误警报，也不能直接与控制组比较。',
        '## 7. 对抗实验',
        table(['样本','攻击类型','基础均分','攻击均分','分数变化'],[[a['report_id'],a['attack'],num(a['base_mean']),num(a['attack_mean']),num(a['delta'])] for a in s['attacks']]),
        '正向分差表示攻击后得分更高，负向表示得分下降；它不能单独证明攻击被识别。特别是错误引用应当降低证据维度，不能以“分数不变”衡量正确鲁棒性。事实标签与原始输出可在facts.csv及run_*目录逐项追溯。',
        '## 典型分歧案例',
        '在成功审计中按报告、运行和事实顺序，选择各参考标签的首个分歧；不把接口故障当作模型语义案例。\n\n'+('\n\n'.join(examples) or '未发现满足上述规则的分歧；这不等于消除了参考标注偏差。'),
        '## 8. 资源用量与可复核性',
        table(['阶段','底层请求数','接口报告token','缺失用量请求'],[[k,v['requests'],v['reported_tokens'],v['requests_without_usage']] for k,v in s['usage'].items()]),
        'token按接口返回值累计，不含本次Codex对话用量及此前开发试点；失败且未返回用量的请求无法纳入token总数。没有经账单核验的价格，故不推算人民币费用。每次审计耗时见runs.csv；并行运行的耗时相加不是实际墙钟总时间。',
        '## 9. 局限与结论边界',
        '本实验只有6篇独立论文，均为公开机器学习论文，不能代表所有学科、中文论文或复杂扫描PDF。系统使用PDF文本证据，没有恢复图表视觉语义，实验不涉及论文模型的训练复现。',
        '参考模型参与样本构造、事实拆分及标注，虽然请求隔离，仍可能产生共同偏差。双轮一致不证明真值正确。自然报告的参考事实拆分与审计后语义对齐也由模型辅助完成，可能有遗漏或错配。后续若需要人工金标结论，应另行开展真实人工标注，不能仅替换报告名称。',
        f'本次完成了可追溯的端到端评测，成功运行{s["successful_audits"]}/96次。当前证据仅支持报告中列明的样本内表现，未通过目标不能被总体分数或重复稳定性掩盖。全部失败、未决标签及明细随数据提交，供复核与后续改进。',
        '## 附录：数据包索引',
        table(['路径','内容'],[['inputs/','论文PDF、证据分块、盲事实输入、身份排除记录'],['reports/','36份实际被审计报告'],['construction/、generation/','样本构造与Hy3自然生成原始请求/返回'],['reference/、reference_freeze.json','独立参考请求、证据匹配、裁决、冻结散列'],['protocol.json','实验输入、代码和配置冻结'],['run_1/至run_3/','完整审计输出与底层用量记录'],['alignment/、alignment_freeze.json','盲语义对齐及冻结'],['analysis/','逐运行、逐事实、逐报告、排序、攻击、用量CSV及汇总JSON']]),
        '最终有效参考标签位于reference_recovery，reference_selection.json指定读取目录；reference保留原始服务故障记录。resumptions记录审计恢复事件。successful_subset.json为事后成功子集统计，不替代冻结脚本的summary.json。',
        '论文来源：'+ '；'.join(f'{p["title"]}：https://arxiv.org/abs/{p["arxiv_version"]}' for p in papers)+'。']
    text='\n\n'.join(lines)+'\n'
    (OUT/'submission_report.md').write_text(text,encoding='utf-8')
    save(OUT/'analysis/report_build.json',{'summary_sha256':sha(OUT/'analysis/summary.json'),'report_sha256':sha(OUT/'submission_report.md')})
    print('Written '+str(OUT/'submission_report.md'))

if __name__=='__main__':
    main()
