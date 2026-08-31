"""Compare repeated real-model review artifacts for decision stability."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


_ORDER = {"STRONG_REJECT": 0, "WEAK_REJECT": 1, "BORDERLINE": 2, "WEAK_ACCEPT": 3, "STRONG_ACCEPT": 4}


def check(paths: list[Path]) -> dict[str, object]:
    if len(paths) < 2:
        raise ValueError("至少需要两次真实评审结果")
    payloads = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
    reports = [payload["report"] for payload in payloads]
    decisions = [str(report["decision"]) for report in reports]
    scores = [float(report["overall_score"]) for report in reports]
    decision_span = max(_ORDER.get(value, -1) for value in decisions) - min(_ORDER.get(value, -1) for value in decisions)
    score_span = max(scores) - min(scores)
    result = {
        "passed": decision_span <= 1 and score_span <= 1.5,
        "decision_span_bands": decision_span,
        "score_span": score_span,
        "decisions": decisions,
        "scores": scores,
        "paths": [str(path) for path in paths],
        "policy": "同一论文重复运行允许最多一档建议漂移、评分最多 1.5 分；超过阈值需降低温度或复核提示词。",
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="检查真实投稿评审重复运行稳定性")
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = check(args.paths)
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
