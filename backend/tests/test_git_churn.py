import pytest
from app.services.git_churn import (
    FileChurnMetric,
    GitChurnAnalyzer,
    GitChurnResult,
    clamp,
)


def test_git_churn_no_git_directory(tmp_path):
    analyzer = GitChurnAnalyzer()
    res = analyzer.analyze_churn(str(tmp_path))
    assert res.has_git_history is False
    assert res.metrics == {}
    assert res.max_churn == 0.0


def test_git_churn_exact_formula_and_clamping():
    # Cchurn = clamp((commit_count / 20) * 50.0 + ((insertions + deletions) / 1000) * 30.0 + (author_count / 5) * 20.0, 0.0, 100.0)

    # 1. Zero values
    assert GitChurnAnalyzer.calculate_churn_score(0, 0, 0, 0) == 0.0

    # 2. Typical values: 10 commits, 200 insertions, 100 deletions, 2 authors
    # (10/20)*50.0 = 25.0, (300/1000)*30.0 = 9.0, (2/5)*20.0 = 8.0 -> 42.0
    score = GitChurnAnalyzer.calculate_churn_score(10, 200, 100, 2)
    assert score == 42.0

    # 3. Clamping upper bound: 50 commits, 5000 lines, 10 authors
    # (50/20)*50 = 125, (5000/1000)*30 = 150, (10/5)*20 = 40 -> 315 -> clamped to 100.0
    score_high = GitChurnAnalyzer.calculate_churn_score(50, 2500, 2500, 10)
    assert score_high == 100.0

    # 4. Component tests
    # 20 commits alone gives (20/20)*50 = 50.0
    assert GitChurnAnalyzer.calculate_churn_score(20, 0, 0, 0) == 50.0

    # 1000 lines alone gives (1000/1000)*30 = 30.0
    assert GitChurnAnalyzer.calculate_churn_score(0, 500, 500, 0) == 30.0

    # 5 authors alone gives (5/5)*20 = 20.0
    assert GitChurnAnalyzer.calculate_churn_score(0, 0, 0, 5) == 20.0

    # Sum of unitary maximums = 50.0 + 30.0 + 20.0 = 100.0
    assert GitChurnAnalyzer.calculate_churn_score(20, 500, 500, 5) == 100.0


def test_git_churn_parser_null_delimited():
    analyzer = GitChurnAnalyzer()
    # Format: format=tformat:COMMIT%x00%H%x00%aN
    mock_log = (
        "COMMIT\0hash1\0Alice\0"
        "10\t5\tapp/main.py\0"
        "20\t2\tapp/utils.py\0"
        "COMMIT\0hash2\0Bob\0"
        "5\t1\tapp/main.py\0"
    )
    res = analyzer._parse_git_log_output(mock_log)
    assert res.has_git_history is True
    assert "app/main.py" in res.metrics
    assert "app/utils.py" in res.metrics

    m_main = res.metrics["app/main.py"]
    assert m_main.commit_count == 2
    assert m_main.author_count == 2
    assert m_main.added_lines == 15
    assert m_main.deleted_lines == 6
    assert m_main.churn_lines == 21
    expected_main_score = GitChurnAnalyzer.calculate_churn_score(2, 15, 6, 2)
    assert m_main.relative_churn == expected_main_score
    assert m_main.relative_churn == 13.6

    m_utils = res.metrics["app/utils.py"]
    assert m_utils.commit_count == 1
    assert m_utils.author_count == 1
    assert m_utils.added_lines == 20
    assert m_utils.deleted_lines == 2
    assert m_utils.churn_lines == 22
    expected_utils_score = GitChurnAnalyzer.calculate_churn_score(1, 20, 2, 1)
    assert m_utils.relative_churn == expected_utils_score
    assert m_utils.relative_churn == 7.2

    assert res.max_churn == 13.6


def test_defect_hotspot_fusion_formula():
    static_h = 75.0
    churn_metric = FileChurnMetric(
        file_path="app/core.py",
        commit_count=10,
        added_lines=100,
        deleted_lines=50,
        author_count=2,
        relative_churn=80.0,
    )
    # H_defect = clamp(0.60 * 75.0 + 0.40 * 80.0, 0, 100) = 45.0 + 32.0 = 77.0
    defect_h = GitChurnAnalyzer.calculate_defect_hotspot_score(
        static_hotspot_score=static_h,
        churn_metric=churn_metric,
        has_git_history=True,
    )
    assert defect_h == 77.0


def test_defect_hotspot_fallback_no_git():
    static_h = 82.5
    defect_h = GitChurnAnalyzer.calculate_defect_hotspot_score(
        static_hotspot_score=static_h,
        churn_metric=None,
        has_git_history=False,
    )
    assert defect_h == 82.5


def test_defect_hotspot_clamping_boundary():
    # Test boundary clamping at 100.0 and 0.0
    metric_high = FileChurnMetric(
        file_path="f.py",
        commit_count=10,
        added_lines=100,
        deleted_lines=50,
        author_count=2,
        relative_churn=100.0,
    )
    h_max = GitChurnAnalyzer.calculate_defect_hotspot_score(100.0, metric_high, True)
    assert h_max == 100.0

    metric_zero = FileChurnMetric(
        file_path="f.py",
        commit_count=0,
        added_lines=0,
        deleted_lines=0,
        author_count=0,
        relative_churn=0.0,
    )
    h_min = GitChurnAnalyzer.calculate_defect_hotspot_score(0.0, metric_zero, True)
    assert h_min == 0.0
