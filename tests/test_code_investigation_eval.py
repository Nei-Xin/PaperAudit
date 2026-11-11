"""The published evaluation's case files and scoring rules stay internally consistent."""

from __future__ import annotations

from hashlib import sha256
import io
import json
from pathlib import Path
import zipfile

import pytest

from eval.code_investigation.run import build_archive
from eval.code_investigation.score import predict

ROOT = Path(__file__).resolve().parents[1] / "eval" / "code_investigation"
CASE_FILES = ["cases.json", "cases_holdout.json"]


@pytest.mark.parametrize("name", CASE_FILES)
def test_case_files_are_well_formed(name):
    cases = json.loads((ROOT / name).read_text())
    ids = [item["id"] for item in cases["items"]]
    assert len(ids) == len(set(ids))
    for item in cases["items"]:
        assert item["paper"] in cases["papers"]
        assert item["expected"] in {"CONSISTENT", "INCONSISTENT", "NOT_LOCATED"}
        assert item["keywords"] and item["question"].endswith("？")
        if item["mutation"]:
            # A controlled edit always turns a consistent question into an inconsistent one.
            assert item["mutation"] in cases["mutations"] and item["expected"] == "INCONSISTENT"
            original = next(other for other in cases["items"] if other["id"] == item["id"].removesuffix("x"))
            assert original["expected"] == "CONSISTENT" and original["question"] == item["question"]
        else:
            assert bool(item["gold_paths"]) == (item["expected"] != "NOT_LOCATED")
    assert {item["mutation"] for item in cases["items"]} - {None} == set(cases["mutations"])
    for edits in cases["mutations"].values():
        assert all(count >= 1 and old != new for _, old, new, count in edits)


def test_holdout_shares_nothing_with_development_and_is_frozen():
    dev, holdout = (json.loads((ROOT / name).read_text()) for name in CASE_FILES)
    for field in ("repo", "pdf_sha256", "zip_sha256"):
        assert not ({p[field] for p in dev["papers"].values()} & {p[field] for p in holdout["papers"].values()})
    assert not ({i["question"] for i in dev["items"]} & {i["question"] for i in holdout["items"]})
    freeze = json.loads((ROOT / "holdout_freeze.json").read_text())
    assert sha256((ROOT / "cases_holdout.json").read_bytes()).hexdigest() == freeze["cases_holdout_sha256"]


def archive(files: dict[str, str]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as target:
        for path, content in files.items():
            target.writestr(f"repo-abc123/{path}", content)
    return buffer.getvalue()


def test_controlled_edit_replaces_exactly_the_counted_occurrences():
    raw = archive({"train.py": "lr = 0.1\nwarmup = 0.1\n", "docs/data.bin": "x", "README.md": "lr 0.1"})
    built = zipfile.ZipFile(io.BytesIO(build_archive(raw, ["train.py", "README.md"], [["train.py", "lr = 0.1", "lr = 0.5", 1]])))
    assert sorted(built.namelist()) == ["repo/README.md", "repo/train.py"]
    assert built.read("repo/train.py").decode() == "lr = 0.5\nwarmup = 0.1\n"
    with pytest.raises(SystemExit, match="expected 1 occurrences"):
        build_archive(raw, None, [["train.py", "0.1", "0.5", 1]])


ITEM = {"keywords": ["dropout"], "expected": "INCONSISTENT"}


def agent(findings, status="ANSWERED", **extra):
    return {"mode": "agent", "status": status, "findings": findings, "trace": {"fallback": False}, **extra}


@pytest.mark.parametrize("row, predicted", [
    (agent([{"verdict": "INCONSISTENT", "text": "dropout 不同"}]), "INCONSISTENT"),
    (agent([{"verdict": "INCONSISTENT", "text": "dropout 不同"},
            {"verdict": "CONSISTENT", "text": "层数相同"}]), "INCONSISTENT"),          # off-topic finding ignored
    (agent([{"verdict": "INCONSISTENT", "text": "dropout 位置不同"},
            {"verdict": "CONSISTENT", "text": "dropout 概率相同"}]), "MIXED"),
    (agent([]), "ABSTAIN"),
    (agent([{"verdict": "CONSISTENT", "text": "dropout"}], status="INSUFFICIENT_EVIDENCE"), "ABSTAIN"),
    ({"mode": "agent", "error": "timeout"}, "ERROR"),
    ({"mode": "agent", "status": "ANSWERED", "findings": [], "relation": "MISMATCH",
      "trace": {"fallback": True}}, "INCONSISTENT"),                                  # answered by the fallback
    ({"mode": "fixed", "status": "ANSWERED", "relation": "CONFIGURES"}, "CONSISTENT"),
    ({"mode": "fixed", "status": "ANSWERED", "relation": "PARTIAL_MATCH"}, "PARTIAL"),
    ({"mode": "fixed", "status": "ANSWERED", "relation": None}, "ABSTAIN"),
])
def test_both_pipelines_are_scored_on_one_scale(row, predicted):
    assert predict(row, ITEM) == predicted
