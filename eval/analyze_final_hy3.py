"""Blind semantic alignment and deterministic aggregation for frozen Hy3 audits."""
from __future__ import annotations
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import csv
from itertools import combinations
import json
from pathlib import Path
import re
from statistics import fmean, pstdev
from eval.final_hy3_experiment import OUT, ROOT, request, sha
from eval.reference_annotation_v2 import read, save

def align():
    protocol=read(OUT/'protocol.json')
    jobs=[(r,i) for r in protocol['reports'] for i in range(1,r['repeats']+1)]
    def job(pair):
        r,i=pair; rid=r['report_id']; runpath=OUT/f'run_{i}'/(rid+'.json')
        if not runpath.exists():
            raise ValueError('Audit not yet attempted: '+str(runpath))
        run=read(runpath)
        if run['status']!='ok':
            return
        blind=read(OUT/'inputs'/('blind_'+rid+'.json'))
        claims=[{k:a['claim'][k] for k in ('claim_id','text','source_id','source_quote')} for a in run['audit']['audits']]
        def valid(v):
            assert len(v['matches'])==len(blind['facts'])
            assert {m['fact_id'] for m in v['matches']}=={f['fact_id'] for f in blind['facts']}
            for m in v['matches']:
                assert m['coverage'] in {'full','partial','missing','uncertain'}
                assert len(m['claim_ids'])==len(set(m['claim_ids']))
                assert set(m['claim_ids'])<={c['claim_id'] for c in claims}
                assert m['coverage']!='full' or m['claim_ids']
        # No prediction judgment, score, reference label, quality tier or construction gold.
        try:
            request(OUT/'alignment'/f'{rid}_{i}.json',
                '只做语义对应，不判断事实真伪。将原始事实对齐到系统抽取的claims。full要求选中的claim完整保留原事实主体、关系、数字、条件和结论强度；'
                '仅同主题或同source_id绝不等于完整覆盖。多个claim可以共同完整覆盖一个fact。抽取中丢失数字/限定词/改写过强结论时必须partial。'
                '没有相应内容missing，不确定uncertain。只返回JSON {"matches":[{"fact_id":"...","claim_ids":["..."],"coverage":"full|partial|missing|uncertain","reason":"简短理由"}]}，包含所有fact_id。',
                {'facts':blind['facts'],'claims':claims},validator=valid)
        except RuntimeError:
            # Kept as missing alignment; aggregation counts this failure explicitly.
            return
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(job,jobs))
    paths=list((OUT/'alignment').glob('*.json'))
    save(OUT/'alignment_freeze.json',{'runner_sha256':sha(Path(__file__)),
        'sha256':{str(p.relative_to(OUT)):sha(p) for p in sorted(paths)}})

def ratio(n,d):
    return n/d if d else None

