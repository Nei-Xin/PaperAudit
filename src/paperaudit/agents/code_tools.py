"""Read-only tools over one parsed paper and one parsed codebase.

Nothing here touches the filesystem, the network or an interpreter: every tool
reads the in-memory index built at upload time. The workspace also records what
each tool actually showed the model, so a final citation can be checked against
text the investigation really read.
"""

from __future__ import annotations

from paperaudit.code_retrieval import CodeRetriever
from paperaudit.models import PaperChunk, ParsedCodebase, ParsedPaper
from paperaudit.retrieval import EvidenceRetriever

MAX_RESULT_CHARS = 8_000
MAX_LINE_CHARS = 300
MAX_READ_LINES = 150
MAX_GREP_HITS = 40
MAX_DIR_ENTRIES = 80


class ToolError(ValueError):
    """Invalid arguments. Reported back to the model; never ends the run."""


def _function(name: str, description: str, properties: dict, required: list[str]) -> dict:
    return {"type": "function", "function": {
        "name": name, "description": description,
        "parameters": {"type": "object", "properties": properties,
                       "required": required, "additionalProperties": False},
    }}


_STR, _INT = {"type": "string"}, {"type": "integer", "minimum": 1}

TOOL_SPECS = [
    _function("list_dir", "List files and sub-directories directly inside a repository directory. "
              "Use an empty path for the repository root.", {"path": _STR}, ["path"]),
    _function("grep_code", "Case-insensitive literal text search over every line of the repository "
              "(not a regular expression). Returns matching lines with path and line number. "
              "Optionally restrict to paths starting with path_prefix.",
              {"text": _STR, "path_prefix": _STR}, ["text"]),
    _function("search_code", "Ranked keyword search over indexed functions, classes and file sections. "
              "Use English identifiers and concepts. Returns numbered source for the best matches.",
              {"query": _STR}, ["query"]),
    _function("find_symbol", "Locate where a function, class or method is defined. Returns locations only; "
              "call read_file to see the source.", {"name": _STR}, ["name"]),
    _function("read_file", f"Read numbered lines of one file, at most {MAX_READ_LINES} lines per call.",
              {"path": _STR, "start_line": _INT, "end_line": _INT}, ["path", "start_line", "end_line"]),
    _function("search_paper", "Ranked search over the paper text using a targeted English query. "
              "Returns passages with chunk_id and page.", {"query": _STR}, ["query"]),
    _function("read_page", "Read the parsed text blocks of one paper page.", {"page": _INT}, ["page"]),
]


def _string(arguments: dict, key: str, *, required: bool = True, limit: int = 300) -> str:
    value = arguments.get(key, "")
    if not isinstance(value, str) or len(value) > limit:
        raise ToolError(f"{key} must be a string of at most {limit} characters")
    if required and not value.strip():
        raise ToolError(f"{key} is required")
    return value.strip()


def _integer(arguments: dict, key: str) -> int:
    value = arguments.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ToolError(f"{key} must be a positive integer")
    return value


