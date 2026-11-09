"""Shared read payloads for the React API and the legacy preview server.

The handle adapter preserves the preview/static-export route contract.
Writable reading routes live in main.py; business mutations live in workflows.py.
"""

from __future__ import annotations

import json
import re
from collections import OrderedDict
from dataclasses import asdict
from threading import Lock
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pymupdf

from paperaudit.config import Settings
from paperaudit.evidence import refresh_evidence_anchors, refresh_learning_report_evidence
from paperaudit.models import EvidenceAnchor
from paperaudit.reporting import render_learning_markdown, render_markdown
from paperaudit.storage import ProjectStore, StorageError
from paperaudit.ui.audit_view import selected_evidence


JSON = "application/json; charset=utf-8"
MARKDOWN = "text/markdown; charset=utf-8"
PDF = "application/pdf"


class NotFound(Exception):
    pass


def _model(value):
    return None if value is None else value.model_dump(mode="json")


def _json(payload: object) -> tuple[int, str, bytes]:
    return 200, JSON, json.dumps(payload, ensure_ascii=False).encode("utf-8")


def _page_sizes(pdf_bytes: bytes) -> list[dict[str, float]]:
    document = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    try:
        return [{"width": float(p.rect.width), "height": float(p.rect.height)} for p in document]
    finally:
        document.close()


def _stamp(*paths: Path) -> tuple:
    """Change marker for cached payloads: (mtime, size) of each input file."""
    marks = []
    for path in paths:
        try:
            stat = path.stat()
        except FileNotFoundError:
            marks.append(None)
        else:
            marks.append((stat.st_mtime_ns, stat.st_size))
    return tuple(marks)


class _Memo:
    """Small LRU of derived payloads, valid while the input files are unchanged.

    Opening an audit re-parses the paper index and re-anchors evidence, which
    takes seconds on large papers; repeated reads should not pay that again.
    """

    def __init__(self, size: int = 48) -> None:
        self.size = size
        self.items: OrderedDict[tuple, tuple[tuple, object]] = OrderedDict()
        self.lock = Lock()

    def get(self, key: tuple, stamp: tuple, compute):
        with self.lock:
            hit = self.items.get(key)
            if hit and hit[0] == stamp:
                self.items.move_to_end(key)
                return hit[1]
        value = compute()
        with self.lock:
            self.items[key] = (stamp, value)
            self.items.move_to_end(key)
            while len(self.items) > self.size:
                self.items.popitem(last=False)
        return value


