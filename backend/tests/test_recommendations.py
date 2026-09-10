import uuid
import pytest
from app.analyzers.base import ExtractedSymbol
from app.dependencies.graph import DetectedCycle, DirectedDependencyGraph
from app.health.calculator import HealthCalculator
from app.health.recommendations import RecommendationEngine
from app.metrics.base import (
    FileMetrics,
    SymbolMetrics,
)
from app.services.file_discovery import DiscoveredFile
from app.rules.base import CodebaseIssue, IssueCategory, IssueSeverity


def test_empty_issues_recommendations():
    calc = HealthCalculator()
    rec_engine = RecommendationEngine(calc)
    health = calc.compute({}, [], DirectedDependencyGraph(), [])
    recs = rec_engine.generate_recommendations(
        current_health=health,
        file_metrics_map={},
        parsed_files_data=[],
        graph=DirectedDependencyGraph(),
        issues=[],
    )
    assert recs == []


def test_symbol_complexity_recommendation_modeled_recovery():
    calc = HealthCalculator()
    rec_engine = RecommendationEngine(calc)

    fid = uuid.uuid4()
    fpath = "app/complex.py"
    df = DiscoveredFile(
        path=fpath,
        filename="complex.py",
        extension=".py",
        size_bytes=1000,
        line_count=200,
        language="Python",
        is_analyzable=True,
    )

    sm = SymbolMetrics(
        name="huge_handler",
        symbol_type="function",
        start_line=10,
        end_line=150,
        lines_of_code=140,
        cyclomatic_complexity=35,
        nesting_depth=5,
        parameter_count=3,
    )
    fm = FileMetrics(
        file_path=fpath,
        language="Python",
        total_lines=200,
        sloc=150,
        comment_lines=10,
        blank_lines=40,
        statement_count=100,
        maintainability_score=45.0,
        total_cyclomatic_complexity=35,
        average_cyclomatic_complexity=35.0,
        max_cyclomatic_complexity=35,
        symbols_metrics=[sm],
    )

    parsed_files_data = [{
        "df": df,
        "symbols": [ExtractedSymbol(name="huge_handler", symbol_type="function", start_line=10, start_column=0, end_line=150, end_column=0)],
        "symbols_metrics": [sm],
        "content": "",
    }]

    graph = DirectedDependencyGraph()
    graph.add_file_node(fid, fpath, "Python")

    issue = CodebaseIssue(
        id=uuid.uuid4(),
        rule_id="COMPLEX-001",
        rule_name="Critical Complexity",
        category=IssueCategory.COMPLEXITY.value,
        severity=IssueSeverity.CRITICAL.value,
        title="Critical Complexity",
        description="CC=35",
        file_id=fid,
        file_path=fpath,
        symbol_name="huge_handler",
        remediation_effort_minutes=90,
        metadata_json={
            "target_type": "symbol",
            "target_identifier": f"{fpath}::huge_handler",
        },
    )

    fmap = {fpath: fm}
    current_health = calc.compute(fmap, parsed_files_data, graph, [issue])

    recs = rec_engine.generate_recommendations(
        current_health=current_health,
        file_metrics_map=fmap,
        parsed_files_data=parsed_files_data,
        graph=graph,
        issues=[issue],
        max_recommendations=5,
    )

    assert len(recs) == 1
    rec = recs[0]
    assert rec.target_type == "symbol"
    assert rec.target_identifier == f"{fpath}::huge_handler"
    assert rec.estimated_score_recovery is not None
    assert rec.estimated_score_recovery > 0.0
    assert rec.estimated_effort_minutes == 90
    assert not rec.qualitative

    d = rec.to_dict()
    assert d["target_name"] == "huge_handler"
    assert d["effort_hours"] == 1.5
    assert d["expected_score_recovery"] == rec.estimated_score_recovery


