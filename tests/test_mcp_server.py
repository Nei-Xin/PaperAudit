"""Optional integration coverage: uv run --extra mcp pytest tests/test_mcp_server.py."""
from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path
import subprocess
import sys

import pytest

pytest.importorskip("mcp")
from mcp import Client, StdioServerParameters

from paperaudit.agents.code_tools import CodeWorkspace, TOOL_SPECS
from paperaudit.code_parser import CURRENT_CODE_INDEX_VERSION
from paperaudit.mcp_server import create_server, load_snapshot
from paperaudit.storage import StorageError
from test_code_investigation import codebase, paper

PID = "0123456789abcdef"
CALLS = {
    "list_dir": ({"path": ""}, "src/"),
    "grep_code": ({"text": "dropout", "path_prefix": "configs/"}, "configs/base.yaml:2:"),
    "search_code": ({"query": "Encoder dropout"}, "src/model.py L"),
    "find_symbol": ({"name": "Encoder"}, "src/model.py L"),
    "read_file": ({"path": "configs/base.yaml", "start_line": 1, "end_line": 3}, "dropout: 0.3"),
    "search_paper": ({"query": "dropout rate"}, "chunk_id=p2_b1 | page 2"),
    "grep_paper": ({"text": "0.1"}, "chunk_id=p2_b1 | page 2"),
    "read_page": ({"page": 2}, "chunk_id=p2_b1 | page 2"),
}


@pytest.fixture
def library(tmp_path):
    project = tmp_path / "library" / "projects" / PID
    project.mkdir(parents=True)
    (project / "paper-index.json").write_text(paper().model_dump_json())
    (project / "codebase.json").write_text(codebase().model_dump_json())
    return project.parents[1]


def digest(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file()}


@pytest.mark.parametrize("mode", ["auto", "legacy"])
def test_stdio_all_tools_read_only_snapshot_and_protocol_modes(library, mode):
    before = digest(library)
    paths = [library, *library.rglob("*")]
    permissions = {path: path.stat().st_mode for path in paths}
    for path in paths:
        path.chmod(0o555 if path.is_dir() else 0o444)

    async def check():
        params = StdioServerParameters(command=sys.executable, args=[
            "-m", "paperaudit.mcp_server", "--storage-root", str(library), "--project", PID],
            # No model config or credentials passed to the MCP process.
            env={"PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")})
        async with Client(params, mode=mode, read_timeout_seconds=15) as client:
            listed = await client.list_tools()
            assert {t.name: t.input_schema for t in listed.tools} == {
                s["function"]["name"]: s["function"]["parameters"] for s in TOOL_SPECS}
            assert set(CALLS) == {t.name for t in listed.tools}
            for tool in listed.tools:
                assert tool.annotations.read_only_hint
                assert tool.annotations.idempotent_hint
                assert not tool.annotations.destructive_hint
                assert not tool.annotations.open_world_hint
                arguments, expected = CALLS[tool.name]
                result = await client.call_tool(tool.name, arguments)
                assert not result.is_error
                assert expected in result.content[0].text
            # Repeated full-text queries share indexes safely in the same process.
            results = await asyncio.gather(*[
                client.call_tool("search_paper", {"query": "dropout"}) for _ in range(4)])
            assert all(not result.is_error for result in results)
        # Context exit closes stdio and the subprocess without a lingering listener.

    try:
        asyncio.run(check())
        assert digest(library) == before
    finally:
        for path, permission in permissions.items():
            path.chmod(permission)


def test_tool_failures_are_recoverable_and_never_read_arbitrary_files(tmp_path):
    secret = tmp_path / "not-in-index.txt"
    secret.write_text("OUTSIDE_INDEX_SENTINEL")

    async def check():
        with CodeWorkspace(paper(), codebase()) as workspace:
            async with Client(create_server(workspace)) as client:
                cases = [
                    ("read_file", {"path": str(secret), "start_line": 1, "end_line": 1}),
                    ("read_file", {"path": "../not-in-index.txt", "start_line": 1, "end_line": 1}),
                    ("read_page", {"page": True}), ("read_page", {"page": 0}),
                    ("read_page", {"page": 99}), ("read_page", {"page": "2"}),
                    ("read_page", {}), ("list_dir", {}),
                    ("grep_code", {"text": "x" * 201}),
                    ("grep_paper", {"text": "dropout", "project_id": PID}),
                    ("investigate", {"question": "call a model"}),
                    ("write_file", {"path": str(secret), "content": "replaced"}),
                ]
                for name, arguments in cases:
                    result = await client.call_tool(name, arguments)
                    assert result.is_error, (name, arguments)
                    assert "OUTSIDE_INDEX_SENTINEL" not in result.content[0].text
                result = await client.call_tool("read_page", {"page": 2})
                assert not result.is_error
                assert "page 2" in result.content[0].text
    asyncio.run(check())
    assert secret.read_text() == "OUTSIDE_INDEX_SENTINEL"


def test_legacy_index_rebuilt_only_in_memory_and_snapshot_stays_fixed(library):
    path = library / "projects" / PID / "codebase.json"
    path.write_text(codebase().model_copy(update={"index_version": 1, "chunks": []}).model_dump_json())
    before = digest(library)
    parsed, sources = load_snapshot(library, PID)
    assert sources.index_version == CURRENT_CODE_INDEX_VERSION
    assert sources.chunks
    assert digest(library) == before
    path.write_text("corrupted by an external replacement")
    with CodeWorkspace(parsed, sources) as workspace:
        assert "dropout: 0.3" in workspace.run("read_file", CALLS["read_file"][0])[0]


def test_loader_does_not_create_missing_storage_and_rejects_bad_inputs(tmp_path, library):
    missing = tmp_path / "not-created"
    with pytest.raises(StorageError):
        load_snapshot(missing, PID)
    assert not missing.exists()
    for pid in ["../" + PID, "", "/etc/passwd", "0" * 17]:
        with pytest.raises(StorageError):
            load_snapshot(library, pid)
    with pytest.raises(StorageError):
        load_snapshot("relative", PID)
    path = library / "projects" / PID / "codebase.json"
    path.unlink()
    with pytest.raises(StorageError, match="codebase.json"):
        load_snapshot(library, PID)
    path.write_text("invalid json")
    with pytest.raises(StorageError, match="无法解析"):
        load_snapshot(library, PID)
    path.write_text(codebase().model_copy(update={"index_version": CURRENT_CODE_INDEX_VERSION + 1}).model_dump_json())
    with pytest.raises(StorageError, match="更新版本"):
        load_snapshot(library, PID)


def test_loader_rejects_index_and_project_symlinks(tmp_path, library):
    path = library / "projects" / PID / "paper-index.json"
    moved = tmp_path / "elsewhere.json"
    path.rename(moved)
    path.symlink_to(moved)
    with pytest.raises(StorageError, match="索引链接"):
        load_snapshot(library, PID)
    second_id = "1" * 16
    (library / "projects" / second_id).symlink_to(path.parent, target_is_directory=True)
    with pytest.raises(StorageError, match="符号链接"):
        load_snapshot(library, second_id)


def test_startup_errors_use_stderr_and_nonzero_exit(tmp_path):
    result = subprocess.run([sys.executable, "-m", "paperaudit.mcp_server", "--project", PID,
                             "--storage-root", str(tmp_path / "missing")],
                            capture_output=True, text=True, timeout=15)
    assert result.returncode == 2
    assert result.stdout == ""
    assert "PaperAudit MCP" in result.stderr
    assert not (tmp_path / "missing").exists()
