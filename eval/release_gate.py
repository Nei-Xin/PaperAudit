"""PaperAudit v1 release gate.

The gate validates immutable release artifacts and the frozen evaluation snapshot.
It never calls the API and never changes audit rules.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EVAL_DIR = ROOT / "eval"
DEFAULT_ACTUAL = EVAL_DIR / "results_final_holdout_actual" / "metrics.json"


def _display_command(args: list[str]) -> str:
    """Render a reproducible command without leaking a local checkout path."""
    displayed: list[str] = []
    for index, arg in enumerate(args):
        path = Path(arg)
        if path.is_absolute():
            try:
                arg = path.resolve().relative_to(ROOT.resolve()).as_posix()
            except ValueError:
                arg = "python" if index == 0 else path.name
        displayed.append(arg)
    return " ".join(displayed)


def _run(name: str, args: list[str], env: dict[str, str]) -> dict[str, Any]:
    completed = subprocess.run(
        args,
        cwd=ROOT,
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )
    return {
        "name": name,
        "command": _display_command(args),
        "returncode": completed.returncode,
        "passed": completed.returncode == 0,
        "stdout_tail": completed.stdout[-2000:],
        "stderr_tail": completed.stderr[-2000:],
    }


def _check_actual_snapshot(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"passed": False, "reason": f"missing snapshot: {path}"}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        metrics = payload["metrics"]
        checks = {
            "sample_count": metrics.get("sample_count") == 48,
            "retrieval_hit_rate": float(metrics.get("retrieval_hit_rate", 0)) >= 0.85,
            "label_accuracy": float(metrics.get("label_accuracy", 0)) >= 0.80,
            "error_type_accuracy": float(metrics.get("error_type_accuracy", 0)) >= 0.75,
            "severity_accuracy": float(metrics.get("severity_accuracy", 0)) >= 0.80,
            "abstain_rate": float(metrics.get("abstain_rate", 1)) == 0.0,
            "dry_run_false": payload.get("config", {}).get("dry_run") is False,
        }
        return {"passed": all(checks.values()), "checks": checks, "metrics": metrics}
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        return {"passed": False, "reason": f"invalid snapshot: {exc}"}


def run_gate(actual_snapshot: Path = DEFAULT_ACTUAL) -> dict[str, Any]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTHONIOENCODING"] = "utf-8"
    python = sys.executable
    steps = [
        _run("pytest", [python, "-m", "pytest", "-q"], env),
        _run("holdout_isolation", [python, "eval/check_holdout_isolation.py"], env),
        _run(
            "offline_regression",
            [python, "eval/run_regression.py", "--output-dir", "eval/results_regression_v1_gate", "--top-k", "5"],
            env,
        ),
        _run("app_compile", [python, "-m", "py_compile", "app.py"], env),
        _run(
            "diagnostics_compile",
            [python, "-m", "py_compile", "eval/aggregate_production_diagnostics.py", "eval/e2e_smoke.py"],
            env,
        ),
    ]
    snapshot = _check_actual_snapshot(actual_snapshot)
    result = {
        "release": "PaperAudit v1",
        "passed": all(step["passed"] for step in steps) and bool(snapshot["passed"]),
        "steps": steps,
        "final_holdout_snapshot": snapshot,
        "policy": "规则冻结；最终留出集只作发布快照校验，不用于调参",
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="运行 PaperAudit v1 发布门禁。")
    parser.add_argument("--actual-snapshot", type=Path, default=DEFAULT_ACTUAL)
    parser.add_argument("--output", type=Path, default=EVAL_DIR / "release_gate_v1.json")
    args = parser.parse_args()
    result = run_gate(args.actual_snapshot)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
