import uuid
import pytest

from app.models.analysis import AnalysisJob, AnalysisStatus
from app.models.dependency import Dependency, FileDependencyMetric
from app.models.file import RepositoryFile
from app.models.repository import Repository


@pytest.mark.asyncio
async def test_dependency_api_endpoints(async_client, test_db):
    """Verifies summary, edges, graph, cycles, and impact endpoints."""
    # 1. Setup DB objects
    repo = Repository(
        id=uuid.uuid4(),
        url="https://github.com/dep-test/api-repo",
        owner="dep-test",
        name="api-repo",
        default_branch="main",
    )
    test_db.add(repo)
    await test_db.flush()

    dep_summary = {
        "total_dependencies": 3,
        "internal_dependencies": 2,
        "external_dependencies": 1,
        "unresolved_dependencies": 0,
        "analyzed_files": 2,
        "isolated_files_count": 0,
        "average_fan_in": 1.0,
        "average_fan_out": 1.0,
        "max_fan_in": 1,
        "max_fan_out": 1,
        "average_instability": 0.5,
        "circular_dependency_count": 1,
        "cycle_cap_reached": False,
        "top_fan_in": [
            {"file_id": "file-b", "file_path": "b.py", "fan_in": 1, "fan_out": 1, "instability": 0.5}
        ],
        "top_fan_out": [
            {"file_id": "file-a", "file_path": "a.py", "fan_in": 1, "fan_out": 1, "instability": 0.5}
        ],
        "cycles_summary": [
            {"cycle_id": 1, "length": 2, "files": ["a.py", "b.py", "a.py"]}
        ],
        "architecture_hotspots": {
            "core_foundation": [],
            "high_coupling": ["a.py", "b.py"],
            "cyclic_modules": ["a.py", "b.py"],
            "isolated_modules": [],
        },
    }

    job = AnalysisJob(
        id=uuid.uuid4(),
        repository_id=repo.id,
        status=AnalysisStatus.COMPLETED.value,
        stage="completed",
        progress=100,
        dependency_summary=dep_summary,
    )
    test_db.add(job)
    await test_db.flush()

    file_a = RepositoryFile(
        id=uuid.uuid4(),
        analysis_id=job.id,
        path="a.py",
        filename="a.py",
        extension=".py",
        language="Python",
        size_bytes=200,
        line_count=10,
    )
    file_b = RepositoryFile(
        id=uuid.uuid4(),
        analysis_id=job.id,
        path="b.py",
        filename="b.py",
        extension=".py",
        language="Python",
        size_bytes=300,
        line_count=15,
    )
    test_db.add_all([file_a, file_b])
    await test_db.flush()

    # Add FileDependencyMetrics
    fdm_a = FileDependencyMetric(
        id=uuid.uuid4(),
        analysis_id=job.id,
        file_id=file_a.id,
        fan_in=1,
        fan_out=1,
        internal_dependencies_count=1,
        external_dependencies_count=0,
        unresolved_dependencies_count=0,
        instability=0.5,
        in_cycle=True,
        cycle_count=1,
    )
    fdm_b = FileDependencyMetric(
        id=uuid.uuid4(),
        analysis_id=job.id,
        file_id=file_b.id,
        fan_in=1,
        fan_out=1,
        internal_dependencies_count=1,
        external_dependencies_count=0,
        unresolved_dependencies_count=0,
        instability=0.5,
        in_cycle=True,
        cycle_count=1,
    )
    test_db.add_all([fdm_a, fdm_b])

    # Add Dependencies: A -> B, B -> A, A -> sys (external)
    dep_ab = Dependency(
        id=uuid.uuid4(),
        analysis_id=job.id,
        source_file_id=file_a.id,
        target_file_id=file_b.id,
        target_module="b",
        dependency_type="import",
        imported_symbols=["*"],
        line_number=1,
        resolution_status="internal",
    )
    dep_ba = Dependency(
        id=uuid.uuid4(),
        analysis_id=job.id,
        source_file_id=file_b.id,
        target_file_id=file_a.id,
        target_module="a",
        dependency_type="import",
        imported_symbols=["*"],
        line_number=1,
        resolution_status="internal",
    )
    dep_ext = Dependency(
        id=uuid.uuid4(),
        analysis_id=job.id,
        source_file_id=file_a.id,
        target_file_id=None,
        target_module="sys",
        dependency_type="import",
        imported_symbols=["*"],
        line_number=2,
        resolution_status="external",
    )
    test_db.add_all([dep_ab, dep_ba, dep_ext])
    await test_db.commit()

    # Test 1: GET /analyses/{id}/dependencies (Summary)
    resp_sum = await async_client.get(f"/api/v1/analyses/{job.id}/dependencies")
    assert resp_sum.status_code == 200
    data_sum = resp_sum.json()
    assert data_sum["total_dependencies"] == 3
    assert data_sum["internal_dependencies"] == 2
    assert data_sum["external_dependencies"] == 1
    assert data_sum["circular_dependency_count"] == 1

    # Test 2: GET /analyses/{id}/dependencies/edges
    resp_edges = await async_client.get(f"/api/v1/analyses/{job.id}/dependencies/edges?resolution_status=internal")
    assert resp_edges.status_code == 200
    data_edges = resp_edges.json()
    assert data_edges["total"] == 2
    assert len(data_edges["items"]) == 2

    # Test 3: GET /analyses/{id}/dependencies/graph
    resp_graph = await async_client.get(f"/api/v1/analyses/{job.id}/dependencies/graph")
    assert resp_graph.status_code == 200
    data_graph = resp_graph.json()
    assert len(data_graph["nodes"]) == 2
    assert len(data_graph["edges"]) == 2

    # Test 4: GET /analyses/{id}/dependencies/cycles
    resp_cycles = await async_client.get(f"/api/v1/analyses/{job.id}/dependencies/cycles")
    assert resp_cycles.status_code == 200
    data_cycles = resp_cycles.json()
    assert data_cycles["total_cycles"] == 1
    assert data_cycles["cycles"][0]["length"] == 2

    # Test 5: GET /analyses/{id}/dependencies/impact/{file_id}
    resp_impact = await async_client.get(f"/api/v1/analyses/{job.id}/dependencies/impact/{file_a.id}?direction=dependents")
    assert resp_impact.status_code == 200
    data_impact = resp_impact.json()
    assert data_impact["target_file_path"] == "a.py"
    assert data_impact["affected_files_count"] == 1
    assert data_impact["items"][0]["file_path"] == "b.py"
    assert data_impact["items"][0]["depth"] == 1

    # Test 6: Impact 404 on invalid file
    bad_id = uuid.uuid4()
    resp_bad = await async_client.get(f"/api/v1/analyses/{job.id}/dependencies/impact/{bad_id}")
    assert resp_bad.status_code == 404
