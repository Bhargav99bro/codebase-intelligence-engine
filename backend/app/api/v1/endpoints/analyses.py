import logging
from typing import Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.analysis import AnalysisJob
from app.models.file import RepositoryFile
from app.models.repository import Repository
from app.models.symbol import Symbol
from app.core.config import settings
from app.schemas.analysis import AnalysisJobResponse
from app.schemas.symbol import SymbolItemResponse, SymbolListResponse
from app.services.cancellation_manager import request_cancellation_sync
from app.services.event_streamer import sse_event_generator
from app.services.job_recovery import recover_stale_jobs

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/recover-stale",
    summary="Recover Stale Analysis Jobs",
    description="Identifies active analysis jobs that have stalled beyond the timeout threshold and marks them as failed.",
)
async def trigger_stale_job_recovery(
    threshold_minutes: Optional[int] = Query(None, ge=1, le=1440),
    db: AsyncSession = Depends(get_db),
):
    mins = threshold_minutes or settings.STALE_JOB_THRESHOLD_MINUTES
    recovered_ids = await recover_stale_jobs(db, threshold_minutes=mins)
    return {
        "recovered_count": len(recovered_ids),
        "recovered_job_ids": [str(rid) for rid in recovered_ids],
        "threshold_minutes": mins,
    }


@router.get(
    "/{analysis_id}",
    response_model=AnalysisJobResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Analysis Job Status & Metrics",
    description="Polls real-time execution status, progress percentage, stage, ingestion metrics, and symbol counts.",
)
async def get_analysis_status(
    analysis_id: str,
    db: AsyncSession = Depends(get_db),
) -> AnalysisJobResponse:
    try:
        job_uuid = uuid.UUID(analysis_id)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid analysis ID format: '{analysis_id}'. Expected standard UUID.",
        )

    stmt = (
        select(AnalysisJob)
        .options(selectinload(AnalysisJob.repository))
        .where(AnalysisJob.id == job_uuid)
    )
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis job with ID '{analysis_id}' was not found.",
        )

    return AnalysisJobResponse(
        id=job.id,
        repository_id=job.repository_id,
        repository_url=job.repository.url,
        owner=job.repository.owner,
        name=job.repository.name,
        status=job.status,
        stage=job.stage,
        progress=job.progress,
        message=job.message,
        error_message=job.error_message,
        commit_hash=job.commit_hash,
        total_files=job.total_files,
        analyzable_files=job.analyzable_files,
        total_lines=job.total_lines,
        total_bytes=job.total_bytes,
        language_distribution=job.language_distribution or {},
        total_symbols=job.total_symbols or 0,
        symbol_distribution=job.symbol_distribution or {},
        metadata_json=job.metadata_json or {},
        started_at=job.started_at,
        completed_at=job.completed_at,
        created_at=job.created_at,
    )


@router.get(
    "/{analysis_id}/symbols",
    response_model=SymbolListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Extracted Structural Symbols",
    description="Returns paginated symbols extracted from the codebase with optional filtering by type, file, or search query.",
)
async def get_analysis_symbols(
    analysis_id: str,
    skip: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(50, ge=1, le=200, description="Maximum items per page"),
    symbol_type: Optional[str] = Query(None, description="Filter by symbol type: function, class, method, import, export, interface, type"),
    file_id: Optional[uuid.UUID] = Query(None, description="Filter by specific repository file ID"),
    search: Optional[str] = Query(None, description="Search symbol by name or qualified name"),
    db: AsyncSession = Depends(get_db),
) -> SymbolListResponse:
    try:
        job_uuid = uuid.UUID(analysis_id)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid analysis ID format: '{analysis_id}'. Expected standard UUID.",
        )

    # Base query joined with repository_files to obtain file_path
    base_query = (
        select(Symbol, RepositoryFile.path.label("file_path"))
        .join(RepositoryFile, Symbol.file_id == RepositoryFile.id)
        .where(Symbol.analysis_id == job_uuid)
    )

    if symbol_type:
        base_query = base_query.where(Symbol.symbol_type == symbol_type.lower().strip())
    if file_id:
        base_query = base_query.where(Symbol.file_id == file_id)
    if search:
        search_filter = f"%{search.strip()}%"
        base_query = base_query.where(
            (Symbol.name.ilike(search_filter)) | (Symbol.qualified_name.ilike(search_filter))
        )

    # Count total matching rows
    count_query = select(func.count()).select_from(base_query.subquery())
    count_result = await db.execute(count_query)
    total_count = count_result.scalar() or 0

    # Paginated query ordered by file path and start line
    paged_query = (
        base_query
        .order_by(RepositoryFile.path.asc(), Symbol.start_line.asc(), Symbol.start_column.asc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(paged_query)
    rows = result.all()

    items = [
        SymbolItemResponse(
            id=sym.id,
            analysis_id=sym.analysis_id,
            file_id=sym.file_id,
            file_path=file_path,
            name=sym.name,
            symbol_type=sym.symbol_type,
            qualified_name=sym.qualified_name,
            start_line=sym.start_line,
            start_column=sym.start_column,
            end_line=sym.end_line,
            end_column=sym.end_column,
            parent_symbol_id=sym.parent_symbol_id,
            signature=sym.signature,
            metadata_json=sym.metadata_json or {},
            created_at=sym.created_at,
        )
        for sym, file_path in rows
    ]

    return SymbolListResponse(
        items=items,
        total=total_count,
        skip=skip,
        limit=limit,
    )


@router.post(
    "/{analysis_id}/cancel",
    status_code=status.HTTP_200_OK,
    summary="Cancel In-Flight Analysis Job",
    description="Idempotently requests cooperative cancellation of an in-flight analysis job, stopping workers and cleaning workspace.",
)
async def cancel_analysis_job(
    analysis_id: str,
    db: AsyncSession = Depends(get_db),
):
    try:
        job_uuid = uuid.UUID(analysis_id)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid analysis ID format: '{analysis_id}'.",
        )

    stmt = select(AnalysisJob).where(AnalysisJob.id == job_uuid)
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis job with ID '{analysis_id}' was not found.",
        )

    # Celery app optional fallback
    celery_app = None
    try:
        from app.workers.celery_app import celery_app as cap
        celery_app = cap
    except Exception:
        pass

    cancel_res = request_cancellation_sync(job, db, celery_app=celery_app)
    await db.commit()
    return cancel_res


@router.get(
    "/{analysis_id}/events",
    summary="Server-Sent Events (SSE) Stream",
    description="Streams real-time analysis pipeline stages, progress percentage, log messages, and terminal completion events.",
)
async def stream_analysis_events(
    analysis_id: str,
    db: AsyncSession = Depends(get_db),
):
    try:
        job_uuid = uuid.UUID(analysis_id)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid analysis ID format: '{analysis_id}'.",
        )

    stmt = select(AnalysisJob).where(AnalysisJob.id == job_uuid)
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis job with ID '{analysis_id}' was not found.",
        )

    summary_payload = None
    if job.status == "completed":
        summary_payload = {
            "status": "completed",
            "overall_score": (job.health_summary or {}).get("overall_score"),
            "grade": (job.health_summary or {}).get("grade"),
            "quality_gate_status": job.quality_gate_status,
            "total_files": job.total_files,
            "total_symbols": job.total_symbols,
            "message": job.message,
        }

    generator = sse_event_generator(
        analysis_id=analysis_id,
        initial_status=job.status,
        initial_stage=job.stage,
        initial_progress=job.progress,
        initial_message=job.message,
        error_message=job.error_message,
        summary_data=summary_payload,
    )

    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

