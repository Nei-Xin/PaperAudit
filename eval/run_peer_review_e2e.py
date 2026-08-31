"""Run one real PaperAudit peer-review generation against a local PDF.

The command sends the selected PDF text to the configured Hy3 endpoint, then
persists only the structured report and non-secret runtime metadata. It is
intended for stage-9 smoke/regression runs and never uploads a directory.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from paperaudit.config import Settings
from paperaudit.pdf_parser import parse_pdf
from paperaudit.service import AuditService


def run(pdf_path: Path, output: Path) -> dict[str, object]:
    settings = Settings.from_env()
    if not settings.is_configured:
        raise RuntimeError("API 配置不完整，无法执行真实评审。")
    pdf_bytes = pdf_path.read_bytes()
    paper = parse_pdf(pdf_bytes)
    started = time.perf_counter()
    report = AuditService(settings).generate_peer_review(paper)
    elapsed = round(time.perf_counter() - started, 3)
    payload = {
        "evaluation_version": "peer-review-stage9-e2e-v1",
        "pdf": str(pdf_path.resolve()),
        "paper_title": paper.title,
        "page_count": paper.page_count,
        "chunk_count": len(paper.chunks),
        "model": settings.model,
        "reasoning_effort": settings.reasoning_effort,
        "prompt_version": report.prompt_version,
        "rubric_version": report.rubric_version,
        "elapsed_seconds": elapsed,
        "report": report.model_dump(mode="json"),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="执行一次真实模型投稿评审端到端冒烟")
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.pdf, args.output)
    report = result["report"]
    print(json.dumps({
        "passed": bool(report.get("dimensions")),
        "paper_title": result["paper_title"],
        "decision": report.get("decision"),
        "overall_score": report.get("overall_score"),
        "concern_count": len(report.get("major_concerns", [])) + len(report.get("minor_concerns", [])),
        "parse_warnings": len(report.get("parse_warnings", [])),
        "output": str(args.output.resolve()),
    }, ensure_ascii=False, indent=2))
    return 0 if report.get("dimensions") else 1


if __name__ == "__main__":
    raise SystemExit(main())
