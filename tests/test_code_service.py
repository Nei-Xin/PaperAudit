from __future__ import annotations

from paperaudit.code_service import CodeLearningService, resolve_answer_scope
from paperaudit.config import Settings
from paperaudit.models import (
    AnswerScope,
    AnswerStatus,
    CodeAnswerDraft,
    CodeChunk,
    CodeFile,
    CodeSelection,
    JointAnswerDraft,
    JointQuery,
    PageRect,
    PaperChunk,
    PaperCodeRelation,
    ParsedCodebase,
    ParsedPaper,
    QuestionQuery,
)


def settings() -> Settings:
    return Settings(api_base="https://example.invalid/v1", api_key="test", model="hy3")


def codebase() -> ParsedCodebase:
    content = "class DirectorAgent:\n    def select_mode(self, poem):\n        return 'dialogue'\n"
    return ParsedCodebase(
        name="demo",
        files=[CodeFile(path="agents/director.py", language="python", content=content, line_count=3)],
        chunks=[
            CodeChunk(
                chunk_id="c00001",
                path="agents/director.py",
                language="python",
                symbol="DirectorAgent",
                start_line=1,
                end_line=3,
                content=content,
            )
        ],
    )


def paper() -> ParsedPaper:
    return ParsedPaper(
        title="Demo Paper",
        page_count=2,
        chunks=[
            PaperChunk(
                chunk_id="p2_b1",
                page=2,
                content="The Director Agent selects an instructional mode.",
                rects=[PageRect(x0=72, y0=100, x1=320, y1=120)],
            )
        ],
    )


class FakeCodeClient:
    def __init__(
        self,
        fabricated: bool = False,
        status: AnswerStatus = AnswerStatus.ANSWERED,
    ):
        self.fabricated = fabricated
        self.status = status
        self.last_code_candidate_ids: list[str] = []

    def plan_code_question(self, *args, **kwargs) -> QuestionQuery:
        return QuestionQuery(query_en="DirectorAgent select_mode")

    def answer_code_question(self, *args, **kwargs) -> CodeAnswerDraft:
        self.last_code_candidate_ids = [candidate.chunk_id for candidate in args[1]]
        return CodeAnswerDraft(
            answer="DirectorAgent.select_mode 选择教学模式。",
            status=self.status,
            citation_chunk_ids=["invented" if self.fabricated else "c00001"],
        )

    def plan_joint_question(self, *args, **kwargs) -> JointQuery:
        return JointQuery(
            paper_query_en="Director Agent instructional mode",
            code_query_en="DirectorAgent select_mode",
        )

    def answer_joint_question(self, *args, **kwargs) -> JointAnswerDraft:
        return JointAnswerDraft(
            answer="论文描述模式选择，代码由 DirectorAgent 实现。",
            status=AnswerStatus.ANSWERED,
            paper_citation_chunk_ids=["p2_b1"],
            code_citation_chunk_ids=["c00001"],
            relation=PaperCodeRelation.IMPLEMENTS,
        )


def test_scope_resolution_and_manual_override() -> None:
    assert resolve_answer_scope("这个函数在哪里实现？", AnswerScope.AUTO) == AnswerScope.CODE
    assert resolve_answer_scope("代码是否实现论文方法？", AnswerScope.AUTO) == AnswerScope.JOINT
    assert resolve_answer_scope("论文中的方法在代码哪里实现？", AnswerScope.AUTO) == AnswerScope.JOINT
    assert resolve_answer_scope("论文方法是什么？", AnswerScope.AUTO) == AnswerScope.PAPER
    assert resolve_answer_scope("这个函数做什么？", AnswerScope.PAPER) == AnswerScope.PAPER


def test_code_answer_has_validated_file_and_lines() -> None:
    service = CodeLearningService(settings(), client=FakeCodeClient())  # type: ignore[arg-type]

    answer = service.answer(paper(), codebase(), "这个函数做什么？", AnswerScope.CODE)

    assert answer.status == AnswerStatus.ANSWERED
    assert answer.scope == AnswerScope.CODE
    assert answer.code_citations[0].path == "agents/director.py"
    assert (answer.code_citations[0].start_line, answer.code_citations[0].end_line) == (1, 3)


def test_fabricated_code_citation_is_rejected() -> None:
    service = CodeLearningService(
        settings(),
        client=FakeCodeClient(fabricated=True),  # type: ignore[arg-type]
    )

    answer = service.answer(paper(), codebase(), "这个函数做什么？", AnswerScope.CODE)

    assert answer.status == AnswerStatus.INSUFFICIENT_EVIDENCE
    assert answer.code_citations == []


def test_insufficient_navigation_answer_keeps_validated_candidate_link() -> None:
    service = CodeLearningService(
        settings(),
        client=FakeCodeClient(status=AnswerStatus.INSUFFICIENT_EVIDENCE),  # type: ignore[arg-type]
    )

    answer = service.answer(paper(), codebase(), "核心代码在哪一个文件？", AnswerScope.CODE)

    assert answer.status == AnswerStatus.INSUFFICIENT_EVIDENCE
    assert answer.code_citations[0].path == "agents/director.py"
    assert answer.code_citations[0].start_line == 1


def test_joint_answer_keeps_paper_and_code_citations() -> None:
    service = CodeLearningService(settings(), client=FakeCodeClient())  # type: ignore[arg-type]

    answer = service.answer(
        paper(),
        codebase(),
        "代码是否实现论文中的模式选择？",
        AnswerScope.JOINT,
    )

    assert answer.status == AnswerStatus.ANSWERED
    assert answer.relation == PaperCodeRelation.IMPLEMENTS
    assert answer.paper_citations[0].page == 2
    assert answer.code_citations[0].path == "agents/director.py"


