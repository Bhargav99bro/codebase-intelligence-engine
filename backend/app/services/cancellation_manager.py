import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional
import uuid

from fastapi import HTTPException
import redis

from app.core.config import settings
from app.models.analysis import AnalysisJob, AnalysisStatus

logger = logging.getLogger(__name__)


class AnalysisCancelledException(Exception):
    """Raised when an analysis pipeline detects a cancellation request at a checkpoint."""
    pass


def get_redis_client() -> Optional[redis.Redis]:
    """Returns a connected Redis client if available."""
    try:
        return redis.from_url(
            settings.REDIS_URL,
            socket_connect_timeout=0.1,
            socket_timeout=0.1,
            retry_on_timeout=False,
            decode_responses=True,
        )
    except Exception as e:
        logger.warning("Could not connect to Redis for cancellation: %s", e)
        return None


def get_cancel_key(analysis_id: str) -> str:
    return f"analysis:cancel_requested:{analysis_id}"


def get_events_channel(analysis_id: str) -> str:
    return f"analysis:events:{analysis_id}"


def is_cancellation_requested(analysis_id: str, redis_client: Optional[redis.Redis] = None) -> bool:
    """Checks whether cancellation has been requested for this analysis."""
    r = redis_client or get_redis_client()
    if r:
        try:
            val = r.get(get_cancel_key(analysis_id))
            return val is not None
        except Exception as e:
            logger.warning("Error checking Redis cancellation key: %s", e)
    return False


def check_checkpoint(analysis_id: str, stage_name: str, redis_client: Optional[redis.Redis] = None) -> None:
    """Cooperative cancellation checkpoint checked between pipeline stages.

    Raises AnalysisCancelledException if cancellation has been requested.
    """
    if is_cancellation_requested(analysis_id, redis_client):
        logger.info("Cooperative cancellation triggered for %s before stage %s", analysis_id, stage_name)
        raise AnalysisCancelledException(f"Analysis cancelled by user before stage '{stage_name}'")


def request_cancellation_sync(
    job: Optional[AnalysisJob],
    session: Any,
    celery_app: Optional[Any] = None,
) -> Dict[str, Any]:
    """Idempotently requests cancellation of an analysis job."""
    if not job:
        raise HTTPException(status_code=404, detail="Analysis job not found")

    analysis_id = str(job.id)

    # 1. Non-cancellable terminal states
    if job.status in (AnalysisStatus.COMPLETED.value, "completed"):
        raise HTTPException(status_code=409, detail="Cannot cancel an analysis that has already completed.")
    if job.status in (AnalysisStatus.FAILED.value, "failed"):
        raise HTTPException(status_code=409, detail="Cannot cancel an analysis that has already failed.")

    # 2. Already cancelled or cancellation requested (Idempotent success)
    if job.status in (AnalysisStatus.CANCELLED.value, "cancelled"):
        return {"status": "cancelled", "message": "Analysis is already cancelled.", "cancelled": True}
    if job.status in (AnalysisStatus.CANCELLATION_REQUESTED.value, "cancellation_requested"):
        return {"status": "cancellation_requested", "message": "Cancellation has already been requested.", "cancelled": True}

    # 3. Queued state: cancel immediately without starting worker
    r = get_redis_client()
    if job.status in (AnalysisStatus.QUEUED.value, "queued"):
        job.status = AnalysisStatus.CANCELLED.value
        job.stage = "cancelled"
        job.is_cancelled = True
        job.completed_at = datetime.now(timezone.utc)
        job.message = "Analysis cancelled by user while queued."

        if r:
            try:
                import json
                r.publish(
                    get_events_channel(analysis_id),
                    json.dumps({
                        "event": "cancelled",
                        "data": {"status": "cancelled", "message": "Analysis cancelled while queued."},
                    }),
                )
            except Exception as e:
                logger.warning("Failed to publish cancellation event: %s", e)

        # Revoke Celery task if present
        if celery_app and job.metadata_json and "task_id" in job.metadata_json:
            try:
                celery_app.control.revoke(job.metadata_json["task_id"], terminate=False)
            except Exception as e:
                logger.warning("Failed to revoke queued Celery task: %s", e)

        return {"status": "cancelled", "message": "Analysis cancelled while queued.", "cancelled": True}

    # 4. Running state: mark cancellation_requested in Redis & DB
    job.status = AnalysisStatus.CANCELLATION_REQUESTED.value
    job.is_cancelled = True
    job.message = "Cancellation requested by user..."

    if r:
        try:
            import json
            # Set key with 1-hour TTL
            r.set(get_cancel_key(analysis_id), "true", ex=3600)
            r.publish(
                get_events_channel(analysis_id),
                json.dumps({
                    "event": "stage",
                    "data": {
                        "status": "cancellation_requested",
                        "stage": "cancelling",
                        "message": "Cancellation requested. Halting pipeline safely...",
                    },
                }),
            )
        except Exception as e:
            logger.warning("Failed to set Redis cancellation key: %s", e)

    return {
        "status": "cancellation_requested",
        "message": "Cancellation requested. The pipeline will halt at the next checkpoint.",
        "cancelled": True,
    }