def csv_save(path,rows):
    if not rows:
        return
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def summarize():
    protocol=read(OUT/'protocol.json'); dest=OUT/'analysis';dest.mkdir(exist_ok=True)
    assert (OUT/'alignment_freeze.json').exists()
    for freeze in ('reference_freeze','alignment_freeze'):
        for name,h in read(OUT/(freeze+'.json'))['sha256'].items():
            assert sha(OUT/name)==h
    refs={}
    refdir=read(OUT/'reference_selection.json')['directory'] if (OUT/'reference_selection.json').exists() else 'reference'
    for path in (OUT/refdir).glob('P*/labels.json'):
        for f in read(path):
            refs[(f['report_id'],f['fact_id'])]=f
    runrows=[]; factrows=[]; reportrows=[]; errors=[]
    label_rank={'SUPPORTED':0,'PARTIALLY_SUPPORTED':1,'NO_SUPPORT_FOUND':2,'CONTRADICTED':3}
    for report in protocol['reports']:
        rid=report['report_id']; blind=read(OUT/'inputs'/('blind_'+rid+'.json'))
        sources={s.source_id:s.text for s in __import__('paperaudit.claim_extraction',fromlist=['split_report_sources']).split_report_sources(blind['report_text'])}
        scores=[]; observations=[]
        for i in range(1,report['repeats']+1):
            path=OUT/f'run_{i}'/(rid+'.json')
            if not path.exists():
                raise ValueError('Incomplete experiment; cannot produce final analysis')
            run=read(path);good=run['status']=='ok'
            summary=run.get('audit',{}).get('summary',{})
            score=summary.get('total_score');scores.append(score)
            runrows.append(dict(report_id=rid,paper_id=report['paper_id'],kind=report['kind'],tier=report.get('tier'),
                repeat=i,status=run['status'],total_score=score,seconds=run['seconds'],
                claims=len(run.get('audit',{}).get('audits',[])),**summary.get('dimensions',{k:None for k in ('factual_support','evidence_correctness','evidence_completeness','numeric_consistency','content_coverage','conclusion_boundary')})))
            if not good:
                errors.append(dict(report_id=rid,repeat=i,error_type=run.get('error_type')))
            aligned=None
            for attempt in (1,2):
                ap=OUT/'alignment'/f'{rid}_{i}_attempt{attempt}.json'
                if ap.exists() and read(ap)['status']=='ok':
                    aligned=read(ap)['value']; break
            am={m['fact_id']:m for m in (aligned or {}).get('matches',[])}
            audits={a['claim']['claim_id']:a for a in run.get('audit',{}).get('audits',[])}
            for f in blind['facts']:
                fid=f['fact_id'];m=am.get(fid,{})
                selected=[audits[c] for c in m.get('claim_ids',[])]
                full=m.get('coverage')=='full' and bool(selected)
                labels=[a['judgment']['label'] for a in selected]
                decided=full and 'ABSTAIN' not in labels
                predicted=max(labels,key=lambda v:label_rank.get(v,-1)) if decided else None
                risk=decided and any(a['judgment']['severity'] in {'high','critical'} for a in selected)
                ref=refs.get((rid,fid),{});g=ref.get('reference') or {};resolved=ref.get('status')=='resolved'
                citation=re.findall(r'（(?:证据|引用|来源)：[^）]+）',sources.get(f.get('source_id'),''))
                retained=bool(full and citation and all(any(c in (a['claim'].get('provided_evidence') or '') for a in selected) for c in citation))
                row=dict(report_id=rid,paper_id=report['paper_id'],kind=report['kind'],repeat=i,fact_id=fid,
                    reference_status=ref.get('status','missing'),reference_label=g.get('label'),reference_severity=g.get('severity'),
                    coverage=m.get('coverage','alignment_failed' if good else 'audit_failed'),semantic_full=bool(full),
                    prediction_label=predicted,prediction_high_risk=bool(risk),nonabstain=bool(decided),
                    correct=bool(resolved and decided and predicted==g.get('label')),
                    has_original_citation=bool(citation),citation_retained=retained,
                    claim_ids=';'.join(m.get('claim_ids',[])))
                factrows.append(row);observations.append(row)
        complete=all(v is not None for v in scores)
        agreements=[]
        if report['repeats']==3:
            for f in blind['facts']:
                fs=[o for o in observations if o['fact_id']==f['fact_id']]
                agreements.extend(a['nonabstain'] and b['nonabstain'] and a['prediction_label']==b['prediction_label'] for a,b in combinations(fs,2))
        reportrows.append(dict(report_id=rid,paper_id=report['paper_id'],kind=report['kind'],tier=report.get('tier'),attack=report.get('attack'),
            mean_score=fmean(scores) if complete else None,score_std=pstdev(scores) if complete and len(scores)==3 else None,
            label_repeat_agreement=fmean(agreements) if agreements else None,
            semantic_fact_recall=fmean(o['semantic_full'] for o in observations),fact_count=len(blind['facts']),report_chars=len(blind['report_text'])))
    def metrics(rows):
        ref=[r for r in rows if r['reference_status']=='resolved']; high=[r for r in ref if r['reference_severity'] in {'high','critical'}];sup=[r for r in ref if r['reference_label']=='SUPPORTED']
        decided=[r for r in ref if r['nonabstain']];cit=[r for r in rows if r['has_original_citation']]
        return dict(fact_observations=len(rows),resolved_reference_observations=len(ref),
            semantic_fact_recall=ratio(sum(r['semantic_full'] for r in rows),len(rows)),
            end_to_end_label_accuracy=ratio(sum(r['correct'] for r in ref),len(ref)),
            decided_label_accuracy=ratio(sum(r['correct'] for r in decided),len(decided)),
            high_risk_denominator=len(high),high_risk_recall=ratio(sum(r['prediction_high_risk'] for r in high),len(high)),
            supported_denominator=len(sup),supported_high_risk_false_positive=ratio(sum(r['prediction_high_risk'] for r in sup),len(sup)),
            nonabstain=ratio(sum(r['nonabstain'] for r in rows),len(rows)),
            original_citation_denominator=len(cit),original_citation_retention=ratio(sum(r['citation_retained'] for r in cit),len(cit)))
    rankings=[]; lookup={r['report_id']:r for r in reportrows}
    for p in read(OUT/'inputs/papers.json'):
        ss=[lookup[p['paper_id']+'_'+t]['mean_score'] for t in ('high','medium','low')]
        rankings.append(dict(paper_id=p['paper_id'],high=ss[0],medium=ss[1],low=ss[2],correct=all(s is not None for s in ss) and ss[0]>ss[1]>ss[2]))
    attacks=[]
    for r in protocol['reports']:
        if r['kind']=='adversarial':
            current=lookup[r['report_id']]['mean_score'];base=lookup[r['base_report_id']]['mean_score']
            attacks.append(dict(report_id=r['report_id'],attack=r['attack'],base_mean=base,attack_mean=current,
                delta=current-base if current is not None and base is not None else None))
    usage=[]
    reused=set()
    for manifest in (OUT/'reference_recovery').glob('P*/recovery_manifest.json'):
        reused.update(manifest.parent/Path(item['source']).name for item in read(manifest)['preserved_attempts'])
    for path in OUT.rglob('*attempt*.json'):
        if path in reused:
            continue
        d=read(path)
        usage.append(dict(stage=path.relative_to(OUT).parts[0],status=d['status'],tokens=(d.get('usage') or {}).get('total_tokens'),seconds=d.get('seconds',0)))
    for path in OUT.glob('run_*/*_requests.json'):
        usage.extend(dict(stage='audit',status=q['status'],tokens=(q.get('usage') or {}).get('total_tokens'),seconds=q['seconds']) for q in read(path))
    groups={kind:metrics([r for r in factrows if r['kind']==kind]) for kind in ('controlled','natural','adversarial')}
    controlled=[r for r in reportrows if r['kind']=='controlled']
    summary=dict(expected_audits=96,attempted_audits=len(runrows),successful_audits=sum(r['status']=='ok' for r in runrows),
        reference_fact_counts=dict(Counter(f['status'] for f in refs.values())),groups=groups,rankings=rankings,
        ranking_rate=sum(r['correct'] for r in rankings)/6,
        controlled_mean_score_std=fmean(r['score_std'] for r in controlled) if all(r['score_std'] is not None for r in controlled) else None,
        controlled_label_repeat_agreement=fmean(r['label_repeat_agreement'] for r in controlled),
        usage={stage:dict(requests=sum(q['stage']==stage for q in usage),reported_tokens=sum(q['tokens'] or 0 for q in usage if q['stage']==stage),
            requests_without_usage=sum(q['tokens'] is None for q in usage if q['stage']==stage)) for stage in sorted({q['stage'] for q in usage})},
        attacks=attacks,failures=errors,
        independence_note='6 independent papers; repeated facts/runs are correlated. No iid confidence interval over repeated facts.',
        aggregation='Full semantic coverage required. Multi-claim fact uses worst decided label: CONTRADICTED > NO_SUPPORT_FOUND > PARTIALLY_SUPPORTED > SUPPORTED. Any ABSTAIN makes fact undecided.')
    save(dest/'summary.json',summary)
    for name,rows in [('runs',runrows),('facts',factrows),('reports',reportrows),('ranking',rankings),('attacks',attacks),('usage',usage)]:
        csv_save(dest/(name+'.csv'),rows)
    print(json.dumps({'successful':summary['successful_audits'],'ranking_rate':summary['ranking_rate']},ensure_ascii=False))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['align','summarize']);args=p.parse_args();globals()[args.phase]()
