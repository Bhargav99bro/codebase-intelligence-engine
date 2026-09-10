import uuid
import pytest

from app.dependencies.base import DependencyType, ResolutionStatus, ResolvedDependency
from app.dependencies.graph import DirectedDependencyGraph


def test_dependency_graph_metrics_and_instability():
    graph = DirectedDependencyGraph()

    id_a = uuid.uuid4()
    id_b = uuid.uuid4()
    id_c = uuid.uuid4()
    id_isolated = uuid.uuid4()

    graph.add_file_node(id_a, "a.py", "Python")
    graph.add_file_node(id_b, "b.py", "Python")
    graph.add_file_node(id_c, "c.py", "Python")
    graph.add_file_node(id_isolated, "isolated.py", "Python")

    # A -> B (A imports B)
    graph.process_resolved_dependency(
        ResolvedDependency(
            source_file_path="a.py",
            source_file_id=id_a,
            target_module="b",
            dependency_type=DependencyType.IMPORT.value,
            imported_symbols=["*"],
            line_number=1,
            resolution_status=ResolutionStatus.INTERNAL.value,
            target_file_id=id_b,
            target_file_path="b.py",
        )
    )

    # A -> C (A imports C)
    graph.process_resolved_dependency(
        ResolvedDependency(
            source_file_path="a.py",
            source_file_id=id_a,
            target_module="c",
            dependency_type=DependencyType.IMPORT.value,
            imported_symbols=["*"],
            line_number=2,
            resolution_status=ResolutionStatus.INTERNAL.value,
            target_file_id=id_c,
            target_file_path="c.py",
        )
    )

    # B -> C (B imports C)
    graph.process_resolved_dependency(
        ResolvedDependency(
            source_file_path="b.py",
            source_file_id=id_b,
            target_module="c",
            dependency_type=DependencyType.IMPORT.value,
            imported_symbols=["*"],
            line_number=1,
            resolution_status=ResolutionStatus.INTERNAL.value,
            target_file_id=id_c,
            target_file_path="c.py",
        )
    )

    # External dependency from A
    graph.process_resolved_dependency(
        ResolvedDependency(
            source_file_path="a.py",
            source_file_id=id_a,
            target_module="sys",
            dependency_type=DependencyType.IMPORT.value,
            imported_symbols=["*"],
            line_number=3,
            resolution_status=ResolutionStatus.EXTERNAL.value,
        )
    )

    graph.compute_metrics()

    # Verify A: fan_in=0, fan_out=2 -> I = 2 / (0 + 2) = 1.0 (maximally unstable)
    node_a = graph.nodes[id_a]
    assert node_a.fan_in == 0
    assert node_a.fan_out == 2
    assert node_a.instability == 1.0
    assert node_a.internal_dependencies_count == 2
    assert node_a.external_dependencies_count == 1

    # Verify B: fan_in=1 (from A), fan_out=1 (to C) -> I = 1 / (1 + 1) = 0.5
    node_b = graph.nodes[id_b]
    assert node_b.fan_in == 1
    assert node_b.fan_out == 1
    assert node_b.instability == 0.5

    # Verify C: fan_in=2 (from A, B), fan_out=0 -> I = 0 / (2 + 0) = 0.0 (maximally stable)
    node_c = graph.nodes[id_c]
    assert node_c.fan_in == 2
    assert node_c.fan_out == 0
    assert node_c.instability == 0.0

    # Verify Isolated node: zero degree case explicitly defined as 0.0
    node_iso = graph.nodes[id_isolated]
    assert node_iso.fan_in == 0
    assert node_iso.fan_out == 0
    assert node_iso.instability == 0.0

    # Summary metrics
    summary = graph.get_summary_metrics()
    assert summary["total_dependencies"] == 4
    assert summary["internal_dependencies"] == 3
    assert summary["external_dependencies"] == 1
    assert summary["isolated_files_count"] == 1
    assert summary["max_fan_in"] == 2
    assert summary["max_fan_out"] == 2
