import logging
import time
from collections import defaultdict
from typing import ClassVar, Dict, List, Optional
from fastapi import HTTPException, Request, status

from app.core.config import settings
from app.core.logging import request_id_var
from app.core.redis import redis_client

logger = logging.getLogger(__name__)


class RateLimiter:
    """Configurable rate limiter supporting Redis and in-memory fallback."""

    # In-memory timestamp storage for fallback: key -> list of float timestamps
    _memory_store: ClassVar[Dict[str, List[float]]] = defaultdict(list)

    def __init__(self, limit: int, window_seconds: int = 60, name: str = "default") -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self.name = name

    @classmethod
    def reset_memory_store(cls) -> None:
        """Clears in-memory rate limit records (useful for testing)."""
        cls._memory_store.clear()

    def _get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()
        if request.client and request.client.host:
            return request.client.host
        return "127.0.0.1"

    async def __call__(self, request: Request) -> None:
        if not settings.RATE_LIMIT_ENABLED or settings.ENVIRONMENT == "test":
            return

        client_ip = self._get_client_ip(request)
        key = f"rate_limit:{self.name}:{client_ip}"
        now = time.time()

        allowed = True
        redis_worked = False
        redis_error: Optional[Exception] = None

        try:
            pipe = redis_client.pipeline()
            pipe.incr(key)
            pipe.expire(key, self.window_seconds)
            results = await pipe.execute()
            current_count = results[0]
            redis_worked = True
            if current_count > self.limit:
                allowed = False
        except Exception as exc:
            redis_error = exc
            redis_worked = False

        if not redis_worked:
            req_id = getattr(request.state, "request_id", None) or request_id_var.get("")
            if not settings.RATE_LIMIT_ALLOW_MEMORY_FALLBACK:
                logger.error(
                    "REDIS_RATE_LIMIT_UNAVAILABLE: Redis is down (%s) and RATE_LIMIT_ALLOW_MEMORY_FALLBACK=False. Rejecting request with 503 for '%s' from %s.",
                    redis_error,
                    self.name,
                    client_ip,
                )
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Rate limiting backend unavailable (Redis degraded; distributed rate limiting required).",
                    headers={
                        "Retry-After": "5",
                        "X-Request-ID": req_id or "",
                        "X-RateLimit-Degraded": "unavailable",
                    },
                )

            # Explicitly log degraded in-memory mode (per-process, non-distributed)
            logger.warning(
                "REDIS_RATE_LIMITER_DEGRADED: Redis is unavailable (%s). Operating in DEGRADED in-memory rate limiting mode for '%s' (non-distributed, per-process state for client %s).",
                redis_error,
                self.name,
                client_ip,
            )
            if hasattr(request, "state"):
                request.state.rate_limit_degraded = True

            cutoff = now - self.window_seconds
            timestamps = self._memory_store[key]
            # Prune timestamps older than window
            self._memory_store[key] = [t for t in timestamps if t > cutoff]
            if len(self._memory_store[key]) >= self.limit:
                allowed = False
            else:
                self._memory_store[key].append(now)

        if not allowed:
            req_id = getattr(request.state, "request_id", None) or request_id_var.get("")
            logger.warning(
                "Rate limit exceeded for client %s on %s (limit %d/%ds, degraded=%s)",
                client_ip,
                self.name,
                self.limit,
                self.window_seconds,
                not redis_worked,
            )
            resp_headers = {
                "Retry-After": str(self.window_seconds),
                "X-Request-ID": req_id or "",
            }
            if not redis_worked:
                resp_headers["X-RateLimit-Degraded"] = "true"

            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded for '{self.name}'. Maximum {self.limit} requests per {self.window_seconds} seconds.",
                headers=resp_headers,
            )
