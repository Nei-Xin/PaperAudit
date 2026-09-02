"""Create a reproducible paper-level dev/holdout split for peer-review labels.

The split is intentionally defined by OpenReview forum URL rather than row order,
so all issue records from one paper stay in the same partition.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


DEFAULT_HOLDOUT_FORUMS = {
    "https://openreview.net/forum?id=GHlJM45fWY",  # GeoPlant / strong accept
    "https://openreview.net/forum?id=pf9J3GNxSe",  # critical phase / weak reject
    "https://openreview.net/forum?id=PFBXbXpMdi",  # geolocation / borderline
}


def _load(path: Path) -> list[dict[str, object]]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows:
        raise ValueError(f"{path} 为空")
    return rows


def split(rows: list[dict[str, object]], holdout_forums: set[str]) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    unknown = holdout_forums - {str(row.get("openreview_url", "")) for row in rows}
    if unknown:
        raise ValueError("holdout 论文不在回归集中：" + ", ".join(sorted(unknown)))
    dev: list[dict[str, object]] = []
    holdout: list[dict[str, object]] = []
    for row in rows:
        target = holdout if str(row.get("openreview_url", "")) in holdout_forums else dev
        target.append({**row, "split": "holdout" if target is holdout else "dev"})
    if {str(row["openreview_url"]) for row in dev} & {str(row["openreview_url"]) for row in holdout}:
        raise AssertionError("论文级 split 泄漏")
    return dev, holdout


def _write(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="按 OpenReview 论文划分 peer-review dev/holdout")
    parser.add_argument("--input", type=Path, default=Path(__file__).with_name("peer_review_regression.jsonl"))
    parser.add_argument("--dev", type=Path, default=Path(__file__).with_name("peer_review_regression_dev.jsonl"))
    parser.add_argument("--holdout", type=Path, default=Path(__file__).with_name("peer_review_regression_holdout.jsonl"))
    args = parser.parse_args()
    rows = _load(args.input)
    dev, holdout = split(rows, DEFAULT_HOLDOUT_FORUMS)
    _write(args.dev, dev)
    _write(args.holdout, holdout)
    print(json.dumps({
        "dev_records": len(dev),
        "dev_papers": len({str(row["openreview_url"]) for row in dev}),
        "holdout_records": len(holdout),
        "holdout_papers": len({str(row["openreview_url"]) for row in holdout}),
        "holdout_decisions": dict(Counter(str(row["gold_decision"]) for row in holdout)),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
