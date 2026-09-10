import asyncio
import json
import logging
from typing import Any, AsyncGenerator, Dict, Optional

import redis.asyncio as aioredis
from app.core.config import settings

logger = logging.getLogger(__name__)


def get_events_channel(analysis_id: str) -> str:
    return f"analysis:events:{analysis_id}"


def format_sse(event_type: str, data: Any) -> str:
    """Formats an event and payload into standard Server-Sent Events text."""
    payload = json.dumps(data) if not isinstance(data, str) else data
    return f"event: {event_type}\ndata: {payload}\n\n"


def publish_pipeline_event(
    analysis_id: str,
    event_type: str,
    data: Dict[str, Any],
) -> None:
    """Synchronously publishes a pipeline event to the Redis channel for active SSE subscribers."""
    try:
        import redis
        r = redis.from_url(
            settings.REDIS_URL,
            socket_connect_timeout=0.1,
            socket_timeout=0.1,
            retry_on_timeout=False,
            decode_responses=True,
        )
        channel = get_events_channel(analysis_id)
        msg = json.dumps({"event": event_type, "data": data})
        r.publish(channel, msg)
    except Exception as exc:
        logger.debug("Failed to publish SSE event to Redis for %s: %s", analysis_id, exc)


async def sse_event_generator(
    analysis_id: str,
    initial_status: str,
    initial_stage: str,
    initial_progress: int,
    initial_message: str,
    error_message: Optional[str] = None,
    summary_data: Optional[Dict[str, Any]] = None,
) -> AsyncGenerator[str, None]:
    """Generates Server-Sent Events according to the complete Phase 7 lifecycle."""
    channel_name = get_events_channel(analysis_id)

    # 1. Immediately emit current state
    if initial_status in ("completed", "complete"):
        yield format_sse("complete", summary_data or {"status": "completed", "message": initial_message})
        return
    elif initial_status in ("failed", "error"):
        yield format_sse("error", {"status": "failed", "error": error_message or initial_message})
        return
    elif initial_status in ("cancelled", "canceled"):
        yield format_sse("cancelled", {"status": "cancelled", "message": initial_message})
        return
    else:
        # Non-terminal: emit current stage
        yield format_sse(
            "stage",
            {
                "status": initial_status,
                "stage": initial_stage,
                "progress": initial_progress,
                "message": initial_message,
            },
        )

    # 2. Subscribe to Redis Pub/Sub for subsequent live events
    redis_client = None
    pubsub = None
    try:
        redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(channel_name)

        while True:
            try:
                # Wait for next event with a 15-second keepalive timeout
                msg = await asyncio.wait_for(pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0), timeout=15.0)

                if msg and msg.get("type") == "message":
                    raw_data = msg.get("data", "")
                    try:
                        parsed = json.loads(raw_data)
                        ev_type = parsed.get("event", "stage")
                        ev_data = parsed.get("data", {})
                    except Exception:
                        ev_type = "stage"
                        ev_data = {"raw": raw_data}

                    yield format_sse(ev_type, ev_data)

                    # Close on terminal events
                    if ev_type in ("complete", "error", "cancelled"):
                        logger.info("SSE terminal event %s received for %s, closing stream.", ev_type, analysis_id)
                        break

            except asyncio.TimeoutError:
                # 15-second idle heartbeat keepalive comment
                yield ": keepalive\n\n"

            except asyncio.CancelledError:
                # Browser / client disconnected
                logger.info("Client disconnected from SSE stream for %s", analysis_id)
                break

    except Exception as exc:
        logger.warning("Error in SSE event generator for %s: %s", analysis_id, exc)
    finally:
        if pubsub:
            try:
                await pubsub.unsubscribe(channel_name)
                await pubsub.close()
            except Exception:
                pass
        if redis_client:
            try:
                await redis_client.close()
            except Exception:
                pass
