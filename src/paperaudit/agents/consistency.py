"""Check every checkable point of a paper against its code.

An orchestrator plans the checkpoints, then hands each one to its own
investigation. Investigations run in parallel and share nothing but the
read-only paper and codebase: each has a fresh conversation, its own tool
workspace and its own request budget, so one going wrong cannot spend or
confuse another. The orchestrator owns the overall request ceiling and only
assembles the results; it does not write conclusions of its own.
"""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from threading import Condition
from time import monotonic

from paperaudit.hy3_client import Hy3Client
from paperaudit.models import (
    AnswerScope,
    AnswerStatus,
    ConsistencyCheckpoint,
    ConsistencyItem,
    ConsistencyItemStatus,
    ConsistencyReport,
    ConsistencySummary,
    EvidenceAnchor,
    FindingVerdict,
    ParsedCodebase,
    ParsedPaper,
)
from paperaudit.evidence import _quote_rects
from paperaudit.request_budget import RequestBudget, use_request_budget

from .code_investigator import CodeInvestigator, _appears_in_order, _collapse, _fragments, _typeset

Progress = Callable[[str, float], None]

STOP_NOTES = {
    "request_limit": "调查达到模型请求上限，未得出结论。",
    "time_limit": "调查达到时间上限，未得出结论。",
    "invalid_model_response": "模型响应无效，未得出结论。",
    "provider_error": "模型服务请求失败，未得出结论。",
}


