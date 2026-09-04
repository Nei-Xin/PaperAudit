"""运行方向一完整报告三档判别与重复一致性实验。"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from difflib import SequenceMatcher
from itertools import combinations
from pathlib import Path
from statistics import fmean, pstdev
from typing import Any

from paperaudit.config import Settings
from paperaudit.models import ClaimCategory
from paperaudit.pdf_parser import parse_pdf
from paperaudit.service import AuditService


ROOT = Path(__file__).resolve().parents[1]
EVAL_DIR = ROOT / "eval"
DEFAULT_DATASET_DIR = EVAL_DIR / "direction_one_report_test"
DEFAULT_OUTPUT_DIR = DEFAULT_DATASET_DIR / "results_actual"
NEGATIVE_LABELS = {"PARTIALLY_SUPPORTED", "CONTRADICTED", "NO_SUPPORT_FOUND"}
HIGH_SEVERITIES = {"high", "critical"}


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _git_metadata() -> dict[str, Any]:
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    diff = subprocess.run(
        ["git", "diff", "--binary", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout
    return {
        "commit": commit,
        "working_tree_clean": not bool(status.strip()),
        "working_tree_diff_sha256": _sha256_bytes(diff),
    }


def _runtime_metadata(settings: Settings) -> dict[str, Any]:
    return {
        "model": settings.model,
        "reasoning_effort": settings.reasoning_effort,
        "temperature": settings.temperature,
        "top_p": settings.top_p,
        "retrieval_top_k": settings.retrieval_top_k,
        "judge_batch_size": settings.judge_batch_size,
        "max_paper_chars": settings.max_paper_chars,
        "prompt_source_sha256": _sha256_file(ROOT / "src" / "paperaudit" / "hy3_client.py"),
        "audit_rules_sha256": _sha256_file(ROOT / "src" / "paperaudit" / "audit_rules.py"),
        "scoring_sha256": _sha256_file(ROOT / "src" / "paperaudit" / "scoring.py"),
        "service_sha256": _sha256_file(ROOT / "src" / "paperaudit" / "service.py"),
        "runner_sha256": _sha256_file(Path(__file__)),
    }


def validate_dataset(dataset_dir: Path) -> dict[str, Any]:
    manifest = json.loads((dataset_dir / "manifest.json").read_text(encoding="utf-8"))
    reports = _load_jsonl(dataset_dir / str(manifest["files"]["report_index"]))
    mutations = _load_jsonl(dataset_dir / str(manifest["files"]["mutations"]))
    papers = json.loads((dataset_dir / str(manifest["files"]["papers"])).read_text(encoding="utf-8"))
    paper_by_id = {str(row["paper_id"]): row for row in papers}
    if len(reports) != int(manifest["report_count"]):
        raise ValueError("report_index 数量与 manifest 不一致。")
    if len({str(row["report_id"]) for row in reports}) != len(reports):
        raise ValueError("report_id 不唯一。")
    by_paper: dict[str, set[str]] = {}
    for row in reports:
        paper_id = str(row["paper_id"])
        by_paper.setdefault(paper_id, set()).add(str(row["tier"]))
        report_path = dataset_dir / str(row["report_path"])
        if _sha256_file(report_path) != row["report_sha256"]:
            raise ValueError(f"{row['report_id']} 报告 SHA-256 不匹配。")
        if paper_id not in paper_by_id:
            raise ValueError(f"{row['report_id']} 缺少论文元数据。")
    expected_tiers = {"high", "medium", "low"}
    if any(tiers != expected_tiers for tiers in by_paper.values()):
        raise ValueError("每篇论文必须恰好包含高、中、低三档报告。")
    for paper_id, paper in paper_by_id.items():
        pdf_path = EVAL_DIR / str(paper["local_pdf"])
        if _sha256_file(pdf_path) != paper["sha256"]:
            raise ValueError(f"{paper_id} PDF SHA-256 不匹配。")
    report_ids = {str(row["report_id"]) for row in reports}
    if any(str(row["report_id"]) not in report_ids for row in mutations):
        raise ValueError("mutations 包含未知 report_id。")
    return {
        "manifest": manifest,
        "reports": reports,
        "mutations": mutations,
        "papers": papers,
        "paper_by_id": paper_by_id,
    }


def _normalize(text: str) -> str:
    return re.sub(r"[\W_]+", "", text.lower())


def _similarity(expected: dict[str, Any], audit: dict[str, Any]) -> float:
    left = _normalize(str(expected.get("claim_text") or expected.get("text") or ""))
    claim = audit["claim"]
    right = _normalize(str(claim["text"]))
    if not left or not right:
        return 0.0
    score = SequenceMatcher(None, left, right).ratio()
    if str(expected.get("category")) == str(claim.get("category")):
        score = min(1.0, score + 0.08)
    return score


def _align(
    expected: list[dict[str, Any]],
    audits: list[dict[str, Any]],
    *,
    threshold: float,
) -> list[tuple[int, int, float]]:
    candidates = sorted(
        (
            (_similarity(item, audit), left_index, right_index)
            for left_index, item in enumerate(expected)
            for right_index, audit in enumerate(audits)
        ),
        reverse=True,
    )
    used_left: set[int] = set()
    used_right: set[int] = set()
    matches: list[tuple[int, int, float]] = []
    for score, left_index, right_index in candidates:
        if score < threshold:
            break
        if left_index in used_left or right_index in used_right:
            continue
        used_left.add(left_index)
        used_right.add(right_index)
        matches.append((left_index, right_index, round(score, 4)))
    return sorted(matches)


def _pairwise_label_agreement(left: dict[str, Any], right: dict[str, Any]) -> float:
    left_audits = list(left["audit"]["audits"])
    right_audits = list(right["audit"]["audits"])
    expected = [
        {"text": row["claim"]["text"], "category": row["claim"]["category"]}
        for row in left_audits
    ]
    matches = _align(expected, right_audits, threshold=0.45)
    equal = sum(
        left_audits[left_index]["judgment"]["label"]
        == right_audits[right_index]["judgment"]["label"]
        for left_index, right_index, _ in matches
    )
    denominator = max(len(left_audits), len(right_audits), 1)
    return equal / denominator


def _report_summary(report: dict[str, Any], runs: list[dict[str, Any]]) -> dict[str, Any]:
    scores = [row["audit"]["summary"]["total_score"] for row in runs]
    numeric_scores = [float(value) for value in scores if value is not None]
    coverages = [float(row["audit"]["summary"]["audit_coverage"]) for row in runs]
    agreements = [_pairwise_label_agreement(left, right) for left, right in combinations(runs, 2)]
    grades = [str(row["audit"]["summary"]["grade"]) for row in runs]
    return {
        "report_id": report["report_id"],
        "paper_id": report["paper_id"],
        "tier": report["tier"],
        "run_count": len(runs),
        "scores": scores,
        "mean_score": round(fmean(numeric_scores), 4) if numeric_scores else None,
        "score_std": round(pstdev(numeric_scores), 4) if len(numeric_scores) > 1 else 0.0,
        "mean_audit_coverage": round(fmean(coverages), 4),
        "label_pairwise_agreement": round(fmean(agreements), 4) if agreements else None,
        "grades": dict(Counter(grades)),
        "claim_counts": [len(row["audit"]["audits"]) for row in runs],
    }


def summarize(
    dataset: dict[str, Any],
    output_dir: Path,
    selected_reports: list[dict[str, Any]],
    repeats: int,
) -> dict[str, Any]:
    wrappers_by_report: dict[str, list[dict[str, Any]]] = {}
    for report in selected_reports:
        report_id = str(report["report_id"])
        wrappers_by_report[report_id] = [
            json.loads((output_dir / f"run_{repeat}" / f"{report_id}.json").read_text(encoding="utf-8"))
            for repeat in range(1, repeats + 1)
        ]
    report_rows = [
        _report_summary(report, wrappers_by_report[str(report["report_id"])])
        for report in selected_reports
    ]

    ranking_rows = []
    for paper_id in dict.fromkeys(str(row["paper_id"]) for row in selected_reports):
        rows = [row for row in report_rows if row["paper_id"] == paper_id]
        scores = {str(row["tier"]): row["mean_score"] for row in rows}
        if set(scores) != {"high", "medium", "low"} or any(value is None for value in scores.values()):
            continue
        ordered = bool(scores["high"] > scores["medium"] > scores["low"])
        ranking_rows.append({"paper_id": paper_id, "scores": scores, "ordered": ordered})

    selected_ids = {str(row["report_id"]) for row in selected_reports}
    high_mutations = [
        row
        for row in dataset["mutations"]
        if str(row["report_id"]) in selected_ids and str(row["gold_severity"]) in HIGH_SEVERITIES
    ]
    mutation_results = []
    for mutation in high_mutations:
        detected_runs = 0
        alignments = []
        for wrapper in wrappers_by_report[str(mutation["report_id"])]:
            audits = list(wrapper["audit"]["audits"])
            matches = _align([mutation], audits, threshold=0.40)
            if not matches:
                alignments.append({"matched": False})
                continue
            _, audit_index, score = matches[0]
            judgment = audits[audit_index]["judgment"]
            detected = (
                str(judgment["label"]) in NEGATIVE_LABELS
                and str(judgment["severity"]) in HIGH_SEVERITIES
            )
            detected_runs += int(detected)
            alignments.append(
                {
                    "matched": True,
                    "score": score,
                    "predicted_claim": audits[audit_index]["claim"]["text"],
                    "label": judgment["label"],
                    "severity": judgment["severity"],
                    "detected": detected,
                }
            )
        mutation_results.append(
            mutation
            | {
                "detected_runs": detected_runs,
                "detected_by_majority": detected_runs >= repeats // 2 + 1,
                "alignments": alignments,
            }
        )

    report_agreements = [
        float(row["label_pairwise_agreement"])
        for row in report_rows
        if row["label_pairwise_agreement"] is not None
    ]
    score_stds = [float(row["score_std"]) for row in report_rows]
    coverages = [float(row["mean_audit_coverage"]) for row in report_rows]
    ranking_accuracy = (
        sum(row["ordered"] for row in ranking_rows) / len(ranking_rows) if ranking_rows else None
    )
    high_risk_recall = (
        sum(row["detected_by_majority"] for row in mutation_results) / len(mutation_results)
        if mutation_results
        else None
    )
    aggregate = {
        "report_count": len(report_rows),
        "paper_count": len({str(row["paper_id"]) for row in selected_reports}),
        "ranking_paper_count": len(ranking_rows),
        "ranking_accuracy": round(ranking_accuracy, 4) if ranking_accuracy is not None else None,
        "mean_label_pairwise_agreement": round(fmean(report_agreements), 4)
        if report_agreements
        else None,
        "mean_report_score_std": round(fmean(score_stds), 4) if score_stds else None,
        "max_report_score_std": round(max(score_stds), 4) if score_stds else None,
        "mean_audit_coverage": round(fmean(coverages), 4) if coverages else None,
        "high_risk_mutation_count": len(mutation_results),
        "high_risk_recall": round(high_risk_recall, 4) if high_risk_recall is not None else None,
    }
    thresholds = dataset["manifest"]["thresholds"]
    checks = {
        "complete_three_tier_ranking": bool(
            ranking_accuracy is not None and ranking_accuracy >= thresholds["ranking_accuracy"]
        ),
        "label_pairwise_agreement": bool(
            aggregate["mean_label_pairwise_agreement"] is not None
            and aggregate["mean_label_pairwise_agreement"]
            >= thresholds["label_pairwise_agreement"]
        ),
        "mean_report_score_std": bool(
            aggregate["mean_report_score_std"] is not None
            and aggregate["mean_report_score_std"] <= thresholds["mean_report_score_std"]
        ),
        "mean_audit_coverage": bool(
            aggregate["mean_audit_coverage"] is not None
            and aggregate["mean_audit_coverage"] >= thresholds["mean_audit_coverage"]
        ),
        "high_risk_recall": bool(
            aggregate["high_risk_recall"] is not None
            and aggregate["high_risk_recall"] >= thresholds["high_risk_recall"]
        ),
    }
    full_dataset = len(selected_reports) == int(dataset["manifest"]["report_count"])
    result = {
        "experiment": dataset["manifest"]["dataset"],
        "full_dataset": full_dataset,
        "passed": all(checks.values()) if full_dataset else None,
        "thresholds": thresholds,
        "checks": checks,
        "aggregate": aggregate,
        "ranking": ranking_rows,
        "reports": report_rows,
        "high_risk_mutations": mutation_results,
        "policy": dataset["manifest"]["policy"],
    }
    (output_dir / "summary.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return result


def run(
    dataset_dir: Path,
    output_dir: Path,
    *,
    repeats: int,
    paper_id: str | None,
    report_id: str | None,
    resume: bool,
    workers: int,
) -> dict[str, Any]:
    dataset = validate_dataset(dataset_dir)
    reports = [
        row
        for row in dataset["reports"]
        if (paper_id is None or str(row["paper_id"]) == paper_id)
        and (report_id is None or str(row["report_id"]) == report_id)
    ]
    if not reports:
        raise ValueError("没有匹配的实验报告。")
    settings = Settings.from_env()
    if not settings.is_configured:
        raise ValueError("真实 API 未配置，请检查 HY3_API_BASE、HY3_API_KEY 和 HY3_MODEL。")
    runtime = _runtime_metadata(settings)
    git = _git_metadata()
    dataset_hashes = {
        name: _sha256_file(dataset_dir / str(relative_path))
        for name, relative_path in dataset["manifest"]["files"].items()
    }
    run_config = {
        "dataset_manifest_sha256": _sha256_file(dataset_dir / "manifest.json"),
        "dataset_file_sha256": dataset_hashes,
        "runtime": runtime,
        "git": git,
        "repeats": repeats,
        "workers": workers,
    }
    run_config_hash = _sha256_bytes(
        json.dumps(run_config, ensure_ascii=False, sort_keys=True).encode("utf-8")
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "run_config.json").write_text(
        json.dumps(run_config | {"run_config_sha256": run_config_hash}, ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )

    parsed_by_paper: dict[str, Any] = {}
    for paper_key in {str(report["paper_id"]) for report in reports}:
        paper = dataset["paper_by_id"][paper_key]
        parsed_by_paper[paper_key] = parse_pdf(
            (EVAL_DIR / str(paper["local_pdf"])).read_bytes()
        )

    def execute(report: dict[str, Any], repeat: int, output_path: Path) -> None:
        paper_key = str(report["paper_id"])
        report_text = (dataset_dir / str(report["report_path"])).read_text(encoding="utf-8")
        paper_scope = dataset["paper_by_id"][paper_key]["scope"]
        audit = AuditService(settings).audit(
            parsed_by_paper[paper_key],
            report_text,
            [ClaimCategory(str(value)) for value in paper_scope],
            mode="direction_one_report_test",
        )
        wrapper = {
            "report_id": str(report["report_id"]),
            "paper_id": paper_key,
            "tier": report["tier"],
            "repeat": repeat,
            "run_config_sha256": run_config_hash,
            "audit": audit.model_dump(mode="json"),
        }
        output_path.write_text(
            json.dumps(wrapper, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    total = len(reports) * repeats
    completed = 0
    for repeat in range(1, repeats + 1):
        run_dir = output_dir / f"run_{repeat}"
        run_dir.mkdir(parents=True, exist_ok=True)
        pending: list[tuple[dict[str, Any], Path]] = []
        for report in reports:
            report_key = str(report["report_id"])
            output_path = run_dir / f"{report_key}.json"
            if resume and output_path.is_file():
                existing = json.loads(output_path.read_text(encoding="utf-8"))
                if existing.get("run_config_sha256") != run_config_hash:
                    raise ValueError(f"{output_path} 的运行配置不匹配，不能 resume。")
                completed += 1
                print(f"[{completed}/{total}] reuse {report_key} run {repeat}", flush=True)
                continue
            pending.append((report, output_path))
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(execute, report, repeat, output_path): str(report["report_id"])
                for report, output_path in pending
            }
            for future in as_completed(futures):
                future.result()
                completed += 1
                print(
                    f"[{completed}/{total}] complete {futures[future]} run {repeat}", flush=True
                )
    return summarize(dataset, output_dir, reports, repeats)


def main() -> None:
    parser = argparse.ArgumentParser(description="运行方向一完整报告三档判别实验。")
    parser.add_argument("--dataset-dir", type=Path, default=DEFAULT_DATASET_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--paper-id")
    parser.add_argument("--report-id")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    if args.repeats < 1:
        raise SystemExit("--repeats 必须大于 0。")
    if args.workers < 1:
        raise SystemExit("--workers 必须大于 0。")
    if args.validate_only:
        dataset = validate_dataset(args.dataset_dir)
        print(
            json.dumps(
                {
                    "valid": True,
                    "paper_count": len(dataset["papers"]),
                    "report_count": len(dataset["reports"]),
                    "mutation_count": len(dataset["mutations"]),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return
    result = run(
        args.dataset_dir,
        args.output_dir,
        repeats=args.repeats,
        paper_id=args.paper_id,
        report_id=args.report_id,
        resume=args.resume,
        workers=args.workers,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["full_dataset"] and not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
