import uuid
import pytest
from app.analyzers.base import ExtractedSymbol
from app.metrics.base import FileMetrics, SymbolMetrics
from app.services.file_discovery import DiscoveredFile
from app.rules.base import RuleContext
from app.rules.complexity_rules import (
    CriticalComplexityMethodRule,
    HighComplexityMethodRule,
    DeepNestingRule,
    GiantFileRule,
    LongParameterListRule,
)


def make_context(symbols=None, symbol_metrics=None, file_metrics=None):
    file_id = uuid.uuid4()
    fpath = "sample.py"
    df = DiscoveredFile(
        path=fpath,
        filename="sample.py",
        extension=".py",
        size_bytes=1000,
        line_count=200,
        language="Python",
        is_analyzable=True,
    )
    syms = symbols or []
    sm_list = symbol_metrics or []
    fm = file_metrics or FileMetrics(
        file_path=fpath,
        language="Python",
        total_lines=200,
        sloc=150,
        comment_lines=20,
        blank_lines=30,
        statement_count=100,
        maintainability_score=75.0,
        total_cyclomatic_complexity=20,
        average_cyclomatic_complexity=4.0,
        max_cyclomatic_complexity=10,
        symbols_metrics=sm_list,
    )
    parsed_files_data = [{
        "df": df,
        "symbols": syms,
        "symbols_metrics": sm_list,
        "parser_status": "success",
        "parser_error": None,
        "symbol_count": len(syms),
        "content": "",
    }]
    return RuleContext(
        parsed_files_data=parsed_files_data,
        file_metrics_map={fpath: fm},
        graph=None,
        file_id_map={fpath: file_id},
    )


def test_critical_complexity_rule():
    rule = CriticalComplexityMethodRule()
    sym = ExtractedSymbol(
        name="monster_function",
        symbol_type="function",
        start_line=10,
        start_column=0,
        end_line=150,
        end_column=0,
    )
    sm = SymbolMetrics(
        name="monster_function",
        symbol_type="function",
        start_line=10,
        end_line=150,
        lines_of_code=140,
        cyclomatic_complexity=32,
        nesting_depth=3,
        parameter_count=3,
    )
    ctx = make_context(symbols=[sym], symbol_metrics=[sm])
    issues = rule.evaluate(ctx)

    assert len(issues) == 1
    iss = issues[0]
    assert iss.rule_id == "COMPLEX-001"
    assert iss.severity == "critical"
    assert iss.symbol_name == "monster_function"
    assert iss.metadata_json["cyclomatic_complexity"] == 32
    assert iss.remediation_effort_minutes == 90


def test_high_complexity_rule():
    rule = HighComplexityMethodRule()
    sym = ExtractedSymbol(
        name="busy_function",
        symbol_type="function",
        start_line=20,
        start_column=0,
        end_line=60,
        end_column=0,
    )
    sm = SymbolMetrics(
        name="busy_function",
        symbol_type="function",
        start_line=20,
        end_line=60,
        lines_of_code=40,
        cyclomatic_complexity=18,
        nesting_depth=3,
        parameter_count=2,
    )
    ctx = make_context(symbols=[sym], symbol_metrics=[sm])
    issues = rule.evaluate(ctx)

    assert len(issues) == 1
    iss = issues[0]
    assert iss.rule_id == "COMPLEX-002"
    assert iss.severity == "major"
    assert iss.metadata_json["cyclomatic_complexity"] == 18


def test_deep_nesting_rule():
    rule = DeepNestingRule()
    sym = ExtractedSymbol(
        name="nested_hell",
        symbol_type="function",
        start_line=30,
        start_column=0,
        end_line=80,
        end_column=0,
    )
    sm = SymbolMetrics(
        name="nested_hell",
        symbol_type="function",
        start_line=30,
        end_line=80,
        lines_of_code=50,
        cyclomatic_complexity=8,
        nesting_depth=6,
        parameter_count=2,
    )
    ctx = make_context(symbols=[sym], symbol_metrics=[sm])
    issues = rule.evaluate(ctx)

    assert len(issues) == 1
    iss = issues[0]
    assert iss.rule_id == "COMPLEX-003"
    assert iss.severity == "major"
    assert iss.metadata_json["nesting_depth"] == 6