def test_cycle_break_recommendation():
    calc = HealthCalculator()
    rec_engine = RecommendationEngine(calc)

    id_a = uuid.uuid4()
    id_b = uuid.uuid4()
    graph = DirectedDependencyGraph()
    graph.add_file_node(id_a, "a.py", "Python")
    graph.add_file_node(id_b, "b.py", "Python")
    graph.cycles = [
        DetectedCycle(cycle_id=1, length=2, file_ids=[id_a, id_b], file_paths=["a.py", "b.py"], edges=[])
    ]

    issue = CodebaseIssue(
        id=uuid.uuid4(),
        rule_id="ARCH-001",
        rule_name="Cyclic Dependency",
        category=IssueCategory.ARCHITECTURE.value,
        severity=IssueSeverity.CRITICAL.value,
        title="Cycle #1",
        description="a -> b -> a",
        file_id=id_a,
        file_path="a.py",
        remediation_effort_minutes=120,
        metadata_json={
            "cycle_id": 1,
            "target_type": "cycle",
            "target_identifier": "cycle::1",
        },
    )

    fm_a = FileMetrics(file_path="a.py", language="Python", total_lines=50, sloc=40, comment_lines=5, blank_lines=5, statement_count=20, maintainability_score=80.0, total_cyclomatic_complexity=2, average_cyclomatic_complexity=2.0, max_cyclomatic_complexity=2, symbols_metrics=[])
    fm_b = FileMetrics(file_path="b.py", language="Python", total_lines=50, sloc=40, comment_lines=5, blank_lines=5, statement_count=20, maintainability_score=80.0, total_cyclomatic_complexity=2, average_cyclomatic_complexity=2.0, max_cyclomatic_complexity=2, symbols_metrics=[])
    fmap = {"a.py": fm_a, "b.py": fm_b}

    current_health = calc.compute(fmap, [], graph, [issue])

    recs = rec_engine.generate_recommendations(
        current_health=current_health,
        file_metrics_map=fmap,
        parsed_files_data=[],
        graph=graph,
        issues=[issue],
    )

    assert len(recs) == 1
    rec = recs[0]
    assert rec.target_type == "cycle"
    assert rec.target_identifier == "cycle::1"
    assert rec.estimated_score_recovery is not None
    assert rec.estimated_score_recovery > 0.0
    assert rec.estimated_effort_minutes == 120


def test_recommendation_ranking_deterministic_tie_breaker():
    calc = HealthCalculator()
    rec_engine = RecommendationEngine(calc)

    # 4 candidates where delta S, severities, and effort are identical
    # Canonical IDs: "repo/z.py", "repo/a.py", "repo/m.py", "repo/b.py"
    issues = [
        CodebaseIssue(
            rule_id="SEC-001",
            rule_name="Secret",
            category=IssueCategory.SECURITY.value,
            severity=IssueSeverity.BLOCKER.value,
            title="Secret in z",
            description="...",
            file_path="repo/z.py",
            remediation_effort_minutes=60,
            metadata_json={"target_identifier": "repo/z.py", "target_type": "file"},
        ),
        CodebaseIssue(
            rule_id="SEC-001",
            rule_name="Secret",
            category=IssueCategory.SECURITY.value,
            severity=IssueSeverity.BLOCKER.value,
            title="Secret in a",
            description="...",
            file_path="repo/a.py",
            remediation_effort_minutes=60,
            metadata_json={"target_identifier": "repo/a.py", "target_type": "file"},
        ),
        CodebaseIssue(
            rule_id="SEC-001",
            rule_name="Secret",
            category=IssueCategory.SECURITY.value,
            severity=IssueSeverity.BLOCKER.value,
            title="Secret in m",
            description="...",
            file_path="repo/m.py",
            remediation_effort_minutes=60,
            metadata_json={"target_identifier": "repo/m.py", "target_type": "file"},
        ),
        CodebaseIssue(
            rule_id="SEC-001",
            rule_name="Secret",
            category=IssueCategory.SECURITY.value,
            severity=IssueSeverity.BLOCKER.value,
            title="Secret in b",
            description="...",
            file_path="repo/b.py",
            remediation_effort_minutes=60,
            metadata_json={"target_identifier": "repo/b.py", "target_type": "file"},
        ),
    ]

    fm_map = {
        "repo/z.py": FileMetrics(file_path="repo/z.py", language="Python", sloc=100, total_lines=100),
        "repo/a.py": FileMetrics(file_path="repo/a.py", language="Python", sloc=100, total_lines=100),
        "repo/m.py": FileMetrics(file_path="repo/m.py", language="Python", sloc=100, total_lines=100),
        "repo/b.py": FileMetrics(file_path="repo/b.py", language="Python", sloc=100, total_lines=100),
    }

    graph = DirectedDependencyGraph()
    parsed_files_data = [
        {"df": DiscoveredFile(path=p, filename=p.split("/")[-1], extension=".py", size_bytes=100, line_count=100, language="Python", is_analyzable=True), "content": "", "symbols": [], "symbols_metrics": []}
        for p in fm_map
    ]

    current_health = calc.compute(fm_map, parsed_files_data, graph, issues)

    recs = rec_engine.generate_recommendations(
        current_health=current_health,
        file_metrics_map=fm_map,
        parsed_files_data=parsed_files_data,
        graph=graph,
        issues=issues,
        max_recommendations=4,
    )

    assert len(recs) == 4
    # All 4 have identical delta_s, identical blocker severity, identical effort.
    # Tie-breaking MUST be strictly alphabetical on target_identifier:
    identifiers = [r.target_identifier for r in recs]
    assert identifiers == ["repo/a.py", "repo/b.py", "repo/m.py", "repo/z.py"]


