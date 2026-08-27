from __future__ import annotations

from io import BytesIO
from zipfile import ZipFile

import pytest

from paperaudit.code_parser import (
    CURRENT_CODE_INDEX_VERSION,
    CodeParseError,
    parse_code_zip,
    rebuild_code_index,
)
from paperaudit.models import ParsedCodebase


def make_zip(files: dict[str, str | bytes]) -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        for path, content in files.items():
            archive.writestr(path, content)
    return buffer.getvalue()


def test_parse_code_zip_extracts_python_symbols_and_lines() -> None:
    codebase = parse_code_zip(
        make_zip(
            {
                "repo/README.md": "# Demo\nUsage guide.",
                "repo/src/model.py": (
                    "VALUE = 1\n\n"
                    "class DemoModel:\n"
                    "    def run(self, value):\n"
                    "        return value + VALUE\n\n"
                    "def build_model():\n"
                    "    return DemoModel()\n"
                ),
            }
        ),
        "demo.zip",
    )

    assert codebase.name == "demo"
    assert [file.path for file in codebase.files] == ["README.md", "src/model.py"]
    model = next(chunk for chunk in codebase.chunks if chunk.symbol == "DemoModel")
    run = next(chunk for chunk in codebase.chunks if chunk.symbol == "DemoModel.run")
    builder = next(chunk for chunk in codebase.chunks if chunk.symbol == "build_model")
    assert (model.start_line, model.end_line) == (3, 3)
    assert (run.start_line, run.end_line) == (4, 5)
    assert (builder.start_line, builder.end_line) == (7, 8)
    assert all(chunk.chunk_id.startswith("c") for chunk in codebase.chunks)
    assert codebase.index_version == CURRENT_CODE_INDEX_VERSION


def test_python_class_methods_are_indexed_independently() -> None:
    codebase = parse_code_zip(
        make_zip(
            {
                "amp.py": (
                    "class MaskData:\n"
                    "    \"\"\"Stores mask metadata.\"\"\"\n"
                    "    def filter(self, keep):\n"
                    "        self.values = self.values[keep]\n\n"
                    "    def to_numpy(self):\n"
                    "        return self.values.detach().cpu().numpy()\n"
                )
            }
        )
    )

    symbols = {chunk.symbol: chunk for chunk in codebase.chunks}
    assert (symbols["MaskData"].start_line, symbols["MaskData"].end_line) == (1, 2)
    assert (symbols["MaskData.filter"].start_line, symbols["MaskData.filter"].end_line) == (3, 4)
    assert (symbols["MaskData.to_numpy"].start_line, symbols["MaskData.to_numpy"].end_line) == (6, 7)


def test_async_decorated_method_includes_decorator() -> None:
    codebase = parse_code_zip(
        make_zip(
            {
                "worker.py": (
                    "class Worker:\n"
                    "    @classmethod\n"
                    "    async def build(cls):\n"
                    "        return cls()\n"
                )
            }
        )
    )

    method = next(chunk for chunk in codebase.chunks if chunk.symbol == "Worker.build")
    assert (method.start_line, method.end_line) == (2, 4)
    assert method.content.startswith("    @classmethod")


def test_rebuild_code_index_is_stable_and_upgrades_legacy_index() -> None:
    current = parse_code_zip(
        make_zip({"demo.py": "class Demo:\n    def run(self):\n        return 1\n"})
    )
    legacy = ParsedCodebase(
        name=current.name,
        files=current.files,
        chunks=[current.chunks[0]],
    )

    first = rebuild_code_index(legacy)
    second = rebuild_code_index(legacy)

    assert first == second
    assert first.index_version == CURRENT_CODE_INDEX_VERSION
    assert [chunk.symbol for chunk in first.chunks] == ["Demo", "Demo.run"]


def test_parse_code_zip_rejects_path_traversal() -> None:
    with pytest.raises(CodeParseError, match="不安全路径"):
        parse_code_zip(make_zip({"../escape.py": "print('bad')"}))


def test_parse_code_zip_ignores_secrets_and_unsupported_files() -> None:
    codebase = parse_code_zip(
        make_zip(
            {
                "repo/main.py": "def main():\n    return 1\n",
                "repo/.env": "API_KEY=secret",
                "repo/credentials.json": '{"token":"secret"}',
                "repo/assets/logo.png": b"\x89PNG\x00",
                "repo/.venv/lib.py": "SECRET = True",
            }
        )
    )

    paths = [file.path for file in codebase.files]
    assert paths == ["main.py"]
    assert "secret" not in "\n".join(chunk.content for chunk in codebase.chunks).lower()


def test_invalid_python_falls_back_to_line_chunks() -> None:
    codebase = parse_code_zip(make_zip({"broken.py": "def broken(:\n    pass\n"}))

    assert codebase.chunks
    assert codebase.chunks[0].start_line == 1
    assert any("语法解析失败" in warning for warning in codebase.warnings)


def test_oversized_source_file_is_skipped_with_warning() -> None:
    codebase = parse_code_zip(
        make_zip(
            {
                "main.py": "def main():\n    return 1\n",
                "generated.py": b"x" * (1024 * 1024 + 1),
            }
        )
    )

    assert [file.path for file in codebase.files] == ["main.py"]
    assert any("generated.py" in warning for warning in codebase.warnings)
