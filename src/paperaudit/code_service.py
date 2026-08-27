from __future__ import annotations

from collections.abc import Sequence

from .code_parser import parse_code_zip
from .code_retrieval import CodeRetriever
from .config import Settings
from .hy3_client import Hy3Client
from .models import (
    AnswerScope,
    AnswerStatus,
    CodeCandidate,
    CodeCitation,
    CodeSelection,
    EvidenceAnchor,
    EvidenceCandidate,
    JointAnswer,
    PaperAnswer,
    ParsedCodebase,
    ParsedPaper,
)
from .retrieval import EvidenceRetriever
from .service import AuditService


_JOINT_TERMS = ("是否实现", "一致", "对应论文", "论文和代码", "论文与代码", "复现", "差异")
_CODE_TERMS = ("函数", "类", "代码", "实现", "配置", "脚本", "文件", "调用", "仓库", "源码")
_NAVIGATION_TERMS = (
    "核心代码",
    "核心文件",
    "入口文件",
    "项目结构",
    "哪个文件",
    "哪些文件",
    "从哪里开始",
    "主流程",
)


def resolve_answer_scope(question: str, requested: AnswerScope) -> AnswerScope:
    if requested != AnswerScope.AUTO:
        return requested
    normalized = question.lower()
    if any(term in normalized for term in _JOINT_TERMS) or (
        "论文" in normalized and any(term in normalized for term in _CODE_TERMS)
    ):
        return AnswerScope.JOINT
    if any(term in normalized for term in _CODE_TERMS):
        return AnswerScope.CODE
    return AnswerScope.PAPER


def _is_repository_navigation_question(question: str) -> bool:
    normalized = question.lower()
    return any(term in normalized for term in _NAVIGATION_TERMS)


def _code_citations(
    ids: Sequence[str],
    candidates: Sequence[CodeCandidate],
) -> list[CodeCitation]:
    candidate_map = {candidate.chunk_id: candidate for candidate in candidates}
    citations: list[CodeCitation] = []
    seen: set[str] = set()
    for chunk_id in ids:
        candidate = candidate_map.get(chunk_id)
        if candidate is None or chunk_id in seen:
            continue
        seen.add(chunk_id)
        citations.append(
            CodeCitation(
                chunk_id=chunk_id,
                path=candidate.path,
                start_line=candidate.start_line,
                end_line=candidate.end_line,
                symbol=candidate.symbol,
                text=candidate.text,
            )
        )
    return citations


def _selected_code_candidates(
    codebase: ParsedCodebase,
    selection: CodeSelection | None,
) -> list[CodeCandidate]:
    if selection is None:
        return []
    candidates: list[CodeCandidate] = []
    for index, chunk in enumerate(codebase.chunks):
        if chunk.path != selection.path:
            continue
        if chunk.end_line < selection.start_line or chunk.start_line > selection.end_line:
            continue
        candidates.append(
            CodeCandidate(
                chunk_id=chunk.chunk_id,
                path=chunk.path,
                language=chunk.language,
                symbol=chunk.symbol,
                # Keep the real indexed chunk ID for citation validation, but
                # expose the user's exact selection for answering/navigation.
                start_line=selection.start_line,
                end_line=selection.end_line,
                text=selection.context_text or selection.text,
                score=3.0 - len(candidates) * 0.01,
            )
        )
        if len(candidates) >= 4:
            break
    return candidates


def _merge_code_candidates(
    selected: Sequence[CodeCandidate],
    retrieved: Sequence[CodeCandidate],
    limit: int,
) -> list[CodeCandidate]:
    seen: set[str] = set()
    return [
        candidate
        for candidate in [*selected, *retrieved]
        if not (candidate.chunk_id in seen or seen.add(candidate.chunk_id))
    ][:limit]


def _paper_citations(
    ids: Sequence[str],
    candidates: Sequence[EvidenceCandidate],
    paper: ParsedPaper,
) -> list[EvidenceAnchor]:
    candidate_map = {candidate.chunk_id: candidate for candidate in candidates}
    chunk_map = {chunk.chunk_id: chunk for chunk in paper.chunks}
    citations: list[EvidenceAnchor] = []
    seen: set[str] = set()
    for chunk_id in ids:
        candidate = candidate_map.get(chunk_id)
        chunk = chunk_map.get(chunk_id)
        if candidate is None or chunk is None or chunk_id in seen:
            continue
        seen.add(chunk_id)
        citations.append(
            EvidenceAnchor(
                chunk_id=chunk_id,
                page=chunk.page,
                text=chunk.content,
                rects=chunk.rects,
            )
        )
    return citations


