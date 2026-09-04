from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from paperaudit.config import Settings
from paperaudit.audit_rules import (
    calibrate_judgment,
    choose_majority,
    judgment_signature,
    needs_evidence_retry,
    needs_second_pass,
    validate_judgment_references,
)
from paperaudit.hy3_client import Hy3Client, Hy3ResponseError
from paperaudit.models import (
    AtomicClaim,
    AutoLabel,
    ClaimAudit,
    ClaimCategory,
    ClaimJudgment,
    EvidenceCandidate,
    Severity,
)
from paperaudit.retrieval import EvidenceRetriever, build_claim_query
from paperaudit.scoring import build_summary


EVAL_DIR = Path(__file__).resolve().parent
LABELS = [label.value for label in AutoLabel]
ERROR_TYPES = {
    "numeric_or_metric_mismatch",
    "wrong_attribution",
    "missing_condition",
    "overgeneralization",
    "external_hallucination",
    "contradiction",
}


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _claim(sample: dict[str, Any]) -> AtomicClaim:
    return AtomicClaim(
        claim_id=str(sample["sample_id"]),
        text=str(sample["report_text"]),
        category=ClaimCategory(str(sample["category"])),
        key_claim=bool(sample.get("key_claim", False)),
        query_en=str(sample["query_en"]),
        entities=[],
        numbers=[str(value) for value in sample.get("numbers", [])],
        metric=str(sample["metric"]) if sample.get("metric") else None,
        dataset=None,
        provided_evidence=str(sample["provided_evidence"])
        if sample.get("provided_evidence")
        else None,
    )


def _validated_judgment(
    judgment: ClaimJudgment | None,
    candidates: list,
) -> ClaimJudgment:
    if not candidates:
        return ClaimJudgment(
            claim_id=judgment.claim_id if judgment else "unknown",
            label=AutoLabel.ABSTAIN,
            explanation="本地检索未返回候选证据，暂时无法可靠判断。",
            severity=Severity.NONE,
        )
    calibrated = calibrate_judgment(judgment) if judgment is not None else None
    return validate_judgment_references(calibrated, candidates)


def _macro_f1(gold: list[str], predicted: list[str], labels: list[str]) -> float:
    values: list[float] = []
    for label in labels:
        tp = sum(g == label and p == label for g, p in zip(gold, predicted, strict=True))
        fp = sum(g != label and p == label for g, p in zip(gold, predicted, strict=True))
        fn = sum(g == label and p != label for g, p in zip(gold, predicted, strict=True))
        if tp == 0 and fp == 0 and fn == 0:
            continue
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        values.append(2 * precision * recall / (precision + recall) if precision + recall else 0.0)
    return round(sum(values) / len(values), 4) if values else 0.0


def _metric_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """计算一组预测行的指标，不包含混淆矩阵和分组信息。"""
    gold = [str(row["gold_label"]) for row in rows]
    predicted = [str(row["predicted_label"]) for row in rows]
    gold_errors = [str(row["gold_error_type"]) for row in rows if row.get("gold_error_type")]
    predicted_errors = [
        str(row["predicted_error_type"])
        for row in rows
        if row.get("gold_error_type")
    ]
    error_accuracy = (
        sum(g == p for g, p in zip(gold_errors, predicted_errors, strict=True)) / len(gold_errors)
        if gold_errors
        else None
    )
    gold_severity = [str(row["gold_severity"]) for row in rows]
    predicted_severity = [str(row["predicted_severity"]) for row in rows]
    gold_evidence_rows = [row for row in rows if row.get("gold_evidence_chunk_ids")]
    retrieval_hits = [row["retrieval_hit"] for row in gold_evidence_rows]
    return {
        "sample_count": len(rows),
        "label_accuracy": round(sum(g == p for g, p in zip(gold, predicted, strict=True)) / len(rows), 4)
        if rows
        else 0.0,
        "label_macro_f1": _macro_f1(gold, predicted, LABELS),
        "error_type_accuracy": round(error_accuracy, 4) if error_accuracy is not None else None,
        "severity_accuracy": round(
            sum(g == p for g, p in zip(gold_severity, predicted_severity, strict=True)) / len(rows),
            4,
        )
        if rows
        else 0.0,
        "abstain_rate": round(predicted.count(AutoLabel.ABSTAIN.value) / len(rows), 4)
        if rows
        else 0.0,
        "gold_evidence_count": len(gold_evidence_rows),
        "retrieval_hit_rate": round(sum(retrieval_hits) / len(retrieval_hits), 4)
        if retrieval_hits
        else None,
        "label_distribution": dict(Counter(predicted)),
    }