def test_selected_paper_chunk_is_kept_for_joint_lookup() -> None:
    service = CodeLearningService(settings(), client=FakeCodeClient())  # type: ignore[arg-type]

    answer = service.answer(
        paper(),
        codebase(),
        "这段论文内容在代码中如何实现？",
        AnswerScope.JOINT,
        selected_paper_chunk_ids=["p2_b1"],
        selected_paper_text="The Director Agent selects an instructional mode.",
    )

    assert answer.status == AnswerStatus.ANSWERED
    assert [citation.chunk_id for citation in answer.paper_citations] == ["p2_b1"]
    assert answer.code_citations[0].chunk_id == "c00001"


def test_selected_code_chunk_is_prioritized_before_retrieved_candidates() -> None:
    client = FakeCodeClient()
    service = CodeLearningService(settings(), client=client)  # type: ignore[arg-type]
    selected_content = "def unrelated_helper():\n    return 1\n"
    extended = codebase().model_copy(
        update={
            "files": [
                *codebase().files,
                CodeFile(
                    path="utils/helper.py",
                    language="python",
                    content=selected_content,
                    line_count=2,
                ),
            ],
            "chunks": [
                *codebase().chunks,
                CodeChunk(
                    chunk_id="c00002",
                    path="utils/helper.py",
                    language="python",
                    symbol="unrelated_helper",
                    start_line=1,
                    end_line=2,
                    content=selected_content,
                ),
            ],
        }
    )

    answer = service.answer(
        paper(),
        extended,
        "这个函数做什么？",
        AnswerScope.CODE,
        selected_code=CodeSelection(
            path="utils/helper.py",
            start_line=1,
            end_line=2,
            text=selected_content,
            context_text=selected_content,
        ),
    )

    assert client.last_code_candidate_ids[0] == "c00002"
    assert answer.status == AnswerStatus.INSUFFICIENT_EVIDENCE
    assert answer.code_citations == []
    assert answer.selected_code is not None
    assert answer.selected_code.path == "utils/helper.py"


def test_selected_method_uses_exact_lines_with_legacy_class_chunk() -> None:
    client = FakeCodeClient()
    service = CodeLearningService(settings(), client=client)  # type: ignore[arg-type]
    legacy = codebase()
    selection = CodeSelection(
        path="agents/director.py",
        start_line=2,
        end_line=2,
        text="    def select_mode(self, poem):",
        context_text="    def select_mode(self, poem):",
    )

    answer = service.answer(
        paper(),
        legacy,
        "请解释这个方法。",
        AnswerScope.CODE,
        selected_code=selection,
    )

    assert answer.code_citations[0].chunk_id == "c00001"
    assert (answer.code_citations[0].start_line, answer.code_citations[0].end_line) == (2, 2)
    assert answer.code_citations[0].text == selection.context_text


def test_joint_answer_with_selection_rejects_unrelated_code_citation() -> None:
    selected_content = "def helper():\n    return 1\n"
    extended = codebase().model_copy(
        update={
            "files": [
                *codebase().files,
                CodeFile(
                    path="utils.py",
                    language="python",
                    content=selected_content,
                    line_count=2,
                ),
            ],
            "chunks": [
                *codebase().chunks,
                CodeChunk(
                    chunk_id="c00002",
                    path="utils.py",
                    language="python",
                    symbol="helper",
                    start_line=1,
                    end_line=2,
                    content=selected_content,
                ),
            ],
        }
    )
    service = CodeLearningService(settings(), client=FakeCodeClient())  # type: ignore[arg-type]

    answer = service.answer(
        paper(),
        extended,
        "这段代码和论文有什么关系？",
        AnswerScope.JOINT,
        selected_code=CodeSelection(
            path="utils.py",
            start_line=1,
            end_line=2,
            text=selected_content,
            context_text=selected_content,
        ),
    )

    assert answer.status == AnswerStatus.INSUFFICIENT_EVIDENCE
    assert answer.code_citations == []


def test_markdown_selection_is_prioritized_as_repository_content() -> None:
    client = FakeCodeClient()
    service = CodeLearningService(settings(), client=client)  # type: ignore[arg-type]
    markdown = "## Our Pledge\n\nWe pledge to provide a welcoming environment.\n"
    selected_base = codebase()
    selected_base = selected_base.model_copy(
        update={
            "files": [
                *selected_base.files,
                CodeFile(
                    path="CODE_OF_CONDUCT.md",
                    language="markdown",
                    content=markdown,
                    line_count=3,
                ),
            ],
            "chunks": [
                *selected_base.chunks,
                CodeChunk(
                    chunk_id="c00002",
                    path="CODE_OF_CONDUCT.md",
                    language="markdown",
                    symbol="Our Pledge",
                    start_line=1,
                    end_line=3,
                    content=markdown,
                ),
            ],
        }
    )

    service.answer(
        paper(),
        selected_base,
        "请解释这段仓库文档的含义和用途。",
        AnswerScope.CODE,
        selected_code=CodeSelection(
            path="CODE_OF_CONDUCT.md",
            start_line=1,
            end_line=3,
            text=markdown,
            context_text=markdown,
        ),
    )

    assert client.last_code_candidate_ids[0] == "c00002"
