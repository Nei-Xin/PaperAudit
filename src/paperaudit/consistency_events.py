"""Small durable event journal; single-process writers, independent streaming readers."""
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
import os
from pathlib import Path

from paperaudit.agents.models import CodeInvestigationStep
from paperaudit.models import ConsistencyEvent

MAX_EVENT_BYTES = 8192


class StepLog(list[CodeInvestigationStep]):
    """Record the ordinary trace and optionally notify after each completed step."""
    def __init__(self, on_step: Callable[[CodeInvestigationStep], None] | None = None):
        super().__init__()
        self.on_step = on_step

    def append(self, step: CodeInvestigationStep) -> None:
        super().append(step)
        if self.on_step:
            self.on_step(step)


def step_fields(step: CodeInvestigationStep) -> dict:
    # Never publish raw submissions, rejected quotations, model content or arbitrary arguments.
    allowed = {
        'list_dir': {'path'}, 'grep_code': {'text', 'path_prefix'}, 'search_code': {'query'},
        'find_symbol': {'name'}, 'read_file': {'path', 'start_line', 'end_line'},
        'search_paper': {'query'}, 'grep_paper': {'text'}, 'read_page': {'page'},
        'propose_checkpoint': {'topic'},
    }.get(step.tool, set())
    args = {k: v[:300] if isinstance(v, str) else v for k, v in step.arguments.items()
            if k in allowed and isinstance(v, (str, int, bool))}
    outcome = step.outcome[:400]
    if step.tool == 'submit_answer':
        args = {}
        outcome = '结论通过引用校验。' if step.ok else '引用校验未通过，正在修正或保留为证据不足。'
    elif step.tool == 'propose_checkpoint':
        args = {k: v for k, v in args.items() if k == 'topic'}
        outcome = '核对要点已接受。' if step.ok else '要点校验未通过。'
    elif step.tool not in {'list_dir','grep_code','search_code','find_symbol','read_file',
                           'search_paper','grep_paper','read_page','verify_findings','continue_reading'}:
        args, outcome = {}, '工具步骤已完成。' if step.ok else '工具步骤未通过。'
    return dict(tool=step.tool[:60], arguments=args, outcome=outcome, ok=step.ok)


def append_event(path: Path, job_id: str, fields: dict) -> ConsistencyEvent:
    """Caller serializes writers. Repair only an incomplete final line after a crash."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a+b') as handle:
        handle.seek(0, os.SEEK_END)
        size = handle.tell()
        start = max(0, size - MAX_EVENT_BYTES * 2)
        handle.seek(start)
        tail = handle.read()
        if tail and not tail.endswith(b'\n'):
            boundary = tail.rfind(b'\n')
            if boundary < 0 and start:
                raise ValueError('Invalid event journal tail')
            size = start + boundary + 1
            handle.truncate(size)
            tail = tail[:boundary + 1]
        last = ConsistencyEvent.model_validate_json(tail.splitlines()[-1]) if tail else None
        if last and last.job_id != job_id:
            raise ValueError('Event journal identity mismatch')
        event = ConsistencyEvent(**fields, event_id=last.event_id + 1 if last else 1,
                                 job_id=job_id, created_at=datetime.now(timezone.utc).isoformat())
        data = event.model_dump_json().encode() + b'\n'
        if len(data) > MAX_EVENT_BYTES:
            raise ValueError('Event exceeds size limit')
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    return event


def read_events(path: Path, offset: int = 0, limit: int = 128) -> tuple[list[ConsistencyEvent], int]:
    """Only complete records are visible; offset advances as they are consumed."""
    events = []
    try:
        with path.open('rb') as handle:
            handle.seek(offset)
            for _ in range(limit):
                line = handle.readline(MAX_EVENT_BYTES + 1)
                if not line:
                    break
                if len(line) > MAX_EVENT_BYTES:
                    raise ValueError('Invalid event size')
                if not line.endswith(b'\n'):
                    break
                events.append(ConsistencyEvent.model_validate_json(line))
                offset = handle.tell()
    except FileNotFoundError:
        pass  # Old jobs and newly queued tasks legitimately have no events.
    return events, offset
