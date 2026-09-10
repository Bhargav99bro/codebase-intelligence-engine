import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root_endpoint(async_client: AsyncClient):
    """Test the root endpoint returns API metadata."""
    response = await async_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "version" in data
    assert "health_check" in data
    assert data["health_check"] == "/api/v1/health"


@pytest.mark.asyncio
async def test_health_endpoint_structure(async_client: AsyncClient):
    """Test the health endpoint returns structured subsystem health information."""
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()

    # Validate top-level schema
    assert "status" in data
    assert data["status"] in ["healthy", "degraded", "unhealthy"]
    assert "project" in data
    assert "version" in data
    assert "environment" in data
    assert "timestamp" in data
    assert "services" in data

    # Validate services dictionary
    services = data["services"]
    assert "api" in services
    assert "database" in services
    assert "redis" in services

    # Validate component schema
    assert services["api"]["status"] == "connected"
    assert "status" in services["database"]
    assert "status" in services["redis"]
