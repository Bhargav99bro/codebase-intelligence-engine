from typing import Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.analysis import AnalysisJob
from app.models.dependency import FileDependencyMetric
from app.models.duplication import GitChurnMetric
from app.models.file import RepositoryFile
from app.models.issue import AnalysisIssue
from app.models.metrics import FileMetric
from app.services.hotspot_analyzer import HotspotAnalyzer

router = APIRouter()


@router.get(
    "/{analysis_id}/hotspots",
    status_code=status.HTTP_200_OK,
    summary="Get Top Codebase Hotspots",
    description="Returns top ranked architectural and complexity hotspots based on normalized multi-metric scoring (SLOC, CC, Nesting, Fan-In, Fan-Out, and issue burden).",
)
async def get_analysis_hotspots(
    analysis_id: str,
    limit: int = Query(10, ge=1, le=50, description="Maximum number of hotspots to return"),
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

    # Query file metrics
    fm_stmt = select(FileMetric).where(FileMetric.analysis_id == job_uuid)
    fm_res = await db.execute(fm_stmt)
    fm_rows = fm_res.scalars().all()

    # Query file dependency metrics
    dm_stmt = select(FileDependencyMetric).where(FileDependencyMetric.analysis_id == job_uuid)
    dm_res = await db.execute(dm_stmt)
    dm_rows = dm_res.scalars().all()

    # Query issues
    iss_stmt = select(AnalysisIssue).where(AnalysisIssue.analysis_id == job_uuid)
    iss_res = await db.execute(iss_stmt)
    iss_rows = iss_res.scalars().all()

    # Query repository files for accurate path mapping
    rf_stmt = select(RepositoryFile).where(RepositoryFile.analysis_id == job_uuid)
    rf_res = await db.execute(rf_stmt)
    rf_rows = rf_res.scalars().all()

    hotspots = HotspotAnalyzer.analyze_from_db_records(
        file_metrics_rows=fm_rows,
        dep_metrics_rows=dm_rows,
        issues_rows=iss_rows,
        files_rows=rf_rows,
        max_results=limit,
    )

    # Query Git Churn metrics if available
    churn_stmt = select(GitChurnMetric).where(GitChurnMetric.analysis_id == job_uuid)
    churn_res = await db.execute(churn_stmt)
    churn_rows = churn_res.scalars().all()
    churn_by_file = {c.file_path: c for c in churn_rows}
    has_history = len(churn_rows) > 0

    hotspot_dicts = []
    for h in hotspots:
        h_dict = h.to_dict()
        churn_item = churn_by_file.get(h.file_path)
        c_score = round(churn_item.churn_score, 1) if churn_item else 0.0
        defect_score = round(
            max(0.0, min(100.0, 0.60 * h.hotspot_score + 0.40 * c_score)), 1
        ) if has_history else h.hotspot_score
        h_dict["churn_score"] = c_score
        h_dict["defect_hotspot_score"] = defect_score
        hotspot_dicts.append(h_dict)

    return {
        "total_analyzed_files": len(fm_rows),
        "hotspots": hotspot_dicts,
    }
