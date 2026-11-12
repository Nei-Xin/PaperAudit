"""One bounded investigation through a deployed API; verify live delivery and replay.

Uses an existing saved plan and one custom question (at most 12 new model requests).
Never retries the model task. Repeating identical inputs reuses the existing job;
use a fresh question when an independently live smoke is explicitly intended.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import time
import urllib.request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', required=True)
    parser.add_argument('--project', required=True)
    parser.add_argument('--plan', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--question', default='论文预训练的 warmup 轮数与 main_pretrain.py 的默认参数是否相同？请区分预训练和监督训练设置，并引用具体配置。')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    origin = args.base_url.rstrip('/')
    base = f'{origin}/api/projects/{args.project}'
    started = time.monotonic()

    def write(name, data):
        (args.output / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')

    def request(path, body=None):
        req = urllib.request.Request(base + path, headers={'Origin': origin})
        if body is not None:
            req.data = json.dumps(body).encode()
            req.add_header('Content-Type', 'application/json')
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.load(response)

    def elapsed():
        return round(time.monotonic() - started, 3)

    plan = request(f'/consistency-plans/{args.plan}')
    job = request(f'/consistency-plans/{args.plan}/execute', {
        'privacy_ack': True, 'selected_ids': [], 'extra_questions': [args.question],
    })
    job_id = job['job_id']
    write('submission.json', {'project_id': args.project, 'plan_id': args.plan,
                            'job_id': job_id, 'question': args.question})
    print(json.dumps({'job_id': job_id, 'status': job['status']}), flush=True)
    assert job['status'] in {'QUEUED', 'RUNNING'}, 'Existing completed job reused; do not retry automatically'
    events = []
    headers_seen = []
    first_tool = None
    terminal = None

    def stream(after=0):
        headers = {'Accept': 'text/event-stream'}
        if after:
            headers['Last-Event-ID'] = str(after)
        req = urllib.request.Request(base + f'/consistency-jobs/{job_id}/events', headers=headers)
        with urllib.request.urlopen(req, timeout=30) as response:
            observed = {k: response.headers.get(k) for k in ('Content-Type', 'Cache-Control', 'X-Accel-Buffering')}
            headers_seen.append(observed)
            assert observed['Content-Type'].startswith('text/event-stream')
            assert observed['Cache-Control'] == 'no-store'
            assert observed['X-Accel-Buffering'] == 'no'
            record = {}
            for raw in response:
                assert elapsed() < 300, 'Smoke exceeded wall time bound'
                line = raw.decode().rstrip('\r\n')
                if not line:
                    if 'data' in record:
                        yield record.get('event', 'message'), json.loads(record['data']), record.get('id')
                    record = {}
                elif not line.startswith(':'):
                    key, _, value = line.partition(':')
                    record[key] = value.lstrip(' ')

    connection = stream()
    try:
        for kind, data, event_id in connection:
            assert kind == 'audit', f'Ended without a live tool event: {kind}'
            assert int(event_id) == data['event_id']
            events.append({'received_seconds': elapsed(), 'connection': 1, 'event': data})
            if data['kind'] == 'tool_step':
                current = next(j for j in request('/consistency-jobs') if j['job_id'] == job_id)
                first_tool = {'event_id': data['event_id'], 'tool': data['tool'],
                              'received_seconds': elapsed(), 'job_status': current['status']}
                write('first-tool.json', first_tool)
                print(json.dumps(first_tool), flush=True)
                break
    finally:
        connection.close()  # Deliberate disconnect before task completion.
    assert first_tool and first_tool['job_status'] == 'RUNNING'
    cursor = events[-1]['event']['event_id']
    for kind, data, event_id in stream(cursor):
        if kind == 'end':
            terminal = data
            break
        assert kind == 'audit', kind
        assert int(event_id) == data['event_id']
        events.append({'received_seconds': elapsed(), 'connection': 2, 'event': data})
    write('events.json', events)
    assert terminal and terminal['status'] == 'SUCCEEDED', terminal
    terminal_seconds = elapsed()
    ids = [e['event']['event_id'] for e in events]
    assert ids == list(range(1, len(ids) + 1)), ids
    replay = []
    replay_end = None
    for kind, data, _ in stream():
        if kind == 'end':
            replay_end = data
            break
        assert kind == 'audit', kind
        replay.append(data)
    assert replay == [e['event'] for e in events]
    assert replay_end == terminal
    report = request('/consistency-reports/' + terminal['report_id'])
    # Public artifacts omit deployment model identifiers; never fetch settings/credentials.
    def public(value):
        if isinstance(value, dict):
            return {k: public(v) for k, v in value.items() if k != 'model'}
        if isinstance(value, list):
            return [public(v) for v in value]
        return value
    write('report.json', public(report))
    kinds = [e['event']['kind'] for e in events]
    assert 'verification' in kinds and 'item_finished' in kinds
    assert kinds.index('verification') < kinds.index('item_finished') < len(kinds) - 1
    assert events[-1]['event']['status'] == 'SUCCEEDED'
    assert len(report['items']) == 1
    requests = report['requests'] - plan['requests']
    assert 1 <= requests <= 12
    outcome = {
        'job_id': job_id, 'report_id': terminal['report_id'], 'status': terminal['status'],
        'first_tool': first_tool, 'terminal_seconds': terminal_seconds,
        'disconnect_after_event': cursor, 'event_count': len(events),
        'contiguous_ids': True, 'reconnect_no_duplicates_or_gaps': True,
        'full_replay_matches': True, 'headers': headers_seen,
        'new_requests': requests, 'new_tokens': report['tokens'] - plan['tokens'],
        'saved_plan_requests': plan['requests'], 'saved_plan_tokens': plan['tokens'],
        'summary': report['summary'],
        'limitations': ['One known development question; engineering smoke, not an accuracy evaluation.',
                       'Live API reached through SSH tunnel; arbitrary reverse proxies not evaluated.'],
    }
    write('outcome.json', outcome)
    print(json.dumps(outcome, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
