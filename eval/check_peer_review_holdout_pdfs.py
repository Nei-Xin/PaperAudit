from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from paperaudit.pdf_parser import parse_pdf


def check(manifest_path: Path) -> dict[str, object]:
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    rows = payload["papers"]
    failures: list[dict[str, object]] = []
    for row in rows:
        path = Path(str(row["local_pdf"]))
        if not path.is_file():
            path = manifest_path.parent.parent / path
        if not path.is_file():
            failures.append({"paper_key": row["paper_key"], "reason": "missing_pdf"})
            continue
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        try:
            paper = parse_pdf(data)
            pages = paper.page_count
        except Exception as exc:
            failures.append({"paper_key": row["paper_key"], "reason": "parse_error", "error": type(exc).__name__})
            continue
        if digest != row["sha256"] or pages != row["page_count"]:
            failures.append({"paper_key": row["paper_key"], "reason": "manifest_mismatch", "sha256": digest, "page_count": pages})
    return {"manifest": str(manifest_path), "paper_count": len(rows), "failures": failures, "passed": not failures}


def main() -> int:
    parser = argparse.ArgumentParser(description="校验 peer-review holdout 固定论文 PDF")
    parser.add_argument("--manifest", type=Path, default=Path(__file__).with_name("peer_review_holdout_papers.json"))
    args = parser.parse_args()
    result = check(args.manifest)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
