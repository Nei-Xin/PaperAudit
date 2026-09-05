"""One frozen 3-report x 3-run regression check of the core audit changes.

python -m eval.run_core_report_validation
python -m eval.run_core_report_validation --summarize-only
Never changes the application, source reports or their existing gold annotations.
"""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
from itertools import combinations
import json
from pathlib import Path
from statistics import fmean
import time

from eval.build_direction_one_report_test import _base_claims, _claim_for_tier
from eval.run_report_discrimination import _report_summary, validate_dataset, _runtime_metadata
from paperaudit.claim_extraction import split_report_sources
from paperaudit.config import Settings
from paperaudit.models import ClaimCategory
from paperaudit.pdf_parser import parse_pdf
from paperaudit.service import AuditService


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "eval/direction_one_report_test"
OUTPUT = ROOT / "eval/core_report_validation_20260905"
SELECTED = ("R002", "R005", "R018")
THRESHOLDS = {
    "label_pairwise_agreement": 0.90,
    "mean_report_score_std": 3.0,
    "high_risk_majority_recall": 0.80,
    "supported_high_risk_false_positive_rate": 0.0,
    "expected_source_extraction_rate": 1.0,
}


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(dataset):
    samples = [json.loads(line) for line in (ROOT / "eval/final_holdout_resolved_samples.jsonl").read_text(encoding="utf-8").splitlines()]
    reports = [r for r in dataset["reports"] if r["report_id"] in SELECTED]
    expected = {}
    for report in reports:
        text = (DATASET / report["report_path"]).read_text(encoding="utf-8")
        sources = split_report_sources(text)
        gold = [_claim_for_tier(c, report["tier"]) for c in _base_claims(
            report["paper_id"], [s for s in samples if s["paper_id"] == report["paper_id"]],
        )]
        used = set()
        for claim in gold:
            source = next(s for s in sources if claim["text"] in s.text and s.source_id not in used)
            used.add(source.source_id)
            claim["source_id"] = source.source_id
            claim["report_location"] = source.report_location
        expected[report["report_id"]] = gold
    return reports, expected