class CodeWorkspace:
    def __init__(self, paper: ParsedPaper, codebase: ParsedCodebase):
        self.paper, self.codebase = paper, codebase
        self.files = {file.path: file.content.splitlines() for file in codebase.files}
        self.paper_chunks = {chunk.chunk_id: chunk for chunk in paper.chunks}
        self.observed_lines: dict[str, set[int]] = {}
        self.observed_chunks: dict[str, PaperChunk] = {}
        self._code_index: CodeRetriever | None = None
        self._paper_index: EvidenceRetriever | None = None
        self._tools = {
            "list_dir": self._list_dir, "grep_code": self._grep_code,
            "search_code": self._search_code, "find_symbol": self._find_symbol,
            "read_file": self._read_file, "search_paper": self._search_paper,
            "read_page": self._read_page,
        }

    def __enter__(self) -> "CodeWorkspace":
        return self

    def __exit__(self, *_: object) -> None:
        for index in (self._code_index, self._paper_index):
            if index is not None:
                index.close()

    def run(self, name: str, arguments: dict) -> tuple[str, str]:
        """Return (text shown to the model, one-line outcome for the trace)."""
        tool = self._tools.get(name)
        if tool is None:
            raise ToolError(f"Unknown tool {name}")
        unknown = set(arguments) - set(
            next(s for s in TOOL_SPECS if s["function"]["name"] == name)["function"]["parameters"]["properties"])
        if unknown:
            raise ToolError(f"Unexpected arguments: {sorted(unknown)}")
        text, outcome = tool(arguments)
        if len(text) > MAX_RESULT_CHARS:
            text = text[:MAX_RESULT_CHARS] + "\n[output truncated; narrow the request]"
        return text, outcome

    # Observation bookkeeping -------------------------------------------------

    def observe_lines(self, path: str, start: int, end: int) -> None:
        self.observed_lines.setdefault(path, set()).update(range(start, end + 1))

    def observe_chunk(self, chunk_id: str) -> None:
        chunk = self.paper_chunks.get(chunk_id)
        if chunk is not None:
            self.observed_chunks[chunk_id] = chunk

    def _numbered(self, path: str, start: int, end: int, budget: int) -> str:
        """Render numbered lines and mark as observed only lines shown in full."""
        lines, used, shown_end = [], 0, start - 1
        for number in range(start, end + 1):
            source = self.files[path][number - 1]
            clipped = len(source) > MAX_LINE_CHARS
            rendered = f"{number:>5}| " + (
                source[:MAX_LINE_CHARS] + " [line clipped; not citable]" if clipped else source)
            if used + len(rendered) + 1 > budget:
                break
            lines.append(rendered)
            used += len(rendered) + 1
            shown_end = number
            if not clipped:  # A clipped line cannot back a verbatim quotation.
                self.observe_lines(path, number, number)
        if shown_end < end:
            lines.append(f"[stopped before line {shown_end + 1}; read it separately if needed]")
        return "\n".join(lines)

    def _resolve_file(self, path: str) -> str:
        normalized = path.strip().removeprefix("./").lstrip("/")
        if normalized not in self.files:
            raise ToolError(f"No such file: {path}. Use list_dir or grep_code to find real paths.")
        return normalized

    # Tools -------------------------------------------------------------------

    def _list_dir(self, arguments: dict) -> tuple[str, str]:
        prefix = _string(arguments, "path", required=False).removeprefix("./").strip("/")
        prefix = "" if prefix == "." else prefix
        prefix = f"{prefix}/" if prefix else ""
        directories: dict[str, int] = {}
        files: list[str] = []
        for path, lines in self.files.items():
            if not path.startswith(prefix):
                continue
            head, _, rest = path[len(prefix):].partition("/")
            if rest:
                directories[head] = directories.get(head, 0) + 1
            else:
                files.append(f"{head}  ({len(lines)} lines)")
        if not directories and not files:
            raise ToolError(f"No such directory: {prefix or '/'}")
        entries = [f"{name}/  ({count} files)" for name, count in sorted(directories.items())] + sorted(files)
        shown = entries[:MAX_DIR_ENTRIES]
        if len(entries) > len(shown):
            shown.append(f"[{len(entries) - len(shown)} more entries not shown]")
        return "\n".join(shown), f"列出 {len(entries)} 项"

    def _grep_code(self, arguments: dict) -> tuple[str, str]:
        needle = _string(arguments, "text", limit=200).casefold()
        prefix = _string(arguments, "path_prefix", required=False).removeprefix("./").lstrip("/")
        hits: list[str] = []
        total = 0
        for path in sorted(self.files):
            if not path.startswith(prefix):
                continue
            for number, line in enumerate(self.files[path], 1):
                if needle not in line.casefold():
                    continue
                total += 1
                if len(hits) < MAX_GREP_HITS and len(line) <= MAX_LINE_CHARS:
                    hits.append(f"{path}:{number}: {line.strip()}")
                    self.observe_lines(path, number, number)
        if not total:
            return ("No matches. This does not prove the repository lacks the feature; "
                    "try another spelling or search_code."), "无匹配"
        if total > len(hits):
            hits.append(f"[{total - len(hits)} more matches not shown; narrow with path_prefix]")
        return "\n".join(hits), f"匹配 {total} 行"

    def _search_code(self, arguments: dict) -> tuple[str, str]:
        query = _string(arguments, "query")
        if self._code_index is None:
            self._code_index = CodeRetriever(self.codebase.chunks)
        found = self._code_index.search(query, 6)
        if not found:
            return "No indexed code matched. Try grep_code with a literal identifier.", "无匹配"
        budget = MAX_RESULT_CHARS // len(found)
        blocks = []
        for item in found:
            header = f"## {item.path} L{item.start_line}-{item.end_line}" + (
                f" ({item.symbol})" if item.symbol else "")
            end = min(item.end_line, len(self.files.get(item.path, ())))
            body = self._numbered(item.path, item.start_line, end, budget - len(header) - 60) \
                if item.path in self.files and end >= item.start_line else ""
            blocks.append(f"{header}\n{body}")
        return "\n\n".join(blocks), f"返回 {len(found)} 个代码片段"

    def _find_symbol(self, arguments: dict) -> tuple[str, str]:
        name = _string(arguments, "name", limit=120).casefold()
        exact, partial = [], []
        for chunk in self.codebase.chunks:
            symbol = (chunk.symbol or "").casefold()
            if not symbol:
                continue
            location = f"{chunk.path} L{chunk.start_line}-{chunk.end_line}  {chunk.symbol}"
            if symbol == name or symbol.rsplit(".", 1)[-1] == name:
                exact.append(location)
            elif name in symbol:
                partial.append(location)
        found = (exact + partial)[:30]
        if not found:
            return "No indexed definition has that name. Try grep_code.", "未找到定义"
        return "\n".join(found), f"找到 {len(found)} 处定义"

    def _read_file(self, arguments: dict) -> tuple[str, str]:
        path = self._resolve_file(_string(arguments, "path"))
        start, end = _integer(arguments, "start_line"), _integer(arguments, "end_line")
        total = len(self.files[path])
        if start > total or end < start:
            raise ToolError(f"{path} has {total} lines; requested {start}-{end}")
        end = min(end, total, start + MAX_READ_LINES - 1)
        return self._numbered(path, start, end, MAX_RESULT_CHARS - 80), f"读取 {path} L{start}–{end}"

    def _paper_blocks(self, chunks: list[PaperChunk]) -> str:
        blocks, used = [], 0
        for chunk in chunks:
            block = f"[chunk_id={chunk.chunk_id} | page {chunk.page}]\n{chunk.content}"
            if used + len(block) > MAX_RESULT_CHARS - 80:
                continue  # Whole passages only, as elsewhere in the audit.
            blocks.append(block)
            used += len(block) + 2
            self.observe_chunk(chunk.chunk_id)
        return "\n\n".join(blocks)

    def _search_paper(self, arguments: dict) -> tuple[str, str]:
        query = _string(arguments, "query")
        if self._paper_index is None:
            self._paper_index = EvidenceRetriever(self.paper.chunks)
        found = [self.paper_chunks[item.chunk_id] for item in self._paper_index.search(query, "I", 6)]
        text = self._paper_blocks(found)
        if not text:
            return "No passage matched. Try other terms or read_page.", "无匹配"
        return text, f"返回 {text.count('[chunk_id=')} 个论文片段"

    def _read_page(self, arguments: dict) -> tuple[str, str]:
        page = _integer(arguments, "page")
        if page > self.paper.page_count:
            raise ToolError(f"The paper has {self.paper.page_count} pages")
        text = self._paper_blocks([chunk for chunk in self.paper.chunks if chunk.page == page])
        if not text:
            return "No parsed text on this page (figures and scanned tables are not readable).", "该页无可读文本"
        return text, f"读取第 {page} 页的 {text.count('[chunk_id=')} 个片段"
