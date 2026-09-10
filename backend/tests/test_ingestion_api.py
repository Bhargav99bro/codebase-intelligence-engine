import uuid
from unittest.mock import patch
import pytest
from httpx import AsyncClient

from app.models.analysis import AnalysisJob, AnalysisStatus
from app.models.repository import Repository


@pytest.mark.asyncio
async def test_submit_repository_success(async_client: AsyncClient, test_db):
    """Test successful submission of a valid repository URL."""
    with patch("app.api.v1.endpoints.repositories.ingest_repository_task.delay") as mock_delay:
        mock_delay.return_value = None

        response = await async_client.post(
            "/api/v1/repositories/analyze",
            json={"repository_url": "https://github.com/octocat/Hello-World.git"},
        )

        assert response.status_code == 202
        data = response.json()
        assert "analysis_id" in data
        assert data["status"] == "queued"
        assert data["repository_url"] == "https://github.com/octocat/Hello-World"
        assert mock_delay.called

        # Verify job was persisted in database
        job_id = uuid.UUID(data["analysis_id"])
        job = await test_db.get(AnalysisJob, job_id)
        assert job is not None
        assert job.status == AnalysisStatus.QUEUED.value
        assert job.stage == "queued"


@pytest.mark.asyncio
async def test_submit_repository_invalid_url(async_client: AsyncClient):
    """Test submission with invalid and malicious URLs."""
    # Non-GitHub
    resp1 = await async_client.post(
        "/api/v1/repositories/analyze",
        json={"repository_url": "https://gitlab.com/owner/repo"},
    )
    assert resp1.status_code == 400
    assert "Unsupported domain" in resp1.json()["detail"]

    # Command injection attempt
    resp2 = await async_client.post(
        "/api/v1/repositories/analyze",
        json={"repository_url": "https://github.com/owner/repo; rm -rf /"},
    )
    assert resp2.status_code == 400
    assert "dangerous or invalid" in resp2.json()["detail"]


@pytest.mark.asyncio
async def test_submit_repository_queue_unavailable(async_client: AsyncClient):
    """Test that when Celery/Redis queue is unavailable, API returns 503 rather than silent fallback."""
    with patch("app.api.v1.endpoints.repositories.ingest_repository_task.delay") as mock_delay:
        mock_delay.side_effect = ConnectionError("Could not connect to Redis broker")

        response = await async_client.post(
            "/api/v1/repositories/analyze",
            json={"repository_url": "https://github.com/pallets/flask"},
        )

        assert response.status_code == 503
        data = response.json()
        assert "Job queue service (Redis/Celery) is currently unavailable" in data["detail"]


@pytest.mark.asyncio
async def test_get_analysis_status_lifecycle(async_client: AsyncClient, test_db):
    """Test retrieving analysis job status and metrics."""
    # Create test repository and analysis job
    repo = Repository(
        url="https://github.com/test-org/test-repo",
        owner="test-org",
        name="test-repo",
        default_branch="main",
    )
    test_db.add(repo)
    await test_db.flush()

    job = AnalysisJob(
        repository_id=repo.id,
        status="completed",
        stage="completed",
        progress=100,
        message="Ingestion complete",
        commit_hash="c0ffee1234567890",
        total_files=42,
        analyzable_files=38,
        total_lines=1250,
        total_bytes=45000,
        language_distribution={"Python": 75.0, "YAML": 25.0},
    )
    test_db.add(job)
    await test_db.commit()

    # Query status endpoint
    response = await async_client.get(f"/api/v1/analyses/{job.id}")
    assert response.status_code == 200
    data = response.json()

    assert data["id"] == str(job.id)
    assert data["owner"] == "test-org"
    assert data["name"] == "test-repo"
    assert data["status"] == "completed"
    assert data["progress"] == 100
    assert data["commit_hash"] == "c0ffee1234567890"
    assert data["total_files"] == 42
    assert data["analyzable_files"] == 38
    assert data["language_distribution"] == {"Python": 75.0, "YAML": 25.0}


@pytest.mark.asyncio
async def test_get_analysis_not_found_and_bad_id(async_client: AsyncClient):
    """Test 404 for nonexistent job and 400 for bad UUID."""
    random_uuid = str(uuid.uuid4())
    resp_404 = await async_client.get(f"/api/v1/analyses/{random_uuid}")
    assert resp_404.status_code == 404

    resp_400 = await async_client.get("/api/v1/analyses/not-a-valid-uuid")
    assert resp_400.status_code == 400
    assert "Invalid analysis ID format" in resp_400.json()["detail"]
