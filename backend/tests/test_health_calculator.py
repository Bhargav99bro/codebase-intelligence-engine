import math
import uuid
import pytest
from app.analyzers.base import ExtractedSymbol
from app.dependencies.graph import (
    DetectedCycle,
    DirectedDependencyGraph,
)
from app.health.calculator import HealthCalculator, clamp
from app.metrics.base import (
    FileMetrics,
    SymbolMetrics,
)
from app.rules.base import CodebaseIssue, IssueCategory, IssueSeverity


def test_grade_calculation():
    calc = HealthCalculator()
    assert calc.calculate_grade(100.0) == "A+"
    assert calc.calculate_grade(95.0) == "A+"
    assert calc.calculate_grade(94.9) == "A"
    assert calc.calculate_grade(90.0) == "A"
    assert calc.calculate_grade(85.0) == "B"
    assert calc.calculate_grade(80.0) == "B"
    assert calc.calculate_grade(75.0) == "C"
    assert calc.calculate_grade(70.0) == "C"
    assert calc.calculate_grade(65.0) == "D"
    assert calc.calculate_grade(60.0) == "D"
    assert calc.calculate_grade(59.9) == "F"
    assert calc.calculate_grade(0.0) == "F"


def test_maintainability_score_formula():
    calc = HealthCalculator()
    # 2 files: one healthy MI=80, one low MI=30
    fm1 = FileMetrics(
        file_path="f1.py",
        language="Python",
        total_lines=100,
        sloc=80,
        comment_lines=10,
        blank_lines=10,
        statement_count=50,
        maintainability_score=80.0,
        total_cyclomatic_complexity=5,
        average_cyclomatic_complexity=1.0,
        max_cyclomatic_complexity=2,
        symbols_metrics=[],
    )
    fm2 = FileMetrics(
        file_path="f2.py",
        language="Python",
        total_lines=100,
        sloc=80,
        comment_lines=10,
        blank_lines=10,
        statement_count=50,
        maintainability_score=30.0,
        total_cyclomatic_complexity=25,
        average_cyclomatic_complexity=5.0,
        max_cyclomatic_complexity=12,
        symbols_metrics=[],
    )
    fmap = {"f1.py": fm1, "f2.py": fm2}

    # mean_mi = 55.0. low_mi_count = 1 -> p_low_mi = 0.5.
    # symbols: 1 documented, 1 undocumented -> r_doc = 0.5 -> 50.0
    # score = 0.70 * 55.0 + 0.30 * 50.0 - 0.5 * 25.0 = 38.5 + 15.0 - 12.5 = 41.0
    sym_doc = ExtractedSymbol(name="doc_func", symbol_type="function", start_line=1, start_column=0, end_line=5, end_column=0, metadata_json={"docstring": "hello"})
    sym_undoc = ExtractedSymbol(name="undoc_func", symbol_type="function", start_line=1, start_column=0, end_line=5, end_column=0, metadata_json={})
    parsed = [{"symbols": [sym_doc, sym_undoc]}]

    score = calc.calculate_maintainability_score(fmap, parsed)
    assert score == pytest.approx(41.0, abs=0.1)


def test_complexity_score_formula():
    calc = HealthCalculator()
    # 2 functions: one CC=5, one CC=22, nesting=5
    sm1 = SymbolMetrics(name="simple", symbol_type="function", start_line=1, end_line=10, lines_of_code=10, cyclomatic_complexity=5, nesting_depth=1, parameter_count=1)
    sm2 = SymbolMetrics(name="complex", symbol_type="function", start_line=11, end_line=50, lines_of_code=40, cyclomatic_complexity=22, nesting_depth=5, parameter_count=2)

    fm = FileMetrics(
        file_path="f.py",
        language="Python",
        total_lines=50,
        sloc=50,
        comment_lines=0,
        blank_lines=0,
        statement_count=30,
        maintainability_score=60.0,
        total_cyclomatic_complexity=27,
        average_cyclomatic_complexity=13.5,
        max_cyclomatic_complexity=22,
        symbols_metrics=[sm1, sm2],
    )

    score = calc.calculate_complexity_score({"f.py": fm})
    # f_mod = 0/2, f_high = 0/2, f_vhigh = 1/2 = 0.5
    # deduction_dist = 0.5 * 60 = 30.0
    # deduction_outliers = min(15, (22 - 15) * 0.5) + min(10, (5 - 4) * 2.0) = 3.5 + 2.0 = 5.5
    # score = 100 - (30.0 + 5.5) = 64.5
    assert score == pytest.approx(64.5, abs=0.1)


