"""Per-investigation request limits isolated across concurrent claim workers."""

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from time import monotonic


class BudgetExceeded(RuntimeError):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


@dataclass
class RequestBudget:
    max_requests: int = 12
    max_seconds: float = 180
    requests: int = 0
    tokens: int = 0
    started: float = field(default_factory=monotonic)

    def check(self) -> float:
        remaining = self.max_seconds - (monotonic() - self.started)
        if remaining <= 0:
            raise BudgetExceeded("time_limit")
        if self.requests >= self.max_requests:
            raise BudgetExceeded("request_limit")
        return remaining

    def reserve(self) -> float:
        remaining = self.check()
        self.requests += 1
        return remaining


active_budget: ContextVar[RequestBudget | None] = ContextVar("investigation_budget", default=None)


@contextmanager
def use_request_budget(budget: RequestBudget):
    token = active_budget.set(budget)
    try:
        yield budget
    finally:
        active_budget.reset(token)
