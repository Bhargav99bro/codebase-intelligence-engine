import logging
from celery import Celery
from app.core.config import settings

logger = logging.getLogger(__name__)

celery_app = Celery(
    "codebase_intelligence_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
    task_track_started=True,
    task_time_limit=settings.CLONE_TIMEOUT_SECONDS + 180,  # Grace period beyond clone timeout
    worker_prefetch_multiplier=1,  # Prevent worker from hoarding memory-heavy ingestion tasks
    worker_concurrency=settings.CELERY_WORKER_CONCURRENCY,
    worker_max_tasks_per_child=10,  # Prevent memory leaks/fragmentation by recycling worker processes
    worker_max_memory_per_child=200000,  # 200MB memory ceiling per child worker process
    task_routes={
        "app.workers.tasks.ingest_repository_task": {"queue": "ingestion"},
    },
)

# Auto-discover tasks from workers module
celery_app.autodiscover_tasks(["app.workers"])
