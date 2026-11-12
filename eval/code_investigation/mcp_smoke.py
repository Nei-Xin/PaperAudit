"""Run the official Inspector against an uploaded MAE project, without model calls.

The config must select PaperAudit's stdio server and the unmodified MAE inputs.
Requires npm; npx obtains pinned Inspector and its supported Node runtime locally.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess

INSPECTOR_VERSION = "2.15.0"
NODE_VERSION = "22.23.4"
CALLS = {
    # Inspector's key=value parser rejects empty values; '.' also denotes the root.
    "list_dir": ({"path": "."}, "main_pretrain.py"),
    "grep_code": ({"text": "warmup_epochs", "path_prefix": "main_pretrain.py"}, "default=40"),
    "search_code": ({"query": "warmup_epochs"}, "main_pretrain.py"),
    "find_symbol": ({"name": "get_args_parser"}, "main_pretrain.py"),
    "read_file": ({"path": "main_pretrain.py", "start_line": 65, "end_line": 75}, "default=40"),
    "search_paper": ({"query": "warmup epochs pre-training"}, "page "),
    "grep_paper": ({"text": "warmup epochs"}, "chunk_id="),
    "read_page": ({"page": 11}, "Table 8. Pre-training setting."),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--server", default="paperaudit")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    command = ["npx", "--yes", f"--package=node@{NODE_VERSION}",
               f"--package=@modelcontextprotocol/inspector@{INSPECTOR_VERSION}",
               "mcp-inspector", "--cli", "--config", str(args.config.resolve()), "--server", args.server]

    def invoke(name, flags):
        result = subprocess.run(command + flags, capture_output=True, text=True, timeout=60)
        if result.returncode:
            # Keep paths or deployment diagnostics out of published artifacts.
            raise RuntimeError(f"Inspector {name} failed (exit {result.returncode}); "
                               "run the same command interactively for diagnostics")
        payload = json.loads(result.stdout)
        (args.output / f"{name}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        return payload

    listed = invoke("tools", ["--method", "tools/list"])
    assert {t["name"] for t in listed["tools"]} == set(CALLS)
    results = []
    for name, (arguments, expected) in CALLS.items():
        flags = ["--method", "tools/call", "--tool-name", name]
        for key, value in arguments.items():
            flags += ["--tool-arg", f"{key}={value}"]
        result = invoke(name, flags)
        text = "\n".join(c["text"] for c in result["content"] if c["type"] == "text")
        assert not result.get("isError") and expected in text, name
        results.append({"tool": name, "arguments": arguments, "ok": True, "characters": len(text)})
        print(json.dumps(results[-1], ensure_ascii=False), flush=True)
    outcome = {"inspector_version": INSPECTOR_VERSION, "node_version": NODE_VERSION,
               "tools": results, "server_model_requests": 0,
               "scope": "MAE engineering smoke; source retrieval only, no accuracy evaluation"}
    (args.output / "outcome.json").write_text(json.dumps(outcome, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
