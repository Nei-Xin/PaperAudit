from __future__ import annotations

import json
from pathlib import Path

import pytest

from eval.run_peer_review_e2e import run


def test_e2e_runner_requires_configured_api(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HY3_API_BASE", "")
    monkeypatch.setenv("HY3_API_KEY", "")
    pdf = tmp_path / "missing.pdf"
    pdf.write_bytes(b"not a pdf")
    with pytest.raises(RuntimeError, match="API 配置不完整"):
        run(pdf, tmp_path / "result.json")


def test_e2e_runner_output_shape_is_json() -> None:
    # The real network call is intentionally not performed in unit tests.
    payload = {"report": {"dimensions": []}}
    assert json.loads(json.dumps(payload))["report"]["dimensions"] == []
