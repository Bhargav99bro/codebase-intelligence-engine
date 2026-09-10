import json
import logging
import uuid
import pytest
from httpx import AsyncClient

from app.core.logging import (
    ContextAwareTextFormatter,
    SensitiveDataFilter,
    StructuredJsonFormatter,
    analysis_id_var,
    request_id_var,
    sanitize_sensitive_data,
)


@pytest.mark.asyncio
async def test_correlation_id_propagation(async_client: AsyncClient):
    custom_id = f"test-req-{uuid.uuid4().hex[:8]}"
    resp = await async_client.get("/", headers={"x-request-id": custom_id})
    assert resp.status_code == 200
    assert resp.headers.get("x-request-id") == custom_id
    assert "x-response-time-ms" in resp.headers


@pytest.mark.asyncio
async def test_correlation_id_auto_generation(async_client: AsyncClient):
    resp = await async_client.get("/")
    assert resp.status_code == 200
    generated_id = resp.headers.get("x-request-id")
    assert generated_id is not None
    assert len(generated_id) >= 16


def test_structured_json_formatter():
    formatter = StructuredJsonFormatter()
    record = logging.LogRecord(
        name="test.logger",
        level=logging.INFO,
        pathname="app/test.py",
        lineno=42,
        msg="Executing intelligence analysis on repository",
        args=(),
        exc_info=None,
    )
    token_req = request_id_var.set("req-789")
    token_ana = analysis_id_var.set("ana-456")
    try:
        formatted = formatter.format(record)
        data = json.loads(formatted)
        assert data["level"] == "INFO"
        assert data["logger"] == "test.logger"
        assert data["message"] == "Executing intelligence analysis on repository"
        assert data["request_id"] == "req-789"
        assert data["analysis_id"] == "ana-456"
        assert "timestamp" in data
    finally:
        request_id_var.reset(token_req)
        analysis_id_var.reset(token_ana)


def test_sensitive_credential_sanitization():
    # Passwords and secrets
    s1 = sanitize_sensitive_data("Connect to db with password='super_secret_password' and user=admin")
    assert "super_secret_password" not in s1
    assert "[REDACTED]" in s1

    # Bearer tokens
    s2 = sanitize_sensitive_data("Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.token")
    assert "Bearer [REDACTED]" in s2

    # API keys
    s3 = sanitize_sensitive_data("api_key: secret_api_key_12345")
    assert "secret_api_key_12345" not in s3
    assert "[REDACTED]" in s3

    # Embedded URL credentials
    s4 = sanitize_sensitive_data("Clone from https://user:super_pass@github.com/org/repo")
    assert "super_pass" not in s4
    assert "[REDACTED]" in s4


def test_sensitive_data_logging_filter():
    filt = SensitiveDataFilter()
    record = logging.LogRecord(
        name="test",
        level=logging.WARNING,
        pathname="test.py",
        lineno=10,
        msg="Leaked token=my_secret_token_abc in logs",
        args=(),
        exc_info=None,
    )
    filt.filter(record)
    assert "my_secret_token_abc" not in record.msg
    assert "[REDACTED]" in record.msg


@pytest.mark.asyncio
async def test_standardized_error_format_404(async_client: AsyncClient):
    random_uuid = str(uuid.uuid4())
    resp = await async_client.get(f"/api/v1/analyses/{random_uuid}")
    assert resp.status_code == 404
    body = resp.json()

    # Backwards-compatible detail
    assert "detail" in body
    assert f"Analysis job with ID '{random_uuid}' was not found" in body["detail"]

    # Phase 9 Standard Error Object
    assert "error" in body
    assert body["error"]["code"] == "NOT_FOUND"
    assert "message" in body["error"]
    assert "request_id" in body["error"]


@pytest.mark.asyncio
async def test_standardized_error_format_422(async_client: AsyncClient):
    # Missing required body field repository_url
    resp = await async_client.post("/api/v1/repositories/analyze", json={})
    assert resp.status_code == 422
    body = resp.json()

    # Backwards-compatible detail
    assert "detail" in body

    # Phase 9 Standard Error Object
    assert "error" in body
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "request_id" in body["error"]


@pytest.mark.asyncio
async def test_bounded_pagination(async_client: AsyncClient):
    # Attempting to request page_size > 100 on issues endpoint should trigger 422
    random_uuid = str(uuid.uuid4())
    resp = await async_client.get(f"/api/v1/analyses/{random_uuid}/issues?page_size=500")
    assert resp.status_code == 422
