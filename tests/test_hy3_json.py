from __future__ import annotations

import json
import inspect

from paperaudit.hy3_client import Hy3Client, _extract_json


def test_claim_extraction_prompt_has_no_fixed_thirty_claim_limit() -> None:
    source = inspect.getsource(Hy3Client.extract_claims)

    assert "at most 30" not in source
    assert "all material claims" in source


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
