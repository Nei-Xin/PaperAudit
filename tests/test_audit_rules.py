from paperaudit.audit_rules import calibrate_judgment, calibrate_severity, needs_second_pass
from paperaudit.models import AutoLabel, ClaimErrorType, ClaimJudgment, Severity


def _judgment(label: AutoLabel, error: ClaimErrorType | None, severity: Severity) -> ClaimJudgment:
    return ClaimJudgment(
        claim_id="C001",
        label=label,
        explanation="test",
        claim_error_type=error,
        severity=severity,
    )


def test_calibrate_severity_uses_error_rubric() -> None:
    judgment = _judgment(
        AutoLabel.CONTRADICTED,
        ClaimErrorType.NUMERIC_OR_METRIC_MISMATCH,
        Severity.MEDIUM,
    )
    assert calibrate_severity(judgment).severity == Severity.HIGH


def test_calibrate_severity_keeps_supported_at_none() -> None:
    judgment = _judgment(AutoLabel.SUPPORTED, None, Severity.HIGH)
    assert calibrate_severity(judgment).severity == Severity.NONE


def test_needs_second_pass_only_for_label_error_conflicts() -> None:
    conflicting = _judgment(
        AutoLabel.SUPPORTED,
        ClaimErrorType.MISSING_CONDITION,
        Severity.NONE,
    )
    stable = _judgment(
        AutoLabel.CONTRADICTED,
        ClaimErrorType.NUMERIC_OR_METRIC_MISMATCH,
        Severity.HIGH,
    )
    assert needs_second_pass(conflicting)
    assert not needs_second_pass(stable)


def test_calibrate_judgment_aligns_label_and_severity() -> None:
    judgment = _judgment(
        AutoLabel.NO_SUPPORT_FOUND,
        ClaimErrorType.WRONG_ATTRIBUTION,
        Severity.MEDIUM,
    )
    calibrated = calibrate_judgment(judgment)
    assert calibrated.label == AutoLabel.CONTRADICTED
    assert calibrated.severity == Severity.HIGH


def test_calibrate_judgment_does_not_promote_negative_label_without_error_type() -> None:
    for label in (AutoLabel.CONTRADICTED, AutoLabel.NO_SUPPORT_FOUND):
        calibrated = calibrate_judgment(_judgment(label, None, Severity.NONE))

        assert calibrated.label == label


def test_mild_numeric_and_proof_errors_get_review_without_keyword_escalation() -> None:
    mild = _judgment(AutoLabel.PARTIALLY_SUPPORTED, ClaimErrorType.OVERGENERALIZATION, Severity.MEDIUM)
    for text in ("提升了 50%", "已证明最优性", "provably optimal"):
        assert needs_second_pass(mild, text)
    assert not needs_second_pass(mild, "方法适用范围更广")
    supported = _judgment(AutoLabel.SUPPORTED, None, Severity.NONE)
    assert not needs_second_pass(supported, "在数据集 A 上提升 50%")
    assert calibrate_judgment(supported).severity == Severity.NONE


def test_unsupported_core_result_is_high_but_scope_only_error_is_medium() -> None:
    invented = _judgment(AutoLabel.PARTIALLY_SUPPORTED, ClaimErrorType.EXTERNAL_HALLUCINATION, Severity.MEDIUM)
    result = calibrate_judgment(invented)
    assert result.label == AutoLabel.NO_SUPPORT_FOUND
    assert result.severity == Severity.HIGH
    scoped = _judgment(AutoLabel.PARTIALLY_SUPPORTED, ClaimErrorType.OVERGENERALIZATION, Severity.MEDIUM)
    assert calibrate_judgment(scoped).severity == Severity.MEDIUM
