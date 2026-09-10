import logging
import redis.asyncio as aioredis
from app.core.config import settings

logger = logging.getLogger(__name__)

import re

def normalize_redis_ssl_url(url: str) -> str:
    """Normalizes Redis SSL URL query parameters for redis-py and Celery compatibility.

    redis-py SSLConnection expects lowercase values ('required', 'optional', 'none').
    Converts uppercase Python constant names like 'CERT_REQUIRED' to 'required'.
    """
    if not isinstance(url, str):
        return url

    def _normalize_cert_reqs(match):
        val = match.group(1).lower()
        if "required" in val:
            return "ssl_cert_reqs=required"
        elif "optional" in val:
            return "ssl_cert_reqs=optional"
        elif "none" in val:
            return "ssl_cert_reqs=none"
        return match.group(0)

    return re.sub(r"ssl_cert_reqs=([a-zA-Z_]+)", _normalize_cert_reqs, url, flags=re.IGNORECASE)


def get_redis_client(url: str = None) -> aioredis.Redis:
    """Creates a Redis client with normalized SSL configuration."""
    target_url = normalize_redis_ssl_url(url or settings.REDIS_URL)
    return aioredis.from_url(
        target_url,
        encoding="utf-8",
        decode_responses=True,
        socket_timeout=3.0,
        socket_connect_timeout=3.0,
    )


redis_client = get_redis_client()


async def check_redis_connection() -> dict:
    """Probes the Redis server and returns connection health details."""
    try:
        ping_response = await redis_client.ping()
        if ping_response:
            return {"status": "connected", "details": "Redis responding"}
        return {"status": "error", "details": "Redis ping failed"}
    except Exception as exc:
        logger.warning("Redis health check failed: %s", exc)
        return {"status": "disconnected", "details": str(exc)}