def test_architecture_score_formula():
    calc = HealthCalculator()
    graph = DirectedDependencyGraph()
    id1, id2, id3 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    graph.add_file_node(id1, "a.py", "Python")
    graph.add_file_node(id2, "b.py", "Python")
    graph.add_file_node(id3, "c.py", "Python")

    # 1 cycle between a and b
    graph.cycles = [
        DetectedCycle(cycle_id=1, length=2, file_ids=[id1, id2], file_paths=["a.py", "b.py"], edges=[])
    ]

    issues = [
        CodebaseIssue(
            rule_id="ARCH-002",
            rule_name="God Module",
            category="architecture",
            severity="major",
            title="God Module",
            description="...",
        )
    ]

    score = calc.calculate_architecture_score(graph, issues)
    # n_files = 3. n_cycles = 1, n_cyclic_files = 2.
    # penalty_cycles = min(45, 12 + (2/3)*25) = 12 + 16.67 = 28.67
    # penalty_coupling = min(30, 1 * 6) = 6.0
    # penalty_sap = 0
    # score = 100 - (28.67 + 6.0) = 65.33 -> 65.3
    assert score == pytest.approx(65.3, abs=0.2)


def test_hygiene_score_formula_weights():
    calc = HealthCalculator()
    # 1 blocker, 1 critical, 1 major, 1 minor
    issues = [
        CodebaseIssue(rule_id="SEC-001", rule_name="Secret", category=IssueCategory.SECURITY.value, severity=IssueSeverity.BLOCKER.value, title="Secret", description="..."),
        CodebaseIssue(rule_id="SEC-002", rule_name="Eval", category=IssueCategory.SECURITY.value, severity=IssueSeverity.CRITICAL.value, title="Eval", description="..."),
        CodebaseIssue(rule_id="HYGIENE-001", rule_name="Empty Except", category=IssueCategory.HYGIENE.value, severity=IssueSeverity.MAJOR.value, title="Except", description="..."),
        CodebaseIssue(rule_id="HYGIENE-002", rule_name="Dead Private", category=IssueCategory.HYGIENE.value, severity=IssueSeverity.MINOR.value, title="Dead", description="..."),
    ]
    # total_sloc = 1000 -> scale_factor = max(1.0, sqrt(1000/1000)) = 1.0
    # weight_raw = 1*25.0 + 1*12.0 + 1*5.0 + 1*1.5 = 43.5
    # score = 100 - 43.5 = 56.5
    score = calc.calculate_hygiene_score(issues, total_sloc=1000)
    assert score == pytest.approx(56.5, abs=0.1)


def test_overall_health_clamping():
    calc = HealthCalculator()
    assert clamp(-15.0, 0.0, 100.0) == 0.0
    assert clamp(120.0, 0.0, 100.0) == 100.0

    # Test extreme blocker count clamping
    massive_blockers = [
        CodebaseIssue(rule_id="SEC-001", rule_name="Secret", category=IssueCategory.SECURITY.value, severity=IssueSeverity.BLOCKER.value, title="Secret", description="...")
        for _ in range(50)
    ]
    score = calc.calculate_hygiene_score(massive_blockers, total_sloc=500)
    assert score == 0.0


def test_hygiene_score_ignores_architecture_complexity_maintainability_issues():
    calc = HealthCalculator()

    # Create issues from other pillars (architecture, complexity, maintainability)
    non_hygiene_issues = [
        CodebaseIssue(rule_id="ARCH-001", rule_name="Cycle", category=IssueCategory.ARCHITECTURE.value, severity=IssueSeverity.BLOCKER.value, title="Cycle", description="..."),
        CodebaseIssue(rule_id="ARCH-002", rule_name="God Module", category=IssueCategory.ARCHITECTURE.value, severity=IssueSeverity.CRITICAL.value, title="God Module", description="..."),
        CodebaseIssue(rule_id="COMPLEX-001", rule_name="Crit CC", category=IssueCategory.COMPLEXITY.value, severity=IssueSeverity.CRITICAL.value, title="Crit CC", description="..."),
        CodebaseIssue(rule_id="COMPLEX-002", rule_name="High CC", category=IssueCategory.COMPLEXITY.value, severity=IssueSeverity.MAJOR.value, title="High CC", description="..."),
        CodebaseIssue(rule_id="MAINT-001", rule_name="Low MI", category=IssueCategory.MAINTAINABILITY.value, severity=IssueSeverity.MAJOR.value, title="Low MI", description="..."),
        CodebaseIssue(rule_id="MAINT-002", rule_name="High Churn", category=IssueCategory.MAINTAINABILITY.value, severity=IssueSeverity.MINOR.value, title="High Churn", description="..."),
    ]

    # Without any hygiene/security issues, hygiene score should remain a perfect 100.0
    score_clean = calc.calculate_hygiene_score(non_hygiene_issues, total_sloc=1000)
    assert score_clean == 100.0, f"Expected 100.0 hygiene score despite non-hygiene issues, got {score_clean}"

    # Adding a single hygiene minor issue should deduct exactly according to hygiene formula only
    mixed_issues = non_hygiene_issues + [
        CodebaseIssue(rule_id="HYGIENE-002", rule_name="Dead Private", category=IssueCategory.HYGIENE.value, severity=IssueSeverity.MINOR.value, title="Dead Private", description="...")
    ]
    # For total_sloc=1000, scale_factor=1.0, 1 minor = 1.5 deduction -> 98.5
    score_mixed = calc.calculate_hygiene_score(mixed_issues, total_sloc=1000)
    assert score_mixed == 98.5

