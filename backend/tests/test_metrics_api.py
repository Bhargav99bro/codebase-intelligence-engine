import uuid
import pytest

from app.models.analysis import AnalysisJob, AnalysisStatus
from app.models.file import RepositoryFile
from app.models.metrics import FileMetric, SymbolMetric
from app.models.repository import Repository
from app.models.symbol import Symbol


@pytest.mark.asyncio
async def test_metrics_api_endpoints(async_client, test_db):
    """Tests /metrics, /metrics/files, and /metrics/symbols endpoints with filtering and sorting."""
    # 1. Setup test data
    repo = Repository(
        url="https://github.com/api-test/metrics-api-repo",
        owner="api-test",
        name="metrics-api-repo",
        default_branch="main",
    )
    test_db.add(repo)
    await test_db.flush()

    summary_data = {
        "repository_totals": {
            "total_sloc": 150,
            "total_files": 2,
            "total_symbols": 5,
            "total_functions": 2,
            "total_classes": 1,
            "total_methods": 2,
        },
        "averages": {
            "average_cyclomatic_complexity": 3.5,
            "average_function_size": 25.0,
            "average_nesting_depth": 1.5,
        },
        "maximums": {
            "max_cyclomatic_complexity": 8,
            "max_function_size": 45,
            "max_nesting_depth": 3,
        },
        "maintainability": {
            "score": 82.5,
            "rating": "good",
            "label": "Good Maintainability",
        },
        "complexity_distribution": {"low": 3, "moderate": 1, "high": 0, "very_high": 0},
        "quality_summary": {
            "total_quality_flags": 1,
            "flagged_files_count": 1,
            "flagged_functions_count": 1,
            "severity_counts": {"MEDIUM": 1},
            "top_hotspots": [],
        },
    }

    job = AnalysisJob(
        repository_id=repo.id,
        status=AnalysisStatus.COMPLETED.value,
        stage="completed",
        progress=100,
        message="Completed",
        total_files=2,
        total_lines=200,
        summary_metrics=summary_data,
    )
    test_db.add(job)
    await test_db.flush()

    rf1 = RepositoryFile(
        analysis_id=job.id,
        path="src/main.py",
        filename="main.py",
        extension=".py",
        language="Python",
        line_count=120,
        parser_status="parsed",
    )
    rf2 = RepositoryFile(
        analysis_id=job.id,
        path="src/utils.js",
        filename="utils.js",
        extension=".js",
        language="JavaScript",
        line_count=80,
        parser_status="parsed",
    )
    test_db.add_all([rf1, rf2])
    await test_db.flush()

    fm1 = FileMetric(
        analysis_id=job.id,
        file_id=rf1.id,
        total_lines=120,
        sloc=95,
        total_cyclomatic_complexity=12,
        average_cyclomatic_complexity=4.0,
        max_cyclomatic_complexity=8,
        maintainability_score=78.0,
        quality_flags=[{"flag": "HIGH_COMPLEXITY", "description": "High CC", "metric_value": 8, "threshold": 5, "severity": "MEDIUM", "location": "src/main.py:10"}],
    )
    fm2 = FileMetric(
        analysis_id=job.id,
        file_id=rf2.id,
        total_lines=80,
        sloc=55,
        total_cyclomatic_complexity=4,
        average_cyclomatic_complexity=2.0,
        max_cyclomatic_complexity=3,
        maintainability_score=88.0,
        quality_flags=[],
    )
    test_db.add_all([fm1, fm2])
    await test_db.flush()

    sym1 = Symbol(
        analysis_id=job.id,
        file_id=rf1.id,
        name="process_orders",
        symbol_type="function",
        start_line=10,
        start_column=0,
        end_line=45,
        end_column=0,
        signature="def process_orders(orders, user)",
    )
    sym2 = Symbol(
        analysis_id=job.id,
        file_id=rf2.id,
        name="formatDate",
        symbol_type="function",
        start_line=5,
        start_column=0,
        end_line=20,
        end_column=1,
        signature="function formatDate(date)",
    )
    test_db.add_all([sym1, sym2])
    await test_db.flush()

    sm1 = SymbolMetric(
        symbol_id=sym1.id,
        analysis_id=job.id,
        file_id=rf1.id,
        lines_of_code=35,
        cyclomatic_complexity=8,
        nesting_depth=2,
        parameter_count=2,
        quality_flags=[{"flag": "HIGH_COMPLEXITY", "description": "High CC", "metric_value": 8, "threshold": 5, "severity": "MEDIUM", "location": "src/main.py:10"}],
    )
    sm2 = SymbolMetric(
        symbol_id=sym2.id,
        analysis_id=job.id,
        file_id=rf2.id,
        lines_of_code=15,
        cyclomatic_complexity=2,
        nesting_depth=1,
        parameter_count=1,
        quality_flags=[],
    )
    test_db.add_all([sm1, sm2])
    await test_db.commit()

    # 2. Test GET /metrics
    resp = await async_client.get(f"/api/v1/analyses/{job.id}/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert data["analysis_id"] == str(job.id)
    assert data["repository_totals"]["total_sloc"] == 150
    assert data["maintainability"]["score"] == 82.5
    assert data["maintainability"]["rating"] == "good"

    # 3. Test GET /metrics/files (default sorting by total_cyclomatic_complexity desc)
    resp_files = await async_client.get(f"/api/v1/analyses/{job.id}/metrics/files")
    assert resp_files.status_code == 200
    files_data = resp_files.json()
    assert files_data["total"] == 2
    assert len(files_data["items"]) == 2
    # First item should have highest CC (main.py with 12)
    assert files_data["items"][0]["file_path"] == "src/main.py"
    assert files_data["items"][0]["total_cyclomatic_complexity"] == 12

    # Test filtering by language
    resp_py = await async_client.get(f"/api/v1/analyses/{job.id}/metrics/files?language=Python")
    assert resp_py.status_code == 200
    py_data = resp_py.json()
    assert py_data["total"] == 1
    assert py_data["items"][0]["file_path"] == "src/main.py"

    # Test filtering by min_complexity
    resp_high_cc = await async_client.get(f"/api/v1/analyses/{job.id}/metrics/files?min_complexity=10")
    assert resp_high_cc.status_code == 200
    assert resp_high_cc.json()["total"] == 1

    # 4. Test GET /metrics/symbols (sorted by CC desc)
    resp_syms = await async_client.get(f"/api/v1/analyses/{job.id}/metrics/symbols")
    assert resp_syms.status_code == 200
    syms_data = resp_syms.json()
    assert syms_data["total"] == 2
    # Highest CC first
    assert syms_data["items"][0]["symbol_name"] == "process_orders"
    assert syms_data["items"][0]["cyclomatic_complexity"] == 8

    # Test search query
    resp_search = await async_client.get(f"/api/v1/analyses/{job.id}/metrics/symbols?search=format")
    assert resp_search.status_code == 200
    search_data = resp_search.json()
    assert search_data["total"] == 1
    assert search_data["items"][0]["symbol_name"] == "formatDate"

    # 5. Test 404 on nonexistent analysis
    non_existent_id = uuid.uuid4()
    resp_404 = await async_client.get(f"/api/v1/analyses/{non_existent_id}/metrics")
    assert resp_404.status_code == 404