def _as_paper_history(history: Sequence[JointAnswer]) -> list[PaperAnswer]:
    return [
        PaperAnswer(
            question=item.question,
            answer=item.answer,
            status=item.status,
            citations=item.paper_citations,
        )
        for item in history[-4:]
    ]


class CodeLearningService:
    def __init__(self, settings: Settings, client: Hy3Client | None = None):
        self.settings = settings
        self.client = client or Hy3Client(settings)

    def parse(self, zip_bytes: bytes, filename: str) -> ParsedCodebase:
        return parse_code_zip(zip_bytes, filename)

    def _retrieve_code(
        self,
        codebase: ParsedCodebase,
        query: str,
        limit: int | None = None,
    ) -> list[CodeCandidate]:
        with CodeRetriever(codebase.chunks) as retriever:
            return retriever.search(query, limit or max(self.settings.retrieval_top_k * 2, 8))

    def answer(
        self,
        paper: ParsedPaper,
        codebase: ParsedCodebase,
        question: str,
        requested_scope: AnswerScope = AnswerScope.AUTO,
        history: Sequence[JointAnswer] = (),
        selected_paper_chunk_ids: Sequence[str] = (),
        selected_paper_text: str | None = None,
        selected_code: CodeSelection | None = None,
    ) -> JointAnswer:
        normalized = question.strip()
        if not normalized:
            raise ValueError("追问内容不能为空。")
        if len(normalized) > 1000:
            raise ValueError("追问内容过长，请控制在 1000 个字符以内。")
        scope = resolve_answer_scope(normalized, requested_scope)
        if scope == AnswerScope.PAPER:
            paper_answer = AuditService(self.settings, client=self.client).answer_question(
                paper,
                normalized,
                _as_paper_history(history),
                selected_chunk_ids=selected_paper_chunk_ids,
                selected_text=selected_paper_text,
            )
            return JointAnswer(
                question=paper_answer.question,
                answer=paper_answer.answer,
                scope=scope,
                status=paper_answer.status,
                selected_code=selected_code,
                paper_citations=paper_answer.citations,
            )
        if scope == AnswerScope.CODE:
            return self._answer_code(
                codebase,
                normalized,
                history,
                selected_paper_text,
                selected_code,
            )
        return self._answer_joint(
            paper,
            codebase,
            normalized,
            history,
            selected_paper_chunk_ids,
            selected_paper_text,
            selected_code,
        )

    def _answer_code(
        self,
        codebase: ParsedCodebase,
        question: str,
        history: Sequence[JointAnswer],
        selected_paper_text: str | None,
        selected_code: CodeSelection | None,
    ) -> JointAnswer:
        query = self.client.plan_code_question(
            codebase.name,
            question,
            history,
            selected_paper_text,
            selected_code,
        )
        retrieval_query = " ".join(
            value for value in [query.query_en, *query.entities, *query.numbers] if value.strip()
        )
        navigation_question = _is_repository_navigation_question(question)
        if navigation_question:
            retrieval_query += " main entrypoint architecture model predictor builder pipeline"
        selected_candidates = _selected_code_candidates(codebase, selected_code)
        selected_candidate_ids = {item.chunk_id for item in selected_candidates}
        candidates = _merge_code_candidates(
            selected_candidates,
            self._retrieve_code(codebase, retrieval_query),
            max(self.settings.retrieval_top_k * 2, 8),
        )
        if not candidates:
            return JointAnswer(
                question=question,
                answer="当前代码索引中未检索到足够相关的实现，暂时无法可靠回答。",
                scope=AnswerScope.CODE,
                status=AnswerStatus.INSUFFICIENT_EVIDENCE,
                selected_code=selected_code,
            )
        draft = self.client.answer_code_question(
            question,
            candidates,
            history,
            selected_paper_text,
            selected_code,
        )
        citations = _code_citations(draft.citation_chunk_ids, candidates)
        if draft.status == AnswerStatus.INSUFFICIENT_EVIDENCE and navigation_question and not citations:
            citations = _code_citations(
                [candidate.chunk_id for candidate in candidates[:3]],
                candidates,
            )
        if draft.status == AnswerStatus.ANSWERED and not citations:
            return JointAnswer(
                question=question,
                answer="模型未返回可验证的有效代码引用，本次回答已转为证据不足。",
                scope=AnswerScope.CODE,
                status=AnswerStatus.INSUFFICIENT_EVIDENCE,
                selected_code=selected_code,
            )
        if (
            draft.status == AnswerStatus.ANSWERED
            and selected_code is not None
            and not selected_candidate_ids.intersection(
                citation.chunk_id for citation in citations
            )
        ):
            return JointAnswer(
                question=question,
                answer="模型未引用用户选中的代码，本次回答已转为证据不足。",
                scope=AnswerScope.CODE,
                status=AnswerStatus.INSUFFICIENT_EVIDENCE,
                selected_code=selected_code,
            )
        return JointAnswer(
            question=question,
            answer=draft.answer,
            scope=AnswerScope.CODE,
            status=draft.status,
            selected_code=selected_code,
            code_citations=citations,
        )

    def _answer_joint(
        self,
        paper: ParsedPaper,
        codebase: ParsedCodebase,
        question: str,
        history: Sequence[JointAnswer],
        selected_paper_chunk_ids: Sequence[str],
        selected_paper_text: str | None,
        selected_code: CodeSelection | None,
    ) -> JointAnswer:
        query = self.client.plan_joint_question(
            paper.title,
            codebase.name,
            question,
            history,
            selected_paper_text,
            selected_code,
        )
        paper_query = " ".join([query.paper_query_en, *query.entities])
        code_query = " ".join([query.code_query_en, *query.entities])
        with EvidenceRetriever(paper.chunks) as retriever:
            paper_candidates = retriever.search(
                paper_query,
                "J",
                max(self.settings.retrieval_top_k * 2, 8),
            )
        paper_map = {chunk.chunk_id: chunk for chunk in paper.chunks}
        selected_candidates = [
            EvidenceCandidate(
                evidence_id=f"JS_e{index + 1}",
                chunk_id=chunk.chunk_id,
                page=chunk.page,
                text=chunk.content,
                score=2.0 - index * 0.01,
            )
            for index, chunk_id in enumerate(dict.fromkeys(selected_paper_chunk_ids))
            if (chunk := paper_map.get(chunk_id)) is not None
        ]
        seen_paper: set[str] = set()
        paper_candidates = [
            candidate
            for candidate in [*selected_candidates, *paper_candidates]
            if not (candidate.chunk_id in seen_paper or seen_paper.add(candidate.chunk_id))
        ][:12]
        selected_code_candidates = _selected_code_candidates(codebase, selected_code)
        selected_code_candidate_ids = {
            item.chunk_id for item in selected_code_candidates
        }
        code_candidates = _merge_code_candidates(
            selected_code_candidates,
            self._retrieve_code(codebase, code_query, 12),
            12,
        )
        if not paper_candidates and not code_candidates:
            return JointAnswer(
                question=question,
                answer="当前论文和代码索引中都未检索到足够相关的证据。",
                scope=AnswerScope.JOINT,
                status=AnswerStatus.INSUFFICIENT_EVIDENCE,
                selected_code=selected_code,
            )
        draft = self.client.answer_joint_question(
            question,
            paper_candidates,
            code_candidates,
            history,
            selected_paper_text,
            selected_code,
        )
        paper_citations = _paper_citations(
            draft.paper_citation_chunk_ids,
            paper_candidates,
            paper,
        )
        code_citations = _code_citations(draft.code_citation_chunk_ids, code_candidates)
        if draft.status == AnswerStatus.ANSWERED and not (paper_citations or code_citations):
            return JointAnswer(
                question=question,
                answer="模型未返回可验证的论文或代码引用，本次回答已转为证据不足。",
                scope=AnswerScope.JOINT,
                status=AnswerStatus.INSUFFICIENT_EVIDENCE,
                selected_code=selected_code,
            )
        if (
            draft.status == AnswerStatus.ANSWERED
            and selected_code is not None
            and not selected_code_candidate_ids.intersection(
                citation.chunk_id for citation in code_citations
            )
        ):
            return JointAnswer(
                question=question,
                answer="模型未引用用户选中的代码，本次回答已转为证据不足。",
                scope=AnswerScope.JOINT,
                status=AnswerStatus.INSUFFICIENT_EVIDENCE,
                selected_code=selected_code,
            )
        return JointAnswer(
            question=question,
            answer=draft.answer,
            scope=AnswerScope.JOINT,
            status=draft.status,
            selected_code=selected_code,
            paper_citations=paper_citations,
            code_citations=code_citations,
            relation=draft.relation,
        )
