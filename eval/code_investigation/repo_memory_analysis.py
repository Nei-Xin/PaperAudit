"""Analyze a completed frozen repository-memory run without modifying scores."""
import argparse
from collections import Counter
import json
from pathlib import Path


def totals(rows):
    n=len(rows)
    return {'n':n,'correct':sum(r['correct'] for r in rows),
        'requests':sum(r['requests'] for r in rows),'tokens':sum(r['tokens'] for r in rows),
        'mean_requests':round(sum(r['requests'] for r in rows)/n,3) if n else 0,
        'mean_tokens':round(sum(r['tokens'] for r in rows)/n,1) if n else 0,
        'mean_seconds':round(sum(r['seconds'] for r in rows)/n,2) if n else 0,
        'predictions':dict(Counter(r['predicted'] for r in rows)),
        'map_used':sum((r.get('trace') or {}).get('repo_map_used',False) for r in rows),
        'list_dir':sum(s['tool']=='list_dir' for r in rows for s in (r.get('trace') or {}).get('steps',[])),
        'read_file':sum(s['tool']=='read_file' for r in rows for s in (r.get('trace') or {}).get('steps',[]))}


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('run',type=Path);args=ap.parse_args()
    protocol=json.loads((args.run/'protocol.json').read_text())
    rows=[json.loads(l) for l in (args.run/'observations.jsonl').read_text().splitlines()]
    maps={r['variant']:r['map'] for l in (args.run/'maps.jsonl').read_text().splitlines() if (r:=json.loads(l))}
    expected={(i,a,r) for i in protocol['items'] for a in protocol['arms'] for r in range(protocol['repeats'])}
    assert len(rows)==len(expected) and {(r['item'],r['arm'],r['repeat']) for r in rows}==expected
    pairs=[]
    for item in protocol['items']:
        for repeat in range(protocol['repeats']):
            a=next(r for r in rows if (r['item'],r['repeat'],r['arm'])==(item,repeat,'baseline'))
            b=next(r for r in rows if (r['item'],r['repeat'],r['arm'])==(item,repeat,'map'))
            pairs.append({'item':item,'repeat':repeat,'baseline':a['predicted'],'map':b['predicted'],
                'expected':a['expected'],'baseline_correct':a['correct'],'map_correct':b['correct'],
                'map_used':(b.get('trace') or {}).get('repo_map_used',False),
                'request_delta':b['requests']-a['requests'],'token_delta':b['tokens']-a['tokens']})
    def groups(key):
        return {str(v):{a:totals([r for r in rows if key(r)==v and r['arm']==a]) for a in protocol['arms']}
                for v in sorted({key(r) for r in rows})}
    variants=groups(lambda r:r['variant'])
    for key,value in variants.items():
        value['map_generation']={k:maps[key][k] for k in ['requests','tokens','stop_reason']}
        value['map_including_generation']={k:value['map'][k]+maps[key][k] for k in ['requests','tokens']}
    result={'overall':{a:totals([r for r in rows if r['arm']==a]) for a in protocol['arms']},
        'by_paper':groups(lambda r:r['item'].split('-')[0]),'by_repeat':groups(lambda r:r['repeat']),
        'by_variant':variants,'paired_outcomes':dict(Counter(f"baseline_{p['baseline_correct']}_map_{p['map_correct']}" for p in pairs)),
        'notes':['Pairs share question and repeat index, not a common model random seed.',
                 'Map costs allocated once per exact variant. Empty maps are still charged.',
                 'Correctness is reference-label agreement, not independent evidence-support judgment.']}
    used_keys={(r['item'],r['repeat']) for r in rows if r['arm']=='map' and (r.get('trace') or {}).get('repo_map_used')}
    result['exploratory_by_map_available']={str(used):{a:totals([r for r in rows if r['arm']==a
        and (((r['item'],r['repeat']) in used_keys)==used)]) for a in protocol['arms']} for used in [True,False]}
    result['notes'].append('Availability subgroup is post-run descriptive analysis, not the decision metric.')
    (args.run/'analysis.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    (args.run/'paired-results.jsonl').write_text(''.join(json.dumps(p,ensure_ascii=False)+'\n' for p in pairs))
    print(json.dumps(result['overall']))

if __name__=='__main__':main()
