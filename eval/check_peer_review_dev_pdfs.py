"""Validate that every dev paper has a fixed, intact local PDF."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse


def _paper_key(row: dict[str, object]) -> str:
    """Return a stable paper key from arXiv or OpenReview provenance."""
    explicit = str(row.get("paper_key", "")).strip()
    if explicit:
        return explicit
    arxiv = str(row.get("arxiv_url", "")).strip()
    if arxiv:
        return arxiv.rsplit("/", 1)[-1].removesuffix(".pdf").split("v", 1)[0]
    forum = str(row.get("openreview_url", "")).strip()
    query = parse_qs(urlparse(forum).query)
    return str(query.get("id", [""])[0])


def check(manifest_path: Path, dev_path: Path) -> dict[str, object]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    papers = manifest.get("papers", [])
    dev_rows = [json.loads(line) for line in dev_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    dev_keys = {_paper_key(row) for row in dev_rows if _paper_key(row)}
    manifest_keys = {str(row.get("paper_key", "")) for row in papers}
    missing_manifest = sorted(dev_keys - manifest_keys)
    missing_files: list[str] = []
    hash_mismatch: list[str] = []
    for row in papers:
        path = Path(str(row.get("local_pdf", "")))
        if not path.is_file():
            missing_files.append(str(path))
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != str(row.get("sha256", "")):
            hash_mismatch.append(str(path))
    result = {
        "passed": not missing_manifest and not missing_files and not hash_mismatch,
        "dev_paper_count": len(dev_keys),
        "manifest_paper_count": len(manifest_keys),
        "missing_manifest": missing_manifest,
        "missing_files": missing_files,
        "hash_mismatch": hash_mismatch,
        "policy": "只使用固定版本 PDF；哈希不一致时禁止进入真实模型回归。",
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="检查投稿评审 dev 集 PDF 完整性")
    root = Path(__file__).parent
    parser.add_argument("--manifest", type=Path, default=root / "peer_review_dev_papers.json")
    parser.add_argument("--dev", type=Path, default=root / "peer_review_regression_dev.jsonl")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = check(args.manifest, args.dev)
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
