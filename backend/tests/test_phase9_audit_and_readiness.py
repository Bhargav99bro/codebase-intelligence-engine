import logging
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.core.middleware import CorrelationIdMiddleware
from app.core.rate_limiter import RateLimiter
from app.core.redis import redis_client


@pytest.mark.asyncio
async def test_rate_limiter_redis_healthy():
    """Verify that when Redis is healthy, distributed rate limiting is used without degradation."""
    RateLimiter.reset_memory_store()
    orig_env = settings.ENVIRONMENT
    orig_enabled = settings.RATE_LIMIT_ENABLED
    try:
        settings.ENVIRONMENT = "development"
        settings.RATE_LIMIT_ENABLED = True

        mock_pipe = MagicMock()
        mock_pipe.incr.return_value = None
        mock_pipe.expire.return_value = None
        mock_pipe.execute = AsyncMock(return_value=[1, True])

        with patch.object(redis_client, "pipeline", return_value=mock_pipe):
            limiter = RateLimiter(limit=2, window_seconds=60, name="redis_healthy_test")
            app = FastAPI()
            app.add_middleware(CorrelationIdMiddleware)

            @app.get("/test", dependencies=[Depends(limiter)])
            async def endpoint():
                return {"status": "ok"}

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get("/test")
                assert resp.status_code == 200
                assert resp.headers.get("x-ratelimit-degraded") is None
                assert mock_pipe.incr.called
    finally:
        settings.ENVIRONMENT = orig_env
        settings.RATE_LIMIT_ENABLED = orig_enabled
        RateLimiter.reset_memory_store()


@pytest.mark.asyncio
async def test_rate_limiter_redis_unavailable_degraded_fallback(caplog):
    """Verify that Redis failure is NOT silent: warning is logged, degraded header is added, in-memory store enforces limit."""
    RateLimiter.reset_memory_store()
    orig_env = settings.ENVIRONMENT
    orig_enabled = settings.RATE_LIMIT_ENABLED
    orig_fallback = settings.RATE_LIMIT_ALLOW_MEMORY_FALLBACK
    try:
        settings.ENVIRONMENT = "development"
        settings.RATE_LIMIT_ENABLED = True
        settings.RATE_LIMIT_ALLOW_MEMORY_FALLBACK = True

        mock_pipe = MagicMock()
        mock_pipe.execute = AsyncMock(side_effect=ConnectionError("Redis connection refused"))

        with patch.object(redis_client, "pipeline", return_value=mock_pipe), caplog.at_level(logging.WARNING):
            limiter = RateLimiter(limit=2, window_seconds=60, name="redis_degraded_test")
            app = FastAPI()
            app.add_middleware(CorrelationIdMiddleware)

            @app.get("/test", dependencies=[Depends(limiter)])
            async def endpoint():
                return {"status": "ok"}

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                r1 = await client.get("/test")
                assert r1.status_code == 200
                assert r1.headers.get("x-ratelimit-degraded") == "true"
                assert "REDIS_RATE_LIMITER_DEGRADED" in caplog.text

                r2 = await client.get("/test")
                assert r2.status_code == 200
                assert r2.headers.get("x-ratelimit-degraded") == "true"

                # 3rd request exceeds limit -> 429
                r3 = await client.get("/test")
                assert r3.status_code == 429
                assert r3.headers.get("x-ratelimit-degraded") == "true"
                assert "Rate limit exceeded" in r3.text
    finally:
        settings.ENVIRONMENT = orig_env
        settings.RATE_LIMIT_ENABLED = orig_enabled
        settings.RATE_LIMIT_ALLOW_MEMORY_FALLBACK = orig_fallback
        RateLimiter.reset_memory_store()


@pytest.mark.asyncio
async def test_rate_limiter_redis_unavailable_fallback_disabled_fails_closed(caplog):
    """Verify that when fallback is disabled, Redis failure fails closed with 503 and error log."""
    RateLimiter.reset_memory_store()
    orig_env = settings.ENVIRONMENT
    orig_enabled = settings.RATE_LIMIT_ENABLED
    orig_fallback = settings.RATE_LIMIT_ALLOW_MEMORY_FALLBACK
    try:
        settings.ENVIRONMENT = "production"
        settings.RATE_LIMIT_ENABLED = True
        settings.RATE_LIMIT_ALLOW_MEMORY_FALLBACK = False

        mock_pipe = MagicMock()
        mock_pipe.execute = AsyncMock(side_effect=ConnectionError("Redis connection refused"))

        with patch.object(redis_client, "pipeline", return_value=mock_pipe), caplog.at_level(logging.ERROR):
            limiter = RateLimiter(limit=5, window_seconds=60, name="redis_fail_closed_test")
            app = FastAPI()
            app.add_middleware(CorrelationIdMiddleware)

            @app.get("/test", dependencies=[Depends(limiter)])
            async def endpoint():
                return {"status": "ok"}

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get("/test")
                assert resp.status_code == 503
                assert "REDIS_RATE_LIMIT_UNAVAILABLE" in caplog.text
                assert resp.headers.get("x-ratelimit-degraded") == "unavailable"
                assert "distributed rate limiting required" in resp.json()["detail"]
    finally:
        settings.ENVIRONMENT = orig_env
        settings.RATE_LIMIT_ENABLED = orig_enabled
        settings.RATE_LIMIT_ALLOW_MEMORY_FALLBACK = orig_fallback
        RateLimiter.reset_memory_store()


