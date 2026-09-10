import uuid
import pytest

from app.dependencies.base import DependencyType, ResolutionStatus, ResolvedDependency
from app.dependencies.graph import DirectedDependencyGraph


def _add_internal_edge(graph: DirectedDependencyGraph, src_id: uuid.UUID, src_path: str, tgt_id: uuid.UUID, tgt_path: str):
    graph.add_file_node(src_id, src_path, "Python")
    graph.add_file_node(tgt_id, tgt_path, "Python")
    graph.process_resolved_dependency(
        ResolvedDependency(
            source_file_path=src_path,
            source_file_id=src_id,
            target_module=tgt_path,
            dependency_type=DependencyType.IMPORT.value,
            imported_symbols=["*"],
            line_number=1,
            resolution_status=ResolutionStatus.INTERNAL.value,
            target_file_id=tgt_id,
            target_file_path=tgt_path,
        )
    )


def test_acyclic_graph_reports_zero_cycles():
    graph = DirectedDependencyGraph()
    id_a = uuid.uuid4()
    id_b = uuid.uuid4()
    id_c = uuid.uuid4()

    _add_internal_edge(graph, id_a, "a.py", id_b, "b.py")
    _add_internal_edge(graph, id_b, "b.py", id_c, "c.py")

    cycles = graph.detect_cycles()
    assert len(cycles) == 0
    assert graph.cycle_cap_reached is False


def test_two_node_cycle():
    graph = DirectedDependencyGraph()
    id_a = uuid.uuid4()
    id_b = uuid.uuid4()

    # A -> B -> A
    _add_internal_edge(graph, id_a, "a.py", id_b, "b.py")
    _add_internal_edge(graph, id_b, "b.py", id_a, "a.py")

    cycles = graph.detect_cycles()
    assert len(cycles) == 1
    c = cycles[0]
    assert c.length == 2
    assert c.file_paths == ["a.py", "b.py", "a.py"]
    assert graph.nodes[id_a].in_cycle is True
    assert graph.nodes[id_b].in_cycle is True


def test_three_node_cycle_and_rotation_deduplication():
    graph = DirectedDependencyGraph()
    id_a = uuid.uuid4()
    id_b = uuid.uuid4()
    id_c = uuid.uuid4()

    # A -> B -> C -> A
    _add_internal_edge(graph, id_a, "a.py", id_b, "b.py")
    _add_internal_edge(graph, id_b, "b.py", id_c, "c.py")
    _add_internal_edge(graph, id_c, "c.py", id_a, "a.py")

    cycles = graph.detect_cycles()
    # Must report exactly 1 cycle, not 3 rotations!
    assert len(cycles) == 1
    c = cycles[0]
    assert c.length == 3
    assert c.file_paths == ["a.py", "b.py", "c.py", "a.py"]


def test_self_loop_cycle():
    graph = DirectedDependencyGraph()
    id_a = uuid.uuid4()

    # A -> A
    _add_internal_edge(graph, id_a, "a.py", id_a, "a.py")

    cycles = graph.detect_cycles()
    assert len(cycles) == 1
    assert cycles[0].length == 1
    assert cycles[0].file_paths == ["a.py", "a.py"]


def test_disjoint_cycles():
    graph = DirectedDependencyGraph()
    id_a = uuid.uuid4()
    id_b = uuid.uuid4()
    id_c = uuid.uuid4()
    id_d = uuid.uuid4()

    # Cycle 1: A <-> B
    _add_internal_edge(graph, id_a, "a.py", id_b, "b.py")
    _add_internal_edge(graph, id_b, "b.py", id_a, "a.py")

    # Cycle 2: C <-> D
    _add_internal_edge(graph, id_c, "c.py", id_d, "d.py")
    _add_internal_edge(graph, id_d, "d.py", id_c, "c.py")

    cycles = graph.detect_cycles()
    assert len(cycles) == 2


def test_cycle_cap_enforcement():
    # Construct a dense graph (complete directed clique) where cycles exceed limit
    graph = DirectedDependencyGraph()
    nodes = [uuid.uuid4() for _ in range(6)]
    for i in range(len(nodes)):
        for j in range(len(nodes)):
            if i != j:
                _add_internal_edge(graph, nodes[i], f"node_{i}.py", nodes[j], f"node_{j}.py")

    # Run with low cap
    cap = 5
    cycles = graph.detect_cycles(max_cycles=cap)
    assert len(cycles) == cap
    assert graph.cycle_cap_reached is True