def summarize():
    config = json.loads((OUTPUT / "protocol.json").read_text(encoding="utf-8"))
    rows, cases, legacy = [], [], []
    for report in config["reports"]:
        rid = report["report_id"]
        wrappers = [json.loads((OUTPUT / f"run_{i}/{rid}.json").read_text(encoding="utf-8")) for i in range(1, 4)]
        rows.append(_report_summary(report, wrappers))
        old = [json.loads((DATASET / f"results_actual/run_{i}/{rid}.json").read_text(encoding="utf-8")) for i in range(1, 4)]
        legacy.append(_report_summary(report, old))
        for gold in config["expected"][rid]:
            observations = []
            for wrapper in wrappers:
                run = wrapper["audit"]
                matches = [a for a in run["audits"] if a["claim"]["source_id"] == gold["source_id"]]
                observations.append({
                    "count": len(matches),
                    "labels": sorted(a["judgment"]["label"] for a in matches),
                    "errors": [a["judgment"]["claim_error_type"] for a in matches],
                    "severities": [a["judgment"]["severity"] for a in matches],
                    "texts": [a["claim"]["text"] for a in matches],
                    "explanations": [a["judgment"]["explanation"] for a in matches],
                    "provided_evidence": [a["claim"]["provided_evidence"] for a in matches],
                    "high_risk": any(a["judgment"]["severity"] in {"high", "critical"} for a in matches),
                })
            cases.append({
                "report_id": rid, "source_id": gold["source_id"], "text": gold["text"],
                "gold_label": gold["gold_label"], "gold_severity": gold["gold_severity"],
                "observations": observations,
                "majority_high_risk": sum(o["high_risk"] for o in observations) >= 2,
                "source_label_agreement": sum(bool(a["count"] and b["count"]) and a["labels"] == b["labels"]
                    for a, b in combinations(observations, 2)) / 3,
            })
    supported = [c for c in cases if c["gold_label"] == "SUPPORTED"]
    high = [c for c in cases if c["gold_severity"] == "high"]
    total_observations = [o for c in cases for o in c["observations"]]
    metrics = {
        "completed_runs": 9,
        "expected_claims": len(cases),
        "expected_source_extraction_rate": fmean(o["count"] > 0 for o in total_observations),
        "source_label_agreement": fmean(c["source_label_agreement"] for c in cases),
        "label_pairwise_agreement": fmean(r["label_pairwise_agreement"] for r in rows),
        "old_same_subset_label_pairwise_agreement": fmean(r["label_pairwise_agreement"] for r in legacy),
        "mean_report_score_std": fmean(r["score_std"] for r in rows),
        "high_risk_gold_count": len(high),
        "high_risk_majority_recall": fmean(c["majority_high_risk"] for c in high),
        "supported_gold_count": len(supported),
        "supported_high_risk_false_positive_rate": fmean(o["high_risk"] for c in supported for o in c["observations"]),
        "supported_negative_rate": fmean(any(l in {"CONTRADICTED", "NO_SUPPORT_FOUND", "PARTIALLY_SUPPORTED"}
            for l in o["labels"]) for c in supported for o in c["observations"]),
        "stable_source_split_count": sum(len({o["count"] for o in c["observations"]}) == 1 for c in cases),
    }
    checks = {k: metrics[k] <= v if k in {"mean_report_score_std", "supported_high_risk_false_positive_rate"}
              else metrics[k] >= v for k, v in config["thresholds"].items()}
    result = {"passed": all(checks.values()), "checks": checks, "metrics": metrics,
              "reports": rows, "old_same_subset": legacy, "cases": cases,
              "limitations": config["limitations"]}
    save(OUTPUT / "summary.json", result)
    print(json.dumps({"passed": result["passed"], "checks": checks, "metrics": metrics}, ensure_ascii=True), flush=True)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--summarize-only", action="store_true")
    args = parser.parse_args()
    if args.summarize_only:
        summarize()
        return
    if (OUTPUT / "protocol.json").exists():
        raise SystemExit("A frozen run already exists; refusing to overwrite or rerun it.")
    dataset = validate_dataset(DATASET)
    reports, expected = prepare(dataset)
    settings = Settings.from_env()
    source_files = list((ROOT / "src/paperaudit").glob("*.py"))
    config = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "reports": reports, "expected": expected, "thresholds": THRESHOLDS,
        "runtime": _runtime_metadata(settings),
        "code_sha256": {str(p.relative_to(ROOT)): file_hash(p) for p in source_files},
        "runner_sha256": file_hash(Path(__file__)),
        "papers": [dataset["paper_by_id"][r["paper_id"]] for r in reports],
        "policy": "Nine calls fixed before observing results; no report, gold, prompt, rule or threshold changes.",
        "limitations": [
            "Existing controlled reports on real papers, not new natural user reports or independent papers.",
            "Gold labels inherited from the frozen dataset; no independent human double annotation.",
            "Each source's extracted subclaims are grouped for coverage; semantic omissions require review.",
            "The old and new same-subset metrics use the same legacy text-alignment formula; scope grouping is additional.",
            "Cross-report ranking is not tested because each paper has only one quality tier selected.",
        ],
    }
    save(OUTPUT / "protocol.json", config)
    for report in reports:
        (OUTPUT / report["report_path"]).parent.mkdir(parents=True, exist_ok=True)
        (OUTPUT / report["report_path"]).write_bytes((DATASET / report["report_path"]).read_bytes())
    parsed = {r["paper_id"]: parse_pdf((ROOT / "eval" / dataset["paper_by_id"][r["paper_id"]]["local_pdf"]).read_bytes()) for r in reports}

    def execute(report, repeat):
        rid = report["report_id"]
        print(f"START {rid} repeat {repeat}", flush=True)
        started = time.monotonic()
        audit = AuditService(settings).audit(
            parsed[report["paper_id"]], (DATASET / report["report_path"]).read_text(encoding="utf-8"),
            [ClaimCategory(s) for s in dataset["paper_by_id"][report["paper_id"]]["scope"]],
            mode="core_report_validation",
            progress=lambda stage, value: print(f"PROGRESS {rid}/{repeat} {value:.0%}", flush=True),
        )
        save(OUTPUT / f"run_{repeat}/{rid}.json", {
            "report_id": rid, "paper_id": report["paper_id"], "tier": report["tier"],
            "repeat": repeat, "elapsed_seconds": round(time.monotonic() - started, 2),
            "audit": audit.model_dump(mode="json"),
        })
        print(f"DONE {rid}/{repeat}: {len(audit.audits)} claims", flush=True)

    failures = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(execute, report, repeat): (report["report_id"], repeat)
                   for repeat in range(1, 4) for report in reports}
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as exc:
                rid, repeat = futures[future]
                message = str(exc)
                for secret in (settings.api_key, settings.api_base):
                    if secret:
                        message = message.replace(secret, "[redacted]")
                failures.append({"report_id": rid, "repeat": repeat, "error": message[:500]})
                print(f"FAILED {rid}/{repeat}: {type(exc).__name__}", flush=True)
    save(OUTPUT / "failures.json", failures)
    if failures:
        raise SystemExit("Some runs failed; retained all completed outputs and failures.")
    summarize()


if __name__ == "__main__":
    main()
