"""Targeted real-API regression for citation, scope and false-positive repairs.

Reuses three known failing reports as development regressions, once each.
python -m eval.check_core_repairs
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path

from eval.run_core_report_validation import prepare, file_hash, DATASET, ROOT
from eval.run_report_discrimination import validate_dataset, _runtime_metadata
from paperaudit.claim_extraction import split_report_sources
from paperaudit.config import Settings
from paperaudit.models import ClaimCategory
from paperaudit.pdf_parser import parse_pdf
from paperaudit.service import AuditService


OUTPUT = ROOT / "eval/core_repairs_20260905"


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    if OUTPUT.exists():
        raise SystemExit("Refusing to overwrite repair verification results.")
    dataset = validate_dataset(DATASET)
    reports, expected = prepare(dataset)
    settings = Settings.from_env()
    OUTPUT.mkdir()
    save(OUTPUT / "config.json", {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "runtime": _runtime_metadata(settings), "reports": reports, "expected": expected,
        "source_sha256": {str(p.relative_to(ROOT)): file_hash(p) for p in (ROOT / "src/paperaudit").glob("*.py")},
        "policy": "Known failing development reports, one run each. Preserve old validation; no independent quality claim.",
    })

    def run(report):
        rid = report["report_id"]
        print(f"START {rid}", flush=True)
        meta = dataset["paper_by_id"][report["paper_id"]]
        text = (DATASET / report["report_path"]).read_text(encoding="utf-8")
        paper = parse_pdf((ROOT / "eval" / meta["local_pdf"]).read_bytes())
        audit = AuditService(settings).audit(paper, text, [ClaimCategory(s) for s in meta["scope"]],
            progress=lambda stage, value: print(f"PROGRESS {rid} {value:.0%}", flush=True))
        save(OUTPUT / f"{rid}.json", audit.model_dump(mode="json"))
        grouped = {g["source_id"]: [a for a in audit.audits if a.claim.source_id == g["source_id"]]
                   for g in expected[rid]}
        source_by_id = {s.source_id: s for s in split_report_sources(text)}
        anchored = [g for g in expected[rid] if "证据：" in source_by_id[g["source_id"]].text]
        citations_kept = sum(bool(grouped[g["source_id"]]) and all(
            a.claim.provided_evidence and a.claim.provided_evidence in source_by_id[g["source_id"]].text
            for a in grouped[g["source_id"]]) for g in anchored)
        supported = [g for g in expected[rid] if g["gold_label"] == "SUPPORTED"]
        high = [g for g in expected[rid] if g["gold_severity"] == "high"]
        result = {
            "report_id": rid, "claim_count": len(audit.audits),
            "expected_sources": len(grouped), "extracted_sources": sum(bool(v) for v in grouped.values()),
            "expected_citations": len(anchored), "retained_citations": citations_kept,
            "supported_high_risk_false_positives": [g["text"] for g in supported if any(
                a.judgment.severity.value in {"high", "critical"} for a in grouped[g["source_id"]])],
            "high_risk_expected": len(high), "high_risk_detected": sum(any(a.judgment.severity.value in {"high", "critical"}
                and a.judgment.label.value != "ABSTAIN" for a in grouped[g["source_id"]]) for g in high),
            "fabricated_page_detected": any(a.judgment.evidence_error_type and a.judgment.evidence_error_type.value == "fabricated_evidence" for a in audit.audits),
        }
        print(f"DONE {rid}: {json.dumps(result, ensure_ascii=True)}", flush=True)
        return result

    with ThreadPoolExecutor(max_workers=3) as pool:
        rows = list(pool.map(run, reports))
    checks = {
        "all_expected_facts_extracted": all(r["expected_sources"] == r["extracted_sources"] for r in rows),
        "all_citations_preserved": all(r["expected_citations"] == r["retained_citations"] for r in rows),
        "no_supported_high_risk_false_positive": all(not r["supported_high_risk_false_positives"] for r in rows),
        "known_high_risk_errors_detected": all(r["high_risk_expected"] == r["high_risk_detected"] for r in rows),
        "fake_page_detected": next(r for r in rows if r["report_id"] == "R018")["fabricated_page_detected"],
    }
    summary = {"passed": all(checks.values()), "checks": checks, "reports": rows,
               "limitation": "One run of three known development reports, not a new full stability benchmark."}
    save(OUTPUT / "summary.json", summary)
    print(json.dumps(summary, ensure_ascii=True), flush=True)


if __name__ == "__main__":
    main()
