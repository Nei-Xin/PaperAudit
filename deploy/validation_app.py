"""Validation-only API entry point with bounded calls and content-free usage records."""
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from threading import Lock
from time import monotonic

from paperaudit.api.main import create_app
from paperaudit.request_budget import RequestBudget, use_request_budget
from paperaudit.service import AuditService
from paperaudit.code_service import CodeLearningService

_usage_lock = Lock()


@contextmanager
def meter(operation: str):
    # Enough for generation/QA plus JSON repair, without unbounded paid retries.
    budget = RequestBudget(max_requests=18 if operation == "lecture" else 12, max_seconds=600)
    started = monotonic()
    succeeded = False
    try:
        with use_request_budget(budget):
            yield budget
        succeeded = True
    finally:
        record = dict(operation=operation, succeeded=succeeded,
                      requests=budget.requests, total_tokens=budget.tokens,
                      seconds=round(monotonic() - started, 2),
                      completed_at=datetime.now(timezone.utc).isoformat())
        path = Path(os.environ["PAPERAUDIT_VALIDATION_USAGE_FILE"])
        with _usage_lock:
            with path.open("a", encoding="utf-8") as output:
                output.write(json.dumps(record) + "\n")
            path.chmod(0o600)


class ValidationService(AuditService):
    def generate_learning_report(self, paper):
        with meter("lecture"):
            return super().generate_learning_report(paper)

    def audit(self, paper, report_text, scope, **kwargs):
        with meter("audit"):
            return super().audit(paper, report_text, scope, **kwargs)

    def answer_question(self, paper, question, history=(), **kwargs):
        with meter("qa"):
            return super().answer_question(paper, question, history, **kwargs)

    def generate_peer_review(self, paper, **kwargs):
        with meter("review"):
            return super().generate_peer_review(paper, **kwargs)

    def compare_related_work(self, paper, references):
        with meter("related_work"):
            return super().compare_related_work(paper, references)


class ValidationCodeService(CodeLearningService):
    def answer(self, paper, codebase, question, **kwargs):
        with meter("code_qa") as budget:
            answer = super().answer(paper, codebase, question, **kwargs)
            if answer.investigation is not None:
                # An investigation runs under its own request budget; record what it used here too.
                budget.requests += answer.investigation.requests
                budget.tokens += answer.investigation.tokens
            return answer

    def audit_consistency(self, paper, codebase, **kwargs):
        with meter("consistency") as budget:
            report = super().audit_consistency(paper, codebase, **kwargs)
            # Investigations run in worker threads under their own budgets.
            budget.requests, budget.tokens = report.requests, report.tokens
            return report

    def plan_consistency(self, paper, codebase, **kwargs):
        with meter("consistency_plan") as budget:
            plan = super().plan_consistency(paper, codebase, **kwargs)
            budget.requests, budget.tokens = plan.requests, plan.tokens
            return plan

    def check_consistency(self, paper, codebase, checkpoints, plan, **kwargs):
        with meter("consistency_check") as budget:
            report = super().check_consistency(paper, codebase, checkpoints, plan, **kwargs)
            # The plan's own usage was recorded when it was made.
            budget.requests, budget.tokens = report.requests - plan.requests, report.tokens - plan.tokens
            return report


app = create_app(service_factory=ValidationService, code_service_factory=ValidationCodeService)
