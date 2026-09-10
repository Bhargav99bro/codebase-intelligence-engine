import pytest
from app.services.hotspot_analyzer import (
    HotspotAnalyzer,
    calculate_architectural_centrality,
    calculate_complexity_risk,
    calculate_composite_hotspot_score,
    calculate_issue_severity_burden,
)


def test_complexity_risk_boundaries():
    # Zero values -> 0.0
    assert calculate_complexity_risk(0, 0, 0) == 0.0
    assert calculate_complexity_risk(-1, -5, -2) == 0.0

    # Exact threshold -> 100.0 (40 + 40 + 20)
    assert calculate_complexity_risk(1000, 20, 5) == 100.0

    # Partial calculations
    # 500 SLOC -> 20.0, 10 CC -> 20.0, 0 Nesting -> 0.0 => 40.0
    assert calculate_complexity_risk(500, 10, 0) == 40.0

    # Extreme outliers -> clamped to 100.0
    assert calculate_complexity_risk(15000, 120, 25) == 100.0


def test_architectural_centrality_boundaries():
    # Zero values -> 0.0
    assert calculate_architectural_centrality(0, 0) == 0.0
    assert calculate_architectural_centrality(-2, -5) == 0.0

    # Exact threshold (10 fan-in * 6 + 10 fan-out * 4) -> 100.0
    assert calculate_architectural_centrality(10, 10) == 100.0

    # Fan-in only: 10 * 6.0 = 60.0
    assert calculate_architectural_centrality(10, 0) == 60.0

    # Fan-out only: 10 * 4.0 = 40.0
    assert calculate_architectural_centrality(0, 10) == 40.0

    # Extreme outliers -> clamped to 100.0
    assert calculate_architectural_centrality(150, 85) == 100.0


def test_issue_severity_burden_boundaries():
    # Zero issues -> 0.0
    assert calculate_issue_severity_burden(0, 0, 0, 0) == 0.0

    # Individual weights: blocker=40, critical=25, major=10, minor=2
    assert calculate_issue_severity_burden(1, 0, 0, 0) == 40.0
    assert calculate_issue_severity_burden(0, 1, 0, 0) == 25.0
    assert calculate_issue_severity_burden(0, 0, 1, 0) == 10.0
    assert calculate_issue_severity_burden(0, 0, 0, 1) == 2.0

    # Combined exact 100: 1 blocker (40) + 1 critical (25) + 3 major (30) + 2.5 minor -> clamped
    assert calculate_issue_severity_burden(1, 1, 3, 3) == 100.0

    # Extreme outliers -> clamped to 100.0
    assert calculate_issue_severity_burden(10, 10, 50, 100) == 100.0


def test_composite_hotspot_score_boundaries():
    # All zeroes -> 0.0
    assert calculate_composite_hotspot_score(0.0, 0.0, 0.0) == 0.0

    # All max -> 100.0 (0.40 * 100 + 0.35 * 100 + 0.25 * 100)
    assert calculate_composite_hotspot_score(100.0, 100.0, 100.0) == 100.0

    # Balanced weights: 0.40 * 50 + 0.35 * 40 + 0.25 * 20 = 20 + 14 + 5 = 39.0
    assert calculate_composite_hotspot_score(50.0, 40.0, 20.0) == 39.0


def test_hotspot_tie_breaking_determinism():
    # Two files with identical H: tie broken by A_norm, then C_norm, then file_path
    candidates = [
        {
            "path": "z_file.py",
            "sloc": 500,
            "max_cc": 10,
            "max_nesting": 2,
            "fan_in": 5,
            "fan_out": 2,
            "issues": {"blocker": 0, "critical": 0, "major": 1, "minor": 0},
        },
        {
            "path": "a_file.py",
            "sloc": 500,
            "max_cc": 10,
            "max_nesting": 2,
            "fan_in": 5,
            "fan_out": 2,
            "issues": {"blocker": 0, "critical": 0, "major": 1, "minor": 0},
        },
    ]

    hotspots = HotspotAnalyzer.analyze(candidates)
    assert len(hotspots) == 2
    # Identical metrics, alphabetical tie-breaker ensures a_file.py is rank 1
    assert hotspots[0].file_path == "a_file.py"
    assert hotspots[0].rank == 1
    assert hotspots[1].file_path == "z_file.py"
    assert hotspots[1].rank == 2


def test_hotspot_repeatability_on_shuffled_inputs():
    import random

    raw_data = [
        {"path": f"src/module_{i}.py", "sloc": i * 100, "max_cc": i * 2, "max_nesting": i % 4, "fan_in": i, "fan_out": i % 3, "issues": {"blocker": 0, "critical": 0, "major": i % 2, "minor": 1}}
        for i in range(1, 20)
    ]

    # Run original
    h1 = HotspotAnalyzer.analyze(raw_data, max_results=10)

    # Shuffle and run 5 times
    for seed in (42, 99, 123, 777, 2026):
        shuffled = list(raw_data)
        random.seed(seed)
        random.shuffle(shuffled)
        h2 = HotspotAnalyzer.analyze(shuffled, max_results=10)

        assert [x.file_path for x in h1] == [x.file_path for x in h2]
        assert [x.hotspot_score for x in h1] == [x.hotspot_score for x in h2]
