import pytest
from app.services.quality_gate_engine import QualityGateEngine, QualityGateResult


def test_quality_gate_all_passed():
    result = QualityGateEngine.evaluate(
        overall_score=85.0,
        blocker_count=0,
        critical_count=1,
        circular_dependencies_count=0,
        average_maintainability_index=62.0,
        critical_complexity_functions_count=2,
    )

    assert result.status == "PASSED"
    assert result.passed is True
    assert result.total_conditions == 6
    assert result.passed_count == 6
    assert result.failed_count == 0
    assert result.warning_count == 0


def test_quality_gate_warning_only():
    # Trigger QG-004 warn (> 2 critical issues)
    result = QualityGateEngine.evaluate(
        overall_score=82.0,
        blocker_count=0,
        critical_count=3,
        circular_dependencies_count=0,
        average_maintainability_index=60.0,
        critical_complexity_functions_count=1,
    )

    assert result.status == "WARNING"
    assert result.passed is True  # Passes with warnings (not blocked)
    assert result.failed_count == 0
    assert result.warning_count == 1
    assert result.passed_count == 5


def test_quality_gate_fail_on_blocker():
    # Trigger QG-002 fail (> 0 blockers)
    result = QualityGateEngine.evaluate(
        overall_score=90.0,
        blocker_count=1,
        critical_count=0,
        circular_dependencies_count=0,
        average_maintainability_index=75.0,
        critical_complexity_functions_count=0,
    )

    assert result.status == "FAILED"
    assert result.passed is False
    assert result.failed_count == 1


def test_quality_gate_fail_on_cycle():
    # Trigger QG-003 fail (> 0 cycles)
    result = QualityGateEngine.evaluate(
        overall_score=85.0,
        blocker_count=0,
        critical_count=0,
        circular_dependencies_count=1,
        average_maintainability_index=70.0,
        critical_complexity_functions_count=0,
    )

    assert result.status == "FAILED"
    assert result.passed is False
    assert result.failed_count == 1


def test_quality_gate_fail_takes_precedence_over_warn():
    # Both fail (score < 80.0) and warn (criticals > 2)
    result = QualityGateEngine.evaluate(
        overall_score=78.0,
        blocker_count=0,
        critical_count=4,
        circular_dependencies_count=0,
        average_maintainability_index=60.0,
        critical_complexity_functions_count=1,
    )

    assert result.status == "FAILED"
    assert result.passed is False
    assert result.failed_count == 1
    assert result.warning_count == 1


def test_quality_gate_exact_boundary_semantics():
    # QG-001: 80.0 passes, 79.9 fails
    r_pass = QualityGateEngine.evaluate(80.0, 0, 0, 0, 60.0, 0)
    assert r_pass.conditions[0].passed is True

    r_fail = QualityGateEngine.evaluate(79.9, 0, 0, 0, 60.0, 0)
    assert r_fail.conditions[0].passed is False

    # QG-004: 2 criticals passes, 3 fails
    r_crit2 = QualityGateEngine.evaluate(85.0, 0, 2, 0, 60.0, 0)
    assert r_crit2.conditions[3].passed is True

    r_crit3 = QualityGateEngine.evaluate(85.0, 0, 3, 0, 60.0, 0)
    assert r_crit3.conditions[3].passed is False

    # QG-005: 55.0 MI passes, 54.9 fails
    r_mi55 = QualityGateEngine.evaluate(85.0, 0, 0, 0, 55.0, 0)
    assert r_mi55.conditions[4].passed is True

    r_mi54 = QualityGateEngine.evaluate(85.0, 0, 0, 0, 54.9, 0)
    assert r_mi54.conditions[4].passed is False

    # QG-006: 3 crit funcs passes, 4 fails
    r_func3 = QualityGateEngine.evaluate(85.0, 0, 0, 0, 60.0, 3)
    assert r_func3.conditions[5].passed is True

    r_func4 = QualityGateEngine.evaluate(85.0, 0, 0, 0, 60.0, 4)
    assert r_func4.conditions[5].passed is False


def test_quality_gate_custom_threshold_overrides():
    # Custom min_score=70.0 and max_criticals=5
    custom = {
        "min_score": 70.0,
        "max_criticals": 5,
    }
    result = QualityGateEngine.evaluate(
        overall_score=72.0,
        blocker_count=0,
        critical_count=4,
        circular_dependencies_count=0,
        average_maintainability_index=60.0,
        critical_complexity_functions_count=1,
        custom_thresholds=custom,
    )

    assert result.status == "PASSED"
    assert result.passed is True
    assert result.conditions[0].threshold == 70.0
    assert result.conditions[0].passed is True
    assert result.conditions[3].threshold == 5
    assert result.conditions[3].passed is True