def test_giant_file_rule():
    rule = GiantFileRule()
    fm = FileMetrics(
        file_path="sample.py",
        language="Python",
        total_lines=1500,
        sloc=1200,
        comment_lines=100,
        blank_lines=200,
        statement_count=800,
        maintainability_score=45.0,
        total_cyclomatic_complexity=60,
        average_cyclomatic_complexity=5.0,
        max_cyclomatic_complexity=12,
        symbols_metrics=[],
    )
    ctx = make_context(file_metrics=fm)
    issues = rule.evaluate(ctx)

    assert len(issues) == 1
    iss = issues[0]
    assert iss.rule_id == "COMPLEX-004"
    assert iss.severity == "major"
    assert iss.metadata_json["sloc"] == 1200


def test_long_parameter_list_rule():
    rule = LongParameterListRule()
    sym = ExtractedSymbol(
        name="many_args",
        symbol_type="function",
        start_line=5,
        start_column=0,
        end_line=15,
        end_column=0,
    )
    sm = SymbolMetrics(
        name="many_args",
        symbol_type="function",
        start_line=5,
        end_line=15,
        lines_of_code=10,
        cyclomatic_complexity=2,
        nesting_depth=1,
        parameter_count=8,
    )
    ctx = make_context(symbols=[sym], symbol_metrics=[sm])
    issues = rule.evaluate(ctx)

    assert len(issues) == 1
    iss = issues[0]
    assert iss.rule_id == "COMPLEX-005"
    assert iss.severity == "minor"
    assert iss.metadata_json["parameter_count"] == 8


@pytest.mark.parametrize("cc,expected_high,expected_crit", [
    (10, 0, 0),  # CC=10: Neither COMPLEX-002 nor COMPLEX-001
    (11, 1, 0),  # CC=11: COMPLEX-002 fires (11 <= CC < 20), COMPLEX-001 does not
    (19, 1, 0),  # CC=19: COMPLEX-002 fires (11 <= CC < 20), COMPLEX-001 does not
    (20, 0, 1),  # CC=20: COMPLEX-001 fires (CC >= 20), COMPLEX-002 does NOT fire
])
def test_complexity_boundary_cc_10_11_19_20(cc, expected_high, expected_crit):
    rule_high = HighComplexityMethodRule()
    rule_crit = CriticalComplexityMethodRule()

    sym = ExtractedSymbol(
        name="boundary_func",
        symbol_type="function",
        start_line=1,
        start_column=0,
        end_line=30,
        end_column=0,
    )
    sm = SymbolMetrics(
        name="boundary_func",
        symbol_type="function",
        start_line=1,
        end_line=30,
        lines_of_code=25,
        cyclomatic_complexity=cc,
        nesting_depth=2,
        parameter_count=2,
    )
    ctx = make_context(symbols=[sym], symbol_metrics=[sm])

    issues_high = rule_high.evaluate(ctx)
    issues_crit = rule_crit.evaluate(ctx)

    assert len(issues_high) == expected_high, f"Expected {expected_high} COMPLEX-002 for CC={cc}, got {len(issues_high)}"
    assert len(issues_crit) == expected_crit, f"Expected {expected_crit} COMPLEX-001 for CC={cc}, got {len(issues_crit)}"
    if expected_high:
        assert issues_high[0].rule_id == "COMPLEX-002"
        assert issues_high[0].metadata_json["cyclomatic_complexity"] == cc
    if expected_crit:
        assert issues_crit[0].rule_id == "COMPLEX-001"
        assert issues_crit[0].metadata_json["cyclomatic_complexity"] == cc


@pytest.mark.parametrize("param_count,expected_issues", [
    (5, 0),  # params=5: LongParameterListRule should NOT fire (< 6)
    (6, 1),  # params=6: LongParameterListRule fires (>= 6)
    (7, 1),  # params=7: LongParameterListRule fires (>= 6)
])
def test_parameter_count_boundary_5_6_7(param_count, expected_issues):
    rule = LongParameterListRule()
    sym = ExtractedSymbol(
        name="param_func",
        symbol_type="function",
        start_line=1,
        start_column=0,
        end_line=10,
        end_column=0,
    )
    sm = SymbolMetrics(
        name="param_func",
        symbol_type="function",
        start_line=1,
        end_line=10,
        lines_of_code=8,
        cyclomatic_complexity=1,
        nesting_depth=1,
        parameter_count=param_count,
    )
    ctx = make_context(symbols=[sym], symbol_metrics=[sm])
    issues = rule.evaluate(ctx)

    assert len(issues) == expected_issues, f"Expected {expected_issues} COMPLEX-005 for params={param_count}, got {len(issues)}"
    if expected_issues:
        assert issues[0].rule_id == "COMPLEX-005"
        assert issues[0].metadata_json["parameter_count"] == param_count

