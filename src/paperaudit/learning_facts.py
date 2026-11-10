"""Internal fact ledger and literal coverage checks, not semantic entailment proofs."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
import re
import unicodedata
from typing import Literal

from pydantic import Field

from .evidence import _validated_evidence_quote
from .models import PaperChunk, StrictModel


class FactSource(StrictModel):
    chunk_id: str
    quote: str = Field(min_length=8, max_length=320)


class LessonFact(StrictModel):
    fact_id: str = Field(min_length=1)
    kind: Literal["result", "cost", "training", "mechanism", "assumption", "taxonomy"]
    subject: str = Field(min_length=1)
    dataset: str | None = None
    metric: str | None = None
    # source_value preserves literal extraction, including lost table typography.
    source_value: str | None = None
    value: str | None = None
    unit: str | None = None
    finding: str = Field(min_length=1)
    conditions: list[str] = Field(default_factory=list)
    status: Literal["reported", "ambiguous", "conflicting"] = "reported"
    uncertainty: str | None = None
    conflict_group: str | None = None
    sources: list[FactSource] = Field(min_length=1)


class FactMention(StrictModel):
    fact_id: str
    point_index: int = Field(ge=0)
    # Exact excerpt of the explanation, never a quotation or hidden metadata.
    excerpt: str = Field(min_length=1)


class FactProblem(StrictModel):
    code: str
    fact_id: str
    message: str


def normalized(text: str) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", text)).casefold()


def contains_label(text: str, label: str) -> bool:
    label = re.sub(r"\s+", " ", unicodedata.normalize("NFKC", label)).strip().casefold()
    # "AdamW" is not "Adam", and "Set-AB" is not "Set-A". Chinese prose
    # naturally has no word spaces, so boundaries only restrict ASCII names.
    left = r"(?<![a-z_-])" if label and label[0].isascii() and label[0].isalnum() else ""
    right = r"(?![a-z_-])" if label and label[-1].isascii() and label[-1].isalnum() else ""
    text = re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text)).casefold()
    # CJK prose commonly inserts spaces at script boundaries (Transformer 模型
    # vs Transformer模型). Ignore only those layout spaces, never spaces within
    # ASCII identifiers: AdamW / Adam W and Set-A / Set-AB remain distinct.
    def cjk_spacing(value):
        return re.sub(r"(?<=[\u3400-\u9fff])\s+(?=[a-z0-9])|(?<=[a-z0-9])\s+(?=[\u3400-\u9fff])", "", value)
    return bool(re.search(left + re.escape(cjk_spacing(label)) + right, cjk_spacing(text)))


def number_text(text: str) -> str:
    # Convert superscripts BEFORE NFKC, which would turn 10¹⁸ into ambiguous 1018.
    text = re.sub(r"10([⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻]+)",
                  lambda m: "10^" + unicodedata.normalize("NFKC", m[1]).replace("−", "-"), text)
    return unicodedata.normalize("NFKC", text).replace("−", "-").strip()


NUMBER = r"[+-]?(?:\d+(?:\.\d+)?|\.\d+)"
QUANTITY = re.compile(rf"(?P<m>{NUMBER})(?:\s*(?:[eE]\s*(?P<e>[+-]?\d+)|[×·*]\s*10\s*\^\s*(?P<p>[+-]?\d+)))?(?:\s*(?P<percent>%))?")


def quantity(value: str) -> tuple[Decimal, bool] | None:
    match = QUANTITY.fullmatch(number_text(value))
    if match is None:
        return None
    try:
        exponent = int(match["e"] or match["p"] or 0)
        if abs(exponent) > 1000:
            return None
        return Decimal(match["m"]) * Decimal(10) ** exponent, bool(match["percent"])
    except (InvalidOperation, ValueError):
        return None


def source_quantity(value: str) -> tuple[Decimal, bool] | None:
    # Only a literal single-variable assignment may wrap a numeric value. Do not
    # fish a convenient number out of a sentence, formula, range or table row.
    rhs = re.sub(r"^[A-Za-z_][A-Za-z0-9_]*\s*=\s*", "", value.strip())
    return quantity(rhs)


def symbolic_expression(value: str) -> bool:
    text = value.strip()
    return bool(re.fullmatch(r"(?:O\([A-Za-z0-9/+*^(). _√·×-]+\)|[A-Za-z0-9/+*^(). _√·×-]+)", text)
                and re.search(r"[A-Za-z]", text) and quantity(text) is None)


def contains_quantity(text: str, expected: str) -> bool:
    target = quantity(expected)
    if target is None:
        return False
    text = number_text(text)
    for match in QUANTITY.finditer(text):
        before, after = text[:match.start()], text[match.end():]
        if before and (before[-1].isdigit() or before[-1] in ".^+-"):
            continue
        if after and (after[0].isdigit() or re.match(r"\.\d", after)):
            continue
        if quantity(match[0]) == target:
            return True
    return False


def validate_fact(fact: LessonFact, sources: dict[str, PaperChunk]) -> list[FactProblem]:
    errors = []
    def fail(code, message):
        errors.append(FactProblem(code=code, fact_id=fact.fact_id, message=message))
    for anchor in fact.sources:
        chunk = sources.get(anchor.chunk_id)
        if chunk is None or not _validated_evidence_quote(anchor.quote, chunk.content):
            fail("invalid_fact_source", "事实证据不是有效的连续原文。")
    if any(not label.strip() for label in [fact.subject, fact.finding, *fact.conditions]):
        fail("empty_fact_label", "事实主体、结论和条件不能留空。")
    if fact.kind in {"result", "cost"} and not (fact.metric or "").strip():
        fail("missing_metric", "主结果和成本事实必须明确指标。")
    if fact.kind == "cost" and not (fact.unit or "").strip():
        fail("missing_unit", "成本事实必须明确单位。")
    if fact.status != "reported" and not (fact.uncertainty or "").strip():
        fail("missing_uncertainty", "有歧义或冲突的事实必须说明证据边界。")
    if fact.status == "conflicting" and not fact.conflict_group:
        fail("missing_conflict_group", "冲突值必须保留分组，不能静默选取一个。")
    if fact.source_value is not None:
        if not fact.source_value.strip() or not any(
            re.search(r"(?<![\d.])" + re.escape(re.sub(r"\s+", " ", fact.source_value).strip())
                      + r"(?!\d|\.\d)", re.sub(r"\s+", " ", a.quote))
            and (quantity(fact.source_value) is None or contains_quantity(a.quote, fact.source_value))
            for a in fact.sources
        ):
            fail("source_value_absent", "事实的原始数值没有出现在所引摘录中。")
    if fact.value is not None:
        numeric = quantity(fact.value)
        numeric_match = numeric is not None and fact.source_value is not None and source_quantity(fact.source_value) == numeric
        symbolic_match = (fact.kind != "cost" and symbolic_expression(fact.value)
                          and fact.source_value is not None and normalized(fact.value) == normalized(fact.source_value))
        if not numeric_match and not symbolic_match:
            fail("value_not_grounded", "规范化数值与原始数值不等价；不得猜测丢失的指数或列归属。")
    elif fact.kind in {"result", "cost"} and fact.status != "ambiguous" and not (
        fact.kind == "result" and fact.source_value and symbolic_expression(fact.source_value)
    ):
        fail("missing_result_value", "可读的主结果或成本必须保留数值。")
    return errors


def check_mention(fact: LessonFact, mention: FactMention, explanation: str,
                  cited_chunk_ids: set[str]) -> list[FactProblem]:
    errors = []
    def fail(code, message):
        errors.append(FactProblem(code=code, fact_id=fact.fact_id, message=message))
    if mention.excerpt not in explanation:
        fail("excerpt_not_in_explanation", "事实覆盖原句不在解释正文中。")
        return errors
    # Canonical labels are chosen in the plan (Chinese labels are allowed) and
    # retained in the excerpt. Their grounding is still checked by the reviewer.
    for name, label in [("subject", fact.subject), ("dataset", fact.dataset),
                        ("metric", fact.metric), ("unit", fact.unit)]:
        if label and not contains_label(mention.excerpt, label):
            fail(f"missing_{name}", f"事实原句缺少对应的 {name}：{label}。")
    for condition in fact.conditions:
        if not contains_label(mention.excerpt, condition):
            fail("missing_condition", f"事实原句缺少适用条件：{condition}。")
    if fact.value is not None:
        present = (contains_quantity(mention.excerpt, fact.value) if quantity(fact.value) is not None
                   else normalized(fact.value) in normalized(mention.excerpt))
        if not present:
            fail("missing_value", f"事实原句缺少对应数值或符号表达式 {fact.value}，或指数/单位比例错误。")
    if fact.value is None and fact.source_value and normalized(fact.source_value) not in normalized(mention.excerpt):
        fail("missing_raw_value", "有歧义的原始数值必须按抽取形式保留，不得补猜。")
    if fact.uncertainty and normalized(fact.uncertainty) not in normalized(mention.excerpt):
        fail("uncertainty_hidden", "事实原句未保留歧义或冲突说明。")
    if not {a.chunk_id for a in fact.sources}.issubset(cited_chunk_ids):
        fail("fact_evidence_missing", "解释未引用该事实的全部支持来源。")
    return errors
