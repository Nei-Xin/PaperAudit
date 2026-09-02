"""Aggregate non-sensitive metrics from saved PaperAudit audit history."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


def _audit_row(project_dir: Path, audit_path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(audit_path.read_text(encoding="utf-8"))
        metadata = payload["metadata"]
        run = payload["run"]
        judgments = [item.get("judgment", {}) for item in run.get("audits", [])]
        labels = Counter(str(item.get("label", "UNKNOWN")) for item in judgments)
        errors = Counter(
            str(item.get("claim_error_type"))
            for item in judgments
            if item.get("claim_error_type")
        )
        severities = Counter(str(item.get("severity", "unknown")) for item in judgments)
        paper_path = project_dir / "paper.pdf"
        paper_hash = hashlib.sha256(paper_path.read_bytes()).hexdigest() if paper_path.is_file() else None
        summary = run.get("summary", {})
        return {
            "project_id": str(metadata["project_id"]),
            "audit_id": str(metadata["audit_id"]),
            "created_at": metadata.get("created_at"),
            "paper_hash": paper_hash,
            "paper_title": run.get("paper_title"),
            "page_count": run.get("page_count"),
            "mode": run.get("mode"),
            "source_type": metadata.get("source_type"),
            "grade": metadata.get("grade"),
            "total_score": metadata.get("total_score"),
            "audit_coverage": summary.get("audit_coverage"),
            "evidence_discovery_rate": summary.get("evidence_discovery_rate"),
            "claim_count": len(judgments),
            "labels": dict(labels),
            "error_types": dict(errors),
            "severities": dict(severities),
            "abstain_count": labels.get("ABSTAIN", 0),
            "api_model": metadata.get("model"),
            "reasoning_effort": metadata.get("reasoning_effort"),
            "retrieval_top_k": payload.get("runtime", {}).get("retrieval_top_k"),
            "judge_batch_size": payload.get("runtime", {}).get("judge_batch_size"),
        }
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None


def collect(storage_root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    root = storage_root.expanduser().resolve()
    rows: list[dict[str, Any]] = []
    for project_dir in sorted((root / "projects").glob("*")):
        audits_dir = project_dir / "audits"
        for audit_path in sorted(audits_dir.glob("audit-*.json")):
            row = _audit_row(project_dir, audit_path)
            if row is not None:
                rows.append(row)
    error_totals: Counter[str] = Counter()
    error_papers: dict[str, set[str]] = {}
    label_totals: Counter[str] = Counter()
    for row in rows:
        error_totals.update(row["error_types"])
        paper_key = str(row["paper_hash"] or row["project_id"])
        for error_type in row["error_types"]:
            error_papers.setdefault(error_type, set()).add(paper_key)
        label_totals.update(row["labels"])
    error_paper_counts = {
        error_type: len(papers) for error_type, papers in sorted(error_papers.items())
    }
    summary = {
        "storage_root": str(root),
        "audit_count": len(rows),
        "paper_count": len({row["paper_hash"] or row["project_id"] for row in rows}),
        "claim_count": sum(int(row["claim_count"]) for row in rows),
        "label_totals": dict(label_totals),
        "error_type_totals": dict(error_totals),
        "abstain_count": sum(int(row["abstain_count"]) for row in rows),
        "error_type_paper_counts": error_paper_counts,
        "repeated_error_types": sorted(
            error_type
            for error_type, count in error_totals.items()
            if count >= 5 and error_paper_counts.get(error_type, 0) >= 3
        ),
        "policy": "仅聚合自动运行指标；不包含报告正文、API Key 或规则调优逻辑",
    }
    return rows, summary


def main() -> None:
    parser = argparse.ArgumentParser(description="聚合已保存审计历史的生产诊断指标。")
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("eval/production_observations_v1"))
    args = parser.parse_args()
    rows, summary = collect(args.storage_root)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "audits.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8"
    )
    (args.output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
