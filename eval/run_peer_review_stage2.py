"""Evaluate real PaperAudit peer-review predictions on dev and paper-level holdout.

The command intentionally requires externally produced prediction JSONL files and
model/prompt metadata. It never falls back to the oracle dry-run used for schema
checks, so a successful report is evidence of a real offline evaluation run.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from peer_review_quality import _load_jsonl, evaluate


def _evaluate_split(gold_path: Path, prediction_path: Path) -> dict[str, object]:
    if not prediction_path.exists():
        raise FileNotFoundError(f"缺少真实模型 predictions：{prediction_path}")
    if "oracle" in prediction_path.name.lower() or "oracle" in str(prediction_path).lower():
        raise ValueError("阶段 2 不接受 oracle dry-run 作为真实模型结果")
    gold = _load_jsonl(gold_path, validate_schema=True)
    predictions = _load_jsonl(prediction_path)
    return evaluate(gold, predictions)


def main() -> int:
    parser = argparse.ArgumentParser(description="运行 PaperAudit 投稿评审阶段 2 真实模型离线评测")
    parser.add_argument("--dev-predictions", type=Path, required=True)
    parser.add_argument("--holdout-predictions", type=Path, required=True)
    parser.add_argument("--model-version", required=True)
    parser.add_argument("--prompt-version", required=True)
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("peer_review_stage2_report.json"))
    args = parser.parse_args()
    here = Path(__file__).parent
    dev_metrics = _evaluate_split(here / "peer_review_regression_dev.jsonl", args.dev_predictions)
    holdout_metrics = _evaluate_split(here / "peer_review_regression_holdout.jsonl", args.holdout_predictions)
    result = {
        "evaluation_version": "peer-review-stage2-v1",
        "model_version": args.model_version,
        "prompt_version": args.prompt_version,
        "run_at": datetime.now(timezone.utc).isoformat(),
        "gold_policy": "paper_level_holdout",
        "dev": dev_metrics,
        "holdout": holdout_metrics,
    }
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
