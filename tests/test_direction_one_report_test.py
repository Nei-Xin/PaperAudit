from __future__ import annotations

import csv
import json
from pathlib import Path

from eval.build_direction_one_report_test import build
from eval.run_report_discrimination import _pairwise_label_agreement, validate_dataset


def _wrapper(text: str, label: str) -> dict:
    return {
        "audit": {
            "audits": [
                {
                    "claim": {"text": text, "category": "method"},
                    "judgment": {"label": label},
                }
            ]
        }
    }


def test_build_direction_one_report_dataset(tmp_path: Path) -> None:
    manifest = build(tmp_path)
    reports = [
        json.loads(line)
        for line in (tmp_path / "report_index.jsonl").read_text(encoding="utf-8").splitlines()
    ]

    assert manifest["paper_count"] == 6
    assert manifest["report_count"] == 18
    assert manifest["claims_per_report"] == 10
    assert {row["tier"] for row in reports} == {"high", "medium", "low"}
    assert all((tmp_path / row["report_path"]).is_file() for row in reports)
    assert validate_dataset(tmp_path)["manifest"]["status"] == "prepared-not-run"

    with (tmp_path / "human_annotation_template.csv").open(
        newline="", encoding="utf-8-sig"
    ) as stream:
        blind_rows = list(csv.DictReader(stream))
    assert len(blind_rows) == 180
    assert all("tier" not in row for row in blind_rows)
    assert all(not row["label"] for row in blind_rows)


def test_report_tiers_keep_length_comparable(tmp_path: Path) -> None:
    result = build(tmp_path)

    for lengths in result["length_by_paper"].values():
        assert max(lengths.values()) / min(lengths.values()) <= 1.12


def test_pairwise_label_agreement_aligns_minor_rephrasing() -> None:
    left = _wrapper("该方法能够训练具有非凸目标函数的深度神经网络。", "SUPPORTED")
    right = _wrapper("该方法能训练非凸目标函数的深度神经网络。", "SUPPORTED")

    assert _pairwise_label_agreement(left, right) == 1.0
