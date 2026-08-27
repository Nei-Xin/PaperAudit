from __future__ import annotations

import ast
from io import BytesIO
from pathlib import PurePosixPath
import re
import stat
from zipfile import BadZipFile, ZipFile, ZipInfo

from .models import CodeChunk, CodeFile, ParsedCodebase


MAX_ZIP_BYTES = 30 * 1024 * 1024
MAX_TEXT_BYTES = 80 * 1024 * 1024
MAX_FILE_BYTES = 1 * 1024 * 1024
MAX_FILES = 2_000
SUPPORTED_EXTENSIONS = {".py", ".md", ".yaml", ".yml", ".json", ".toml", ".sh"}
IGNORED_DIRECTORIES = {
    ".git",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "dist",
    "build",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "checkpoints",
    "weights",
    "data",
    "datasets",
}
SENSITIVE_PATTERNS = (
    re.compile(r"^\.env(?:\..+)?$", re.IGNORECASE),
    re.compile(r"(?:^|[_-])(?:id_rsa|id_ed25519|private[_-]?key)(?:\.|$)", re.IGNORECASE),
    re.compile(r"\.(?:pem|key|p12|pfx|crt|cer)$", re.IGNORECASE),
    re.compile(r"(?:credentials?|secrets?)\.(?:json|ya?ml|toml|txt)$", re.IGNORECASE),
)
LANGUAGES = {
    ".py": "python",
    ".md": "markdown",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".json": "json",
    ".toml": "toml",
    ".sh": "shell",
}
CURRENT_CODE_INDEX_VERSION = 2


class CodeParseError(ValueError):
    pass


def _safe_path(info: ZipInfo) -> PurePosixPath:
    raw = info.filename.replace("\\", "/")
    path = PurePosixPath(raw)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise CodeParseError(f"ZIP 包含不安全路径：{info.filename}")
    if re.match(r"^[A-Za-z]:", raw):
        raise CodeParseError(f"ZIP 包含绝对路径：{info.filename}")
    return path


def _is_symlink(info: ZipInfo) -> bool:
    mode = (info.external_attr >> 16) & 0xFFFF
    return bool(mode and stat.S_ISLNK(mode))


def _is_ignored(path: PurePosixPath) -> bool:
    lowered_parts = {part.lower() for part in path.parts[:-1]}
    if lowered_parts & IGNORED_DIRECTORIES:
        return True
    filename = path.name
    return any(pattern.search(filename) for pattern in SENSITIVE_PATTERNS)


