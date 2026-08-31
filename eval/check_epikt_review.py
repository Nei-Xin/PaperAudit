"""Deterministic smoke check for the EpiKT review fixture.

This is a content regression check, not a claim that the review is a gold
standard. It catches accidental loss of the high-value findings and forbidden
legacy modules when prompts or rendering change.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


REQUIRED_GROUPS = {
    "episode_semantics": ("episode", "语义有效性"),
    "statistical_robustness": ("显著性", "随机种子", "置信区间"),
    "reproducibility": ("附录", "复现"),
    "long_sequence_scope": ("200", "长程"),
    "gate_interpretation": ("门控", "模型行为分析"),
}


def check(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    checks: dict[str, bool] = {
        "decision_borderline": "投稿建议：BORDERLINE" in text,
        "score_six": "综合评分：6.0 / 10" in text,
        "confidence_three": "评审置信度：3 / 5" in text,
        "no_author_rebuttal": "作者答辩" not in text and "给作者的问题" not in text,
    }
    for name, terms in REQUIRED_GROUPS.items():
        checks[name] = all(term.casefold() in text.casefold() for term in terms)
    return {"passed": all(checks.values()), "checks": checks, "path": str(path)}


def main() -> int:
    parser = argparse.ArgumentParser(description="检查 EpiKT 投稿评审内容回归")
    parser.add_argument("path", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = check(args.path)
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
