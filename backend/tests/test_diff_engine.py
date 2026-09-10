import pytest
from app.services.diff_engine import (
    AnalysisDiffEngine,
    AnalysisDiffResult,
    PRGateStatus,
    canonicalize_cycle,
    compute_issue_fingerprint,
)


def test_issue_fingerprint_line_movement_preservation():
    # An issue originally on line 12 moves to line 85 due to preceding code edits
    fp_original = compute_issue_fingerprint(
        rule_id="COMPLEX-001",
        file_path="app/services/core.py",
        symbol_name="process_transaction",
    )
    fp_moved = compute_issue_fingerprint(
        rule_id="COMPLEX-001",
        file_path="app/services/core.py",
        symbol_name="process_transaction",
    )
    assert fp_original == fp_moved, "Line shift must preserve exact issue fingerprint"


def test_issue_fingerprint_changes_on_rule_file_symbol():
    fp_base = compute_issue_fingerprint("COMPLEX-001", "a.py", "func1")
    # Different rule
    fp_diff_rule = compute_issue_fingerprint("COMPLEX-002", "a.py", "func1")
    assert fp_base != fp_diff_rule

    # Different file
    fp_diff_file = compute_issue_fingerprint("COMPLEX-001", "b.py", "func1")
    assert fp_base != fp_diff_file

    # Different symbol
    fp_diff_sym = compute_issue_fingerprint("COMPLEX-001", "a.py", "func2")
    assert fp_base != fp_diff_sym


def test_cycle_canonicalization_rotation():
    c1 = ["c.py", "a.py", "b.py"]
    c2 = ["a.py", "b.py", "c.py"]
    c3 = ["b.py", "c.py", "a.py"]

    canon1 = canonicalize_cycle(c1)
    canon2 = canonicalize_cycle(c2)
    canon3 = canonicalize_cycle(c3)

    assert canon1 == ("a.py", "b.py", "c.py")
    assert canon2 == ("a.py", "b.py", "c.py")
    assert canon3 == ("a.py", "b.py", "c.py")


def test_cycle_canonicalization_closed_cycle():
    closed = ["x.py", "y.py", "z.py", "x.py"]
    canon = canonicalize_cycle(closed)
    assert canon == ("x.py", "y.py", "z.py")


def test_pr_quality_gate_failed_on_new_blocker():
    engine = AnalysisDiffEngine()
    base = {
        "id": "11111111-1111-1111-1111-111111111111",
        "health_score": {"overall_score": 90.0, "technical_debt_minutes": 100},
        "issues": [],
        "cycles": [],
    }
    curr = {
        "id": "22222222-2222-2222-2222-222222222222",
        "health_score": {"overall_score": 90.0, "technical_debt_minutes": 160},
        "issues": [
            {
                "rule_id": "SEC-001",
                "severity": "blocker",
                "file_path": "a.py",
                "symbol_name": "hardcoded_secret",
            }
        ],
        "cycles": [],
    }
    diff = engine.compare_analyses(base, curr)
    assert diff.base_id == "11111111-1111-1111-1111-111111111111"
    assert diff.head_id == "22222222-2222-2222-2222-222222222222"
    assert diff.quality_gate.status == PRGateStatus.FAILED
    assert diff.quality_gate.passed is False
    assert diff.quality_gate.new_blocker_count == 1
    assert diff.quality_gate.new_critical_count == 0
    assert len(diff.new_issues) == 1


def test_pr_quality_gate_warning_on_new_critical():
    engine = AnalysisDiffEngine()
    base = {
        "id": "11111111-1111-1111-1111-111111111111",
        "health_score": {"overall_score": 90.0, "technical_debt_minutes": 100},
        "issues": [],
        "cycles": [],
    }
    curr = {
        "id": "22222222-2222-2222-2222-222222222222",
        "health_score": {"overall_score": 90.0, "technical_debt_minutes": 160},
        "issues": [
            {
                "rule_id": "SEC-002",
                "severity": "critical",
                "file_path": "a.py",
                "symbol_name": "eval_sink",
            }
        ],
        "cycles": [],
    }
    diff = engine.compare_analyses(base, curr)
    assert diff.quality_gate.status == PRGateStatus.WARNING
    assert diff.quality_gate.passed is False
    assert diff.quality_gate.new_critical_count == 1
    assert diff.quality_gate.new_blocker_count == 0
    assert len(diff.new_issues) == 1