def _decode_text(data: bytes) -> str | None:
    if b"\x00" in data[:4096]:
        return None
    for encoding in ("utf-8-sig", "utf-8"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return None


def _strip_common_root(paths: list[PurePosixPath]) -> list[PurePosixPath]:
    if not paths:
        return []
    first_parts = {path.parts[0] for path in paths}
    if len(first_parts) == 1 and all(len(path.parts) > 1 for path in paths):
        return [PurePosixPath(*path.parts[1:]) for path in paths]
    return paths


def _line_chunk(
    path: str,
    language: str,
    lines: list[str],
    start: int,
    end: int,
    symbol: str | None = None,
) -> CodeChunk:
    content = "\n".join(lines[start - 1 : end]).rstrip()
    return CodeChunk(
        chunk_id="pending",
        path=path,
        language=language,
        symbol=symbol,
        start_line=start,
        end_line=max(start, end),
        content=content,
    )


def _fixed_chunks(path: str, language: str, content: str) -> list[CodeChunk]:
    lines = content.splitlines() or [""]
    chunks: list[CodeChunk] = []
    start = 1
    size = 80
    overlap = 10
    while start <= len(lines):
        end = min(start + size - 1, len(lines))
        chunks.append(_line_chunk(path, language, lines, start, end))
        if end == len(lines):
            break
        start = end - overlap + 1
    return chunks


def _markdown_chunks(path: str, content: str) -> list[CodeChunk]:
    lines = content.splitlines() or [""]
    headings = [
        (index, line.lstrip("#").strip())
        for index, line in enumerate(lines, start=1)
        if re.match(r"^#{1,6}\s+\S", line)
    ]
    if not headings:
        return _fixed_chunks(path, "markdown", content)
    chunks: list[CodeChunk] = []
    if headings[0][0] > 1:
        chunks.append(_line_chunk(path, "markdown", lines, 1, headings[0][0] - 1))
    for index, (start, title) in enumerate(headings):
        end = headings[index + 1][0] - 1 if index + 1 < len(headings) else len(lines)
        chunks.append(_line_chunk(path, "markdown", lines, start, end, title))
    return chunks


def _python_chunks(path: str, content: str) -> tuple[list[CodeChunk], str | None]:
    lines = content.splitlines() or [""]
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return _fixed_chunks(path, "python", content), "Python 语法解析失败，已按行切块"

    nodes = [
        node
        for node in tree.body
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    if not nodes:
        return _fixed_chunks(path, "python", content), None

    def node_start(node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef) -> int:
        return min([node.lineno, *(item.lineno for item in node.decorator_list)])

    chunks: list[CodeChunk] = []
    first_start = min(node_start(node) for node in nodes)
    if first_start > 1:
        chunks.append(_line_chunk(path, "python", lines, 1, first_start - 1, "<module>"))
    for node in nodes:
        end = int(getattr(node, "end_lineno", node.lineno))
        if not isinstance(node, ast.ClassDef):
            chunks.append(_line_chunk(path, "python", lines, node_start(node), end, node.name))
            continue

        methods = [
            child
            for child in node.body
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        if not methods:
            chunks.append(_line_chunk(path, "python", lines, node_start(node), end, node.name))
            continue

        first_method_start = min(node_start(method) for method in methods)
        class_start = node_start(node)
        header_end = max(class_start, first_method_start - 1)
        chunks.append(_line_chunk(path, "python", lines, class_start, header_end, node.name))
        for method in methods:
            method_end = int(getattr(method, "end_lineno", method.lineno))
            chunks.append(
                _line_chunk(
                    path,
                    "python",
                    lines,
                    node_start(method),
                    method_end,
                    f"{node.name}.{method.name}",
                )
            )
    return chunks, None


def _chunks_for_file(path: str, language: str, content: str) -> tuple[list[CodeChunk], str | None]:
    if language == "python":
        return _python_chunks(path, content)
    if language == "markdown":
        return _markdown_chunks(path, content), None
    return _fixed_chunks(path, language, content), None


def rebuild_code_index(codebase: ParsedCodebase) -> ParsedCodebase:
    """Rebuild a stable local index from the source text saved with a project."""
    chunks: list[CodeChunk] = []
    warnings = list(codebase.warnings)
    files = sorted(codebase.files, key=lambda item: item.path.lower())
    for source in files:
        file_chunks, warning = _chunks_for_file(
            source.path,
            source.language,
            source.content,
        )
        if warning:
            message = f"{source.path}：{warning}"
            if message not in warnings:
                warnings.append(message)
        chunks.extend(chunk for chunk in file_chunks if chunk.content.strip())
    rebuilt = [
        chunk.model_copy(update={"chunk_id": f"c{index:05d}"})
        for index, chunk in enumerate(chunks, start=1)
    ]
    if not rebuilt:
        raise CodeParseError("已保存的源码中没有可索引的代码内容。")
    return ParsedCodebase(
        name=codebase.name,
        files=files,
        chunks=rebuilt,
        warnings=warnings,
        index_version=CURRENT_CODE_INDEX_VERSION,
    )


def parse_code_zip(zip_bytes: bytes, filename: str = "source.zip") -> ParsedCodebase:
    if not zip_bytes:
        raise CodeParseError("源码 ZIP 为空。")
    if len(zip_bytes) > MAX_ZIP_BYTES:
        raise CodeParseError("源码 ZIP 超过 30 MB 限制。")
    try:
        archive = ZipFile(BytesIO(zip_bytes))
    except BadZipFile as exc:
        raise CodeParseError("无法读取源码 ZIP。") from exc

    warnings: list[str] = []
    entries: list[tuple[ZipInfo, PurePosixPath]] = []
    with archive:
        infos = archive.infolist()
        if len(infos) > MAX_FILES:
            raise CodeParseError("ZIP 文件数量超过 2,000 个限制。")
        total_size = 0
        for info in infos:
            path = _safe_path(info)
            if info.is_dir() or _is_symlink(info) or _is_ignored(path):
                continue
            if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue
            if info.file_size > MAX_FILE_BYTES:
                warnings.append(f"已跳过超大文件：{path.as_posix()}")
                continue
            total_size += info.file_size
            if total_size > MAX_TEXT_BYTES:
                raise CodeParseError("ZIP 中可读文本总量超过 80 MB 限制。")
            entries.append((info, path))

        normalized_paths = _strip_common_root([path for _, path in entries])
        files: list[CodeFile] = []
        chunks: list[CodeChunk] = []
        for (info, _), normalized_path in zip(entries, normalized_paths, strict=True):
            data = archive.read(info)
            content = _decode_text(data)
            path_text = normalized_path.as_posix()
            if content is None:
                warnings.append(f"已跳过非 UTF-8 或二进制文件：{path_text}")
                continue
            language = LANGUAGES[normalized_path.suffix.lower()]
            lines = content.splitlines() or [""]
            files.append(
                CodeFile(
                    path=path_text,
                    language=language,
                    content=content,
                    line_count=len(lines),
                )
            )
            file_chunks, warning = _chunks_for_file(path_text, language, content)
            if warning:
                warnings.append(f"{path_text}：{warning}")
            chunks.extend(file_chunks)

    if not files or not chunks:
        raise CodeParseError("ZIP 中没有可解析的受支持源码文件。")
    chunks = [
        chunk.model_copy(update={"chunk_id": f"c{index:05d}"})
        for index, chunk in enumerate(chunks, start=1)
        if chunk.content.strip()
    ]
    if not chunks:
        raise CodeParseError("ZIP 中没有可索引的代码内容。")
    name = PurePosixPath(filename).stem or "source"
    files.sort(key=lambda item: item.path.lower())
    return ParsedCodebase(
        name=name,
        files=files,
        chunks=chunks,
        warnings=warnings,
        index_version=CURRENT_CODE_INDEX_VERSION,
    )
