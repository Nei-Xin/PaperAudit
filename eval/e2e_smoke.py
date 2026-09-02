"""Run a small real-API end-to-end smoke test outside all evaluation papers."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

from paperaudit.config import Settings
from paperaudit.models import ClaimCategory
from paperaudit.pdf_parser import parse_pdf
from paperaudit.service import AuditService
from paperaudit.storage import ProjectStore


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PDF = ROOT / "tmp" / "release_smoke" / "mamba.pdf"
DEFAULT_OUTPUT = ROOT / "tmp" / "release_smoke" / "smoke_result.json"


def run_smoke(pdf_path: Path, output_path: Path, storage_path: Path) -> dict[str, object]:
    pdf_path = pdf_path.resolve()
    output_path = output_path.resolve()
    storage_path = storage_path.resolve()
    pdf_bytes = pdf_path.read_bytes()
    paper = parse_pdf(pdf_bytes)
    if paper.page_count < 1 or not paper.chunks:
        raise RuntimeError("PDF 解析未产生有效页面或 chunk。")
    report = (
        "The paper proposes a selective state space model for sequence modeling "
        "and evaluates it on language modeling tasks."
    )
    settings = Settings.from_env()
    if not settings.is_configured:
        raise RuntimeError("API 配置不完整，无法执行真实 API 冒烟测试。")
    service = AuditService(settings)
    run = service.audit(
        paper,
        report,
        [ClaimCategory.CONTRIBUTION, ClaimCategory.METHOD, ClaimCategory.RESULTS],
        mode="release_smoke",
    )
    if not run.audits:
        raise RuntimeError("真实 API 审计未生成任何原子论断。")

    if storage_path.exists():
        shutil.rmtree(storage_path)
    store = ProjectStore(storage_path)
    metadata = store.save_paper_project(pdf_bytes, pdf_path.name, paper)
    audit_metadata = store.save_audit_run(
        metadata.project_id,
        run,
        source_type="uploaded_report",
        source_label="v1 release smoke test",
        model=settings.model,
        reasoning_effort=settings.reasoning_effort,
        retrieval_top_k=settings.retrieval_top_k,
        judge_batch_size=settings.judge_batch_size,
    )
    loaded_metadata, loaded_run = store.load_audit_run(metadata.project_id, audit_metadata.audit_id)
    if len(loaded_run.audits) != len(run.audits):
        raise RuntimeError("持久化后审计条数不一致。")
    result = {
        "passed": True,
        "paper_title": paper.title,
        "page_count": paper.page_count,
        "chunk_count": len(paper.chunks),
        "pdf_sha256": hashlib.sha256(pdf_bytes).hexdigest(),
        "project_id": metadata.project_id,
        "audit_id": loaded_metadata.audit_id,
        "audit_count": len(loaded_run.audits),
        "summary": loaded_run.summary.model_dump(mode="json"),
        "model": settings.model,
        "retrieval_top_k": settings.retrieval_top_k,
        "storage_path": str(storage_path),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="执行 PaperAudit v1 真实 API 端到端冒烟测试。")
    parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--storage", type=Path, default=ROOT / "tmp" / "release_smoke" / "storage")
    args = parser.parse_args()
    result = run_smoke(args.pdf, args.output, args.storage)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
