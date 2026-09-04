from __future__ import annotations

import json
import inspect

from paperaudit.hy3_client import Hy3Client, _extract_json, format_paper_context
from paperaudit.models import PaperChunk


def test_claim_extraction_prompt_has_no_fixed_thirty_claim_limit() -> None:
    source = inspect.getsource(Hy3Client.extract_claims)

    assert "at most 30" not in source
    assert "all material claims" in source


def test_judgment_prompts_define_error_type_priority() -> None:
    batch_source = inspect.getsource(Hy3Client.judge_claims)
    adjudication_source = inspect.getsource(Hy3Client.adjudicate_claim)

    for source in (batch_source, adjudication_source):
        assert "numeric_or_metric_mismatch" in source
        assert "core fact remains supported" in source
        assert "universal word does not override" in source


def test_extract_json_preserves_markdown_code_fence_inside_answer() -> None:
    payload = {
        "answer": "运行命令：\n```bash\npython scripts/amg.py --input image.jpg\n```",
        "status": "ANSWERED",
        "citation_chunk_ids": ["c1"],
    }
    response = f"```json\n{json.dumps(payload, ensure_ascii=False)}\n```"

    assert _extract_json(response) == payload


def test_extract_unfenced_json_with_markdown_code_block() -> None:
    payload = {
        "answer": "```python\nprint('ok')\n```",
        "status": "ANSWERED",
        "citation_chunk_ids": ["c1"],
    }

    assert _extract_json(json.dumps(payload, ensure_ascii=False)) == payload


def test_format_paper_context_keeps_head_and_tail_under_budget() -> None:
    chunks = [
        PaperChunk(chunk_id="head", page=1, content="METHOD_START " + "a" * 40),
        PaperChunk(chunk_id="middle", page=2, content="MIDDLE " + "b" * 40),
        PaperChunk(chunk_id="tail", page=3, content="RESULT_END " + "c" * 40),
    ]
    context = format_paper_context(chunks, 170)
    assert len(context) <= 170
    assert "head" in context
    assert "tail" in context
    assert "上下文已按预算截断" in context
