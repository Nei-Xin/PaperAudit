from __future__ import annotations

from paperaudit.display import fully_supported_rate, label_counts, recover_paper_title
from paperaudit.models import (
    AutoLabel,
    ClaimErrorType,
    EvidenceErrorType,
    PaperChunk,
    ParsedPaper,
)
from paperaudit.reporting import render_markdown
from paperaudit.ui.demo_data import get_demo_audit_run


def _report_run():
    run = get_demo_audit_run()
    no_support = run.audits[3]
    no_support = no_support.model_copy(
        update={
            "judgment": no_support.judgment.model_copy(
                update={
                    "evidence_ids": [no_support.candidates[0].evidence_id],
                    "claim_error_type": ClaimErrorType.OVERGENERALIZATION,
                    "evidence_error_type": EvidenceErrorType.EVIDENCE_MISMATCH,
                    "suggestion": "改为更谨慎的表述。",
                }
            )
        }
    )
    return run.model_copy(update={"audits": [*run.audits[:3], no_support, *run.audits[4:]]})


def test_dynamic_claim_statistics_are_derived_from_actual_audits() -> None:
    run = _report_run()

    counts = label_counts(run.audits)

    assert len(run.audits) == 6
    assert counts[AutoLabel.SUPPORTED] == 2
    assert fully_supported_rate(run.audits) == 33.3


def test_markdown_prioritizes_issues_and_uses_chinese_display_names() -> None:
    report = render_markdown(_report_run())

    assert "本次审计论断：6 条（根据报告内容自动拆分，数量并非固定）" in report
    assert "完全支持论断率：33.3%" in report
    assert "候选证据检索覆盖率" in report
    assert "综合总分" in report and "不等同于事实正确率" in report
    assert "过度概括" in report
    assert "证据不匹配" in report
    assert "NO_SUPPORT_FOUND" not in report
    assert "overgeneralization" not in report
    assert report.index("## 待修改与复核") < report.index("## 已确认内容")
    assert report.index("## 已确认内容") < report.index("## 完整原文依据附录")


def test_no_support_evidence_is_named_as_insufficient_candidate() -> None:
    report = render_markdown(_report_run())

    assert "候选片段（不足以支持该论断）" in report
    assert "C004 · 未找到支持证据" in report


def test_existing_truncated_title_is_recovered_from_first_page_title_block() -> None:
    paper = ParsedPaper(
        title="MLLM-as-a-Judge for Image Safety without",
        page_count=1,
        chunks=[
            PaperChunk(
                chunk_id="p1_b14",
                page=1,
                content="MLLM-as-a-Judge for Image Safety without\nHuman Labeling",
            )
        ],
    )

    assert recover_paper_title(paper).endswith("without Human Labeling")
