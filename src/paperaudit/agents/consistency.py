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

from openai import APIError

from paperaudit.consistency_events import step_fields
from paperaudit.hy3_client import Hy3Client, Hy3ResponseError
from paperaudit.consistency_inputs import input_hashes, validate_plan_inputs
from paperaudit.models import (
    AnswerScope,
    AnswerStatus,
    ConsistencyCheckpoint,
    ConsistencyItem,
    ConsistencyItemStatus,
    ConsistencyPlan,
    ConsistencyReport,
    ConsistencySummary,
    EvidenceAnchor,
    FindingVerdict,
    ParsedCodebase,
    ParsedPaper,
)
from paperaudit.evidence import _quote_rects
from paperaudit.request_budget import BudgetExceeded, RequestBudget, use_request_budget

from .code_investigator import CodeInvestigator, _appears_in_order, _collapse, _fragments, _typeset
from .consistency_planner import ConsistencyPlanner

Progress = Callable[[str, float], None]

STOP_NOTES = {
    "request_limit": "调查达到模型请求上限，未得出结论。",
    "time_limit": "调查达到时间上限，未得出结论。",
    "invalid_model_response": "模型响应无效，未得出结论。",
    "provider_error": "模型服务请求失败，未得出结论。",
}


class ConsistencyOrchestrator:
    PER_ITEM_REQUESTS = 12
    PLAN_REQUESTS = 3  # One call plus the JSON repair, with a spare.

    def __init__(self, client: Hy3Client, model: str, *, max_checkpoints: int = 20,
                 max_requests: int = 160, concurrency: int = 4,
                 repo_map=None, enable_repo_map: bool = False, on_repo_map=None, on_event=None):
        self.client, self.model = client, model
        self.emit = on_event or (lambda **fields: None)
        self.repo_map, self.enable_repo_map, self.on_repo_map = repo_map, enable_repo_map, on_repo_map
        self.max_checkpoints, self.max_requests = max_checkpoints, max(1, max_requests)
        self.concurrency = max(1, concurrency)

    def run(self, paper: ParsedPaper, codebase: ParsedCodebase,
            progress: Progress | None = None, *, strategy: str = "one-shot") -> ConsistencyReport:
        """Plan and check in one go, taking the planner's first max_checkpoints points."""
        plan = self.plan(paper, codebase, progress, strategy=strategy)
        return self.execute(paper, codebase, plan.checkpoints[:self.max_checkpoints], plan, progress, reviewed=False)

    def plan(self, paper: ParsedPaper, codebase: ParsedCodebase, progress: Progress | None = None,
             *, strategy: str = "one-shot") -> ConsistencyPlan:
        """Propose checkpoints. Nothing is checked yet, so a person can review the plan first."""
        (progress or (lambda stage, value: None))("正在阅读论文并规划要核对的要点", 0.05)
        if strategy not in {"one-shot", "agent"}:
            raise ValueError("Unknown consistency planning strategy")
        self.emit(kind="planning_started", outcome="正在规划核对要点。")
        def planning_step(step):
            accepted = step.tool == "propose_checkpoint" and step.ok
            self.emit(kind="checkpoint_accepted" if accepted else "planning_step",
                      checkpoint_id=str(step.arguments["checkpoint_id"]) if accepted else None,
                      topic=str(step.arguments.get("topic", ""))[:160], **step_fields(step))
        if strategy == "agent":
            plan = ConsistencyPlanner(
                self.client, self.model, target=self.max_checkpoints,
                budget=RequestBudget(max_requests=min(12, self.max_requests), max_seconds=240),
                on_step=planning_step,
            ).run(paper, codebase)
            if not plan.checkpoints and plan.requests < self.max_requests:
                fallback = self._plan_in_one_call(paper, self.max_requests - plan.requests)
                plan = fallback.model_copy(update={
                    "fallback": True, "steps": plan.steps, "stop_reason": plan.stop_reason,
                    "requests": plan.requests + fallback.requests, "tokens": plan.tokens + fallback.tokens,
                    "proposed": plan.proposed + fallback.proposed,
                    "rejected": plan.rejected + fallback.rejected,
                    "elapsed_seconds": round(plan.elapsed_seconds + fallback.elapsed_seconds, 1),
                })
        else:
            plan = self._plan_in_one_call(paper, self.max_requests)
        if strategy == "one-shot" or plan.fallback:
            for checkpoint in plan.checkpoints:
                self.emit(kind="checkpoint_accepted", checkpoint_id=checkpoint.checkpoint_id,
                          topic=checkpoint.topic[:160], outcome="核对要点已接受。")
        self.emit(kind="planning_finished", outcome=f"规划得到 {len(plan.checkpoints)} 个有效要点。",
                  status=plan.stop_reason)
        return plan.model_copy(update={**input_hashes(paper, codebase),
                                       "target": self.max_checkpoints, "max_requests": self.max_requests})

    def _plan_in_one_call(self, paper: ParsedPaper, remaining: int) -> ConsistencyPlan:
        started = monotonic()
        budget = RequestBudget(max_requests=min(self.PLAN_REQUESTS, remaining), max_seconds=300)
        drafts, stop = [], "finished"
        with use_request_budget(budget):
            try:
                drafts = self.client.plan_consistency(paper.title, paper.chunks, self.max_checkpoints).checkpoints
            except BudgetExceeded as exc:
                stop = exc.reason
            except Hy3ResponseError:
                stop = "invalid_model_response"
            except APIError:
                stop = "provider_error"
        valid = self._accept(paper, drafts)
        return ConsistencyPlan(
            strategy="one-shot-v1", model=self.model, checkpoints=valid, proposed=len(drafts),
            rejected=len(drafts) - len(valid), stop_reason=stop,
            requests=budget.requests, tokens=budget.tokens, elapsed_seconds=round(monotonic() - started, 1),
        )

    def execute(self, paper: ParsedPaper, codebase: ParsedCodebase, checkpoints: list[ConsistencyCheckpoint],
                plan: ConsistencyPlan, progress: Progress | None = None, *, reviewed: bool = True) -> ConsistencyReport:
        """Investigate the chosen checkpoints in parallel under one request ceiling."""
        validate_plan_inputs(plan, paper, codebase)
        ceiling = min(self.max_requests, plan.max_requests)
        started = monotonic()
        notify = progress or (lambda stage, value: None)

        from .repo_mapper import build_repo_map, usable_map
        memory = None
        reused = False
        map_requests = map_tokens = 0
        if self.enable_repo_map and checkpoints:
            if usable_map(self.repo_map, codebase):
                memory, reused = self.repo_map, True
            elif ceiling - plan.requests >= self.PER_ITEM_REQUESTS + 4:
                notify("正在生成仓库地图", 0.12)
                memory = build_repo_map(self.client, codebase, self.model)
                map_requests, map_tokens = memory.requests, memory.tokens
                if memory.entries and self.on_repo_map:
                    self.on_repo_map(memory)

        state = Condition()
        spent, tokens, running, done = plan.requests + map_requests, plan.tokens + map_tokens, 0, 0
        results: list[ConsistencyItem | None] = [None] * len(checkpoints)

        for checkpoint in checkpoints:
            self.emit(kind="item_queued", checkpoint_id=checkpoint.checkpoint_id,
                      topic=checkpoint.topic[:160], status="queued", outcome="等待核对。")

        def finish_event(item):
            findings = item.answer.findings if item.answer else []
            self.emit(kind="item_finished", checkpoint_id=item.checkpoint.checkpoint_id,
                      status=item.status.value, topic=item.checkpoint.topic[:160],
                      outcome=(item.note or ("核对完成。" if findings else "证据不足，未得出判定。"))[:400],
                      verdicts=[f.verdict.value for f in findings],
                      pending_review=sum(f.needs_review for f in findings))

        def work(index: int) -> None:
            nonlocal spent, tokens, running, done
            checkpoint = checkpoints[index]
            anchor = checkpoint.paper_anchor
            with state:
                # Start only when the ceiling holds even if every running investigation
                # uses its full budget. Wait for others to report what they really used
                # before giving up on this item.
                while spent + (running + 1) * self.PER_ITEM_REQUESTS > ceiling and running:
                    state.wait()
                if spent + (running + 1) * self.PER_ITEM_REQUESTS > ceiling:
                    results[index] = ConsistencyItem(
                        checkpoint=checkpoint, status=ConsistencyItemStatus.NOT_CHECKED,
                        note="达到本次审计的模型请求上限，未核对该项。")
                    done += 1
                    finish_event(results[index])
                    return
                running += 1
            budget = RequestBudget(max_requests=self.PER_ITEM_REQUESTS, max_seconds=180)
            try:
                self.emit(kind="item_started", checkpoint_id=checkpoint.checkpoint_id,
                          topic=checkpoint.topic[:160], status="running", outcome="正在核对。")
                answer, trace = CodeInvestigator(
                    self.client, paper, codebase, self.model,
                    budget=budget, verify_findings=True, repo_map=memory,
                    on_step=lambda step: self.emit(
                        kind="verification" if step.tool == "verify_findings" else "tool_step",
                        checkpoint_id=checkpoint.checkpoint_id, **step_fields(step)),
                ).run(checkpoint.question, AnswerScope.JOINT,
                      selected_paper_chunk_ids=[anchor.chunk_id] if anchor else [],
                      selected_paper_text=anchor.quote if anchor else None)
                item = (ConsistencyItem(checkpoint=checkpoint, status=ConsistencyItemStatus.CHECKED, answer=answer)
                        if answer is not None else
                        ConsistencyItem(checkpoint=checkpoint, status=ConsistencyItemStatus.FAILED,
                                        note=STOP_NOTES.get(trace.stop_reason, "调查未得出结论。")))
            except Exception as exc:  # One failed investigation must not lose the others.
                item = ConsistencyItem(checkpoint=checkpoint, status=ConsistencyItemStatus.FAILED,
                                       note=f"调查出错（{type(exc).__name__}），未得出结论。")
            with state:
                results[index] = item
                spent += budget.requests
                tokens += budget.tokens
                running -= 1
                done += 1
                state.notify_all()
                finish_event(item)
                notify(f"正在逐项核对（{done}/{len(checkpoints)}）", 0.15 + 0.8 * done / len(checkpoints))

        if checkpoints:
            notify(f"正在逐项核对（0/{len(checkpoints)}）", 0.15)
            with ThreadPoolExecutor(max_workers=min(self.concurrency, len(checkpoints)),
                                    thread_name_prefix="paperaudit-consistency") as pool:
                list(pool.map(work, range(len(checkpoints))))

        items = [item for item in results if item is not None]
        return ConsistencyReport(
            strategy_version="consistency-orchestrator-v2-verified",
            model=self.model, paper_title=paper.title, codebase_name=codebase.name,
            items=items, summary=summarize(items), plan_id=plan.plan_id or None, planned=plan.proposed,
            plan_rejected=plan.rejected,
            plan_over_limit=0 if reviewed else max(0, len(plan.checkpoints) - len(checkpoints)),
            plan_unselected=max(0, len(plan.checkpoints) - sum(c.source == "planner" for c in checkpoints)) if reviewed else 0,
            max_checkpoints=self.max_checkpoints, max_requests=ceiling,
            concurrency=self.concurrency, plan_requests=plan.requests,
            repo_map=memory, repo_map_reused=reused, repo_map_requests=map_requests, repo_map_tokens=map_tokens,
            requests=spent, tokens=tokens,
            elapsed_seconds=round(plan.elapsed_seconds + monotonic() - started, 1),
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
                if finding.needs_review:
                    summary.pending_review += 1
                elif finding.verdict == FindingVerdict.CONSISTENT:
                    summary.consistent += 1
                elif finding.verdict == FindingVerdict.INCONSISTENT:
                    summary.inconsistent += 1
                elif finding.verdict == FindingVerdict.PARTIAL:
                    summary.partial += 1
                else:
                    summary.not_located += 1
    return summary
