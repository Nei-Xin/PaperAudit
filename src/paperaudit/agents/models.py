"""Stored actions and traces; importing these does not load LangGraph."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class InvestigationAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool: Literal["search_paper", "read_page", "expand_context", "finish"]
    query: str | None = Field(default=None, max_length=500)
    page: int | None = Field(default=None, ge=1, strict=True)
    chunk_id: str | None = Field(default=None, max_length=200)
    missing_aspects: list[str] = Field(default_factory=list, max_length=8)
    reason: str = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def validate_arguments(self):
        required = {"search_paper": "query", "read_page": "page",
                    "expand_context": "chunk_id"}.get(self.tool)
        for field in ("query", "page", "chunk_id"):
            value = getattr(self, field)
            if field == required:
                if value is None or (isinstance(value, str) and not value.strip()):
                    raise ValueError(f"{self.tool} requires {field}")
            elif value is not None:
                raise ValueError(f"{self.tool} does not accept {field}")
        return self


class InvestigationStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: InvestigationAction
    added_evidence_ids: list[str] = Field(default_factory=list)
    outcome: str
    judgment_label: str | None = None


StopReason = Literal[
    "verified", "model_finished", "round_limit", "request_limit", "time_limit",
    "evidence_budget", "no_new_evidence", "repeated_action", "invalid_tool_arguments",
    "invalid_model_response", "provider_error",
]


class InvestigationTrace(BaseModel):
    model_config = ConfigDict(extra="forbid")

    strategy_version: str = "langgraph-evidence-v4"
    model: str
    paper_hash: str
    trigger: str
    max_rounds: int = 2
    max_requests: int = 12
    max_seconds: float = 180
    max_candidates: int = 24
    max_chars: int = 18_000
    steps: list[InvestigationStep] = Field(default_factory=list)
    stop_reason: StopReason
    missing_aspects: list[str] = Field(default_factory=list)
    requests: int = 0
    tokens: int = 0
    elapsed_seconds: float = 0
    retained_partial: bool = False


STOP_LABELS = {
    "verified": "新判断已通过引用校验", "model_finished": "未发现可继续执行的补查",
    "round_limit": "达到两轮补查上限", "request_limit": "达到模型请求上限",
    "time_limit": "达到调查时间上限", "evidence_budget": "达到候选原文预算",
    "no_new_evidence": "未获得可加入的新证据", "repeated_action": "重复动作已停止",
    "invalid_tool_arguments": "工具参数无效", "invalid_model_response": "模型响应无效",
    "provider_error": "模型服务请求失败",
}

TOOL_LABELS = {
    "search_paper": "全文检索", "read_page": "读取指定页",
    "expand_context": "补读相邻上下文", "finish": "结束调查",
}


CodeStopReason = Literal[
    "answered", "citations_rejected", "verification_pending", "request_limit", "time_limit",
    "invalid_model_response", "provider_error",
]


class CodeInvestigationStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool: str
    arguments: dict[str, object] = Field(default_factory=dict)
    outcome: str
    ok: bool = True


class CodeInvestigationTrace(BaseModel):
    """What the paper-code investigator did; stored with the answer it produced."""

    model_config = ConfigDict(extra="forbid")

    strategy_version: str = "code-investigation-v1"
    model: str
    max_requests: int
    max_seconds: float
    max_tool_calls: int
    steps: list[CodeInvestigationStep] = Field(default_factory=list)
    stop_reason: CodeStopReason
    # What the first submission failed on, when the single repair was used.
    first_rejections: list[str] = Field(default_factory=list)
    # What was still removed after that repair.
    rejected_citations: list[str] = Field(default_factory=list)
    requests: int = 0
    tokens: int = 0
    elapsed_seconds: float = 0
    # True when the investigation did not produce the answer and the fixed
    # single-retrieval pipeline answered instead.
    fallback: bool = False
    repo_map_used: bool = False
