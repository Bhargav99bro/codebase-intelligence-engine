import pytest
from httpx import ASGITransport, AsyncClient
from starlette.requests import Request
from starlette.responses import PlainTextResponse

from app.core.config import settings
from app.core.middleware import SecurityHeadersMiddleware
from app.core.rate_limiter import RateLimiter
from app.main import app
from app.services.url_validator import (
    RepositoryUrlValidationError,
    is_ip_literal_or_private,
    validate_and_normalize_github_url,
    validate_and_normalize_repository_url,
)


def test_ip_literal_detection():
    # IPv4 loopback
    assert is_ip_literal_or_private("127.0.0.1") is True
    assert is_ip_literal_or_private("127.0.0.2") is True
    # Link-local / AWS metadata
    assert is_ip_literal_or_private("169.254.169.254") is True
    # Private RFC1918
    assert is_ip_literal_or_private("10.0.0.1") is True
    assert is_ip_literal_or_private("192.168.1.1") is True
    assert is_ip_literal_or_private("172.16.0.1") is True
    # IPv6 loopback
    assert is_ip_literal_or_private("::1") is True
    assert is_ip_literal_or_private("[::1]") is True
    # Hostnames
    assert is_ip_literal_or_private("localhost") is True
    assert is_ip_literal_or_private("github.com") is False
    assert is_ip_literal_or_private("gitlab.com") is False


def test_ssrf_ip_literals_rejected_in_urls():
    ssrf_urls = [
        "https://127.0.0.1/owner/repo",
        "https://127.0.0.2/owner/repo",
        "https://169.254.169.254/owner/repo",
        "https://10.0.0.1/owner/repo",
        "https://192.168.1.1/owner/repo",
        "https://172.16.0.1/owner/repo",
        "https://localhost/owner/repo",
    ]
    for url in ssrf_urls:
        with pytest.raises(RepositoryUrlValidationError, match="IP literals and private/loopback"):
            validate_and_normalize_github_url(url)
        with pytest.raises(RepositoryUrlValidationError, match="IP literals and private/loopback"):
            validate_and_normalize_repository_url(url)


def test_port_restriction_in_urls():
    non_standard_ports = [
        "https://github.com:8080/owner/repo",
        "https://github.com:22/owner/repo",
        "https://github.com:80/owner/repo",
    ]
    for url in non_standard_ports:
        with pytest.raises(RepositoryUrlValidationError, match="Non-standard ports are not allowed"):
            validate_and_normalize_github_url(url)
        with pytest.raises(RepositoryUrlValidationError, match="Non-standard ports are not allowed"):
            validate_and_normalize_repository_url(url)


def test_gitlab_support_in_repository_url_validator():
    res = validate_and_normalize_repository_url("https://gitlab.com/gitlab-org/gitlab.git")
    assert res.owner == "gitlab-org"
    assert res.name == "gitlab"
    assert res.host == "gitlab.com"
    assert res.url == "https://gitlab.com/gitlab-org/gitlab"


@pytest.mark.asyncio
async def test_security_headers_middleware():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/")
        assert resp.status_code == 200
        assert resp.headers["X-Content-Type-Options"] == "nosniff"
        assert resp.headers["X-Frame-Options"] == "DENY"
        assert resp.headers["X-XSS-Protection"] == "1; mode=block"
        assert resp.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
        assert "Content-Security-Policy" in resp.headers


@pytest.mark.asyncio
async def test_rate_limiter_triggers_429():
    RateLimiter.reset_memory_store()
    orig_env = settings.ENVIRONMENT
    orig_rate = settings.RATE_LIMIT_ENABLED
    try:
        # Temporarily enable rate limiter in development mode
        settings.ENVIRONMENT = "development"
        settings.RATE_LIMIT_ENABLED = True

        limiter = RateLimiter(limit=2, window_seconds=60, name="test_security_limit")

        from fastapi import Depends, FastAPI
        test_app = FastAPI()

        @test_app.get("/test-limit", dependencies=[Depends(limiter)])
        async def limited_endpoint():
            return {"status": "ok"}

        async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
            r1 = await client.get("/test-limit")
            assert r1.status_code == 200

            r2 = await client.get("/test-limit")
            assert r2.status_code == 200

            # 3rd request must be blocked with 429
            r3 = await client.get("/test-limit")
            assert r3.status_code == 429
            assert "retry-after" in r3.headers or "Retry-After" in r3.headers
            assert "Rate limit exceeded" in r3.text

    finally:
        settings.ENVIRONMENT = orig_env
        settings.RATE_LIMIT_ENABLED = orig_rate
        RateLimiter.reset_memory_store()


def test_invalid_characters_in_repository_url_validator():
    dangerous = [
        "https://gitlab.com/owner/repo; rm -rf /",
        "https://gitlab.com/owner/repo`reboot`",
        "https://gitlab.com/owner/repo|curl evil",
        "https://gitlab.com/owner/repo\x00evil",
    ]
    for url in dangerous:
        with pytest.raises(RepositoryUrlValidationError, match="dangerous or invalid"):
            validate_and_normalize_repository_url(url)


def test_credential_embedded_in_repository_url_rejected():
    creds = [
        "https://user:pass@gitlab.com/owner/repo",
        "https://token@gitlab.com/owner/repo",
    ]
    for url in creds:
        with pytest.raises(RepositoryUrlValidationError, match="embedded credentials"):
            validate_and_normalize_repository_url(url)


def test_path_traversal_in_repository_url_rejected():
    traversals = [
        "https://gitlab.com/owner/../repo",
        "https://gitlab.com/owner/..\\repo",
    ]
    for url in traversals:
        with pytest.raises(RepositoryUrlValidationError, match="Path traversal"):
            validate_and_normalize_repository_url(url)
