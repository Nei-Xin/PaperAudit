"""Run stage-9 real-model reviews for every fixed dev PDF.

Each paper is generated independently and written immediately so interrupted
runs can resume without repeating completed API calls. Gold issue labels are
never included in model prompts.
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from paperaudit.config import Settings
from paperaudit.models import PeerReviewVenue
from paperaudit.pdf_parser import parse_pdf
from paperaudit.service import AuditService


_VENUES = {
    "NeurIPS": PeerReviewVenue.NEURIPS,
    "ICLR": PeerReviewVenue.ICLR,
    "AAAI": PeerReviewVenue.AAAI,
    "IJCAI": PeerReviewVenue.IJCAI,
}


def _load_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _paper_key(row: dict[str, object]) -> str:
    explicit = str(row.get("paper_key", "")).strip()
    if explicit:
        return explicit
    arxiv = str(row.get("arxiv_url", "")).strip()
    if arxiv:
        return arxiv.rsplit("/", 1)[-1].removesuffix(".pdf").split("v", 1)[0]
    forum_id = parse_qs(urlparse(str(row.get("openreview_url", ""))).query).get("id", [""])[0]
    if forum_id:
        return str(forum_id)
    return str(row.get("arxiv_url") or row.get("paper_version_url") or "").rsplit("/", 1)[-1]


def run_batch(manifest_path: Path, dev_path: Path, output_dir: Path, *, temperature: float, resume: bool, only: set[str] | None = None) -> dict[str, object]:
    settings = Settings.from_env()
    if not settings.is_configured:
        raise RuntimeError("API 配置不完整，无法执行真实评审。")
    settings = replace(settings, temperature=temperature)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    dev_rows = _load_jsonl(dev_path)
    meeting_by_url = {str(row.get("arxiv_url") or row.get("paper_version_url")): str(row.get("meeting", "")) for row in dev_rows}
    meeting_by_key = {_paper_key(row): str(row.get("meeting", "")) for row in dev_rows}
    output_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, object]] = []
    for index, item in enumerate(manifest["papers"], 1):
        paper_key = str(item["paper_key"])
        if only and paper_key not in only:
            continue
        output = output_dir / f"{paper_key}.json"
        if resume and output.is_file():
            saved = json.loads(output.read_text(encoding="utf-8"))
            results.append({"paper_key": paper_key, "status": "reused", **saved["summary"]})
            print(f"[{index}/{len(manifest['papers'])}] reuse {paper_key}", flush=True)
            continue
        pdf_path = Path(str(item["local_pdf"]))
        source_key = str(item.get("metadata_url", ""))
        meeting = meeting_by_key.get(paper_key, meeting_by_url.get(source_key, ""))
        venue = _VENUES.get(meeting, PeerReviewVenue.GENERAL)
        print(f"[{index}/{len(manifest['papers'])}] start {paper_key} ({meeting or 'general'})", flush=True)
        started = time.perf_counter()
        try:
            paper = parse_pdf(pdf_path.read_bytes())
            report = AuditService(settings).generate_peer_review(paper, venue=venue)
        except Exception as exc:  # preserve failure state and continue other papers
            failure = {
                "evaluation_version": "peer-review-stage9-dev-v1",
                "paper_key": paper_key,
                "source_url": item["source_url"],
                "local_pdf": str(pdf_path),
                "status": "failed",
                "error_type": type(exc).__name__,
                "error": str(exc),
                "elapsed_seconds": round(time.perf_counter() - started, 3),
            }
            output.write_text(json.dumps(failure, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            results.append({"paper_key": paper_key, "status": "failed", "error_type": type(exc).__name__})
            print(f"[{index}/{len(manifest['papers'])}] failed {paper_key}: {type(exc).__name__}", flush=True)
            continue
        elapsed = round(time.perf_counter() - started, 3)
        concerns = [*report.major_concerns, *report.minor_concerns]
        summary = {
            "decision": report.decision.value,
            "overall_score": report.overall_score,
            "confidence": report.confidence,
            "concern_count": len(concerns),
            "evidence_backed_concern_count": sum(bool(item.evidence) for item in concerns),
            "high_severity_count": sum(item.severity_level.value in {"P0", "P1"} for item in concerns),
            "warning_count": len(report.parse_warnings),
            "elapsed_seconds": elapsed,
        }
        payload = {
            "evaluation_version": "peer-review-stage9-dev-v1",
            "paper_key": paper_key,
            "source_url": item["source_url"],
            "local_pdf": str(pdf_path),
            "sha256": item["sha256"],
            "meeting": meeting,
            "venue": venue.value,
            "model": settings.model,
            "temperature": temperature,
            "reasoning_effort": settings.reasoning_effort,
            "run_at": datetime.now(timezone.utc).isoformat(),
            "summary": summary,
            "report": report.model_dump(mode="json"),
        }
        output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        results.append({"paper_key": paper_key, "status": "generated", **summary})
        print(f"[{index}/{len(manifest['papers'])}] done {paper_key} {summary['decision']} {summary['overall_score']}", flush=True)
    # Rebuild the summary from all per-paper artifacts so a targeted retry does
    # not overwrite the complete batch view with a one-paper subset.
    all_results: list[dict[str, object]] = []
    for item in manifest["papers"]:
        artifact = output_dir / f"{item['paper_key']}.json"
        if not artifact.is_file():
            continue
        saved = json.loads(artifact.read_text(encoding="utf-8"))
        if saved.get("status") == "failed":
            all_results.append({"paper_key": item["paper_key"], "status": "failed", "error_type": saved.get("error_type", "unknown")})
        elif saved.get("summary"):
            all_results.append({"paper_key": item["paper_key"], "status": "generated", **saved["summary"]})
    batch = {
        "evaluation_version": "peer-review-stage9-dev-batch-v1",
        "model": settings.model,
        "temperature": temperature,
        "paper_count": len(all_results),
        "generated_count": sum(item.get("status") == "generated" for item in all_results),
        "failed_count": sum(item.get("status") == "failed" for item in all_results),
        "results": all_results,
    }
    (output_dir / "batch_summary.json").write_text(json.dumps(batch, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return batch


def main() -> int:
    root = Path(__file__).parent
    parser = argparse.ArgumentParser(description="批量运行投稿评审 dev 集真实模型回归")
    parser.add_argument("--manifest", type=Path, default=root / "peer_review_dev_papers.json")
    parser.add_argument("--dev", type=Path, default=root / "peer_review_regression_dev.jsonl")
    parser.add_argument("--output-dir", type=Path, default=root / "stage9_dev_real")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--no-resume", action="store_true")
    parser.add_argument("--paper-key", action="append", help="只运行指定论文，可重复传入")
    args = parser.parse_args()
    result = run_batch(args.manifest, args.dev, args.output_dir, temperature=args.temperature, resume=not args.no_resume, only=set(args.paper_key or []))
    print(json.dumps({"passed": result["paper_count"] > 0, "paper_count": result["paper_count"], "output_dir": str(args.output_dir)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
