from app.metrics.thresholds import (
    DEFAULT_THRESHOLDS,
    MetricThresholds,
    evaluate_file_quality,
    evaluate_function_quality,
)


def test_function_high_and_critical_complexity() -> None:
    # High complexity (15 > 10)
    flags = evaluate_function_quality(
        name="complex_func",
        location="app/calc.py:10",
        cyclomatic_complexity=15,
        lines_of_code=30,
        nesting_depth=2,
        parameter_count=3,
        branch_count=6,
    )
    assert any(f["flag"] == "HIGH_COMPLEXITY" and f["severity"] == "HIGH" for f in flags)

    # Critical complexity (25 > 20)
    flags_crit = evaluate_function_quality(
        name="very_complex_func",
        location="app/calc.py:50",
        cyclomatic_complexity=25,
        lines_of_code=40,
        nesting_depth=3,
        parameter_count=3,
        branch_count=12,
    )
    assert any(f["flag"] == "VERY_HIGH_COMPLEXITY" and f["severity"] == "CRITICAL" for f in flags_crit)


def test_function_large_size_and_deep_nesting() -> None:
    flags = evaluate_function_quality(
        name="giant_func",
        location="app/giant.py:1",
        cyclomatic_complexity=5,
        lines_of_code=120,
        nesting_depth=6,
        parameter_count=7,
        branch_count=9,
    )

    flag_names = {f["flag"] for f in flags}
    assert "VERY_LARGE_FUNCTION" in flag_names
    assert "DEEP_NESTING" in flag_names
    assert "HIGH_PARAMETER_COUNT" in flag_names
    assert "HIGH_BRANCH_COUNT" in flag_names


def test_file_large_and_poor_maintainability() -> None:
    flags = evaluate_file_quality(
        file_path="huge_monolith.py",
        sloc=1200,
        maintainability_score=35.0,
        max_nesting_depth=5,
        max_cyclomatic_complexity=30,
    )

    flag_names = {f["flag"] for f in flags}
    assert "VERY_LARGE_FILE" in flag_names
    assert "POOR_MAINTAINABILITY" in flag_names
