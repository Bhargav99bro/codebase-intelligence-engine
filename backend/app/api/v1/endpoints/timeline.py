import uuid
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.analysis import AnalysisJob, AnalysisStatus
from app.models.issue import AnalysisHealthScore
from app.models.repository import Repository

router = APIRouter()


@router.get(
    "/{repository_id}/timeline",
    status_code=status.HTTP_200_OK,
    summary="Get Repository Health Score & Debt Timeline",
    description="Returns chronological sequence of completed analyses ordered by commit_date ASC NULLS LAST, created_at ASC for longitudinal trend tracking.",
)
async def get_repository_timeline(
    repository_id: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    try:
        repo_uuid = uuid.UUID(repository_id.strip())
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid repository UUID format: '{repository_id}'.",
        )

    repo_stmt = select(Repository).where(Repository.id == repo_uuid)
    repo = (await db.execute(repo_stmt)).scalar_one_or_none()

    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository with ID '{repository_id}' was not found.",
        )

    # Fetch completed analysis jobs ordered by commit_date ASC NULLS LAST, created_at ASC
    jobs_stmt = (
        select(AnalysisJob)
        .options(selectinload(AnalysisJob.health_score))
        .where(
            AnalysisJob.repository_id == repo_uuid,
            AnalysisJob.status == AnalysisStatus.COMPLETED.value,
        )
        .order_by(
            AnalysisJob.commit_date.asc().nullslast(),
            AnalysisJob.created_at.asc(),
        )
    )

    jobs = (await db.execute(jobs_stmt)).scalars().all()

    timeline_points = []
    for job in jobs:
        hs = job.health_score
        timeline_points.append(
            {
                "analysis_id": str(job.id),
                "commit_hash": job.commit_hash,
                "commit_author": job.commit_author,
                "commit_message": job.commit_message,
                "commit_date": job.commit_date.isoformat() if job.commit_date else None,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "overall_score": hs.overall_score if hs else 100.0,
                "grade": hs.grade if hs else "A",
                "maintainability_score": hs.maintainability_score if hs else 100.0,
                "complexity_score": hs.complexity_score if hs else 100.0,
                "architecture_score": hs.architecture_score if hs else 100.0,
                "hygiene_score": hs.hygiene_score if hs else 100.0,
                "duplication_score": hs.duplication_score if hs else 100.0,
                "duplication_ratio": hs.duplication_ratio if hs else 0.0,
                "duplicate_blocks_count": hs.duplicate_blocks_count if hs else 0,
                "duplicate_lines_count": hs.duplicate_lines_count if hs else 0,
                "technical_debt_minutes": hs.technical_debt_minutes if hs else 0,
                "debt_ratio_hours_per_ksloc": hs.debt_ratio_hours_per_ksloc if hs else 0.0,
                "total_issues_count": hs.total_issues_count if hs else 0,
            }
        )

    return {
        "repository_id": str(repo.id),
        "repository_name": f"{repo.owner}/{repo.name}",
        "default_branch": repo.default_branch,
        "timeline_count": len(timeline_points),
        "total_points": len(timeline_points),
        "timeline": timeline_points,
    }
