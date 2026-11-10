"""Run fixed offline ledger checks; optionally score a model-produced benchmark artifact.

No provider calls or project-library writes. A pass is a contract regression result,
not automatic proof of semantic correctness or whole-paper completeness.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from paperaudit.learning_facts import FactMention, LessonFact, check_mention, validate_fact
from paperaudit.models import PaperChunk

SUITE = Path(__file__).resolve().parents[1] / "tests/fixtures/lecture_facts"


def load_case(path: Path):
    case = json.loads(path.read_text())
    sources = {c["chunk_id"]: PaperChunk.model_validate(c) for c in case["chunks"]}
    facts = {f["fact_id"]: LessonFact.model_validate(f) for f in case["facts"]}
    if len(facts) != len(case["facts"]):
        raise ValueError("Duplicate fixture fact IDs")
    errors = [e.model_dump() for fact in facts.values() for e in validate_fact(fact, sources)]
    if errors:
        raise ValueError(f"Invalid fixture facts: {errors}")
    return case, sources, facts


def evaluate_case(path: Path) -> dict:
    case, _, facts = load_case(path)
    results = []
    for example in case["examples"]:
        fact = facts[example["fact_id"]]
        mention = FactMention(fact_id=fact.fact_id, point_index=0, excerpt=example["excerpt"])
        issues = check_mention(fact, mention, example["explanation"],
                               set(example.get("cited_chunk_ids", [a.chunk_id for a in fact.sources])))
        actual = sorted({e.code for e in issues})
        expected = sorted(example["expected_codes"])
        results.append({"name": example["name"], "passed": actual == expected,
                        "expected": expected, "actual": actual})
    return {"case_id": case["case_id"], "paper_type": case["paper_type"],
            "provenance": case["provenance"], "passed": all(r["passed"] for r in results),
            "examples": results}


def evaluate_artifact(path: Path, artifact: dict) -> dict:
    """Benchmark artifacts use fixture fact IDs; never derive gold labels from output."""
    case, sources, gold = load_case(path)
    failures = []
    actual = {}
    for item in artifact.get("facts", []):
        fact = LessonFact.model_validate(item)
        if fact.fact_id in actual:
            failures.append({"fact_id": fact.fact_id, "code": "duplicate_fact"})
        actual[fact.fact_id] = fact
        failures.extend(e.model_dump() for e in validate_fact(fact, sources))
    for fid in gold.keys() - actual.keys():
        failures.append({"fact_id": fid, "code": "missing_gold_fact"})
    for fid in actual.keys() - gold.keys():
        failures.append({"fact_id": fid, "code": "unexpected_fact"})
    # A benchmark fixes canonical labels so output cannot make a wrong binding
    # pass merely by redefining its own ledger. Live semantic review remains needed.
    for fid in gold.keys() & actual.keys():
        for field in ("kind", "subject", "dataset", "metric", "source_value", "value", "unit",
                      "conditions", "status", "uncertainty", "conflict_group"):
            if getattr(gold[fid], field) != getattr(actual[fid], field):
                failures.append({"fact_id": fid, "code": "gold_binding_mismatch", "field": field})
    entries = artifact.get("mentions", [])
    for fid, fact in gold.items():
        mentions = [m for m in entries if m.get("fact_id") == fid]
        if len(mentions) != 1:
            failures.append({"fact_id": fid, "code": "missing_or_duplicate_mention"})
            continue
        item = mentions[0]
        failures.extend(e.model_dump() for e in check_mention(fact,
            FactMention(fact_id=fid, point_index=0, excerpt=item["excerpt"]),
            item["explanation"], set(item["cited_chunk_ids"])))
    for item in entries:
        if item.get("fact_id") not in gold:
            failures.append({"fact_id": item.get("fact_id"), "code": "unknown_mention"})
    return {"case_id": case["case_id"], "passed": not failures, "failures": failures}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", type=Path)
    parser.add_argument("--artifact", type=Path, help="Benchmark facts/mentions JSON; requires --case")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.artifact and not args.case:
        parser.error("--artifact requires --case")
    if args.artifact:
        cases = [evaluate_artifact(args.case, json.loads(args.artifact.read_text()))]
    else:
        cases = [evaluate_case(p) for p in ([args.case] if args.case else sorted(SUITE.glob("*.json")))]
    result = {"mode": "offline_contract_checks", "semantic_quality_certified": False,
              "passed": bool(cases) and all(c["passed"] for c in cases), "cases": cases}
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"passed": result["passed"], "cases": len(cases),
                      "examples": sum(len(c.get("examples", [])) for c in cases)}, ensure_ascii=False))
    for case in cases:
        if not case["passed"]:
            print(json.dumps(case, ensure_ascii=False))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
