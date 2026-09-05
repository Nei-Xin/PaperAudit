import json

import pytest

from paperaudit.claim_extraction import (
    SourceExtractionBatch, source_batches, split_report_sources, validate_source_extraction,
)
from paperaudit.hy3_client import Hy3Client, Hy3ResponseError


def _claim(text, **updates):
    return {"claim_id": "model-id", "text": text, "source_quote": text,
            "category": "results", "query_en": "result", **updates}


def _response(*sources):
    return SourceExtractionBatch.model_validate({"sources": list(sources)})


def test_sources_keep_numbers_and_quantifiers_and_slide_location():
    sources = split_report_sources("[幻灯片 2]\n该方法在所有任务上提升 3.2%。NP 可用于回归、优化和图像补全。")
    assert [s.source_id for s in sources] == ["S0001", "S0002", "S0003"]
    assert sources[1].text == "该方法在所有任务上提升 3.2%。"
    assert sources[2].text == "NP 可用于回归、优化和图像补全。"
    assert all("PPT 第 2 页" in s.report_location for s in sources)
    assert sources == split_report_sources("[幻灯片 2]\n该方法在所有任务上提升 3.2%。NP 可用于回归、优化和图像补全。")


def test_extraction_orders_by_source_and_keeps_skips_and_deduplicates():
    sources = split_report_sources("# 结果\n提升 3.2%。准确率为 90%。")
    response = _response(
        {"source_id": "S0003", "claims": [_claim("准确率为 90%。")]},
        {"source_id": "S0001", "claims": [], "skip_reason": "heading"},
        {"source_id": "S0002", "claims": [_claim("提升 3.2%。"), _claim("提升 3.2%。")]},
    )
    result = validate_source_extraction(response, sources, ["results"])
    assert result.source_count == 3
    assert [c.source_id for c in result.claims] == ["S0002", "S0003"]
    assert result.skipped_sources[0].text == "# 结果"
    assert result.claims[0].report_location == sources[1].report_location


@pytest.mark.parametrize("items", [
    [],  # Entire source silently omitted.
    [{"source_id": "S9999", "claims": [_claim("提升 3.2%。")]}],
    [{"source_id": "S0001", "claims": []}],
    [{"source_id": "S0001", "claims": [_claim("提升 50%。")]}],
    [{"source_id": "S0001", "claims": [_claim("提升 3.2%。", category="method")]}],
    [{"source_id": "S0001", "claims": [_claim("提升 3.2%。")], "skip_reason": "opinion"}],
    [{"source_id": "S0001", "claims": [_claim("提升 3.2%。")]}] * 2,
])
def test_invalid_extraction_is_rejected(items):
    with pytest.raises(ValueError):
        validate_source_extraction(_response(*items), split_report_sources("提升 3.2%。"), ["results"])


def test_batched_extraction_retries_missing_source_and_never_returns_partial_results():
    client = object.__new__(Hy3Client)
    calls = []

    def respond(prompt, response_model, effort):
        calls.append(prompt)
        if len(calls) == 1:
            return _response()
        return _response({"source_id": "S0001", "claims": [_claim("提升 3.2%。")]})

    client._json_call = respond
    result = client.extract_claims("提升 3.2%。", ["results"])
    assert len(calls) == 2
    assert result.claims[0].source_quote == "提升 3.2%。"
    client._json_call = lambda *args: _response()
    with pytest.raises(Hy3ResponseError, match="抽取不完整"):
        client.extract_claims("提升 3.2%。", ["results"])


def test_multiple_batches_account_for_every_input_source():
    client = object.__new__(Hy3Client)
    batch_sizes = []
    contexts = []

    def respond(prompt, response_model, effort):
        payload = json.loads(prompt.split("<untrusted_report>\n")[1].split("\n</untrusted_report>")[0])
        batch_sizes.append(len(payload))
        contexts.append(json.loads(prompt.split("<untrusted_context>\n")[1].split("\n</untrusted_context>")[0]))
        return _response(*[{"source_id": s["source_id"], "claims": [_claim(s["text"])]} for s in payload])

    client._json_call = respond
    text = "\n".join(f"结果 {i}。" for i in range(25))
    result = client.extract_claims(text, ["results"])
    assert batch_sizes == [12, 12, 1]
    assert [s["source_id"] for s in contexts[1]] == ["S0012", "S0025"]
    assert result.source_count == len(result.claims) == 25
    assert len(list(source_batches(split_report_sources(("长" * 4000 + "。\n") * 2)))) == 2


def test_sentence_citations_stay_with_their_own_fact_and_override_model_anchor():
    text = "提升 3.2%。（证据：论文第2页）准确率为90%。 (引用: 第999页，表99)"
    sources = split_report_sources(text)
    assert len(sources) == 2
    assert "第2页" in sources[0].text and "999" not in sources[0].text
    assert "第999页" in sources[1].text
    response = _response(*[{
        "source_id": s.source_id,
        "claims": [_claim(s.text, provided_evidence="invented page 6")],
    } for s in sources])
    result = validate_source_extraction(response, sources, ["results"])
    assert result.claims[0].provided_evidence == "（证据：论文第2页）"
    assert result.claims[1].provided_evidence == "(引用: 第999页，表99)"


def test_dropped_evaluation_fact_is_retried_and_mapped_into_requested_results():
    client = object.__new__(Hy3Client)
    calls = []
    text = "论文在基准数据和商业数据上评估方法。（证据：论文第1页）"

    def respond(prompt, response_model, effort):
        calls.append(prompt)
        if len(calls) == 1:
            return _response({"source_id": "S0001", "claims": [], "skip_reason": "out_of_scope"})
        return _response({"source_id": "S0001", "claims": [_claim(text, category="dataset_setup")]})

    client._json_call = respond
    result = client.extract_claims(text, ["results"])
    assert len(calls) == 2
    assert result.claims[0].category.value == "results"
    assert result.claims[0].provided_evidence == "（证据：论文第1页）"
    assert result.skipped_sources == []


def test_actual_out_of_scope_content_can_still_be_skipped():
    source = split_report_sources("训练集按 80:20 划分。")
    response = _response({"source_id": "S0001", "claims": [], "skip_reason": "out_of_scope"})
    result = validate_source_extraction(response, source, ["results"])
    assert not result.claims
    assert result.skipped_sources[0].reason == "out_of_scope"
    # A results-only inclusion rule must not silently widen a methods-only audit.
    result = validate_source_extraction(response, split_report_sources("在 MNIST 数据集上评估方法。"), ["method"])
    assert len(result.skipped_sources) == 1


def test_section_context_survives_batch_boundaries():
    sources = split_report_sources("## 主要结果\n" + "\n".join(f"实验结果 {i}。" for i in range(15)))
    batches = list(source_batches(sources))
    assert batches[1][0].section_title == "主要结果"
