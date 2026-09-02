from __future__ import annotations

import json
from pathlib import Path

from eval.peer_review_quality_gate import run_gate


def _write(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def _rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for index in range(4):
        rows.append({
            "sample_id": f"p{index}",
            "paper_title": f"Paper {index}",
            "arxiv_url": f"https://arxiv.org/abs/1234.{index:05d}",
            "openreview_url": f"https://openreview.net/forum?id={index}",
            "meeting": "NeurIPS",
            "year": 2025,
            "source_note_id": f"note{index}",
            "source_note_url": f"https://openreview.net/forum?id={index}&noteId=note{index}",
            "category": "evaluation",
            "severity": "P1",
            "confidence": 4,
            "evidence_valid": True,
            "actionability": True,
            "gold_decision": "BORDERLINE",
            "gold_score": 5.0,
            "split": "holdout" if index == 3 else "dev",
        })
    return rows


def test_quality_gate_checks_dataset_and_metrics(tmp_path: Path) -> None:
    gold_path = tmp_path / "gold.jsonl"
    _write(gold_path, _rows())
    result = run_gate(gold_path, min_samples=4, min_papers=4)
    assert result["dataset"]["passed"] is True
    assert result["split"]["passed"] is True
    assert result["passed"] is True


def test_quality_gate_rejects_paper_split_overlap(tmp_path: Path) -> None:
    rows = _rows()
    rows[3]["openreview_url"] = rows[0]["openreview_url"]
    gold_path = tmp_path / "gold.jsonl"
    _write(gold_path, rows)
    result = run_gate(gold_path, min_samples=4, min_papers=3)
    assert result["split"]["passed"] is False
    assert result["passed"] is False


def test_quality_gate_accepts_versioned_cc_by_archive_record(tmp_path: Path) -> None:
    rows = _rows()
    row = rows[0]
    row.pop("source_note_id")
    row.pop("source_note_url")
    row.update({
        "source_archive_url": "https://huggingface.co/datasets/example/reviews",
        "source_record_id": "AbTpJl7vN6#review-1",
        "source_archive_commit": "6ddf7468c69eb82995df5b8468fa367be438e3cf",
        "source_license": "CC-BY-4.0",
    })
    gold_path = tmp_path / "gold.jsonl"
    _write(gold_path, rows)
    result = run_gate(gold_path, min_samples=4, min_papers=4)
    assert result["dataset"]["passed"] is True
    assert result["passed"] is True
