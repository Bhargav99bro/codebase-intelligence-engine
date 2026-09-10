import uuid
import pytest
from app.dependencies.graph import DirectedDependencyGraph
from app.health.calculator import HealthCalculator, clamp
from app.rules.base import IssueSeverity, RuleContext
from app.rules.maintainability_rules import DuplicateBlockRule
from app.services.clone_detector import DuplicateMatch


def test_dup_001_severities_and_remediation():
    rule = DuplicateBlockRule()

    # 1. 50+ lines -> CRITICAL
    dup_crit = DuplicateMatch(
        clone_type=1,
        source_file_path="src/heavy.py",
        source_start_line=10,
        source_end_line=65,
        target_file_path="src/heavy2.py",
        target_start_line=10,
        target_end_line=65,
        line_count=56,
        token_count=120,
        checksum="abcd1",
    )

    # 2. 15-49 lines -> MAJOR
    dup_major = DuplicateMatch(
        clone_type=2,
        source_file_path="src/mid.py",
        source_start_line=5,
        source_end_line=25,
        target_file_path="src/mid2.py",
        target_start_line=5,
        target_end_line=25,
        line_count=21,
        token_count=60,
        checksum="abcd2",
    )

    # 3. 10-14 lines -> MINOR
    dup_minor = DuplicateMatch(
        clone_type=1,
        source_file_path="src/small.py",
        source_start_line=1,
        source_end_line=12,
        target_file_path="src/small2.py",
        target_start_line=1,
        target_end_line=12,
        line_count=12,
        token_count=45,
        checksum="abcd3",
    )

    # 4. < 10 lines -> Ignored
    dup_tiny = DuplicateMatch(
        clone_type=1,
        source_file_path="src/tiny.py",
        source_start_line=1,
        source_end_line=8,
        target_file_path="src/tiny2.py",
        target_start_line=1,
        target_end_line=8,
        line_count=8,
        token_count=40,
        checksum="abcd4",
    )

    ctx = RuleContext(
        parsed_files_data=[],
        file_metrics_map={},
        graph=DirectedDependencyGraph(),
        file_id_map={},
        code_duplicates=[dup_crit, dup_major, dup_minor, dup_tiny],
    )

    issues = rule.evaluate(ctx)
    assert len(issues) == 3

    crit_iss = next(i for i in issues if i.file_path == "src/heavy.py")
    assert crit_iss.severity == IssueSeverity.CRITICAL.value
    assert crit_iss.remediation_effort_minutes == 56 * 2
    assert crit_iss.metadata_json["threshold_remediation_minutes"] == 120
    assert crit_iss.metadata_json["severity_threshold_effort_minutes"] == {"critical": 120, "major": 45, "minor": 30}

    maj_iss = next(i for i in issues if i.file_path == "src/mid.py")
    assert maj_iss.severity == IssueSeverity.MAJOR.value
    assert maj_iss.remediation_effort_minutes == 21 * 2
    assert maj_iss.metadata_json["threshold_remediation_minutes"] == 45

    min_iss = next(i for i in issues if i.file_path == "src/small.py")
    assert min_iss.severity == IssueSeverity.MINOR.value
    assert min_iss.remediation_effort_minutes == 12 * 2
    assert min_iss.metadata_json["threshold_remediation_minutes"] == 30


def test_duplication_score_formula_and_zero_baseline():
    calc = HealthCalculator()

    # Zero duplication baseline: 100.0
    s_zero = calc.calculate_duplication_score(duplication_ratio=0.0, duplicate_blocks_count=0)
    assert s_zero == 100.0

    # 10% ratio, 6 blocks
    # score = 100.0 - (10.0 * 1.5) - min(10.0, 6 * 0.5) = 100 - 15 - 3 = 82.0
    s_mid = calc.calculate_duplication_score(duplication_ratio=10.0, duplicate_blocks_count=6)
    assert s_mid == pytest.approx(82.0, abs=0.1)

    # Severe duplication clamped to 0.0
    s_extreme = calc.calculate_duplication_score(duplication_ratio=80.0, duplicate_blocks_count=50)
    assert s_extreme == 0.0


def test_five_factor_overall_health_weighting():
    calc = HealthCalculator()

    # All perfect: 100.0
    # 0.22*100 + 0.22*100 + 0.22*100 + 0.22*100 + 0.12*100 = 100.0
    breakdown_clean = calc.compute(
        file_metrics_map={},
        parsed_files_data=[],
        graph=DirectedDependencyGraph(),
        issues=[],
        duplication_ratio=0.0,
        duplicate_blocks_count=0,
    )
    assert breakdown_clean.overall_score == 100.0
    assert breakdown_clean.grade == "A+"
    assert breakdown_clean.duplication_score == 100.0
    assert breakdown_clean.category_scores["duplication"]["weight"] == 0.12
    assert breakdown_clean.category_scores["maintainability"]["weight"] == 0.22
