import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.models.analysis import AnalysisJob, AnalysisStatus
from app.models.duplication import CodeDuplicate, GitChurnMetric
from app.models.issue import AnalysisHealthScore
from app.models.repository import Repository


@pytest.mark.asyncio
async def test_compare_self_comparison_rejected(async_client: AsyncClient):
    same_id = str(uuid.uuid4())
    res = await async_client.get(f"/api/v1/analyses/compare?base_id={same_id}&head_id={same_id}")
    assert res.status_code == 400
    assert "Cannot compare an analysis to itself" in res.json()["detail"]


@pytest.mark.asyncio
async def test_compare_invalid_uuid_rejected(async_client: AsyncClient):
    res = await async_client.get("/api/v1/analyses/compare?base_id=not-a-uuid&head_id=11111111-1111-1111-1111-111111111111")
    assert res.status_code == 400
    assert "Invalid UUID" in res.json()["detail"]


@pytest.mark.asyncio
async def test_compare_nonexistent_analysis(async_client: AsyncClient):
    id1 = str(uuid.uuid4())
    id2 = str(uuid.uuid4())
    res = await async_client.get(f"/api/v1/analyses/compare?base_id={id1}&head_id={id2}")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_duplication_endpoint_invalid_uuid(async_client: AsyncClient):
    res = await async_client.get("/api/v1/analyses/invalid-uuid/duplication")
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_duplication_endpoint_nonexistent(async_client: AsyncClient):
    random_id = str(uuid.uuid4())
    res = await async_client.get(f"/api/v1/analyses/{random_id}/duplication")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_churn_endpoint_invalid_uuid(async_client: AsyncClient):
    res = await async_client.get("/api/v1/analyses/invalid-uuid/churn")
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_churn_endpoint_nonexistent(async_client: AsyncClient):
    random_id = str(uuid.uuid4())
    res = await async_client.get(f"/api/v1/analyses/{random_id}/churn")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_timeline_endpoint_invalid_uuid(async_client: AsyncClient):
    res = await async_client.get("/api/v1/repositories/invalid-uuid/timeline")
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_timeline_endpoint_nonexistent(async_client: AsyncClient):
    random_id = str(uuid.uuid4())
    res = await async_client.get(f"/api/v1/repositories/{random_id}/timeline")
    assert res.status_code == 404
