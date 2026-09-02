from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from statistics import fmean, pstdev
from typing import Any

from paperaudit.models import (
    AtomicClaim,
    AutoLabel,
    ClaimAudit,
    ClaimCategory,
    ClaimErrorType,
    ClaimJudgment,
    EvidenceCandidate,
    Severity,
)
from paperaudit.scoring import build_summary
from run_eval import run as run_eval


EVAL_DIR = Path(__file__).resolve().parent


def _synthetic_audits(labels: list[AutoLabel], *, error: bool = False) -> list[ClaimAudit]:
    audits: list[ClaimAudit] = []
    for index, label in enumerate(labels, start=1):
        category = ClaimCategory.CONTRIBUTION if index % 2 else ClaimCategory.RESULTS
        claim_id = f"probe_{index}"
        judgment = ClaimJudgment(
            claim_id=claim_id,
            label=label,
            evidence_ids=[f"{claim_id}_e1"] if label != AutoLabel.ABSTAIN else [],
            explanation="probe",
            claim_error_type=(
                ClaimErrorType.OVERGENERALIZATION
                if error and label != AutoLabel.SUPPORTED
                else None
            ),
            severity=Severity.MEDIUM if error and label != AutoLabel.SUPPORTED else Severity.NONE,
        )
        claim = AtomicClaim(
            claim_id=claim_id,
            text=("probe claim " + "extra wording " * 40) if error else "probe claim",
            category=category,
            key_claim=True,
            query_en="probe claim",
            provided_evidence="第1页",
        )
        candidate = EvidenceCandidate(
            evidence_id=f"{claim_id}_e1", chunk_id="p1_b1", page=1, text="probe", score=1.0
        )
        audits.append(ClaimAudit(claim=claim, candidates=[candidate], judgment=judgment))
    return audits


def scoring_probes() -> dict[str, Any]:
    scope = [ClaimCategory.CONTRIBUTION, ClaimCategory.RESULTS]
    groups = {
        "good": _synthetic_audits([AutoLabel.SUPPORTED] * 8),
        "medium": _synthetic_audits(
            [AutoLabel.SUPPORTED] * 4 + [AutoLabel.PARTIALLY_SUPPORTED] * 4, error=True
        ),
        "bad": _synthetic_audits([AutoLabel.CONTRADICTED] * 8, error=True),
    }
    scores = {
        name: build_summary(audits, scope).model_dump(mode="json")
        for name, audits in groups.items()
    }
    adversarial = build_summary(
        _synthetic_audits([AutoLabel.SUPPORTED] * 8, error=True), scope
    ).model_dump(mode="json")
    ordered = scores["good"]["total_score"] > scores["medium"]["total_score"] > scores["bad"]["total_score"]
    invariant = scores["good"]["total_score"] == adversarial["total_score"]
    return {
        "scores": scores,
        "discrimination_order_correct": ordered,
        "adversarial_length_invariance": invariant,
        "note": "这是评分器层面的自动探针，不等价于对 Hy3 生成报告的人工质量判断。",
    }


def consistency_validation(samples_path: Path, output_dir: Path, repeats: int, count: int) -> dict[str, Any]:
    rows = [json.loads(line) for line in samples_path.read_text(encoding="utf-8").splitlines() if line]
    selected: list[dict[str, Any]] = []
    # Preserve at least one sample per paper for small probes, while allowing
    # a full-set run (count >= number of rows) to measure consistency on every
    # fixed claim rather than silently collapsing to one claim per paper.
    if count >= len(rows):
        selected = rows[:]
    else:
        seen_papers: set[str] = set()
        for row in rows:
            if row["paper_id"] in seen_papers:
                continue
            selected.append(row)
            seen_papers.add(row["paper_id"])
            if len(selected) >= count:
                break
    selected_path = output_dir / "consistency_samples.jsonl"
    selected_path.parent.mkdir(parents=True, exist_ok=True)
    selected_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in selected), encoding="utf-8"
    )
    run_rows: list[list[dict[str, Any]]] = []
    totals: list[float] = []
    for index in range(repeats):
        run_dir = output_dir / f"run_{index + 1}"
        result = run_eval(selected_path, run_dir)
        run_rows.append([json.loads(line) for line in (run_dir / "predictions.jsonl").read_text(encoding="utf-8").splitlines() if line])
        paper_scores = [value["total_score"] for value in result["paper_summaries"].values() if value["total_score"] is not None]
        totals.append(fmean(paper_scores) if paper_scores else math.nan)
    by_sample: dict[str, list[str]] = defaultdict(list)
    for result_rows in run_rows:
        for row in result_rows:
            by_sample[row["sample_id"]].append(row["predicted_label"])
    pairwise = []
    for values in by_sample.values():
        pairs = len(values) * (len(values) - 1) // 2
        pairwise.append(sum(left == right for i, left in enumerate(values) for right in values[i + 1 :]) / pairs if pairs else 1.0)
    return {
        "sample_count": len(selected),
        "repeats": repeats,
        "label_pairwise_agreement": round(fmean(pairwise), 4) if pairwise else None,
        "mean_paper_score": round(fmean(totals), 4) if totals else None,
        "paper_score_std": round(pstdev(totals), 4) if len(totals) > 1 else 0.0,
        "runs": [str(output_dir / f"run_{index + 1}") for index in range(repeats)],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="运行 PaperAudit 的自动有效性验证。")
    parser.add_argument("--samples", type=Path, default=EVAL_DIR / "resolved_samples.jsonl")
    parser.add_argument("--output-dir", type=Path, default=EVAL_DIR / "validation")
    parser.add_argument("--consistency", action="store_true", help="重复调用 Hy3 做一致性验证。")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--count", type=int, default=5, help="一致性验证样本数（默认每篇论文取一条）。")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    result: dict[str, Any] = {"scoring_probes": scoring_probes()}
    if args.consistency:
        result["consistency"] = consistency_validation(args.samples, args.output_dir, args.repeats, args.count)
    (args.output_dir / "validation.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