def _metrics(rows: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    metrics = _metric_summary(rows)
    confusion = Counter(
        (str(row["gold_label"]), str(row["predicted_label"])) for row in rows
    )
    matrix = [
        {"gold_label": g, **{f"predicted_{p}": confusion[(g, p)] for p in LABELS}}
        for g in LABELS
    ]
    # 分层统计仅用于诊断，不参与裁决、评分或阈值判断。
    for field in ("category", "construction"):
        groups: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            value = str(row.get(field) or "unknown")
            groups.setdefault(value, []).append(row)
        metrics[f"by_{field}"] = {
            value: _metric_summary(group_rows)
            for value, group_rows in sorted(groups.items())
        }
    return metrics, matrix


def run(
    samples_path: Path,
    output_dir: Path,
    *,
    paper_id: str | None = None,
    dry_run: bool = False,
    retrieval_top_k: int | None = None,
    oracle_evidence: bool = False,
    papers_path: Path | None = None,
) -> dict[str, Any]:
    samples = _load_jsonl(samples_path)
    samples = [sample for sample in samples if not paper_id or sample["paper_id"] == paper_id]
    if not samples:
        raise ValueError("没有匹配的评测样本。")
    if any("gold_evidence_chunk_ids" not in sample for sample in samples):
        raise ValueError("请先运行 prepare_evidence.py 生成 resolved_samples.jsonl。")

    settings = Settings.from_env()
    top_k = retrieval_top_k or settings.retrieval_top_k
    if top_k < 1:
        raise ValueError("retrieval_top_k 必须大于 0。")
    client = None if dry_run else Hy3Client(settings)
    predictions: list[dict[str, Any]] = []
    paper_summaries: dict[str, Any] = {}
    for current_paper_id in dict.fromkeys(str(sample["paper_id"]) for sample in samples):
        group = [sample for sample in samples if sample["paper_id"] == current_paper_id]
        paper_meta = json.loads((papers_path or (EVAL_DIR / "papers.json")).read_text(encoding="utf-8"))
        paper = next(item for item in paper_meta if item["paper_id"] == current_paper_id)
        pdf_bytes = (EVAL_DIR / str(paper["local_pdf"])).read_bytes()
        if hashlib.sha256(pdf_bytes).hexdigest() != paper["sha256"]:
            raise ValueError(f"{paper['local_pdf']} SHA-256 不匹配。")
        from paperaudit.pdf_parser import parse_pdf

        parsed = parse_pdf(pdf_bytes)
        claims = [_claim(sample) for sample in group]
        audits: list[ClaimAudit] = []
        with EvidenceRetriever(parsed.chunks) as retriever:
            retrieved_by_id = {
                claim.claim_id: retriever.search(
                    build_claim_query(claim), claim.claim_id, top_k
                )
                for claim in claims
            }
            candidates_by_id = dict(retrieved_by_id)
            if oracle_evidence:
                for sample, claim in zip(group, claims, strict=True):
                    gold_ids = [str(value) for value in sample["gold_evidence_chunk_ids"]]
                    gold_chunks = [chunk for chunk in parsed.chunks if chunk.chunk_id in gold_ids]
                    injected = [
                        EvidenceCandidate(
                            evidence_id=f"{claim.claim_id}_gold{index + 1}",
                            chunk_id=chunk.chunk_id,
                            page=chunk.page,
                            text=chunk.content,
                            score=999.0 - index,
                        )
                        for index, chunk in enumerate(gold_chunks)
                    ]
                    existing_chunks = {candidate.chunk_id for candidate in candidates_by_id[claim.claim_id]}
                    candidates_by_id[claim.claim_id] = injected + [
                        candidate
                        for candidate in candidates_by_id[claim.claim_id]
                        if candidate.chunk_id not in existing_chunks.intersection(gold_ids)
                    ]
            judgments: dict[str, ClaimJudgment] = {}
            judgment_votes: dict[str, list[ClaimJudgment]] = {}
            if client is not None:
                for start in range(0, len(claims), max(1, settings.judge_batch_size)):
                    batch = claims[start : start + max(1, settings.judge_batch_size)]
                    try:
                        response = client.judge_claims(
                            [(claim, candidates_by_id[claim.claim_id]) for claim in batch],
                            parsed.page_count,
                        )
                    except Hy3ResponseError:
                        fallback = []
                        for claim in batch:
                            try:
                                single = client.adjudicate_claim(
                                    claim, candidates_by_id[claim.claim_id], parsed.page_count
                                )
                                fallback.extend(single.judgments)
                            except Hy3ResponseError:
                                continue
                        from paperaudit.models import JudgmentBatch

                        response = JudgmentBatch(judgments=fallback)
                    judgments.update({judgment.claim_id: judgment for judgment in response.judgments})
                    for judgment in response.judgments:
                        judgment_votes[judgment.claim_id] = [judgment]
                retry_items = [
                    claim
                    for claim in claims
                    if claim.claim_id in judgments
                    and needs_second_pass(judgments[claim.claim_id], claim.text + " " + claim.query_en)
                ]
                for claim in retry_items:
                    try:
                        retry = client.adjudicate_claim(
                            claim, candidates_by_id[claim.claim_id], parsed.page_count
                        )
                    except Hy3ResponseError:
                        retry = None
                    if retry and retry.judgments:
                        judgment_votes.setdefault(claim.claim_id, []).append(retry.judgments[0])
                        judgments[claim.claim_id] = choose_majority(judgment_votes[claim.claim_id])
                stabilize_items = [
                    claim
                    for claim in retry_items
                    if len(judgment_votes.get(claim.claim_id, [])) == 2
                    and judgment_signature(judgment_votes[claim.claim_id][0])
                    != judgment_signature(judgment_votes[claim.claim_id][1])
                ]
                for claim in stabilize_items:
                    try:
                        retry = client.adjudicate_claim(
                            claim, candidates_by_id[claim.claim_id], parsed.page_count
                        )
                    except Hy3ResponseError:
                        retry = None
                    if retry and retry.judgments:
                        judgment_votes[claim.claim_id].append(retry.judgments[0])
                        judgments[claim.claim_id] = choose_majority(judgment_votes[claim.claim_id])
                evidence_retry_items = [
                    claim
                    for claim in claims
                    if needs_evidence_retry(
                        judgments.get(claim.claim_id), candidates_by_id[claim.claim_id]
                    )
                ]
                for claim in evidence_retry_items:
                    try:
                        retry = client.adjudicate_claim(
                            claim, candidates_by_id[claim.claim_id], parsed.page_count
                        )
                    except Hy3ResponseError:
                        retry = None
                    if retry and retry.judgments:
                        judgment_votes.setdefault(claim.claim_id, []).append(retry.judgments[0])
                        judgments[claim.claim_id] = retry.judgments[0]
            for sample, claim in zip(group, claims, strict=True):
                candidates = candidates_by_id[claim.claim_id]
                judgment = _validated_judgment(judgments.get(claim.claim_id), candidates)
                retrieval_hit = bool(
                    set(str(value) for value in sample["gold_evidence_chunk_ids"])
                    & {candidate.chunk_id for candidate in retrieved_by_id[claim.claim_id]}
                )
                audits.append(ClaimAudit(claim=claim, candidates=candidates, judgment=judgment))
                predictions.append(
                    {
                        "sample_id": sample["sample_id"],
                        "paper_id": current_paper_id,
                        "category": sample.get("category"),
                        "construction": sample.get("construction"),
                        "gold_label": sample["gold_label"],
                        "predicted_label": judgment.label.value,
                        "gold_error_type": sample.get("gold_error_type"),
                        "predicted_error_type": judgment.claim_error_type.value
                        if judgment.claim_error_type
                        else None,
                        "gold_severity": sample["gold_severity"],
                        "predicted_severity": judgment.severity.value,
                        "gold_evidence_chunk_ids": sample["gold_evidence_chunk_ids"],
                        "retrieval_hit": retrieval_hit,
                        "candidate_count": len(candidates),
                        "predicted_evidence_ids": judgment.evidence_ids,
                        "explanation": judgment.explanation,
                    }
                )
        paper_summaries[current_paper_id] = build_summary(
            audits, [ClaimCategory(str(value)) for value in paper["scope"]]
        ).model_dump(mode="json")

    metrics, matrix = _metrics(predictions)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "predictions.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in predictions), encoding="utf-8"
    )
    (output_dir / "metrics.json").write_text(
        json.dumps(
            {"config": {"dry_run": dry_run, "retrieval_top_k": top_k, "oracle_evidence": oracle_evidence}, "metrics": metrics, "paper_summaries": paper_summaries},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    with (output_dir / "confusion_matrix.csv").open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=["gold_label", *[f"predicted_{p}" for p in LABELS]])
        writer.writeheader()
        writer.writerows(matrix)
    return {"metrics": metrics, "output_dir": str(output_dir), "paper_summaries": paper_summaries}


def main() -> None:
    parser = argparse.ArgumentParser(description="运行 PaperAudit 方向一固定原子论断评测。")
    parser.add_argument("--samples", type=Path, default=EVAL_DIR / "resolved_samples.jsonl")
    parser.add_argument("--output-dir", type=Path, default=EVAL_DIR / "results")
    parser.add_argument("--paper-id")
    parser.add_argument("--top-k", type=int, help="覆盖评测时的候选证据数量。")
    parser.add_argument("--dry-run", action="store_true", help="只跑解析和证据检索，不调用 Hy3。")
    parser.add_argument("--oracle-evidence", action="store_true", help="将金标原文 chunk 注入候选集，只评估判断器。")
    parser.add_argument("--papers", type=Path, default=EVAL_DIR / "papers.json")
    args = parser.parse_args()
    print(json.dumps(run(args.samples, args.output_dir, paper_id=args.paper_id, dry_run=args.dry_run, retrieval_top_k=args.top_k, oracle_evidence=args.oracle_evidence, papers_path=args.papers), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
