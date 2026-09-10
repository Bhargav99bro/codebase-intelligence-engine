import os
import shutil
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.main import app
from app.models.analysis import AnalysisJob, AnalysisStatus
from app.models.repository import Repository
from app.services.job_recovery import recover_stale_jobs


@pytest.mark.asyncio
async def test_recover_stale_jobs_marks_stuck_jobs(test_db: AsyncSession):
    # 1. Create a dummy repository
    repo = Repository(
        name=f"test-repo-{uuid.uuid4().hex[:6]}",
        owner="test-owner",
        url=f"https://github.com/test-owner/test-repo-{uuid.uuid4().hex[:6]}",
        default_branch="main",
    )
    test_db.add(repo)
    await test_db.commit()
    await test_db.refresh(repo)

    # 2. Create a stale job (updated 45 minutes ago)
    stale_time = datetime.now(timezone.utc) - timedelta(minutes=45)
    stale_job = AnalysisJob(
        repository_id=repo.id,
        status=AnalysisStatus.PARSING.value,
        stage="parsing",
        progress=40,
        message="Parsing files...",
    )
    # 3. Create a recent job (updated 5 minutes ago)
    recent_job = AnalysisJob(
        repository_id=repo.id,
        status=AnalysisStatus.PARSING.value,
        stage="parsing",
        progress=30,
        message="Parsing recent...",
    )
    # 4. Create an already completed job
    completed_job = AnalysisJob(
        repository_id=repo.id,
        status=AnalysisStatus.COMPLETED.value,
        stage="completed",
        progress=100,
        message="Finished",
    )

    test_db.add_all([stale_job, recent_job, completed_job])
    await test_db.commit()
    await test_db.refresh(stale_job)
    await test_db.refresh(recent_job)
    await test_db.refresh(completed_job)

    # Manually backdate updated_at on stale_job
    stale_job.updated_at = stale_time
    await test_db.commit()

    # Create dummy scratch folder for stale job
    stale_clone_dir = os.path.join(settings.ANALYSIS_STORAGE_PATH, str(stale_job.id))
    os.makedirs(stale_clone_dir, exist_ok=True)
    assert os.path.exists(stale_clone_dir)

    # Run recovery with 30 min threshold
    recovered_ids = await recover_stale_jobs(test_db, threshold_minutes=30)

    assert stale_job.id in recovered_ids
    assert recent_job.id not in recovered_ids
    assert completed_job.id not in recovered_ids

    await test_db.refresh(stale_job)
    await test_db.refresh(recent_job)
    await test_db.refresh(completed_job)

    assert stale_job.status == AnalysisStatus.FAILED.value
    assert "timed out or stalled" in (stale_job.error_message or "")
    assert recent_job.status == AnalysisStatus.PARSING.value
    assert completed_job.status == AnalysisStatus.COMPLETED.value

    # Orphaned scratch dir should have been deleted
    assert not os.path.exists(stale_clone_dir)


@pytest.mark.asyncio
async def test_recover_stale_jobs_endpoint(async_client: AsyncClient, test_db: AsyncSession):
    repo = Repository(
        name=f"test-repo-{uuid.uuid4().hex[:6]}",
        owner="test-owner",
        url=f"https://github.com/test-owner/test-repo-{uuid.uuid4().hex[:6]}",
        default_branch="main",
    )
    test_db.add(repo)
    await test_db.commit()
    await test_db.refresh(repo)

    job = AnalysisJob(
        repository_id=repo.id,
        status=AnalysisStatus.CLONING.value,
        stage="cloning",
        progress=10,
        message="Cloning...",
    )
    test_db.add(job)
    await test_db.commit()
    await test_db.refresh(job)

    job.updated_at = datetime.now(timezone.utc) - timedelta(minutes=60)
    await test_db.commit()

    resp = await async_client.post("/api/v1/analyses/recover-stale?threshold_minutes=30")
    assert resp.status_code == 200
    data = resp.json()
    assert "recovered_count" in data
    assert str(job.id) in data["recovered_job_ids"]


@pytest.mark.asyncio
async def test_ready_and_live_probes(async_client: AsyncClient):
    # Test Liveness Probe
    resp_live = await async_client.get("/api/v1/live")
    assert resp_live.status_code == 200
    live_data = resp_live.json()
    assert live_data["status"] == "live"
    assert "version" in live_data

    # Test Readiness Probe when DB is up
    with patch("app.api.v1.endpoints.health.check_database_connection") as mock_db, \
         patch("app.api.v1.endpoints.health.check_redis_connection") as mock_redis:
        mock_db.return_value = {"status": "connected", "details": "Operational"}
        mock_redis.return_value = {"status": "connected", "details": "Operational"}
        resp_ready = await async_client.get("/api/v1/ready")
        assert resp_ready.status_code == 200
        ready_data = resp_ready.json()
        assert ready_data["status"] == "ready"
        assert ready_data["database"] == "connected"


@pytest.mark.asyncio
async def test_readiness_probe_returns_503_on_database_failure(async_client: AsyncClient):
    with patch("app.api.v1.endpoints.health.check_database_connection") as mock_db:
        mock_db.return_value = {"status": "disconnected", "details": "Connection refused"}
        resp = await async_client.get("/api/v1/ready")
        assert resp.status_code == 503
        data = resp.json()
        assert data["status"] == "not_ready"
        assert data["database"] == "disconnected"
