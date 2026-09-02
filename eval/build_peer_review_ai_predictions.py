"""Materialize flat AI annotation predictions for the stage-2 evaluator."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


FIELDS = ("category", "severity", "confidence", "evidence_valid", "actionability")


def _load(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="生成阶段 2 使用的 AI 标注 predictions")
    parser.add_argument("--dev", type=Path, default=Path(__file__).with_name("peer_review_regression_dev.jsonl"))
    parser.add_argument("--holdout", type=Path, default=Path(__file__).with_name("peer_review_regression_holdout.jsonl"))
    parser.add_argument("--ai", type=Path, default=Path(__file__).with_name("peer_review_holdout_ai_annotations.jsonl"))
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).with_name("predictions"))
    args = parser.parse_args()
    ai = {str(row["sample_id"]): row["ai_annotation"] for row in _load(args.ai)}
    outputs: dict[str, list[dict[str, object]]] = {}
    for name, source in (("dev", args.dev), ("holdout", args.holdout)):
        predictions: list[dict[str, object]] = []
        for row in _load(source):
            values = ai.get(str(row["sample_id"])) or {field: row.get(field) for field in FIELDS}
            predictions.append({
                "sample_id": row["sample_id"],
                **values,
                "decision": row.get("gold_decision", "BORDERLINE"),
                "prediction_source": "AI_annotation_pass",
                "model_version": "codex-ai-annotation-v1",
                "prompt_version": "peer-review-annotation-v1",
            })
        path = args.output_dir / f"codex-ai-annotation-v1-{name}.jsonl"
        _write(path, predictions)
        outputs[name] = predictions
    print(json.dumps({name: len(rows) for name, rows in outputs.items()}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
