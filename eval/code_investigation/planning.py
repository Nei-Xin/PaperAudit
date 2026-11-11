"""Development-only planning comparison and real API workflow smoke test.

Freeze inputs and protocol before paid calls. Run each strategy three times;
keyword matches are candidates for human review, not semantic coverage scores.
Never resumes or overwrites an existing run directory.
"""
from __future__ import annotations

import argparse
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
import time

from fastapi.testclient import TestClient

from paperaudit.agents.consistency import ConsistencyOrchestrator
from paperaudit.agents.consistency_planner import ConsistencyPlanner, PLANNER_TOOLS
from paperaudit.api.main import create_app
from paperaudit.code_parser import parse_code_zip
from paperaudit.config import Settings
from paperaudit.hy3_client import Hy3Client
from paperaudit.models import ConsistencyPlan
from paperaudit.pdf_parser import parse_pdf
from paperaudit.storage import ProjectStore
from .run import build_archive


def wait_job(http, pid, jid):
    deadline = time.monotonic() + 900
    while time.monotonic() < deadline:
        jobs = http.get(f"/api/projects/{pid}/consistency-jobs").raise_for_status().json()
        job = next(j for j in jobs if j["job_id"] == jid)
        if job["status"] not in {"QUEUED", "RUNNING"}:
            return job
        time.sleep(1)
    raise TimeoutError("workflow did not finish within 900 seconds")


def candidate_matches(plan, items, limit):
    result = {}
    for item in items:
        result[item["id"]] = [c.checkpoint_id for c in plan.checkpoints[:limit]
            if any(word.casefold() in (c.topic + " " + (c.paper_anchor.quote if c.paper_anchor else "")).casefold()
                   for word in item["keywords"])]
    return result


