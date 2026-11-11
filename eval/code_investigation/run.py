"""Paper-code investigation vs the fixed single-retrieval pipeline on labelled questions.

Every question targets one comparable point of a real paper and its official
repository at a pinned commit. Some questions run against a copy of the
repository with one documented edit, so the same question has a consistent and
an inconsistent version. Reference labels never enter a prompt.

Without --run this only verifies inputs and writes the frozen protocol.
Observations are appended as they finish; --resume skips finished ones and
refuses to replay a dispatched observation that has no recorded result.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from hashlib import sha256
import io
import json
from pathlib import Path
import threading
import time
import zipfile

from paperaudit.code_parser import parse_code_zip
from paperaudit.code_service import CodeLearningService
from paperaudit.config import Settings
from paperaudit.hy3_client import Hy3Client
from paperaudit.pdf_parser import parse_pdf
from paperaudit.request_budget import RequestBudget, use_request_budget

HERE = Path(__file__).resolve().parent
SOURCES = ["src/paperaudit/agents/code_investigator.py", "src/paperaudit/agents/code_tools.py",
           "src/paperaudit/code_service.py", "src/paperaudit/hy3_client.py",
           "src/paperaudit/code_retrieval.py", "src/paperaudit/retrieval.py"]


def digest(data: bytes) -> str:
    return sha256(data).hexdigest()


def build_archive(raw: bytes, include: list[str] | None, edits: list[list]) -> bytes:
    """Strip the archive root, keep the selected paths and apply counted replacements."""
    source = zipfile.ZipFile(io.BytesIO(raw))
    members = {}
    for info in source.infolist():
        if info.is_dir():
            continue
        path = info.filename.split("/", 1)[1]
        if include is None or any(path == prefix or path.startswith(prefix) for prefix in include):
            members[path] = source.read(info)
    for path, old, new, count in edits:
        text = members[path].decode("utf-8")
        if text.count(old) != count:
            raise SystemExit(f"{path}: expected {count} occurrences of {old!r}, found {text.count(old)}")
        members[path] = text.replace(old, new).encode("utf-8")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as target:
        for path in sorted(members):
            target.writestr(zipfile.ZipInfo(f"repo/{path}", date_time=(2020, 1, 1, 0, 0, 0)), members[path])
    return buffer.getvalue()


def observe(settings: Settings, paper, codebase, item: dict, mode: str) -> dict:
    service = CodeLearningService(settings, Hy3Client(settings))
    meter = RequestBudget(max_requests=40, max_seconds=600)
    started = time.monotonic()
    try:
        if mode == "agent":
            answer = service.answer(paper, codebase, item["question"], investigate=True)
        else:  # Metered the same way; this also disables hidden SDK retries.
            with use_request_budget(meter):
                answer = service.answer(paper, codebase, item["question"], investigate=False)
    except Exception as exc:  # A failed observation stays in the denominator.
        return {"error": f"{type(exc).__name__}: {str(exc)[:400]}",
                "seconds": round(time.monotonic() - started, 1)}
    trace = answer.investigation
    return {
        "status": answer.status.value, "scope": answer.scope.value,
        "relation": answer.relation.value if answer.relation else None,
        "answer": answer.answer,
        "findings": [{"verdict": f.verdict.value, "text": f.text,
                      "code": [f"{c.path} L{c.start_line}-{c.end_line}" for c in f.code_citations],
                      "paper": [c.chunk_id for c in f.paper_citations]} for f in answer.findings],
        "code_citations": [f"{c.path} L{c.start_line}-{c.end_line}" for c in answer.code_citations],
        "paper_citations": [c.chunk_id for c in answer.paper_citations],
        "requests": trace.requests if trace else meter.requests,
        "tokens": trace.tokens if trace else meter.tokens,
        "seconds": round(time.monotonic() - started, 1),
        "trace": trace.model_dump(mode="json") if trace else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=HERE / "cases.json")
    parser.add_argument("--data", type=Path, default=HERE / "data")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--modes", default="agent,fixed")
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--items", default="", help="comma-separated item ids (default: all)")
    parser.add_argument("--max-requests", type=int, default=600, help="stop dispatching beyond this")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    cases = json.loads(args.cases.read_text())
    wanted = set(filter(None, args.items.split(",")))
    items = [item for item in cases["items"] if not wanted or item["id"] in wanted]
    root = HERE.parents[1]
    settings = Settings.from_env()

    parsed: dict[tuple[str, str | None], tuple] = {}
    inputs = {}
    for name, spec in cases["papers"].items():
        pdf, raw = (args.data / name / "paper.pdf").read_bytes(), (args.data / name / "repo.zip").read_bytes()
        if digest(pdf) != spec["pdf_sha256"] or digest(raw) != spec["zip_sha256"]:
            raise SystemExit(f"{name}: input hash mismatch")
        paper = parse_pdf(pdf)
        variants = {None} | {item["mutation"] for item in items if item["paper"] == name}
        for mutation in variants:
            archive = build_archive(raw, spec["include"], cases["mutations"][mutation] if mutation else [])
            codebase = parse_code_zip(archive, f"{name}.zip")
            parsed[(name, mutation)] = (paper, codebase)
            inputs[f"{name}:{mutation or 'original'}"] = {
                "archive_sha256": digest(archive), "files": len(codebase.files),
                "chunks": len(codebase.chunks), "paper_chunks": len(paper.chunks),
                "warnings": codebase.warnings[:5]}

    protocol = {
        "version": cases["version"], "split": cases["split"], "model": settings.model,
        "reasoning_effort": settings.reasoning_effort, "temperature": settings.temperature,
        "modes": args.modes.split(","), "repeats": args.repeats, "items": [item["id"] for item in items],
        "cases": args.cases.name, "cases_sha256": digest(args.cases.read_bytes()),
        "sources": {path: digest((root / path).read_bytes()) for path in SOURCES},
        "uv_lock_sha256": digest((root / "uv.lock").read_bytes()), "inputs": inputs,
    }
    args.output.mkdir(parents=True, exist_ok=True)
    protocol_path, log_path = args.output / "protocol.json", args.output / "observations.jsonl"
    if protocol_path.exists():
        if not args.resume:
            raise SystemExit("output exists; use a new directory or --resume")
        previous = json.loads(protocol_path.read_text())
        if any(previous[key] != protocol[key] for key in ("cases_sha256", "sources", "inputs", "model")):
            raise SystemExit("inputs, sources or model changed since this run started")
    else:
        protocol_path.write_text(json.dumps(protocol, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps(inputs, ensure_ascii=False, indent=1))
    if not args.run:
        print(f"protocol written for {len(items)} items; pass --run to call the model")
        return

    done, dispatched = set(), set()
    if log_path.exists():
        for line in log_path.read_text().splitlines():
            row = json.loads(line)
            key = (row["item"], row["mode"], row["repeat"])
            (done if row["event"] == "result" else dispatched).add(key)
    if dispatched - done:
        raise SystemExit(f"dispatched without result, not replayed automatically: {sorted(dispatched - done)}")

    jobs = [(item, mode, repeat) for repeat in range(args.repeats) for item in items
            for mode in protocol["modes"] if (item["id"], mode, repeat) not in done]
    lock, used = threading.Lock(), [0]

    def record(row: dict) -> None:
        with lock, log_path.open("a") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    def work(job):
        item, mode, repeat = job
        with lock:
            if used[0] >= args.max_requests:
                return item["id"], mode, None
        record({"event": "dispatch", "item": item["id"], "mode": mode, "repeat": repeat})
        paper, codebase = parsed[(item["paper"], item["mutation"])]
        result = observe(settings, paper, codebase, item, mode)
        with lock:
            used[0] += result.get("requests") or 0
        record({"event": "result", "item": item["id"], "mode": mode, "repeat": repeat, **result})
        return item["id"], mode, result

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for future in as_completed([pool.submit(work, job) for job in jobs]):
            name, mode, result = future.result()
            if result is None:
                print(name, mode, "not dispatched: request cap reached", flush=True)
            else:
                print(name, mode, result.get("status"), [f["verdict"] for f in result.get("findings", [])],
                      result.get("relation"), result.get("requests"), result.get("error", ""), flush=True)
    print("requests used:", used[0])


if __name__ == "__main__":
    main()