class ConsistencyOrchestrator:
    PER_ITEM_REQUESTS = 11
    PLAN_REQUESTS = 3  # One call plus the JSON repair, with a spare.

    def __init__(self, client: Hy3Client, model: str, *, max_checkpoints: int = 20,
                 max_requests: int = 160, concurrency: int = 4):
        self.client, self.model = client, model
        self.max_checkpoints, self.max_requests = max_checkpoints, max_requests
        self.concurrency = max(1, concurrency)

    def run(self, paper: ParsedPaper, codebase: ParsedCodebase,
            progress: Progress | None = None) -> ConsistencyReport:
        started = monotonic()
        notify = progress or (lambda stage, value: None)
        notify("正在梳理论文中可核对的要点", 0.05)
        plan_budget = RequestBudget(max_requests=self.PLAN_REQUESTS, max_seconds=300)
        with use_request_budget(plan_budget):
            draft = self.client.plan_consistency(paper.title, paper.chunks, self.max_checkpoints)
        valid = self._accept(paper, draft.checkpoints)
        checkpoints = valid[:self.max_checkpoints]

        state = Condition()
        spent, tokens, running, done = plan_budget.requests, plan_budget.tokens, 0, 0
        results: list[ConsistencyItem | None] = [None] * len(checkpoints)

        def work(index: int) -> None:
            nonlocal spent, tokens, running, done
            checkpoint = checkpoints[index]
            with state:
                # Start only when the ceiling holds even if every running investigation
                # uses its full budget. Wait for others to report what they really used
                # before giving up on this item.
                while spent + (running + 1) * self.PER_ITEM_REQUESTS > self.max_requests and running:
                    state.wait()
                if spent + (running + 1) * self.PER_ITEM_REQUESTS > self.max_requests:
                    results[index] = ConsistencyItem(
                        checkpoint=checkpoint, status=ConsistencyItemStatus.NOT_CHECKED,
                        note="达到本次审计的模型请求上限，未核对该项。")
                    done += 1
                    return
                running += 1
            used_requests = used_tokens = 0
            try:
                answer, trace = CodeInvestigator(
                    self.client, paper, codebase, self.model,
                    budget=RequestBudget(max_requests=self.PER_ITEM_REQUESTS, max_seconds=180),
                ).run(checkpoint.question, AnswerScope.JOINT,
                      selected_paper_chunk_ids=[checkpoint.paper_anchor.chunk_id],
                      selected_paper_text=checkpoint.paper_anchor.quote)
                used_requests, used_tokens = trace.requests, trace.tokens
                item = (ConsistencyItem(checkpoint=checkpoint, status=ConsistencyItemStatus.CHECKED, answer=answer)
                        if answer is not None else
                        ConsistencyItem(checkpoint=checkpoint, status=ConsistencyItemStatus.FAILED,
                                        note=STOP_NOTES.get(trace.stop_reason, "调查未得出结论。")))
            except Exception as exc:  # One failed investigation must not lose the others.
                item = ConsistencyItem(checkpoint=checkpoint, status=ConsistencyItemStatus.FAILED,
                                       note=f"调查出错（{type(exc).__name__}），未得出结论。")
            with state:
                results[index] = item
                spent += used_requests
                tokens += used_tokens
                running -= 1
                done += 1
                notify(f"正在逐项核对（{done}/{len(checkpoints)}）", 0.15 + 0.8 * done / len(checkpoints))
                state.notify_all()

        if checkpoints:
            notify(f"正在逐项核对（0/{len(checkpoints)}）", 0.15)
            with ThreadPoolExecutor(max_workers=min(self.concurrency, len(checkpoints)),
                                    thread_name_prefix="paperaudit-consistency") as pool:
                list(pool.map(work, range(len(checkpoints))))

        items = [item for item in results if item is not None]
        return ConsistencyReport(
            model=self.model, paper_title=paper.title, codebase_name=codebase.name,
            items=items, summary=summarize(items), planned=len(draft.checkpoints),
            plan_rejected=len(draft.checkpoints) - len(valid), plan_over_limit=len(valid) - len(checkpoints),
            max_checkpoints=self.max_checkpoints, max_requests=self.max_requests,
            concurrency=self.concurrency, plan_requests=plan_budget.requests,
            requests=spent, tokens=tokens, elapsed_seconds=round(monotonic() - started, 1),
        )

    def _accept(self, paper: ParsedPaper, drafts) -> list[ConsistencyCheckpoint]:
        """Keep planned points whose quotation really is in the paper, without duplicates."""
        chunks = {chunk.chunk_id: chunk for chunk in paper.chunks}
        accepted: list[ConsistencyCheckpoint] = []
        seen: set[str] = set()
        for draft in drafts:
            chunk = chunks.get(draft.chunk_id.strip())
            fragments = _fragments(draft.quote)
            key = _collapse(draft.topic).casefold()
            if chunk is None or key in seen or sum(map(len, fragments)) < 8:
                continue
            if not (_appears_in_order([part.casefold() for part in fragments], _collapse(chunk.content).casefold())
                    or _appears_in_order([_typeset(part) for part in fragments], _typeset(chunk.content))):
                continue
            seen.add(key)
            quote = fragments[0][:320]
            accepted.append(ConsistencyCheckpoint(
                checkpoint_id=f"K{len(accepted) + 1:02d}", topic=_collapse(draft.topic),
                category=draft.category, question=_collapse(draft.question),
                paper_anchor=EvidenceAnchor(chunk_id=chunk.chunk_id, page=chunk.page, text=chunk.content,
                                            quote=quote, rects=_quote_rects(chunk, quote)),
            ))
        return accepted


def summarize(items: list[ConsistencyItem]) -> ConsistencySummary:
    """Counts only; the report makes no claim beyond what each investigation found."""
    summary = ConsistencySummary(checkpoints=len(items))
    for item in items:
        if item.status == ConsistencyItemStatus.NOT_CHECKED:
            summary.not_checked += 1
        elif item.status == ConsistencyItemStatus.FAILED or item.answer is None:
            summary.failed += 1
        else:
            summary.checked += 1
            if item.answer.status != AnswerStatus.ANSWERED or not item.answer.findings:
                summary.unresolved += 1
                continue
            for finding in item.answer.findings:
                if finding.verdict == FindingVerdict.CONSISTENT:
                    summary.consistent += 1
                elif finding.verdict == FindingVerdict.INCONSISTENT:
                    summary.inconsistent += 1
                elif finding.verdict == FindingVerdict.PARTIAL:
                    summary.partial += 1
                else:
                    summary.not_located += 1
    return summary
