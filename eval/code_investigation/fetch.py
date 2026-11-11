"""Download the papers and repositories named in the case files and verify their hashes.

Nothing is redistributed with this repository: papers come from arXiv and code
from GitHub at the pinned commit. A hash mismatch means the upstream file is no
longer byte-identical to the one that was evaluated (archives are regenerated
occasionally); the evaluation refuses to run on mismatching inputs.
"""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
from urllib.request import Request, urlopen

HERE = Path(__file__).resolve().parent


def download(url: str, target: Path, expected: str) -> str:
    if not target.exists():
        with urlopen(Request(url, headers={"User-Agent": "paper-code-eval"}), timeout=120) as response:
            target.write_bytes(response.read())
    return "ok" if sha256(target.read_bytes()).hexdigest() == expected else "HASH MISMATCH"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, nargs="+",
                        default=[HERE / "cases.json", HERE / "cases_holdout.json"])
    parser.add_argument("--data", type=Path, default=HERE / "data")
    args = parser.parse_args()
    failed = False
    for cases in args.cases:
        for name, spec in json.loads(cases.read_text())["papers"].items():
            folder = args.data / name
            folder.mkdir(parents=True, exist_ok=True)
            results = {
                "paper.pdf": download(f"https://arxiv.org/pdf/{spec['arxiv']}", folder / "paper.pdf", spec["pdf_sha256"]),
                "repo.zip": download(f"https://codeload.github.com/{spec['repo']}/zip/{spec['commit']}",
                                     folder / "repo.zip", spec["zip_sha256"]),
            }
            failed |= "HASH MISMATCH" in results.values()
            print(name, results)
    if failed:
        raise SystemExit("some inputs differ from the evaluated files")


if __name__ == "__main__":
    main()
