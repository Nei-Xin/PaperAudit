"""Bind human-reviewed plans to the exact parsed inputs they describe."""
from hashlib import sha256
import json

from paperaudit.models import ConsistencyPlan, ParsedCodebase, ParsedPaper


def input_hashes(paper: ParsedPaper, codebase: ParsedCodebase) -> dict[str, str]:
    def digest(value):
        return sha256(json.dumps(value.model_dump(mode="json"), sort_keys=True,
                                 ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
    return {"paper_hash": digest(paper), "code_hash": digest(codebase)}


def validate_plan_inputs(plan: ConsistencyPlan, paper: ParsedPaper, codebase: ParsedCodebase) -> None:
    hashes = input_hashes(paper, codebase)
    if plan.paper_hash != hashes["paper_hash"] or plan.code_hash != hashes["code_hash"]:
        raise ValueError("论文或代码已变化，或旧规划缺少版本记录，请重新生成规划。")
