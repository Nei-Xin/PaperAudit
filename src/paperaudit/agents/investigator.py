"""Four-node, bounded LangGraph investigation; no persistent checkpoint replay."""

from hashlib import sha256
import json
from time import monotonic
from typing import TypedDict

from langgraph.graph import END, START, StateGraph
from openai import APIError

from paperaudit.audit_rules import calibrate_judgment, validate_judgment_references
from paperaudit.citation_review import review_citations
from paperaudit.hy3_client import Hy3Client, Hy3ResponseError
from paperaudit.models import AutoLabel, ClaimAudit, ClaimJudgment, ParsedPaper, Severity
from paperaudit.request_budget import BudgetExceeded, RequestBudget, use_request_budget

from .models import InvestigationAction, InvestigationStep, InvestigationTrace, STOP_LABELS
from .tools import append_evidence, execute_tool


class InvestigationState(TypedDict):
    audit: ClaimAudit
    steps: list[InvestigationStep]
    action: InvestigationAction | None
    missing_aspects: list[str]
    stop_reason: str


class EvidenceInvestigator:
    MAX_ROUNDS = 2
    MAX_CANDIDATES = 24
    MAX_CHARS = 18_000

    def __init__(self, client: Hy3Client, paper: ParsedPaper, model: str,
                 *, budget: RequestBudget | None = None):
        self.client, self.paper, self.model = client, paper, model
        self.budget = budget or RequestBudget()
        builder = StateGraph(InvestigationState)
        for name in ("plan", "retrieve", "assess", "finish"):
            builder.add_node(name, getattr(self, f"_{name}"))
        builder.add_edge(START, "plan")
        for name, next_node in (("plan", "retrieve"), ("retrieve", "assess"), ("assess", "plan")):
            builder.add_conditional_edges(
                name, lambda state, target=next_node: "finish" if state["stop_reason"] else target,
                {"finish": "finish", next_node: next_node},
            )
        builder.add_edge("finish", END)
        self.graph = builder.compile()

    def run(self, audit: ClaimAudit, trigger: str) -> ClaimAudit:
        initial = audit.judgment
        missing = audit.citation_review.missing_aspects if audit.citation_review else []
        with use_request_budget(self.budget):
            state = self.graph.invoke({
                "audit": audit, "steps": [], "action": None,
                "missing_aspects": missing, "stop_reason": "",
            }, config={"recursion_limit": 12})
        fingerprint = json.dumps([
            (chunk.chunk_id, chunk.page, chunk.content) for chunk in self.paper.chunks
        ], ensure_ascii=False).encode("utf-8")
        trace = InvestigationTrace(
            model=self.model, paper_hash=sha256(fingerprint).hexdigest(), trigger=trigger,
            max_rounds=self.MAX_ROUNDS, max_requests=self.budget.max_requests,
            max_seconds=self.budget.max_seconds, max_candidates=self.MAX_CANDIDATES,
            max_chars=self.MAX_CHARS, steps=state["steps"], stop_reason=state["stop_reason"],
            missing_aspects=state["missing_aspects"], requests=self.budget.requests,
            tokens=self.budget.tokens, elapsed_seconds=round(monotonic() - self.budget.started, 3),
        )
        return state["audit"].model_copy(update={
            "investigation": trace, "judgment_before_investigation": initial,
        })

    def _plan(self, state: InvestigationState):
        if len(state["steps"]) >= self.MAX_ROUNDS:
            return {"stop_reason": "round_limit"}
        candidates = state["audit"].candidates
        if (len(candidates) >= self.MAX_CANDIDATES
                or sum(len(c.text) for c in candidates) >= self.MAX_CHARS):
            return {"stop_reason": "evidence_budget"}
        try:
            self.budget.check()
            action = self.client.plan_investigation(
                state["audit"].claim, candidates, state["audit"].judgment,
                state["steps"], self.paper.page_count, state["missing_aspects"],
            )
        except BudgetExceeded as exc:
            return {"stop_reason": exc.reason}
        except Hy3ResponseError:
            return {"stop_reason": "invalid_model_response"}
        except APIError:
            return {"stop_reason": "provider_error"}
        update = {"action": action, "missing_aspects": action.missing_aspects}
        if action.tool == "finish":
            return {**update, "stop_reason": "model_finished", "steps": [
                *state["steps"], InvestigationStep(action=action, outcome="调查结束。"),
            ]}

        def key(item):
            return (item.tool, " ".join((item.query or "").casefold().split()),
                    item.page, item.chunk_id)

        if key(action) in {key(step.action) for step in state["steps"]}:
            return {**update, "stop_reason": "repeated_action", "steps": [
                *state["steps"], InvestigationStep(action=action, outcome="重复动作未执行。"),
            ]}
        return update

    def _retrieve(self, state: InvestigationState):
        audit, action = state["audit"], state["action"]
        try:
            self.budget.check()
            found = execute_tool(action, self.paper, audit.claim, audit.candidates)
        except BudgetExceeded as exc:
            return {"stop_reason": exc.reason}
        except ValueError:
            return {"stop_reason": "invalid_tool_arguments", "steps": [
                *state["steps"], InvestigationStep(action=action, outcome="工具参数不在当前论文范围内。"),
            ]}
        candidates, added = append_evidence(
            audit.claim.claim_id, audit.candidates, found,
            max_candidates=self.MAX_CANDIDATES, max_chars=self.MAX_CHARS,
        )
        return {
            "audit": audit.model_copy(update={"candidates": candidates}),
            "steps": [*state["steps"], InvestigationStep(
                action=action, added_evidence_ids=added, outcome=f"新增 {len(added)} 个完整原文片段。",
            )],
            "stop_reason": "" if added else "no_new_evidence",
        }

    def _assess(self, state: InvestigationState):
        audit = state["audit"]
        try:
            self.budget.check()
            batch = self.client.adjudicate_claim(audit.claim, audit.candidates, self.paper.page_count)
            if len(batch.judgments) != 1 or batch.judgments[0].claim_id != audit.claim.claim_id:
                return {"stop_reason": "invalid_model_response"}
            proposal = batch.judgments[0]
            requires_evidence = proposal.label in {
                AutoLabel.SUPPORTED, AutoLabel.CONTRADICTED, AutoLabel.PARTIALLY_SUPPORTED,
            }
            if (not set(proposal.evidence_ids) <= {c.evidence_id for c in audit.candidates}
                    or (requires_evidence and not proposal.evidence_ids)):
                return {"stop_reason": "invalid_model_response"}
            proposal = validate_judgment_references(calibrate_judgment(proposal), audit.candidates)
            judgment = proposal
            review = before_repair = before_review = None
            if proposal.label in {AutoLabel.SUPPORTED, AutoLabel.CONTRADICTED}:
                before_review = proposal
                judgment, review, before_repair = review_citations(
                    self.client, audit.claim, audit.candidates, proposal,
                )
                if (review is None or review.claim_id != audit.claim.claim_id
                        or review.reviewed_label != proposal.label.value):
                    return {"stop_reason": "invalid_model_response"}
                if (judgment.label == AutoLabel.ABSTAIN and review.complete
                        and not review.missing_aspects and not review.suggestion_missing_aspects):
                    return {"stop_reason": "invalid_model_response"}
        except BudgetExceeded as exc:
            return {"stop_reason": exc.reason}
        except Hy3ResponseError:
            return {"stop_reason": "invalid_model_response"}
        except APIError:
            return {"stop_reason": "provider_error"}
        resolved = judgment.label in {AutoLabel.SUPPORTED, AutoLabel.CONTRADICTED}
        steps = [*state["steps"][:-1], state["steps"][-1].model_copy(update={
            "judgment_label": judgment.label.value,
        })]
        return {
            "audit": audit.model_copy(update={
                "judgment": judgment, "citation_review": review,
                "citation_review_before_repair": before_repair,
                "judgment_before_citation_review": before_review,
            }),
            "steps": steps,
            "missing_aspects": [] if resolved else (
                review.missing_aspects + review.suggestion_missing_aspects
                if review is not None else state["missing_aspects"]
            ),
            "stop_reason": "verified" if resolved else "",
        }

    def _finish(self, state: InvestigationState):
        if state["stop_reason"] == "verified":
            return {}
        # An exhausted investigation never establishes absence in the full paper.
        missing = state["missing_aspects"] or ["尚未找到能够完整核验该论断的原文依据"]
        judgment = ClaimJudgment(
            claim_id=state["audit"].claim.claim_id, label=AutoLabel.ABSTAIN,
            severity=Severity.NONE,
            explanation=f"深度核验结束：{STOP_LABELS[state['stop_reason']]}。"
                        f"待核对：{'；'.join(missing)}。请结合论文原文人工复核。",
        )
        return {"audit": state["audit"].model_copy(update={"judgment": judgment}),
                "missing_aspects": missing}
