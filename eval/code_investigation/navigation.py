"""Measure navigation in saved traces without equating tool calls with requests."""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

READ_TOOLS = {'list_dir','grep_code','search_code','find_symbol','read_file','search_paper','grep_paper','read_page'}


def summarize(rows):
    tools=Counter();early=Counter();with_dir=with_unscoped=0
    for row in rows:
        steps=[s for s in row['steps'] if s['tool'] in READ_TOOLS]
        tools.update(s['tool'] for s in steps);early.update(s['tool'] for s in steps[:3])
        with_dir+=any(s['tool']=='list_dir' for s in steps[:3])
        with_unscoped+=any(s['tool']=='grep_code' and not s['arguments'].get('path_prefix','').strip() for s in steps[:3])
    return {'investigations':len(rows),'tool_calls':dict(tools),'first_three':dict(early),
            'first_three_with_list_dir':with_dir,'first_three_with_unscoped_grep':with_unscoped,
            'requests':sum(r['requests'] for r in rows),'tokens':sum(r['tokens'] for r in rows)}


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('input',type=Path);ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();raw=args.input.read_bytes()
    observations=[json.loads(l) for l in raw.decode().splitlines()]
    rows=[{'item':r['item'],'repeat':r['repeat'],'requests':r.get('requests',0),'tokens':r.get('tokens',0),
           'steps':(r.get('trace') or {}).get('steps',[])} for r in observations if r.get('event')=='result' and r['mode']=='agent']
    result={'source_sha256':sha256(raw).hexdigest(),'source':str(args.input),'overall':summarize(rows),
            'by_paper':{p:summarize([r for r in rows if r['item'].split('-')[0]==p]) for p in sorted({r['item'].split('-')[0] for r in rows})},
            'limitations':['Tool calls are not model requests; old traces do not retain request-to-tool grouping.',
                           'Unscoped grep may be a precise parameter lookup, not directory exploration.',
                           'Counts identify a possible optimization, not measured cost savings.']}
    args.output.mkdir(parents=True,exist_ok=False)
    (args.output/'trace-input.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))
    (args.output/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result['overall']))

if __name__=='__main__':main()
