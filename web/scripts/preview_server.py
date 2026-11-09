"""Read-only preview server for the React frontend.

Serves the built app (web/dist, with SPA fallback to index.html) and the GET
endpoints from ``readonly_api.ReadOnlyApi`` reading the live storage
directory. Writes return 405. Single process, standard library only.

There is no login: keep it bound to 127.0.0.1 and reach it via SSH tunnel.

Usage:
    python web/scripts/preview_server.py --dist web/dist --port 18502
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import sys
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from readonly_api import ReadOnlyApi  # noqa: E402

from paperaudit.storage import load_storage_settings  # noqa: E402

mimetypes.add_type("text/javascript", ".mjs")


class Handler(BaseHTTPRequestHandler):
    server_version = "PaperAuditPreview/1"

    def __init__(self, *args, api: ReadOnlyApi, dist: Path, **kwargs) -> None:
        self.api = api
        self.dist = dist
        super().__init__(*args, **kwargs)

    def log_message(self, fmt: str, *args) -> None:  # journald gets one line per request
        sys.stderr.write("%s %s\n" % (self.address_string(), fmt % args))

    def _send(self, status: int, content_type: str, body: bytes, cache: str = "no-store") -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", cache)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path.startswith("/api/"):
            try:
                status, content_type, body = self.api.handle(self.path)
            except Exception as exc:  # surface as JSON, keep serving
                status, content_type = 500, "application/json; charset=utf-8"
                body = json.dumps({"error": {"code": "server_error", "message": str(exc)}}, ensure_ascii=False).encode()
            # The project id is a hash of the PDF bytes, so a project's PDF never changes.
            immutable = status == 200 and self.path.split("?", 1)[0].endswith("/pdf")
            self._send(status, content_type, body, "private, max-age=31536000, immutable" if immutable else "no-store")
            return
        self._serve_static()

    do_HEAD = do_GET

    def _serve_static(self) -> None:
        relative = self.path.split("?", 1)[0].lstrip("/") or "index.html"
        target = (self.dist / relative).resolve()
        if self.dist not in target.parents and target != self.dist or not target.is_file():
            target = self.dist / "index.html"  # SPA fallback for client-side routes
        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        # Hashed build assets can be cached; index.html must always be fresh.
        cache = "public, max-age=31536000, immutable" if "/assets/" in f"/{relative}" else "no-cache"
        self._send(200, content_type, target.read_bytes(), cache)

    def _read_only(self) -> None:
        body = json.dumps(
            {"error": {"code": "read_only", "message": "只读预览：写入接口尚未接入。"}}, ensure_ascii=False
        ).encode()
        self._send(405, "application/json; charset=utf-8", body)

    do_POST = do_PUT = do_PATCH = do_DELETE = _read_only


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dist", type=Path, required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18502)
    args = parser.parse_args()
    if args.host not in {"127.0.0.1", "localhost", "::1"}:
        parser.error("预览服务没有登录，只允许监听本机地址。")
    settings = load_storage_settings()
    if settings is None:
        parser.error("未找到存储设置（PAPERAUDIT_SETTINGS_DIR）。")
    dist = args.dist.resolve()
    if not (dist / "index.html").is_file():
        parser.error(f"{dist} 中没有 index.html，请先构建前端。")
    api = ReadOnlyApi(settings.storage_root)
    server = ThreadingHTTPServer((args.host, args.port), partial(Handler, api=api, dist=dist))
    print(f"PaperAudit preview on http://{args.host}:{args.port} · data {settings.storage_root}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
