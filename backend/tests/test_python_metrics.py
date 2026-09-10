import pytest
from app.analyzers.base import ExtractedSymbol
from app.metrics.python_metrics import PythonMetricsAnalyzer


@pytest.fixture
def analyzer() -> PythonMetricsAnalyzer:
    return PythonMetricsAnalyzer()


def test_python_simple_function(analyzer: PythonMetricsAnalyzer) -> None:
    code = """def add(a, b):
    return a + b
"""
    symbols = [ExtractedSymbol(name="add", symbol_type="function", start_line=1, start_column=0, end_line=2, end_column=16)]
    res = analyzer.calculate("math_ops.py", code, symbols)

    assert res.metric_status == "calculated"
    assert res.total_lines == 2
    assert res.sloc == 2
    assert res.function_count == 1
    assert len(res.symbols_metrics) == 1

    sm = res.symbols_metrics[0]
    assert sm.name == "add"
    assert sm.lines_of_code == 2
    assert sm.cyclomatic_complexity == 1
    assert sm.parameter_count == 2
    assert sm.return_count == 1
    assert sm.nesting_depth == 0


def test_python_branching_and_boolean_conditions(analyzer: PythonMetricsAnalyzer) -> None:
    code = """def evaluate_score(score, is_admin, has_token):
    if score > 90 and (is_admin or has_token):
        return "A+"
    elif score > 75:
        return "B"
    else:
        return "C"
"""
    symbols = [ExtractedSymbol(name="evaluate_score", symbol_type="function", start_line=1, start_column=0, end_line=8, end_column=18)]
    res = analyzer.calculate("scorer.py", code, symbols)

    sm = res.symbols_metrics[0]
    # Base = 1, if (+1), and (+1), or (+1), elif (+1) = 5
    assert sm.cyclomatic_complexity == 5
    assert sm.branch_count == 2  # if, elif
    assert sm.boolean_condition_count >= 2  # and, or
    assert sm.return_count == 3
    assert sm.parameter_count == 3


def test_python_loops_and_exceptions(analyzer: PythonMetricsAnalyzer) -> None:
    code = """def process_items(items):
    total = 0
    for item in items:
        while item > 0:
            try:
                total += item
                item -= 1
            except ValueError:
                break
    return total
"""
    symbols = [ExtractedSymbol(name="process_items", symbol_type="function", start_line=1, start_column=0, end_line=11, end_column=16)]
    res = analyzer.calculate("loop_ops.py", code, symbols)

    sm = res.symbols_metrics[0]
    # Base = 1, for (+1), while (+1), except (+1) = 4
    assert sm.cyclomatic_complexity == 4
    assert sm.loop_count == 2
    assert sm.exception_handler_count == 1
    assert sm.nesting_depth >= 2


def test_python_comprehensions_and_ternary(analyzer: PythonMetricsAnalyzer) -> None:
    code = """def filter_evens(nums):
    result = [x for x in nums if x % 2 == 0 if x > 10]
    label = "positive" if len(result) > 0 else "empty"
    return label, result
"""
    symbols = [ExtractedSymbol(name="filter_evens", symbol_type="function", start_line=1, start_column=0, end_line=5, end_column=24)]
    res = analyzer.calculate("comprehension.py", code, symbols)

    sm = res.symbols_metrics[0]
    # Base = 1, comprehension if x2 (+2), ternary (+1) = 4
    assert sm.cyclomatic_complexity == 4
    assert sm.branch_count >= 3


def test_python_nested_function_scope_isolation(analyzer: PythonMetricsAnalyzer) -> None:
    code = """def outer():
    if True:
        pass
    def inner():
        if False:
            pass
    return inner
"""
    symbols = [
        ExtractedSymbol(name="outer", symbol_type="function", start_line=1, start_column=0, end_line=8, end_column=16),
        ExtractedSymbol(name="inner", symbol_type="function", start_line=4, start_column=4, end_line=6, end_column=16, parent_name="outer"),
    ]
    res = analyzer.calculate("scoped.py", code, symbols)

    assert len(res.symbols_metrics) == 2
    outer_sm = next(s for s in res.symbols_metrics if s.name == "outer")
    inner_sm = next(s for s in res.symbols_metrics if s.name == "inner")

    # Each function has its own baseline of 1 + 1 branch = 2
    assert outer_sm.cyclomatic_complexity == 2
    assert inner_sm.cyclomatic_complexity == 2


def test_python_syntax_error_isolation(analyzer: PythonMetricsAnalyzer) -> None:
    broken_code = """def broken_func(
        this is total invalid python syntax !!!
    """
    res = analyzer.calculate("broken.py", broken_code, [])

    assert res.metric_status == "failed"
    assert res.metric_error is not None
    assert "Syntax error" in res.metric_error


def test_python_maintainability_score(analyzer: PythonMetricsAnalyzer) -> None:
    code = """# Well-documented module
# Provides clean helper utilities

def simple_helper(x: int) -> int:
    \"\"\"Docstring explaining functionality.\"\"\"
    return x * 2
"""
    symbols = [ExtractedSymbol(name="simple_helper", symbol_type="function", start_line=4, start_column=0, end_line=6, end_column=16)]
    res = analyzer.calculate("helper.py", code, symbols)

    assert res.maintainability_score >= 70.0
    assert res.comment_lines >= 3
    assert res.sloc >= 2
