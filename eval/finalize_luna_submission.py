"""Offline figures, transport reconciliation and submission narrative."""
from pathlib import Path
import csv
import hashlib
import json
from collections import Counter
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'eval/luna_reliable_20260907'
def read(p): return json.loads(p.read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,d): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
def table(head,rows): return '\n'.join(['| '+' | '.join(head)+' |','| '+' | '.join(['---']*len(head))+' |']+['| '+' | '.join(map(str,r))+' |' for r in rows])

def main():
    s=read(OUT/'analysis/summary.json'); protocol=read(OUT/'protocol.json')
    a=read(OUT/'amendments/concurrency2/amendment.json'); b=read(OUT/'amendments/concurrency4/amendment.json')
    for freeze in ['reference_freeze','alignment_freeze']:
        for n,h in read(OUT/(freeze+'.json'))['sha256'].items(): assert sha(OUT/n)==h,n
    for n,h in protocol['input_sha256'].items(): assert sha(OUT/n)==h,n
    overrides=dict(a['source_sha256'],**b['source_sha256'])
    for n,h in protocol['source_sha256'].items(): assert sha(ROOT/n)==overrides.get(n.replace('\\','/'),h),n
    for amend in [a,b]:
        for n,h in amend['preserved_results'].items(): assert sha(OUT/n)==h,n
    jobs=[(r,i) for r in protocol['reports'] for i in range(1,r['repeats']+1)]
    runs=[read(OUT/f'run_{i}'/(r['report_id']+'.json')) for r,i in jobs]
    assert len(runs)==96 and sum(r['status']=='ok' for r in runs)==s['successful_audits']==93
    assert len([r for r in runs if r['status']!='ok'])==len(s['failures'])==3
    aligned=0
    for report,i in jobs:
        if read(OUT/f'run_{i}'/(report['report_id']+'.json'))['status']!='ok': continue
        matches=[p for j in (1,2) if (p:=OUT/'alignment'/f'{report["report_id"]}_{i}_attempt{j}.json').exists() and read(p)['status']=='ok']
        assert matches; aligned+=1
    assert aligned==93
    with (OUT/'analysis/facts.csv').open(encoding='utf-8-sig',newline='') as f: facts=list(csv.DictReader(f))
    for kind,metrics in s['groups'].items():
        rows=[r for r in facts if r['kind']==kind]; resolved=[r for r in rows if r['reference_status']=='resolved']; decided=[r for r in resolved if r['nonabstain']=='True']
        for key,num,den in [('end_to_end_label_accuracy',sum(r['correct']=='True' for r in resolved),len(resolved)),('decided_label_accuracy',sum(r['correct']=='True' for r in decided),len(decided)),('semantic_fact_recall',sum(r['semantic_full']=='True' for r in rows),len(rows))]:
            assert abs(metrics[key]-num/den)<1e-12,(kind,key)
    attempts={1:[],2:[],4:[]}; first={1:[],2:[],4:[]}
    for path in OUT.glob('run_*/*_checkpoints/*.json'):
        d=read(path); rel=str(path.relative_to(OUT)); baseline=b['baseline_checkpoints'].get(rel,{})
        old_count=baseline.get('attempts',0)
        if old_count: assert len(d['attempts'])>=old_count
        result_key=str(path.parent.parent.relative_to(OUT)/ (path.parent.name.removesuffix('_checkpoints')+'.json'))
        old_phase=1 if result_key in a['preserved_results'] else 2
        for index,item in enumerate(d['attempts']):
            phase=old_phase if index<old_count else 4
            attempts[phase].append(item)
            if index==0: first[phase].append(item['status']=='ok')
    phases=[]
    for phase,rows in attempts.items():
        phases.append(dict(workers=phase,network_attempts=len(rows),successful_attempts=sum(r['status']=='ok' for r in rows),
            attempt_success_rate=sum(r['status']=='ok' for r in rows)/len(rows),first_attempt_success_rate=sum(first[phase])/len(first[phase]),
            network_seconds=sum(r['seconds'] for r in rows)))
    t=read(OUT/'analysis/transport.json')
    assert sum(r['network_attempts'] for r in phases)==t['network_attempts']==1317
    assert sum(r['successful_attempts'] for r in phases)==t['logical_requests']==1306
    assert phases[0]['network_attempts']==a['baseline_transport']['network_attempts']
    save(OUT/'analysis/concurrency_phases_final.json',phases)
    with (OUT/'analysis/concurrency_phases_final.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(phases[0]));w.writeheader();w.writerows(phases)
    plt.rcParams.update({'font.family':'Microsoft YaHei','axes.unicode_minus':False,'font.size':11})
    figures=OUT/'figures'; figures.mkdir(exist_ok=True)
    names=['控制组','自然组','对抗组']; kinds=['controlled','natural','adversarial']; colors=['#2878a1','#dc963e','#629778']
    fig,ax=plt.subplots(figsize=(9,4.8),layout='constrained')
    for j,(key,label) in enumerate([('semantic_fact_recall','语义事实召回'),('end_to_end_label_accuracy','端到端一致率'),('decided_label_accuracy','已判定一致率')]):
        vals=[s['groups'][k][key]*100 for k in kinds]; bars=ax.bar([i+(j-1)*.24 for i in range(3)],vals,.23,label=label,color=colors[j]); ax.bar_label(bars,fmt='%.1f',fontsize=9,padding=3)
    ax.set(xticks=range(3),xticklabels=names,ylim=(0,115),ylabel='百分比（%）',title='三组事实级结果');ax.legend(loc='upper center',ncol=3,fontsize=9);ax.spines[['top','right']].set_visible(False)
    fig.savefig(figures/'facts.png',dpi=180);plt.close(fig)
    fig,ax=plt.subplots(figsize=(9,4.8),layout='constrained')
    for j,(key,label) in enumerate([('high','高质量'),('medium','中质量'),('low','低质量')]):
        vals=[r[key] if r[key] is not None else float('nan') for r in s['rankings']];bars=ax.bar([i+(j-1)*.24 for i in range(6)],vals,.23,label=label,color=colors[j]);ax.bar_label(bars,fmt='%.1f',fontsize=8,padding=3)
    ax.text(4.24,12,'缺失',ha='center',fontsize=10);ax.set(xticks=range(6),xticklabels=['ALBERT','XLNet','DenseNet','MobileNets','LightGCN','NGCF'],ylim=(0,115),ylabel='规则总分（0-100）',title='报告质量分层：仅展示三次均成功的均分');ax.legend(ncol=3,loc='upper center');ax.spines[['top','right']].set_visible(False)
    fig.savefig(figures/'ranking.png',dpi=180);plt.close(fig)
    fig,ax=plt.subplots(figsize=(9,3.5),layout='constrained');bars=ax.barh(['失败','成功'],[3,93],color=['#bf615c','#2878a1']);ax.bar_label(bars,padding=5);ax.set(xlim=(0,105),xlabel='正式任务数',title='96次正式审计：93成功 / 3应用响应失败');ax.spines[['top','right']].set_visible(False)
    fig.savefig(figures/'completion.png',dpi=180);plt.close(fig)
    text=(OUT/'submission_report.md').read_text(encoding='utf-8').split('## 并发执行协议修订')[0].split('## 并发执行协议与资源核验')[0].rstrip()
    text=text.replace('python -m eval.luna_reliable_experiment all恢复审计','python -m eval.luna_concurrent按修订协议恢复审计')
    text=text.replace('随后按修订改为任务并发2（见协议修订章节）','随后按修订改为任务并发2、4（见协议修订章节）')
    text+='\n\n## 并发执行协议与资源核验\n\n'
    text+=f'并发2修订时间（UTC）：{a["created_at"]}；并发4修订时间（UTC）：{b["created_at"]}。全部旧协议、代码快照、恢复记录和受影响任务范围随数据包保留。模型、提示词、评分、输入和重复次数不变。每次提并发以接下来4个正式任务观察，未额外试跑；对齐单并发。\n\n'
    text+='连续429或重试耗尽时停止派发，等待在途任务结束后按对应修订降级一次；认证/余额拒绝停止新增请求。本轮没有生成降级状态记录。用户停止和进程中断后仅回放已保存响应；服务端已执行但本地未保存的在途请求不能排除额外计费。\n\n'
    text+=table(['任务并发','网络尝试','首次请求成功率','尝试成功率','网络耗时总和（分钟）'],[[r['workers'],r['network_attempts'],f"{r['first_attempt_success_rate']:.2%}",f"{r['attempt_success_rate']:.2%}",f"{r['network_seconds']/60:.2f}"] for r in phases])
    text+='\n\n阶段统计使用并发4切换前的请求检查点预算快照划分每一次网络尝试，涵盖中断任务，三阶段合计与1317次总尝试一致。首次成功率按逻辑请求首次发生的阶段计算；尝试成功率包含重试。耗时为网络等待累加，包含并行重叠，不能解释为实际墙钟时间或严格加速比；各阶段任务构成也不同。旧concurrency_phases.csv是早期不完整日志统计，仅供追溯，以concurrency_phases_final.csv为准。\n\n'
    text+='## 核心图表与结论\n\n![正式任务完成情况](figures/completion.png)\n\n![三组事实级结果](figures/facts.png)\n\n![质量分层得分](figures/ranking.png)\n\n'
    text+='完整结果支持5篇论文的高、中、低严格排序；LightGCN低质量报告的一次失败使该篇无法判定。标签重复一致率82.56%未达到预设90%；完整控制组平均分数标准差缺失，不能宣称通过稳定性门槛。部分低质量报告仍在90分以上，排序能力不等于绝对分数已校准。\n\n'
    text+='自然组已判定一致率93.36%，但端到端一致率65.28%，语义召回77.43%、非弃权覆盖69.90%。主要短板是对全部输入的完整处理；这包含漏抽取、弃权和整份失败的影响，不能把差值全部归因于单一环节。组间事实构造和难度不同，对抗组较高的一致率不证明攻击没有影响。\n\n'
    text+='3次最终失败均记录为Hy3ResponseError（应用沿用的异常类名，并非本轮使用Hy3模型）：P05_natural第1次、P05_low第2次、P05_citation第3次。最终接口响应取得成功仍可能无法通过应用结构或语义校验，故接口完成率100%与审计成功率96.88%并不矛盾。\n\n'
    text+='参考标注、语义对齐与被测模型均为Luna。结果衡量同模型参考一致性，不是人工金标准确率或独立验证。当前报告可作为带明确限制的实验数据材料，不宣称全部效果目标达成。\n'
    (OUT/'submission_report.md').write_text(text,encoding='utf-8')
    save(OUT/'verification/submission_checks.json',dict(tasks=96,successful=93,failed=3,aligned_successful_runs=aligned,metric_recalculation=True,input_and_reference_hashes=True,preserved_results=True,network_attempts=1317,successful_requests=1306,offline_only=True))
    print(json.dumps(phases,ensure_ascii=False))

if __name__=='__main__': main()
