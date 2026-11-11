"""Score observations.jsonl against cases.json and print a Markdown report.

One prediction per observation, on the same scale for both pipelines:
CONSISTENT, INCONSISTENT, NOT_LOCATED, PARTIAL, MIXED, ABSTAIN or ERROR.
Failed and abstaining observations stay in every denominator.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RELATION = {"IMPLEMENTS": "CONSISTENT", "CONFIGURES": "CONSISTENT", "EVALUATES": "CONSISTENT",
            "LOADS_DATA": "CONSISTENT", "DOCUMENTS": "CONSISTENT", "MISMATCH": "INCONSISTENT",
            "PARTIAL_MATCH": "PARTIAL", "NOT_LOCATED": "NOT_LOCATED"}


def predict(row: dict, item: dict) -> str:
    if "error" in row:
        return "ERROR"
    if row["status"] != "ANSWERED":
        return "ABSTAIN"
    findings = row.get("findings") or []
    if row["mode"] == "fixed" or (row.get("trace") or {}).get("fallback"):
        return RELATION.get(row.get("relation"), "ABSTAIN")
    if not findings:
        return "ABSTAIN"
    verdicts = {finding["verdict"] for finding in findings}
    if len(verdicts) > 1:
        # Several findings disagree: keep those about the point the question asks for.
        on_topic = {finding["verdict"] for finding in findings
                    if any(word.casefold() in finding["text"].casefold() for word in item["keywords"])}
        verdicts = on_topic or verdicts
    return verdicts.pop() if len(verdicts) == 1 else "MIXED"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--export", type=Path, help="also write one compact line per observation here")
    args = parser.parse_args()
    protocol = json.loads((args.run / "protocol.json").read_text())
    items = {item["id"]: item for item in
             json.loads((HERE / protocol.get("cases", "cases.json")).read_text())["items"]}
    rows = [json.loads(line) for line in (args.run / "observations.jsonl").read_text().splitlines()]
    rows = [row for row in rows if row["event"] == "result"]
    for row in rows:
        item = items[row["item"]]
        row["predicted"], row["expected"] = predict(row, item), item["expected"]
        row["correct"] = row["predicted"] == row["expected"]
        cited = " ".join(row.get("code_citations") or [])
        row["located"] = any(path in cited for path in item["gold_paths"]) if item["gold_paths"] else None
        row["stratum"] = ("edited" if item["mutation"] else
                          "natural-" + item["expected"].lower().replace("_", "-"))

    def table(title, key):
        print(f"\n### {title}\n\n| | " + " | ".join(modes) + " |\n|---|" + "---|" * len(modes))
        groups = defaultdict(lambda: defaultdict(list))
        for row in rows:
            groups[key(row)][row["mode"]].append(row)
        for name in sorted(groups):
            cells = [f"{sum(r['correct'] for r in groups[name][m])}/{len(groups[name][m])}" for m in modes]
            print(f"| {name} | " + " | ".join(cells) + " |")

    modes = sorted({row["mode"] for row in rows})
    if args.export:
        args.export.parent.mkdir(parents=True, exist_ok=True)
        with args.export.open("w") as handle:
            for row in sorted(rows, key=lambda r: (r["item"], r["mode"], r["repeat"])):
                trace = row.get("trace") or {}
                handle.write(json.dumps({
                    "item": row["item"], "mode": row["mode"], "repeat": row["repeat"],
                    "expected": row["expected"], "predicted": row["predicted"], "correct": row["correct"],
                    "findings": [finding["verdict"] for finding in row.get("findings") or []],
                    "gold_file_cited": row["located"], "requests": row.get("requests"),
                    "tokens": row.get("tokens"), "seconds": row.get("seconds"),
                    "stop_reason": trace.get("stop_reason"), "fallback": trace.get("fallback"),
                    "used_citation_repair": any(step["tool"] == "submit_answer" and not step["ok"]
                                                for step in trace.get("steps", [])) if trace else None,
                }, ensure_ascii=False) + "\n")
    print(f"# {protocol['version']} · {len(rows)} observations")
    table("Verdict matches reference (all observations in the denominator)", lambda r: "all")
    table("By expected verdict", lambda r: r["expected"])
    table("By construction", lambda r: r["stratum"])
    table("By paper", lambda r: items[r["item"]]["paper"])

    print("\n### Predictions\n\n| mode | " + " | ".join(
        labels := ["CONSISTENT", "INCONSISTENT", "NOT_LOCATED", "PARTIAL", "MIXED", "ABSTAIN", "ERROR"])
        + " |\n|---|" + "---|" * len(labels))
    for mode in modes:
        counts = Counter(row["predicted"] for row in rows if row["mode"] == mode)
        print(f"| {mode} | " + " | ".join(str(counts[label]) for label in labels) + " |")

    print("\n### Unsupported verdicts and cost\n\n| mode | says consistent, reference inconsistent | "
          "says inconsistent, reference consistent | gold file cited | requests | tokens | seconds |\n"
          "|---|---|---|---|---|---|---|")
    for mode in modes:
        own = [row for row in rows if row["mode"] == mode]
        located = [row for row in own if row["located"] is not None]
        print(f"| {mode} | {sum(r['predicted'] == 'CONSISTENT' and r['expected'] == 'INCONSISTENT' for r in own)} "
              f"| {sum(r['predicted'] == 'INCONSISTENT' and r['expected'] == 'CONSISTENT' for r in own)} "
              f"| {sum(r['located'] for r in located)}/{len(located)} "
              f"| {sum(r.get('requests') or 0 for r in own)} | {sum(r.get('tokens') or 0 for r in own)} "
              f"| {sum(r.get('seconds') or 0 for r in own):.0f} |")

    agent = [row for row in rows if row["mode"] == "agent" and row.get("trace")]
    if agent:
        stops = Counter(row["trace"]["stop_reason"] + ("+fallback" if row["trace"]["fallback"] else "")
                        for row in agent)
        repaired = sum(any(s["tool"] == "submit_answer" and not s["ok"] for s in row["trace"]["steps"])
                       for row in agent)
        print(f"\nAgent stop reasons: {dict(stops)}; runs that needed the citation repair: {repaired}/{len(agent)}; "
              f"findings removed after repair: "
              f"{sum(sum(' removed: ' in line for line in row['trace']['rejected_citations']) for row in agent)}")

    repeats = sorted({row["repeat"] for row in rows})
    if len(repeats) > 1:
        print("\n### Across repeats\n\n| mode | per repeat | items always right | sometimes right | never right "
              "| items with one verdict in every repeat | majority verdict right |\n|---|---|---|---|---|---|---|")
        for mode in modes:
            by_item = defaultdict(list)
            for row in rows:
                if row["mode"] == mode:
                    by_item[row["item"]].append(row)
            complete = {name: group for name, group in by_item.items() if len(group) == len(repeats)}
            hits = [sum(r["correct"] for r in group) for group in complete.values()]
            stable = sum(len({r["predicted"] for r in group}) == 1 for group in complete.values())
            majority = sum(Counter(r["predicted"] for r in group).most_common(1)[0][0] == group[0]["expected"]
                           and Counter(r["predicted"] for r in group).most_common(1)[0][1] * 2 > len(group)
                           for group in complete.values())
            per = [f"{sum(r['correct'] for r in rows if r['mode'] == mode and r['repeat'] == n)}"
                   f"/{sum(1 for r in rows if r['mode'] == mode and r['repeat'] == n)}" for n in repeats]
            print(f"| {mode} | {', '.join(per)} | {sum(h == len(repeats) for h in hits)} "
                  f"| {sum(0 < h < len(repeats) for h in hits)} | {sum(h == 0 for h in hits)} "
                  f"| {stable}/{len(complete)} | {majority}/{len(complete)} |")
        if len(modes) == 2:
            first, second = modes
            wins = Counter()
            for name in items:
                a = sum(r["correct"] for r in rows if r["item"] == name and r["mode"] == first)
                b = sum(r["correct"] for r in rows if r["item"] == name and r["mode"] == second)
                wins[first if a > b else second if b > a else "tie"] += 1
            print(f"\nItems where one mode is right more often: {dict(wins)}")

    print("\n### Observations that do not match\n")
    for row in sorted(rows, key=lambda r: (r["item"], r["mode"], r["repeat"])):
        if not row["correct"]:
            print(f"- `{row['item']}` {row['mode']} #{row['repeat']}: expected {row['expected']}, "
                  f"got {row['predicted']} — {(row.get('error') or row.get('answer') or '')[:160]!r}")


if __name__ == "__main__":
    main()
