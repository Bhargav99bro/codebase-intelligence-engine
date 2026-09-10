import logging
import redis.asyncio as aioredis
from app.core.config import settings

logger = logging.getLogger(__name__)

redis_client = aioredis.from_url(
    settings.REDIS_URL,
    encoding="utf-8",
    decode_responses=True,
    socket_timeout=3.0,
    socket_connect_timeout=3.0,
)


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
