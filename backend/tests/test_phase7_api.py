import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis import AnalysisJob, AnalysisStatus
from app.models.dependency import FileDependencyMetric
from app.models.file import RepositoryFile
from app.models.issue import AnalysisHealthScore, AnalysisIssue
from app.models.metrics import FileMetric, SymbolMetric
from app.models.repository import Repository


@pytest.mark.asyncio
async def test_phase7_endpoints(async_client: AsyncClient, test_db: AsyncSession):
    # Setup test repository & job
    repo = Repository(
        id=uuid.uuid4(),
        url="https://github.com/phase7-test/api-repo",
        owner="phase7-test",
        name="api-repo",
        default_branch="main",
    )
    test_db.add(repo)
    await test_db.flush()

    job = AnalysisJob(
        id=uuid.uuid4(),
        repository_id=repo.id,
        status=AnalysisStatus.COMPLETED.value,
        stage="completed",
        progress=100,
        total_files=2,
        total_lines=600,
        health_summary={"overall_score": 85.0},
        quality_gate_status="PASSED",
        quality_gate_details={
            "status": "PASSED",
            "passed": True,
            "overall_score": 85.0,
            "total_conditions": 6,
            "passed_count": 6,
            "failed_count": 0,
            "warning_count": 0,
            "conditions": [],
        },
    )
    test_db.add(job)
    await test_db.flush()

    file_1 = RepositoryFile(
        id=uuid.uuid4(),
        analysis_id=job.id,
        path="src/main.py",
        filename="main.py",
        extension=".py",
        language="Python",
        size_bytes=1200,
        line_count=400,
        is_analyzable=True,
        symbol_count=5,
    )
    file_2 = RepositoryFile(
        id=uuid.uuid4(),
        analysis_id=job.id,
        path="src/utils.py",
        filename="utils.py",
        extension=".py",
        language="Python",
        size_bytes=600,
        line_count=200,
        is_analyzable=True,
        symbol_count=3,
    )
    test_db.add_all([file_1, file_2])
    await test_db.flush()

    # Metrics
    fm1 = FileMetric(
        id=uuid.uuid4(),
        analysis_id=job.id,
        file_id=file_1.id,
        total_lines=400,
        sloc=350,
        comment_lines=30,
        blank_lines=20,
        maintainability_score=72.5,
        total_cyclomatic_complexity=15,
        max_cyclomatic_complexity=8,
        max_nesting_depth=3,
    )
    fm2 = FileMetric(
        id=uuid.uuid4(),
        analysis_id=job.id,
        file_id=file_2.id,
        total_lines=200,
        sloc=150,
        comment_lines=20,
        blank_lines=30,
        maintainability_score=88.0,
        total_cyclomatic_complexity=6,
        max_cyclomatic_complexity=4,
        max_nesting_depth=2,
    )
    test_db.add_all([fm1, fm2])

    # Dependency metrics
    dm1 = FileDependencyMetric(
        id=uuid.uuid4(),
        analysis_id=job.id,
        file_id=file_1.id,
        fan_in=5,
        fan_out=3,
    )
    dm2 = FileDependencyMetric(
        id=uuid.uuid4(),
        analysis_id=job.id,
        file_id=file_2.id,
        fan_in=2,
        fan_out=1,
    )
    test_db.add_all([dm1, dm2])

    # Issues
    iss = AnalysisIssue(
        id=uuid.uuid4(),
        analysis_id=job.id,
        file_id=file_1.id,
        rule_id="COMPLEX-002",
        rule_name="HighComplexityMethod",
        category="complexity",
        severity="major",
        title="High Complexity",
        description="Function has CC 15",
        line_number=50,
        remediation_effort_minutes=30,
    )
    test_db.add(iss)

    # Health score row
    hs = AnalysisHealthScore(
        id=uuid.uuid4(),
        analysis_id=job.id,
        overall_score=85.0,
        grade="B",
        maintainability_score=80.0,
        complexity_score=82.0,
        architecture_score=90.0,
        hygiene_score=88.0,
        technical_debt_minutes=30,
        debt_ratio_hours_per_ksloc=1.0,
        total_issues_count=1,
        major_count=1,
    )
    test_db.add(hs)
    await test_db.commit()

    analysis_id = str(job.id)

    # 1. Test /treemap endpoint
    resp = await async_client.get(f"/api/v1/analyses/{analysis_id}/treemap")
    assert resp.status_code == 200
    data = resp.json()
    assert "root" in data
    assert data["root"]["name"] == "root"
    assert data["root"]["sloc"] == 500  # 350 + 150

    # 2. Test /hotspots endpoint
    resp = await async_client.get(f"/api/v1/analyses/{analysis_id}/hotspots")
    assert resp.status_code == 200
    hotspots_data = resp.json()
    assert "hotspots" in hotspots_data
    assert len(hotspots_data["hotspots"]) == 2
    # main.py has higher complexity, fan_in, and issue, so it should be rank 1
    assert hotspots_data["hotspots"][0]["file_path"] == "src/main.py"
    assert hotspots_data["hotspots"][0]["rank"] == 1

    # 3. Test /quality-gate endpoint (default)
    resp = await async_client.get(f"/api/v1/analyses/{analysis_id}/quality-gate")
    assert resp.status_code == 200
    qg_data = resp.json()
    assert qg_data["status"] == "PASSED"

    # Test /quality-gate with custom override to trigger fail (e.g. min_score=95.0)
    resp = await async_client.get(f"/api/v1/analyses/{analysis_id}/quality-gate?min_score=95.0")
    assert resp.status_code == 200
    qg_fail = resp.json()
    assert qg_fail["status"] == "FAILED"
    assert qg_fail["passed"] is False

    # 4. Test /export/sarif
    resp = await async_client.get(f"/api/v1/analyses/{analysis_id}/export/sarif")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/sarif+json")
    sarif_json = resp.json()
    assert sarif_json["version"] == "2.1.0"
    assert len(sarif_json["runs"][0]["results"]) == 1

    # 5. Test /export/markdown
    resp = await async_client.get(f"/api/v1/analyses/{analysis_id}/export/markdown")
    assert resp.status_code == 200
    assert "text/markdown" in resp.headers["content-type"]
    assert "# Codebase Intelligence Audit Report" in resp.text
    assert "src/main.py" in resp.text

    # 6. Test /export/json
    resp = await async_client.get(f"/api/v1/analyses/{analysis_id}/export/json")
    assert resp.status_code == 200
    assert "application/json" in resp.headers["content-type"]
    export_json = resp.json()
    assert export_json["schema_version"] == "1.0"
    assert export_json["analysis_id"] == analysis_id
    assert "hotspots" in export_json

    # 7. Test /cancel endpoint (job is completed -> 409)
    resp = await async_client.post(f"/api/v1/analyses/{analysis_id}/cancel")
    assert resp.status_code == 409

    # 8. Test 404 for nonexistent job
    fake_id = str(uuid.uuid4())
    resp = await async_client.get(f"/api/v1/analyses/{fake_id}/treemap")
    assert resp.status_code == 404
