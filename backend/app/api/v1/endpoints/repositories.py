import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limiter import RateLimiter
from app.models.analysis import AnalysisJob, AnalysisStatus
from app.models.repository import Repository
from app.schemas.repository import RepositoryAnalyzeRequest, RepositoryAnalyzeResponse
from app.services.url_validator import RepositoryUrlValidationError, validate_and_normalize_github_url
from app.workers.tasks import ingest_repository_task

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/analyze",
    response_model=RepositoryAnalyzeResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(RateLimiter(settings.RATE_LIMIT_ANALYSIS_PER_MINUTE, 60, "analyze"))],
    summary="Submit GitHub Repository for Ingestion & Analysis",
    description=(
        "Validates the GitHub URL, initializes the repository and analysis job records, "
        "and dispatches an asynchronous ingestion task to the Celery/Redis queue."
    ),
)
async def submit_repository_for_analysis(
    payload: RepositoryAnalyzeRequest,
    db: AsyncSession = Depends(get_db),
) -> RepositoryAnalyzeResponse:
    # 1. Validate and normalize repository URL
    try:
        validated_url = validate_and_normalize_github_url(payload.repository_url)
    except RepositoryUrlValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    # 2. Get or create Repository entity
    stmt = select(Repository).where(Repository.url == validated_url.url)
    result = await db.execute(stmt)
    repository = result.scalar_one_or_none()

    if not repository:
        repository = Repository(
            url=validated_url.url,
            owner=validated_url.owner,
            name=validated_url.name,
            default_branch="main",
        )
        db.add(repository)
        await db.flush()

    # 3. Create AnalysisJob entity
    job = AnalysisJob(
        repository_id=repository.id,
        status=AnalysisStatus.QUEUED.value,
        stage="queued",
        progress=0,
        message=f"Queued for ingestion: {validated_url.owner}/{validated_url.name}",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # 4. Enqueue to Celery / Redis
    try:
        ingest_repository_task.delay(str(job.id))
        logger.info("Enqueued ingestion task for analysis ID: %s", job.id)
    except Exception as exc:
        logger.error("Failed to enqueue ingestion task to Redis/Celery for analysis %s: %s", job.id, exc)
        job.status = AnalysisStatus.FAILED.value
        job.stage = "failed"
        job.error_message = f"Failed to enqueue task to Redis/Celery queue: {exc}"
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Job queue service (Redis/Celery) is currently unavailable. "
                "Ensure Redis and Celery worker services are running."
            ),
        )

    return RepositoryAnalyzeResponse(
        analysis_id=job.id,
        status=job.status,
        repository_url=repository.url,
        message=f"Repository {repository.owner}/{repository.name} successfully queued for ingestion.",
    )
