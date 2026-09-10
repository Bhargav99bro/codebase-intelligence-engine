import time
import uuid
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.config import settings
from app.core.logging import request_id_var


class CorrelationIdMiddleware:
    """Pure ASGI middleware that tracks request correlation IDs via headers and contextvars."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        correlation_id = None
        for k, v in headers.items():
            if k.lower() in (b"x-request-id", b"x-correlation-id"):
                correlation_id = v.decode("latin1", errors="ignore").strip()
                break

        if not correlation_id:
            correlation_id = uuid.uuid4().hex

        token = request_id_var.set(correlation_id)
        state = scope.setdefault("state", {})
        state["request_id"] = correlation_id

        start_time = time.perf_counter()

        async def send_wrapper(message: dict) -> None:
            if message["type"] == "http.response.start":
                duration_ms = (time.perf_counter() - start_time) * 1000.0
                resp_headers = list(message.get("headers", []))
                resp_headers.append((b"x-request-id", correlation_id.encode("latin1")))
                resp_headers.append((b"x-response-time-ms", f"{duration_ms:.2f}".encode("latin1")))
                if state.get("rate_limit_degraded") and not any(k.lower() == b"x-ratelimit-degraded" for k, _ in resp_headers):
                    resp_headers.append((b"x-ratelimit-degraded", b"true"))
                message["headers"] = resp_headers
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            request_id_var.reset(token)


class SecurityHeadersMiddleware:
    """Pure ASGI middleware that injects hardened security headers into all responses."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not settings.ENABLE_SECURITY_HEADERS:
            await self.app(scope, receive, send)
            return

        async def send_wrapper(message: dict) -> None:
            if message["type"] == "http.response.start":
                resp_headers = list(message.get("headers", []))
                resp_headers.append((b"x-content-type-options", b"nosniff"))
                resp_headers.append((b"x-frame-options", b"DENY"))
                resp_headers.append((b"x-xss-protection", b"1; mode=block"))
                resp_headers.append((b"referrer-policy", b"strict-origin-when-cross-origin"))
                resp_headers.append((b"permissions-policy", b"geolocation=(), microphone=(), camera=()"))

                has_csp = any(k.lower() == b"content-security-policy" for k, _ in resp_headers)
                if not has_csp:
                    resp_headers.append((
                        b"content-security-policy",
                        b"default-src 'self'; frame-ancestors 'none'; object-src 'none';"
                    ))
                message["headers"] = resp_headers
            await send(message)

        await self.app(scope, receive, send_wrapper)
