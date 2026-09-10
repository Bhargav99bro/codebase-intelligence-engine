import uuid
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.analysis import AnalysisJob
from app.models.duplication import GitChurnMetric

router = APIRouter()


@router.get(
    "/{analysis_id}/churn",
    status_code=status.HTTP_200_OK,
    summary="Get Git Churn & Defect Risk Metrics",
    description="Returns git commit frequency, line additions/deletions, and relative churn metrics per file.",
)
async def get_analysis_churn(
    analysis_id: str,
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of file metrics to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    try:
        analysis_uuid = uuid.UUID(analysis_id.strip())
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid UUID format: '{analysis_id}'.",
        )

    stmt = select(AnalysisJob).where(AnalysisJob.id == analysis_uuid)
    res = await db.execute(stmt)
    job = res.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis job with ID '{analysis_id}' was not found.",
        )

    churn_stmt = (
        select(GitChurnMetric)
        .where(GitChurnMetric.analysis_id == analysis_uuid)
        .order_by(
            desc(GitChurnMetric.churn_score),
            desc(GitChurnMetric.commit_count),
            GitChurnMetric.file_path.asc(),
        )
        .offset(offset)
        .limit(limit)
    )

    records = (await db.execute(churn_stmt)).scalars().all()

    # Count all churn records for this analysis
    all_stmt = select(GitChurnMetric).where(GitChurnMetric.analysis_id == analysis_uuid)
    all_records = (await db.execute(all_stmt)).scalars().all()

    has_git_history = len(all_records) > 0
    max_churn = max((r.churn_score for r in all_records), default=0.0)

    return {
        "analysis_id": str(job.id),
        "has_git_history": has_git_history,
        "max_churn": round(max_churn, 1),
        "total_files": len(all_records),
        "limit": limit,
        "offset": offset,
        "churn_metrics": [r.to_dict() for r in records],
    }