def reading_metrics(plan):
    reads = before_proposal = before_accepted = 0
    proposed = accepted = False
    for step in plan.steps:
        if step.tool in PLANNER_TOOLS and step.ok:
            reads += 1
            before_proposal += not proposed
            before_accepted += not accepted
        elif step.tool == "propose_checkpoint":
            proposed = True
            accepted = accepted or step.ok
    return {"successful_reads": reads,
            "reads_before_first_proposal": before_proposal if proposed else None,
            "reads_before_first_accepted": before_accepted if accepted else None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--paper", default="mae")
    parser.add_argument("--target", type=int, default=20)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--execute", action="store_true", help="execute five chosen points plus one custom question after restart")
    args = parser.parse_args()
    if not 1 <= args.target <= 40 or not 1 <= args.repeats <= 3:
        parser.error("target must be 1–40 and repeats 1–3")
    here = Path(__file__).resolve().parent
    cases = json.loads((here / "cases.json").read_text())
    spec = cases["papers"][args.paper]
    pdf = (args.data / args.paper / "paper.pdf").read_bytes()
    archive = (args.data / args.paper / "repo.zip").read_bytes()
    assert sha256(pdf).hexdigest() == spec["pdf_sha256"]
    assert sha256(archive).hexdigest() == spec["zip_sha256"]
    paper = parse_pdf(pdf)
    codebase = parse_code_zip(build_archive(archive, spec["include"], []), f"{args.paper}.zip")
    settings = replace(Settings.from_env(), consistency_max_requests=160, consistency_concurrency=4)
    items = [i for i in cases["items"] if i["paper"] == args.paper and i["mutation"] is None
             and i["expected"] in {"CONSISTENT", "INCONSISTENT"}]
    args.output.mkdir(parents=True, exist_ok=False)
    root = here.parents[1]
    sources = [*root.joinpath("src/paperaudit").rglob("*.py"), Path(__file__)]
    protocol = {"split": "development", "paper": args.paper, "target": args.target,
        "repeats": args.repeats, "strategies": ["one-shot", "agent"], "model": settings.model,
        "temperature": settings.temperature, "reasoning_effort": settings.reasoning_effort,
        "pdf_sha256": spec["pdf_sha256"], "zip_sha256": spec["zip_sha256"],
        "sources": {str(p.relative_to(root)): sha256(p.read_bytes()).hexdigest() for p in sources},
        "coverage_rule": {
            "scope": "Compare only the first target accepted checkpoints; empty or failed plans score zero.",
            "full": "The topic/question explicitly targets the reference parameter or method in the same "
                    "experimental setting, and the quoted evidence states the required value or method. "
                    "A multi-part reference requires all parts, possibly across multiple checkpoints.",
            "partial": "Some required parts are missing, or the question targets the parameter but its "
                       "quote does not state the value/method. Record partial separately; do not count as full.",
            "miss": "Incidental keywords in a quotation for a different question do not count.",
            "review": "Inspect every checkpoint, not only keyword candidates. Record checkpoint IDs and "
                      "reasons per reference; disclose assessor and absence of independent annotation.",
        },
        "reference_items": [{k: i[k] for k in ("id", "question", "keywords")} for i in items],
        "execute_selection": "first 5 accepted points of first nonempty agent plan, plus one learning-rate question",
        "max_requests": 160, "max_planning_requests_per_strategy": {"one-shot": 3, "agent_with_fallback": 15},
        "planner_limits": {"requests": 12, "seconds": 240, "read_calls": ConsistencyPlanner.MAX_READ_CALLS,
                           "reads_per_turn": ConsistencyPlanner.READS_PER_TURN,
                           "closing_requests": ConsistencyPlanner.CLOSING_REQUESTS},
        "comparison_note": "These are fixed per-strategy ceilings, not equal request consumption. "
                           "Include fallback and failure costs; do not tune or replay after inspecting results."}
    (args.output / "protocol.json").write_text(json.dumps(protocol, ensure_ascii=False, indent=2))
    if not args.run:
        print("Inputs verified; protocol saved. Use a new output directory with --run for paid calls.")
        return
    if not settings.is_configured:
        raise SystemExit("Model configuration is missing")
    store = ProjectStore((args.output / "library").resolve())
    pid = store.save_paper_project(pdf, f"{args.paper}.pdf", paper).project_id
    store.save_codebase(pid, codebase)
    def app():
        return create_app(storage_root=store.storage_root, settings=settings,
                          settings_dir=(args.output / "settings").resolve())
    rows, first_plan = [], None
    for repeat in range(args.repeats):
        # Alternate order to reduce systematic warm-up/order effects.
        order = ["one-shot", "agent"] if repeat % 2 == 0 else ["agent", "one-shot"]
        for strategy in order:
            name = f"{strategy}-{repeat + 1}"
            (args.output / f"{name}.dispatched").write_text("No automatic replay of paid calls.\n")
            if strategy == "agent":
                with TestClient(app()) as http:
                    job = http.post(f"/api/projects/{pid}/consistency-jobs", json={
                        "mode": "plan", "planning_strategy": "agent", "privacy_ack": True, "max_checkpoints": args.target}).raise_for_status().json()
                    completed = wait_job(http, pid, job["job_id"])
                    if completed["status"] != "SUCCEEDED":
                        rows.append({"name": name, "strategy": strategy, "status": completed["status"]})
                        (args.output / f"{name}.job.json").write_text(json.dumps(completed, ensure_ascii=False, indent=2))
                        continue
                    plan = ConsistencyPlan.model_validate(http.get(
                        f"/api/projects/{pid}/consistency-plans/{completed['plan_id']}").raise_for_status().json())
                    first_plan = first_plan or plan
            else:
                plan = ConsistencyOrchestrator(Hy3Client(settings), settings.model,
                    max_checkpoints=args.target).plan(paper, codebase, strategy="one-shot")
            (args.output / f"{name}.json").write_text(plan.model_dump_json(indent=2))
            row = {"name": name, "strategy": strategy, "status": "ok" if plan.checkpoints else "empty",
                "accepted": len(plan.checkpoints), "proposed": plan.proposed, "rejected": plan.rejected,
                "requests": plan.requests, "tokens": plan.tokens, "seconds": plan.elapsed_seconds,
                "fallback": plan.fallback, "stop_reason": plan.stop_reason,
                **reading_metrics(plan),
                "keyword_candidates": candidate_matches(plan, items, args.target)}
            rows.append(row)
            (args.output / "summary.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2))
            print(json.dumps({k: v for k, v in row.items() if k != "keyword_candidates"}), flush=True)
    (args.output / "summary.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2))
    if args.execute and first_plan:
        # A fresh lifespan must recover the persisted plan without replaying it.
        with TestClient(app()) as http:
            endpoint = f"/api/projects/{pid}/consistency-plans/{first_plan.plan_id}/execute"
            body = {"privacy_ack": True, "selected_ids": [c.checkpoint_id for c in first_plan.checkpoints[:5]],
                    "extra_questions": ["预训练代码采用了什么学习率调度，与论文是否对应？"]}
            job = http.post(endpoint, json=body).raise_for_status().json()
            duplicate = http.post(endpoint, json=body).raise_for_status().json()
            assert duplicate["job_id"] == job["job_id"]
            completed = wait_job(http, pid, job["job_id"])
            (args.output / "execution-job.json").write_text(json.dumps(completed, ensure_ascii=False, indent=2))
            assert completed["status"] == "SUCCEEDED", completed["status"]
            report = http.get(f"/api/projects/{pid}/consistency-reports/{completed['report_id']}").raise_for_status().json()
            assert [i["checkpoint"]["checkpoint_id"] for i in report["items"]] == body["selected_ids"] + ["U01"]
            assert report["requests"] <= report["max_requests"]
            (args.output / "execution-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
            print(json.dumps({"execution": report["summary"], "requests": report["requests"],
                              "tokens": report["tokens"], "seconds": report["elapsed_seconds"]}), flush=True)


if __name__ == "__main__":
    main()