@pytest.mark.asyncio
async def test_readiness_probe_all_healthy(async_client: AsyncClient):
    """Verify that when PostgreSQL and Redis are both healthy, /ready returns 200."""
    with patch("app.api.v1.endpoints.health.check_database_connection", new_callable=AsyncMock) as mock_db, \
         patch("app.api.v1.endpoints.health.check_redis_connection", new_callable=AsyncMock) as mock_redis:
        mock_db.return_value = {"status": "connected", "details": "Database operational"}
        mock_redis.return_value = {"status": "connected", "details": "Redis operational"}

        resp = await async_client.get("/ready")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ready"
        assert body["database"] == "connected"
        assert body["redis"] == "connected"

        # Liveness remains 200
        resp_live = await async_client.get("/live")
        assert resp_live.status_code == 200
        assert resp_live.json()["status"] == "live"


@pytest.mark.asyncio
async def test_readiness_probe_database_down_fails_503(async_client: AsyncClient):
    """Verify that when PostgreSQL is down, /ready returns 503, but /live remains 200."""
    with patch("app.api.v1.endpoints.health.check_database_connection", new_callable=AsyncMock) as mock_db, \
         patch("app.api.v1.endpoints.health.check_redis_connection", new_callable=AsyncMock) as mock_redis:
        mock_db.return_value = {"status": "disconnected", "details": "PostgreSQL connection refused"}
        mock_redis.return_value = {"status": "connected", "details": "Redis operational"}

        resp = await async_client.get("/ready")
        assert resp.status_code == 503
        body = resp.json()
        assert body["status"] == "not_ready"
        assert body["database"] == "disconnected"
        assert body["redis"] == "connected"

        # Liveness is independent of database health
        resp_live = await async_client.get("/live")
        assert resp_live.status_code == 200
        assert resp_live.json()["status"] == "live"


@pytest.mark.asyncio
async def test_readiness_probe_redis_down_fails_503(async_client: AsyncClient):
    """Verify that when Redis is down, /ready returns 503, but /live remains 200."""
    with patch("app.api.v1.endpoints.health.check_database_connection", new_callable=AsyncMock) as mock_db, \
         patch("app.api.v1.endpoints.health.check_redis_connection", new_callable=AsyncMock) as mock_redis:
        mock_db.return_value = {"status": "connected", "details": "Database operational"}
        mock_redis.return_value = {"status": "disconnected", "details": "Redis connection timeout"}

        resp = await async_client.get("/ready")
        assert resp.status_code == 503
        body = resp.json()
        assert body["status"] == "not_ready"
        assert body["database"] == "connected"
        assert body["redis"] == "disconnected"

        # Liveness is independent of Redis health
        resp_live = await async_client.get("/live")
        assert resp_live.status_code == 200
        assert resp_live.json()["status"] == "live"


@pytest.mark.asyncio
async def test_health_and_root_aliases_consistency(async_client: AsyncClient):
    """Verify that /live, /ready, /health and their /api/v1/ counterparts behave identically."""
    with patch("app.api.v1.endpoints.health.check_database_connection", new_callable=AsyncMock) as mock_db, \
         patch("app.api.v1.endpoints.health.check_redis_connection", new_callable=AsyncMock) as mock_redis:
        mock_db.return_value = {"status": "connected", "details": "Database operational"}
        mock_redis.return_value = {"status": "connected", "details": "Redis operational"}

        r_live_root = await async_client.get("/live")
        r_live_v1 = await async_client.get("/api/v1/live")
        assert r_live_root.status_code == 200
        assert r_live_v1.status_code == 200
        assert r_live_root.json()["status"] == r_live_v1.json()["status"] == "live"

        r_ready_root = await async_client.get("/ready")
        r_ready_v1 = await async_client.get("/api/v1/ready")
        assert r_ready_root.status_code == 200
        assert r_ready_v1.status_code == 200
        assert r_ready_root.json()["status"] == r_ready_v1.json()["status"] == "ready"

        r_health_root = await async_client.get("/health")
        r_health_v1 = await async_client.get("/api/v1/health")
        assert r_health_root.status_code == 200
        assert r_health_v1.status_code == 200
        assert r_health_root.json()["status"] == r_health_v1.json()["status"] == "healthy"
