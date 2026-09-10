import logging
import os
import shutil
from datetime import datetime, timedelta, timezone
from typing import List
import uuid
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.analysis import AnalysisJob, AnalysisStatus

logger = logging.getLogger(__name__)

ACTIVE_STATUSES = [
    AnalysisStatus.QUEUED.value,
    AnalysisStatus.CLONING.value,
    AnalysisStatus.ANALYZING_GIT_CHURN.value,
    AnalysisStatus.DISCOVERING.value,
    AnalysisStatus.PARSING.value,
    AnalysisStatus.EXTRACTING_SYMBOLS.value,
    AnalysisStatus.CALCULATING_METRICS.value,
    AnalysisStatus.DETECTING_DUPLICATION.value,
    AnalysisStatus.ANALYZING_DEPENDENCIES.value,
    AnalysisStatus.EVALUATING_HEALTH.value,
    AnalysisStatus.PERSISTING.value,
    AnalysisStatus.CANCELLATION_REQUESTED.value,
]


async def recover_stale_jobs(
    db: AsyncSession,
    threshold_minutes: int = 30,
) -> List[uuid.UUID]:
    """Finds active analysis jobs with no updates for > threshold_minutes,

    marks them as failed, and cleans up orphaned scratch directories.
    """
    cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=threshold_minutes)

    stmt = select(AnalysisJob).where(
        AnalysisJob.status.in_(ACTIVE_STATUSES),
        or_(
            AnalysisJob.updated_at <= cutoff_time,
            AnalysisJob.updated_at.is_(None),
        ),
    )
    result = await db.execute(stmt)
    stale_jobs = result.scalars().all()

    recovered_ids: List[uuid.UUID] = []

    for job in stale_jobs:
        logger.warning(
            "Stale job detected: %s (status=%s, updated_at=%s). Marking as failed.",
            job.id,
            job.status,
            job.updated_at,
        )
        job.status = AnalysisStatus.FAILED.value
        job.stage = "failed"
        job.error_message = (
            f"Job timed out or stalled: no progress updates for over {threshold_minutes} minutes."
        )

        # Clean up scratch storage folder if present
        clone_dir = os.path.join(settings.ANALYSIS_STORAGE_PATH, str(job.id))
        if os.path.exists(clone_dir):
            try:
                shutil.rmtree(clone_dir, ignore_errors=True)
                logger.info("Cleaned up orphaned storage for stale job %s: %s", job.id, clone_dir)
            except Exception as exc:
                logger.error("Failed to clean up clone dir %s: %s", clone_dir, exc)

        recovered_ids.append(job.id)

    if recovered_ids:
        await db.commit()

    return recovered_ids
