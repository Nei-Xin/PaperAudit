"""Export a PaperAudit storage directory as static mock-API JSON for web dev.

Read-only: it never writes to the storage directory. Responses come from
``readonly_api.ReadOnlyApi`` so the snapshot matches the preview server
exactly. Output goes to web/public/mock-api/ (git-ignored: contains paper text).

Usage:
    PYTHONPATH=src .venv/bin/python web/scripts/export_mock_api.py --storage /path/to/library
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from readonly_api import ReadOnlyApi  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "public" / "mock-api"


def write(api: ReadOnlyApi, path: str) -> None:
    status, content_type, body = api.handle(path)
    if status != 200:
        raise SystemExit(f"{path}: HTTP {status} {body[:200]!r}")
    relative = path.removeprefix("/api/")
    target = OUT / (relative if content_type == "application/pdf" else f"{relative}.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(body)


def export(storage_root: Path) -> None:
    api = ReadOnlyApi(storage_root)
    if OUT.exists():
        shutil.rmtree(OUT)
    for path in ("/api/settings", "/api/storage", "/api/projects"):
        write(api, path)
    projects = api.projects()
    for project in projects:
        base = f"/api/projects/{project['project_id']}"
        for suffix in ("", "/pdf", "/lecture", "/conversations", "/audits", "/review", "/jobs"):
            write(api, base + suffix)
        for record in api.audits(project["project_id"]):
            write(api, f"{base}/audits/{record['audit_id']}")
    print(f"exported {len(projects)} projects to {OUT}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--storage", required=True, type=Path, help="PaperAudit library directory")
    export(parser.parse_args().storage.resolve())
