import uuid
import pytest

from app.dependencies.base import DependencyType, ResolutionStatus, ResolvedDependency
from app.dependencies.graph import DirectedDependencyGraph
from app.dependencies.impact import ImpactAnalyzer


def _connect(graph: DirectedDependencyGraph, src: uuid.UUID, src_path: str, tgt: uuid.UUID, tgt_path: str):
    graph.add_file_node(src, src_path, "Python")
    graph.add_file_node(tgt, tgt_path, "Python")
    graph.process_resolved_dependency(
        ResolvedDependency(
            source_file_path=src_path,
            source_file_id=src,
            target_module=tgt_path,
            dependency_type=DependencyType.IMPORT.value,
            imported_symbols=["*"],
            line_number=1,
            resolution_status=ResolutionStatus.INTERNAL.value,
            target_file_id=tgt,
            target_file_path=tgt_path,
        )
    )


def test_impact_analysis_dependents_blast_radius():
    # Setup:
    # service.py imports database.py
    # api.py imports service.py
    # worker.py imports service.py
    # client.py imports api.py
    # If database.py changes:
    # Direct dependents: service.py (depth 1)
    # Transitive dependents: api.py (depth 2), worker.py (depth 2), client.py (depth 3)
    graph = DirectedDependencyGraph()
    id_db = uuid.uuid4()
    id_svc = uuid.uuid4()
    id_api = uuid.uuid4()
    id_worker = uuid.uuid4()
    id_client = uuid.uuid4()

    _connect(graph, id_svc, "service.py", id_db, "database.py")
    _connect(graph, id_api, "api.py", id_svc, "service.py")
    _connect(graph, id_worker, "worker.py", id_svc, "service.py")
    _connect(graph, id_client, "client.py", id_api, "api.py")

    analyzer = ImpactAnalyzer(graph)
    res = analyzer.analyze(id_db, direction="dependents", max_depth=5)

    assert res is not None
    assert res.target_file_path == "database.py"
    assert res.affected_files_count == 4
    assert res.direct_count == 1  # service.py
    assert res.transitive_count == 3  # api.py, worker.py, client.py

    paths = {it.file_path: (it.depth, it.relationship_path) for it in res.items}
    assert paths["service.py"][0] == 1
    assert paths["service.py"][1] == ["database.py", "service.py"]

    assert paths["api.py"][0] == 2
    assert paths["api.py"][1] == ["database.py", "service.py", "api.py"]

    assert paths["worker.py"][0] == 2
    assert paths["worker.py"][1] == ["database.py", "service.py", "worker.py"]

    assert paths["client.py"][0] == 3
    assert paths["client.py"][1] == ["database.py", "service.py", "api.py", "client.py"]


def test_impact_analysis_dependencies_direction():
    # Setup: client.py imports api.py, api.py imports service.py
    # If client.py is queried with direction='dependencies':
    # Direct dependency: api.py (depth 1)
    # Transitive dependency: service.py (depth 2)
    graph = DirectedDependencyGraph()
    id_client = uuid.uuid4()
    id_api = uuid.uuid4()
    id_svc = uuid.uuid4()

    _connect(graph, id_client, "client.py", id_api, "api.py")
    _connect(graph, id_api, "api.py", id_svc, "service.py")

    analyzer = ImpactAnalyzer(graph)
    res = analyzer.analyze(id_client, direction="dependencies", max_depth=5)

    assert res is not None
    assert res.affected_files_count == 2
    assert res.direct_count == 1
    assert res.transitive_count == 1
    paths = {it.file_path: it.depth for it in res.items}
    assert paths["api.py"] == 1
    assert paths["service.py"] == 2


def test_impact_analysis_depth_limit_and_cycle_safety():
    # Setup: A <-> B cycle (A imports B, B imports A)
    # C imports B
    # Verify BFS terminates gracefully without infinite loop on cycles
    graph = DirectedDependencyGraph()
    id_a = uuid.uuid4()
    id_b = uuid.uuid4()
    id_c = uuid.uuid4()

    _connect(graph, id_a, "a.py", id_b, "b.py")
    _connect(graph, id_b, "b.py", id_a, "a.py")
    _connect(graph, id_c, "c.py", id_b, "b.py")

    analyzer = ImpactAnalyzer(graph)
    # Analyze dependents of A:
    # B imports A (depth 1)
    # C imports B (depth 2)
    # A is visited, cycle stops
    res = analyzer.analyze(id_a, direction="dependents", max_depth=1)
    assert res is not None
    # With max_depth=1, only B is returned
    assert res.affected_files_count == 1
    assert res.items[0].file_path == "b.py"

    # With max_depth=5, B and C are returned, no duplicate A
    res2 = analyzer.analyze(id_a, direction="dependents", max_depth=5)
    assert res2.affected_files_count == 2
    affected_paths = [it.file_path for it in res2.items]
    assert "b.py" in affected_paths
    assert "c.py" in affected_paths
