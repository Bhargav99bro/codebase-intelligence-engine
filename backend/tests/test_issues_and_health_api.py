import uuid
import pytest

from app.models.analysis import AnalysisJob, AnalysisStatus
from app.models.file import RepositoryFile
from app.models.issue import AnalysisHealthScore, AnalysisIssue
from app.models.repository import Repository


@pytest.mark.asyncio
async def test_issues_and_health_endpoints(async_client, test_db):
    # 1. Setup DB objects
    repo = Repository(
        id=uuid.uuid4(),
        url="https://github.com/health-test/api-repo",
        owner="health-test",
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
    )
    test_db.add(job)
    await test_db.flush()

    file_a = RepositoryFile(
        id=uuid.uuid4(),
        analysis_id=job.id,
        path="src/engine.py",
        filename="engine.py",
        extension=".py",
        language="Python",
        size_bytes=450,
        line_count=35,
    )
    test_db.add(file_a)
    await test_db.flush()

    # Create issues
    iss1 = AnalysisIssue(
        id=uuid.uuid4(),
        analysis_id=job.id,
        file_id=file_a.id,
        rule_id="ARCH-002",
        rule_name="God Module",
        category="architecture",
        severity="major",
        title="God Module: src/engine.py",
        description="High coupling and SLOC",
        line_number=1,
        remediation_effort_minutes=90,
        metadata_json={"fan_out": 14, "sloc": 600},
    )
    iss2 = AnalysisIssue(
        id=uuid.uuid4(),
        analysis_id=job.id,
        file_id=file_a.id,
        rule_id="COMPLEX-001",
        rule_name="Critical Complexity",
        category="complexity",
        severity="critical",
        title="Critical Complexity in run()",
        description="CC=25",
        line_number=15,
        symbol_name="run",
        remediation_effort_minutes=90,
        metadata_json={"cyclomatic_complexity": 25},
    )
    iss3 = AnalysisIssue(
        id=uuid.uuid4(),
        analysis_id=job.id,
        file_id=file_a.id,
        rule_id="SEC-001",
        rule_name="Hardcoded Secret Pattern",
        category="security",
        severity="blocker",
        title="Hardcoded AWS Access Key",
        description="Potential secret detected",
        line_number=22,
        remediation_effort_minutes=60,
        metadata_json={"pattern_type": "AWS Access Key"},
    )
    test_db.add_all([iss1, iss2, iss3])

    # Create health score record
    health_score = AnalysisHealthScore(
        id=uuid.uuid4(),
        analysis_id=job.id,
        overall_score=78.5,
        grade="C",
        maintainability_score=82.0,
        complexity_score=75.0,
        architecture_score=80.0,
        hygiene_score=77.0,
        technical_debt_minutes=240,
        debt_ratio_hours_per_ksloc=4.0,
        total_issues_count=3,
        blocker_count=1,
        critical_count=1,
        major_count=1,
        minor_count=0,
        info_count=0,
        category_scores_json={"overall": 78.5},
        recommendations_json=[
            {
                "id": "rec-1",
                "rank": 1,
                "target_type": "symbol",
                "target_name": "run",
                "file_path": "src/engine.py",
                "title": "Refactor run()",
                "summary": "Decompose complex run method",
                "rationale": "Reduces CC from 25 to 10",
                "effort_hours": 1.5,
                "current_health_impact": 3.2,
                "expected_score_recovery": 3.2,
                "primary_category": "complexity",
                "qualitative": False,
            }
        ],
    )
    test_db.add(health_score)
    await test_db.commit()

    # 2. Test GET /analyses/{id}/health
    resp = await async_client.get(f"/api/v1/analyses/{job.id}/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["analysis_id"] == str(job.id)
    assert data["overall_score"] == 78.5
    assert data["grade"] == "C"
    assert data["total_issues_count"] == 3
    assert data["blocker_count"] == 1
    assert len(data["recommendations"]) == 1
    assert data["recommendations"][0]["target_name"] == "run"

    # 3. Test GET /analyses/{id}/issues (all)
    resp = await async_client.get(f"/api/v1/analyses/{job.id}/issues")
    assert resp.status_code == 200
    idata = resp.json()
    assert idata["total"] == 3
    assert len(idata["items"]) == 3
    assert idata["severity_counts"]["blocker"] == 1
    assert idata["category_counts"]["architecture"] == 1

    # 4. Test GET /analyses/{id}/issues with category filter
    resp = await async_client.get(f"/api/v1/analyses/{job.id}/issues?category=architecture")
    assert resp.status_code == 200
    arch_data = resp.json()
    assert arch_data["total"] == 1
    assert arch_data["items"][0]["rule_id"] == "ARCH-002"

    # 5. Test GET /analyses/{id}/issues with severity filter
    resp = await async_client.get(f"/api/v1/analyses/{job.id}/issues?severity=blocker")
    assert resp.status_code == 200
    blocker_data = resp.json()
    assert blocker_data["total"] == 1
    assert blocker_data["items"][0]["rule_id"] == "SEC-001"

    # 6. Test GET /analyses/{id}/issues with search
    resp = await async_client.get(f"/api/v1/analyses/{job.id}/issues?search=God")
    assert resp.status_code == 200
    search_data = resp.json()
    assert search_data["total"] == 1
    assert search_data["items"][0]["rule_id"] == "ARCH-002"

    # 7. Test GET /analyses/{id}/issues/summary
    resp = await async_client.get(f"/api/v1/analyses/{job.id}/issues/summary")
    assert resp.status_code == 200
    sum_data = resp.json()
    assert sum_data["total_issues"] == 3
    assert sum_data["total_technical_debt_minutes"] == 240
    assert len(sum_data["top_violated_rules"]) == 3

    # 8. Test 404 for nonexistent job
    non_existent = uuid.uuid4()
    resp404 = await async_client.get(f"/api/v1/analyses/{non_existent}/health")
    assert resp404.status_code == 404