def test_pr_quality_gate_failed_on_new_cycle():
    engine = AnalysisDiffEngine()
    base = {
        "id": "11111111-1111-1111-1111-111111111111",
        "health_score": {"overall_score": 90.0},
        "issues": [],
        "cycles": [],
    }
    curr = {
        "id": "22222222-2222-2222-2222-222222222222",
        "health_score": {"overall_score": 90.0},
        "issues": [],
        "cycles": [["a.py", "b.py", "a.py"]],
    }
    diff = engine.compare_analyses(base, curr)
    assert diff.quality_gate.status == PRGateStatus.FAILED
    assert diff.quality_gate.new_cycles_count == 1
    assert len(diff.new_cycles) == 1


@pytest.mark.parametrize(
    "delta,expected_status",
    [
        (-2.1, PRGateStatus.FAILED),
        (-2.0, PRGateStatus.WARNING),
        (-1.0, PRGateStatus.WARNING),
        (-0.1, PRGateStatus.WARNING),
        (0.0, PRGateStatus.PASSED),
        (1.5, PRGateStatus.PASSED),
    ],
)
def test_pr_quality_gate_health_drop_boundaries(delta, expected_status):
    engine = AnalysisDiffEngine(allowed_score_drop=2.0)
    base_score = 80.0
    curr_score = base_score + delta
    base = {
        "id": "11111111-1111-1111-1111-111111111111",
        "health_score": {"overall_score": base_score},
        "issues": [],
        "cycles": [],
    }
    curr = {
        "id": "22222222-2222-2222-2222-222222222222",
        "health_score": {"overall_score": curr_score},
        "issues": [],
        "cycles": [],
    }
    diff = engine.compare_analyses(base, curr)
    assert diff.quality_gate.status == expected_status
    assert diff.delta_health_score == round(delta, 1)


def test_pr_quality_gate_configurable_allowed_drop():
    engine = AnalysisDiffEngine(allowed_score_drop=5.0)
    base = {
        "id": "11111111-1111-1111-1111-111111111111",
        "health_score": {"overall_score": 80.0},
        "issues": [],
        "cycles": [],
    }
    curr = {
        "id": "22222222-2222-2222-2222-222222222222",
        "health_score": {"overall_score": 76.5},  # -3.5 drop
        "issues": [],
        "cycles": [],
    }
    diff = engine.compare_analyses(base, curr)
    # -3.5 is between [-5.0, 0.0), so with allowed_score_drop=5.0 it is WARNING, not FAILED
    assert diff.quality_gate.status == PRGateStatus.WARNING

    # But with drop of -5.1 (< -5.0), it should FAIL
    curr_fail = {
        "id": "33333333-3333-3333-3333-333333333333",
        "health_score": {"overall_score": 74.9},  # -5.1 drop
        "issues": [],
        "cycles": [],
    }
    diff_fail = engine.compare_analyses(base, curr_fail)
    assert diff_fail.quality_gate.status == PRGateStatus.FAILED


def test_pr_quality_gate_passed_on_clean_diff():
    engine = AnalysisDiffEngine()
    base = {
        "id": "11111111-1111-1111-1111-111111111111",
        "health_score": {"overall_score": 85.0},
        "issues": [{"rule_id": "MAINT-001", "file_path": "a.py", "symbol_name": "x"}],
        "cycles": [],
    }
    curr = {
        "id": "22222222-2222-2222-2222-222222222222",
        "health_score": {"overall_score": 86.0},
        "issues": [{"rule_id": "MAINT-001", "file_path": "a.py", "symbol_name": "x"}],
        "cycles": [],
    }
    diff = engine.compare_analyses(base, curr)
    assert diff.quality_gate.status == PRGateStatus.PASSED
    assert diff.quality_gate.passed is True
    assert len(diff.new_issues) == 0
    assert len(diff.persistent_issues) == 1
    assert len(diff.fixed_issues) == 0
