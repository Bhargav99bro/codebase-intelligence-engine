import logging
from app.services.ingestion_orchestrator import run_ingestion_pipeline
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="app.workers.tasks.ingest_repository_task",
    bind=True,
    max_retries=2,
    default_retry_delay=10,
)
def ingest_repository_task(self, analysis_id: str) -> str:
    """Celery background task that executes repository ingestion and file discovery."""
    logger.info("Starting background ingestion task for analysis ID: %s", analysis_id)
    try:
        run_ingestion_pipeline(analysis_id)
        return f"Ingestion completed for analysis {analysis_id}"
    except Exception as exc:
        logger.error("Error executing ingestion task %s: %s", analysis_id, exc)
        # Only retry on connection or unexpected transient errors
        if "timeout" in str(exc).lower() or "connection" in str(exc).lower():
            raise self.retry(exc=exc)
        raise exc