def test_recommendation_ranking_severity_hierarchy():
    calc = HealthCalculator()
    rec_engine = RecommendationEngine(calc)

    # 3 candidates:
    # Cand A: 1 BLOCKER, effort 60
    # Cand B: 3 CRITICAL, effort 90
    # Cand C: 5 MAJOR, effort 120
    # Cand D: Qualitative (no metric change, delta S = None)
    issues = [
        CodebaseIssue(
            rule_id="SEC-001",
            rule_name="Secret",
            category=IssueCategory.SECURITY.value,
            severity=IssueSeverity.BLOCKER.value,
            title="Secret",
            description="...",
            file_path="f_blocker.py",
            remediation_effort_minutes=60,
            metadata_json={"target_identifier": "f_blocker.py", "target_type": "file"},
        ),
        CodebaseIssue(
            rule_id="HYGIENE-001",
            rule_name="Except 1",
            category=IssueCategory.HYGIENE.value,
            severity=IssueSeverity.MAJOR.value,
            title="Except 1",
            description="...",
            file_path="f_major.py",
            remediation_effort_minutes=120,
            metadata_json={"target_identifier": "f_major.py", "target_type": "file"},
        ),
    ]

    fm_map = {
        "f_blocker.py": FileMetrics(file_path="f_blocker.py", language="Python", sloc=1000, total_lines=1000),
        "f_major.py": FileMetrics(file_path="f_major.py", language="Python", sloc=1000, total_lines=1000),
    }

    graph = DirectedDependencyGraph()
    parsed_files_data = [
        {"df": DiscoveredFile(path=p, filename=p.split("/")[-1], extension=".py", size_bytes=100, line_count=100, language="Python", is_analyzable=True), "content": "", "symbols": [], "symbols_metrics": []}
        for p in fm_map
    ]

    current_health = calc.compute(fm_map, parsed_files_data, graph, issues)

    recs = rec_engine.generate_recommendations(
        current_health=current_health,
        file_metrics_map=fm_map,
        parsed_files_data=parsed_files_data,
        graph=graph,
        issues=issues,
        max_recommendations=5,
    )

    # Blocker eliminates 25 weight -> higher delta_s than major eliminating 5 weight
    assert recs[0].target_identifier == "f_blocker.py"
    assert recs[1].target_identifier == "f_major.py"


def test_recommendations_k25_candidate_pool_and_top5():
    calc = HealthCalculator()
    rec_engine = RecommendationEngine(calc)

    # Generate 35 candidate targets with distinct files
    issues = []
    fm_map = {}
    parsed_files_data = []

    for i in range(35):
        fp = f"module_{i:02d}.py"
        fm_map[fp] = FileMetrics(file_path=fp, language="Python", sloc=100, total_lines=100)
        parsed_files_data.append({
            "df": DiscoveredFile(path=fp, filename=fp, extension=".py", size_bytes=100, line_count=100, language="Python", is_analyzable=True),
            "content": "",
            "symbols": [],
            "symbols_metrics": [],
        })
        issues.append(
            CodebaseIssue(
                rule_id="HYGIENE-001",
                rule_name="Empty Handler",
                category=IssueCategory.HYGIENE.value,
                severity=IssueSeverity.MAJOR.value,
                title=f"Empty handler in {fp}",
                description="...",
                file_path=fp,
                remediation_effort_minutes=30 + i,  # higher i has higher effort
                metadata_json={"target_identifier": fp, "target_type": "file"},
            )
        )

    graph = DirectedDependencyGraph()
    current_health = calc.compute(fm_map, parsed_files_data, graph, issues)

    # Generate recommendations with max_recommendations=5
    recs = rec_engine.generate_recommendations(
        current_health=current_health,
        file_metrics_map=fm_map,
        parsed_files_data=parsed_files_data,
        graph=graph,
        issues=issues,
        max_recommendations=5,
        max_candidates=25,
    )

    # Exactly 5 top recommendations returned
    assert len(recs) == 5
    # Ranks are 1, 2, 3, 4, 5
    assert [r.rank for r in recs] == [1, 2, 3, 4, 5]