class ReadOnlyApi:
    def __init__(self, storage_root: Path, settings: Settings | None = None) -> None:
        self.storage_root = storage_root
        self.store = ProjectStore(storage_root)
        self.settings = settings or Settings.from_env()
        self._memo = _Memo()

    def _dir(self, project_id: str) -> Path:
        return self.store._project_dir(project_id)

    # ── payloads ─────────────────────────────────────────────
    def settings_payload(self) -> dict:
        s = self.settings
        return {
            "api_base": s.api_base,
            "model": s.model,
            "reasoning_effort": s.reasoning_effort,
            "retrieval_top_k": s.retrieval_top_k,
            "judge_batch_size": s.judge_batch_size,
            "deep_audit": s.deep_audit,
            "configured": s.is_configured,  # never the key itself
        }

    def projects(self) -> list[dict]:
        return [
            asdict(m) | {"has_audit": self.store.has_audit_runs(m.project_id)}
            for m in self.store.list_projects()
        ]

    def _summary(self, project_id: str) -> dict:
        for item in self.projects():
            if item["project_id"] == project_id:
                return item
        raise NotFound(project_id)

    def project(self, project_id: str) -> dict:
        directory = self._dir(project_id)

        def compute() -> dict:
            saved = self.store.load_learning_project(project_id)
            report = saved.report
            return {
                "page_count": saved.paper.page_count,
                "pages": _page_sizes(saved.pdf_bytes),
                "suggested_pages": report.suggested_pages if report else [],
            }

        stamp = _stamp(directory / "paper.pdf", directory / "paper-index.json", directory / "learning-report.json")
        return self._summary(project_id) | self._memo.get(("project", project_id), stamp, compute)

    def pdf(self, project_id: str) -> bytes:
        return (self._dir(project_id) / "paper.pdf").read_bytes()

    def lecture(self, project_id: str):
        directory = self._dir(project_id)

        def compute():
            saved = self.store.load_learning_project(project_id)
            if saved.report is None:
                return None
            return refresh_learning_report_evidence(saved.report, saved.paper)

        stamp = _stamp(directory / "learning-report.json", directory / "paper-index.json")
        return self._memo.get(("lecture", project_id), stamp, compute)

    def conversations(self, project_id: str) -> dict:
        saved = self.store.load_learning_project(project_id)
        return {
            "active_conversation_id": saved.active_conversation_id,
            "conversations": [
                {
                    "conversation_id": r.conversation_id,
                    "title": r.title,
                    "created_at": r.created_at,
                    "updated_at": r.updated_at,
                    "paper_history": [_model(a) for a in r.paper_history],
                    "joint_history": [_model(a) for a in r.joint_history],
                }
                for r in saved.conversations
            ],
        }

    def audits(self, project_id: str) -> list[dict]:
        return [asdict(r) for r in self.store.list_audit_runs(project_id)]

    def audit(self, project_id: str, audit_id: str) -> dict:
        directory = self._dir(project_id)
        stamp = _stamp(directory / "audits" / f"{audit_id}.json", directory / "paper-index.json")
        return self._memo.get(("audit", project_id, audit_id), stamp, lambda: self._audit(project_id, audit_id))

    def _audit(self, project_id: str, audit_id: str) -> dict:
        record, run = self.store.load_audit_run(project_id, audit_id)
        paper = self.store.load_learning_project(project_id).paper
        anchors: dict[str, EvidenceAnchor] = {}
        for item in run.audits:
            for candidate in selected_evidence(item):
                anchors.setdefault(candidate.chunk_id, EvidenceAnchor(
                    chunk_id=candidate.chunk_id, page=candidate.page, text=candidate.text,
                ))
        anchors.update({a.chunk_id: a for a in refresh_evidence_anchors(list(anchors.values()), paper)})
        return {"record": asdict(record), "run": _model(run), "anchors": {k: _model(v) for k, v in anchors.items()}}

    def review(self, project_id: str):
        report = self.store.load_peer_review(project_id)
        if report is None:
            return None
        progress = self.store.load_review_progress(project_id)
        return {
            "report": _model(report),
            "progress": progress,
            "revisions": [_model(r) for r in self.store.list_peer_review_revisions(project_id)],
        }

    def jobs(self, project_id: str) -> dict:
        s = self.store
        return {
            "audit": [_model(j) for j in s.list_audit_jobs(project_id)],
            "learning": [_model(j) for j in s.list_learning_jobs(project_id)],
            "review": [_model(j) for j in s.list_peer_review_jobs(project_id)],
            "revision": [_model(j) for j in s.list_peer_review_revision_jobs(project_id)],
        }

    # ── router ───────────────────────────────────────────────
    def handle(self, raw_path: str) -> tuple[int, str, bytes]:
        """Return (status, content type, body) for a GET /api/... request."""

        url = urlsplit(raw_path)
        fmt = parse_qs(url.query).get("format", ["json"])[0]
        path = url.path.rstrip("/")
        try:
            if path == "/api/settings":
                return _json(self.settings_payload())
            if path == "/api/storage":
                return _json({"name": self.storage_root.name, "path": str(self.storage_root)})
            if path == "/api/projects":
                return _json(self.projects())
            match = re.fullmatch(r"/api/projects/([0-9a-f]+)(?:/(.*))?", path)
            if not match:
                raise NotFound(path)
            pid, rest = match.group(1), match.group(2) or ""
            if rest == "":
                return _json(self.project(pid))
            if rest == "pdf":
                return 200, PDF, self.pdf(pid)
            if rest == "lecture":
                return _json(_model(self.lecture(pid)))
            if rest == "lecture/export":
                report = self.lecture(pid)
                if report is None:
                    raise NotFound(path)
                if fmt == "md":
                    return 200, MARKDOWN, render_learning_markdown(report).encode("utf-8")
                return _json(_model(report))
            if rest == "conversations":
                return _json(self.conversations(pid))
            if rest == "audits":
                return _json(self.audits(pid))
            audit_match = re.fullmatch(r"audits/([A-Za-z0-9_-]+)(/export)?", rest)
            if audit_match:
                detail = self.audit(pid, audit_match.group(1))
                if audit_match.group(2) and fmt == "md":
                    _, run = self.store.load_audit_run(pid, audit_match.group(1))
                    return 200, MARKDOWN, render_markdown(run).encode("utf-8")
                return _json(detail["run"] if audit_match.group(2) else detail)
            if rest == "review":
                return _json(self.review(pid))
            if rest == "review/export":
                report = self.store.load_peer_review(pid)
                if report is None:
                    raise NotFound(path)
                from paperaudit.review_reporting import render_peer_review_markdown
                return 200, MARKDOWN, render_peer_review_markdown(report).encode("utf-8")
            if rest == "jobs":
                return _json(self.jobs(pid))
            raise NotFound(path)
        except (NotFound, StorageError, FileNotFoundError) as exc:
            body = {"error": {"code": "not_found", "message": str(exc) or "未找到"}}
            return 404, JSON, json.dumps(body, ensure_ascii=False).encode("utf-8")
