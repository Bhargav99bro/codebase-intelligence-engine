import uuid
import pytest
from app.dependencies.graph import (
    DetectedCycle,
    DirectedDependencyGraph,
    GraphEdge,
    GraphNode,
)
from app.metrics.base import FileMetrics
from app.rules.architecture_rules import (
    CyclicDependencyRule,
    GodModuleRule,
    UnstableDependencyRule,
    UnstableHubRule,
)
from app.rules.base import RuleContext


def make_arch_context(graph, file_metrics_map=None, file_id_map=None):
    return RuleContext(
        parsed_files_data=[],
        file_metrics_map=file_metrics_map or {},
        graph=graph,
        file_id_map=file_id_map or {},
    )


def test_cyclic_dependency_rule():
    rule = CyclicDependencyRule()
    id_a = uuid.uuid4()
    id_b = uuid.uuid4()
    fmap = {"a.py": id_a, "b.py": id_b}

    graph = DirectedDependencyGraph()
    graph.cycles = [
        DetectedCycle(
            cycle_id=1,
            length=2,
            file_ids=[id_a, id_b],
            file_paths=["a.py", "b.py"],
            edges=[],
        )
    ]

    ctx = make_arch_context(graph, file_id_map=fmap)
    issues = rule.evaluate(ctx)

    assert len(issues) == 1
    iss = issues[0]
    assert iss.rule_id == "ARCH-001"
    assert iss.severity == "critical"
    assert iss.metadata_json["length"] == 2
    assert iss.metadata_json["file_paths"] == ["a.py", "b.py"]
    assert iss.remediation_effort_minutes == 120


def test_god_module_rule():
    rule = GodModuleRule()
    fid = uuid.uuid4()
    fpath = "core/god.py"
    fmap = {fpath: fid}

    graph = DirectedDependencyGraph()
    graph.nodes[fid] = GraphNode(
        file_id=fid,
        file_path=fpath,
        fan_in=3,
        fan_out=15,
        instability=0.83,
    )

    fm = FileMetrics(
        file_path=fpath,
        language="Python",
        total_lines=700,
        sloc=550,
        comment_lines=50,
        blank_lines=100,
        statement_count=400,
        maintainability_score=50.0,
        total_cyclomatic_complexity=40,
        average_cyclomatic_complexity=4.0,
        max_cyclomatic_complexity=10,
        symbols_metrics=[],
    )

    ctx = make_arch_context(graph, file_metrics_map={fpath: fm}, file_id_map=fmap)
    issues = rule.evaluate(ctx)

    assert len(issues) == 1
    iss = issues[0]
    assert iss.rule_id == "ARCH-002"
    assert iss.severity == "major"
    assert iss.metadata_json["fan_out"] == 15
    assert iss.metadata_json["sloc"] == 550


def test_unstable_hub_rule():
    rule = UnstableHubRule()
    fid = uuid.uuid4()
    fpath = "services/hub.py"
    fmap = {fpath: fid}

    graph = DirectedDependencyGraph()
    graph.nodes[fid] = GraphNode(
        file_id=fid,
        file_path=fpath,
        fan_in=10,
        fan_out=9,
        instability=0.47,
    )

    ctx = make_arch_context(graph, file_id_map=fmap)
    issues = rule.evaluate(ctx)

    assert len(issues) == 1
    iss = issues[0]
    assert iss.rule_id == "ARCH-003"
    assert iss.severity == "major"
    assert iss.metadata_json["fan_in"] == 10
    assert iss.metadata_json["fan_out"] == 9


def test_unstable_dependency_rule():
    rule = UnstableDependencyRule()
    id_stable = uuid.uuid4()
    id_volatile = uuid.uuid4()

    graph = DirectedDependencyGraph()
    graph.nodes[id_stable] = GraphNode(
        file_id=id_stable,
        file_path="core/stable.py",
        fan_in=8,
        fan_out=1,
        instability=0.11,
    )
    graph.nodes[id_volatile] = GraphNode(
        file_id=id_volatile,
        file_path="plugins/volatile.py",
        fan_in=1,
        fan_out=7,
        instability=0.875,
    )
    graph.edges = [
        GraphEdge(
            id=uuid.uuid4(),
            source_file_id=id_stable,
            source_file_path="core/stable.py",
            target_file_id=id_volatile,
            target_file_path="plugins/volatile.py",
            target_module="plugins.volatile",
            dependency_type="internal",
            imported_symbols=["PluginHook"],
            line_number=14,
        )
    ]

    ctx = make_arch_context(graph)
    issues = rule.evaluate(ctx)

    assert len(issues) == 1
    iss = issues[0]
    assert iss.rule_id == "ARCH-004"
    assert iss.severity == "minor"
    assert iss.metadata_json["source_instability"] == pytest.approx(0.11, rel=1e-2)
    assert iss.metadata_json["target_instability"] == pytest.approx(0.875, rel=1e-2)
