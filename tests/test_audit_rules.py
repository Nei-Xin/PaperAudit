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
