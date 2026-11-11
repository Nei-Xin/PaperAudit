"""Verify that the holdout set shares nothing with the development set and is unchanged since freezing."""

from hashlib import sha256
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
dev = json.loads((HERE / "cases.json").read_text())
holdout_bytes = (HERE / "cases_holdout.json").read_bytes()
holdout = json.loads(holdout_bytes)
freeze = json.loads((HERE / "holdout_freeze.json").read_text())


def keys(cases, field):
    return {spec[field].split("v")[0] if field == "arxiv" else spec[field] for spec in cases["papers"].values()}


problems = []
for field in ("arxiv", "repo", "pdf_sha256", "zip_sha256"):
    if shared := keys(dev, field) & keys(holdout, field):
        problems.append(f"shared {field}: {sorted(shared)}")
if shared := set(dev["papers"]) & set(holdout["papers"]):
    problems.append(f"shared paper keys: {sorted(shared)}")
if shared := {i["id"] for i in dev["items"]} & {i["id"] for i in holdout["items"]}:
    problems.append(f"shared item ids: {sorted(shared)}")
if shared := {i["question"] for i in dev["items"]} & {i["question"] for i in holdout["items"]}:
    problems.append(f"shared questions: {len(shared)}")
if sha256(holdout_bytes).hexdigest() != freeze["cases_holdout_sha256"]:
    problems.append("cases_holdout.json changed after it was frozen")
if problems:
    raise SystemExit("\n".join(problems))
print(f"ok: {len(dev['papers'])} development papers / {len(dev['items'])} items, "
      f"{len(holdout['papers'])} holdout papers / {len(holdout['items'])} items, no overlap; "
      f"holdout frozen {freeze['frozen_on']} at code commit {freeze['code_commit']}")
