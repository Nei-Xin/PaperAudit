from __future__ import annotations

import argparse
import hashlib
import json
import re
from difflib import SequenceMatcher
from pathlib import Path

from paperaudit.pdf_parser import parse_pdf


EVAL_DIR = Path(__file__).resolve().parent


def _normalize(text: str) -> str:
    text = text.casefold().replace("ﬁ", "fi").replace("ﬂ", "fl").replace("×", "x")
    text = re.sub(r"-\s*", "", text)
    return " ".join(re.findall(r"[a-z0-9]+(?:\.[0-9]+)?", text))


def _match_score(quote: str, content: str) -> float:
    normalized_quote = _normalize(quote)
    normalized_content = _normalize(content)
    if not normalized_quote or not normalized_content:
        return 0.0
    if normalized_quote in normalized_content:
        return 1.0
    quote_tokens = set(normalized_quote.split())
    content_tokens = set(normalized_content.split())
    token_recall = len(quote_tokens & content_tokens) / len(quote_tokens)
    similarity = SequenceMatcher(None, normalized_quote, normalized_content).ratio()
    return token_recall * 0.75 + similarity * 0.25


def _load_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def prepare(samples_path: Path, output_path: Path, papers_path: Path | None = None) -> dict[str, object]:
    papers = json.loads((papers_path or (EVAL_DIR / "papers.json")).read_text(encoding="utf-8"))
    samples = _load_jsonl(samples_path)
    papers_by_id = {paper["paper_id"]: paper for paper in papers}
    parsed_by_id = {}
    paper_checks: list[dict[str, object]] = []

    for paper in papers:
        pdf_path = EVAL_DIR / str(paper["local_pdf"])
        pdf_bytes = pdf_path.read_bytes()
        actual_hash = hashlib.sha256(pdf_bytes).hexdigest()
        if actual_hash != paper["sha256"]:
            raise ValueError(f"{pdf_path.name} SHA-256 不匹配。")
        parsed = parse_pdf(pdf_bytes)
        if parsed.page_count != paper["page_count"]:
            raise ValueError(f"{pdf_path.name} 页数不匹配。")
        parsed_by_id[paper["paper_id"]] = parsed
        paper_checks.append(
            {
                "paper_id": paper["paper_id"],
                "local_pdf": paper["local_pdf"],
                "sha256": actual_hash,
                "page_count": parsed.page_count,
                "chunk_count": len(parsed.chunks),
            }
        )

    unresolved: list[str] = []
    resolved_count = 0
    for sample in samples:
        quote = sample.get("source_quote")
        page = sample.get("source_page")
        sample["gold_evidence_chunk_ids"] = []
        if not quote or not page:
            continue
        sample.setdefault("provided_evidence", f"第{page}页")
        parsed = parsed_by_id[sample["paper_id"]]
        ranked = sorted(
            (
                (_match_score(str(quote), chunk.content), chunk.chunk_id)
                for chunk in parsed.chunks
                if chunk.page == page
            ),
            reverse=True,
        )
        best_score, best_chunk_id = ranked[0]
        if best_score < 0.72:
            unresolved.append(f"{sample['sample_id']} (best={best_score:.3f}, {best_chunk_id})")
            continue
        sample["gold_evidence_chunk_ids"] = [best_chunk_id]
        sample["evidence_match_score"] = round(best_score, 4)
        resolved_count += 1

    if unresolved:
        raise ValueError("以下证据摘录无法可靠映射：" + ", ".join(unresolved))
    _write_jsonl(output_path, samples)
    return {
        "papers": paper_checks,
        "sample_count": len(samples),
        "samples_with_gold_evidence": resolved_count,
        "samples_without_gold_evidence": len(samples) - resolved_count,
        "output": str(output_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="校验评测 PDF 并映射金标证据 chunk。")
    parser.add_argument("--samples", type=Path, default=EVAL_DIR / "samples.jsonl")
    parser.add_argument("--output", type=Path, default=EVAL_DIR / "resolved_samples.jsonl")
    parser.add_argument("--papers", type=Path, default=EVAL_DIR / "papers.json")
    args = parser.parse_args()
    print(json.dumps(prepare(args.samples, args.output, args.papers), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
