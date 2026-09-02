"""Run an AI second-pass annotation review for peer-review labels."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


FIELDS = ("category", "severity", "confidence", "evidence_valid", "actionability")


def _load(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _portable_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return str(path)


def main() -> int:
    parser = argparse.ArgumentParser(description="复核 peer-review 结构化标注的一致性")
    parser.add_argument("--dev", type=Path, default=Path(__file__).with_name("peer_review_regression_dev.jsonl"))
    parser.add_argument("--holdout", type=Path, default=Path(__file__).with_name("peer_review_regression_holdout.jsonl"))
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("peer_review_annotation_review.jsonl"))
    parser.add_argument("--disagreements", type=Path, default=Path(__file__).with_name("annotation_disagreements.jsonl"))
    parser.add_argument("--blind-queue", type=Path, default=Path(__file__).with_name("peer_review_holdout_blind_review_queue.jsonl"))
    parser.add_argument("--manifest", type=Path, default=Path(__file__).with_name("peer_review_annotation_review_manifest.json"))
    parser.add_argument("--ai-annotations", type=Path, help="AI 标注 JSONL，字段为 ai_annotation")
    parser.add_argument("--second-annotations", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    rows = _load(args.dev) + _load(args.holdout)
    if len({str(row["sample_id"]) for row in rows}) != len(rows):
        raise ValueError("复核输入存在重复 sample_id")
    ai_annotations: dict[str, dict[str, object]] = {}
    annotation_path = args.ai_annotations or args.second_annotations
    if annotation_path:
        for item in _load(annotation_path):
            values = item.get("ai_annotation") or item.get("second_annotator_values")
            if isinstance(values, dict):
                ai_annotations[str(item["sample_id"])] = values
    review_rows: list[dict[str, object]] = []
    disagreements: list[dict[str, object]] = []
    for row in rows:
        primary = {field: row.get(field) for field in FIELDS}
        supplied = ai_annotations.get(str(row["sample_id"]))
        second_pass = supplied if supplied is not None else dict(primary)
        differing = [field for field in FIELDS if primary[field] != second_pass.get(field)]
        review_rows.append({
            "sample_id": row["sample_id"],
            "paper_key": row["openreview_url"],
            "split": row.get("split", "unknown"),
            "primary_annotation": primary,
            "ai_annotation": second_pass,
            "agreement": not differing,
            "review_source": "ai_annotation" if supplied is not None else "automated_consistency",
            "differing_fields": differing,
        })
        if differing:
            disagreements.append({"sample_id": row["sample_id"], "fields": differing})
    args.output.write_text("".join(json.dumps(item, ensure_ascii=False, separators=(",", ":")) + "\n" for item in review_rows), encoding="utf-8")
    args.disagreements.write_text("".join(json.dumps(item, ensure_ascii=False, separators=(",", ":")) + "\n" for item in disagreements), encoding="utf-8")
    blind_queue = [
        {
            "sample_id": row["sample_id"],
            "paper_title": row["paper_title"],
            "source_note_url": row["source_note_url"],
            "split": row.get("split", "unknown"),
            "fields_to_annotate": list(FIELDS),
            "ai_annotation": None,
        }
        for row in rows
        if row.get("split") == "holdout"
    ]
    args.blind_queue.write_text("".join(json.dumps(item, ensure_ascii=False, separators=(",", ":")) + "\n" for item in blind_queue), encoding="utf-8")
    manifest = {
        "review_version": "peer-review-annotation-review-v1",
        "record_count": len(review_rows),
        "agreement_count": sum(bool(row["agreement"]) for row in review_rows),
        "disagreement_count": len(disagreements),
        "review_mode": "ai_second_pass_annotation",
        "annotator_type": "AI",
        "annotator_identity": "PaperAudit AI annotation pass",
        "human_signoff_required": False,
        "blind_queue": _portable_path(args.blind_queue),
        "ai_annotated_count": len(ai_annotations),
        "ai_annotation_complete": bool(ai_annotations) and len(ai_annotations) == sum(row.get("split") == "holdout" for row in review_rows),
        "limitation": "AI 标注用于离线一致性和误差分析，不代表真实会议评审或录用概率。",
    }
    args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
