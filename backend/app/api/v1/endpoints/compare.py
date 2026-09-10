import uuid
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limiter import RateLimiter
from app.models.analysis import AnalysisJob, AnalysisStatus
from app.models.dependency import FileDependencyMetric
from app.models.file import RepositoryFile
from app.models.issue import AnalysisHealthScore, AnalysisIssue
from app.services.diff_engine import AnalysisDiffEngine

router = APIRouter()


@router.get(
    "/compare",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(RateLimiter(settings.RATE_LIMIT_COMPARE_PER_MINUTE, 60, "compare"))],
    summary="Compare Two Analyses (Analysis Diff & PR Gate)",
    description="Compares baseline and current analyses to evaluate delta health, technical debt, issue lifecycle, cycle shifts, and PR quality gate.",
)
async def compare_analyses(
    base_id: str = Query(..., description="UUID of the baseline analysis"),
    head_id: str = Query(..., description="UUID of the head / PR analysis"),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    # 1. Self-comparison validation
    if base_id.strip() == head_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot compare an analysis to itself. Specify two distinct analysis IDs.",
        )

    try:
        base_uuid = uuid.UUID(base_id.strip())
        head_uuid = uuid.UUID(head_id.strip())
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid UUID format for base_id or head_id.",
        )

    # 2. Fetch both analyses
    stmt_base = select(AnalysisJob).where(AnalysisJob.id == base_uuid)
    res_base = await db.execute(stmt_base)
    base_job = res_base.scalar_one_or_none()

    if not base_job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Baseline analysis with ID '{base_id}' was not found.",
        )

    stmt_head = select(AnalysisJob).where(AnalysisJob.id == head_uuid)
    res_head = await db.execute(stmt_head)
    head_job = res_head.scalar_one_or_none()

    if not head_job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Head analysis with ID '{head_id}' was not found.",
        )

    # 3. Same repository validation
    if base_job.repository_id != head_job.repository_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Analyses belong to different repositories. Only analyses from the same repository can be compared.",
        )

    # 4. Completed status validation
    if base_job.status != AnalysisStatus.COMPLETED.value or head_job.status != AnalysisStatus.COMPLETED.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Both analyses must be completed to perform a comparison.",
        )

    # 5. Fetch health scores
    hs_base_stmt = select(AnalysisHealthScore).where(AnalysisHealthScore.analysis_id == base_uuid)
    hs_base = (await db.execute(hs_base_stmt)).scalar_one_or_none()

    hs_head_stmt = select(AnalysisHealthScore).where(AnalysisHealthScore.analysis_id == head_uuid)
    hs_head = (await db.execute(hs_head_stmt)).scalar_one_or_none()

    # 6. Fetch issues with file_path
    iss_base_stmt = (
        select(AnalysisIssue, RepositoryFile.path.label("file_path"))
        .outerjoin(RepositoryFile, AnalysisIssue.file_id == RepositoryFile.id)
        .where(AnalysisIssue.analysis_id == base_uuid)
    )
    iss_base_rows = (await db.execute(iss_base_stmt)).all()
    iss_base_list = [issue.to_dict(file_path=fp) for issue, fp in iss_base_rows]

    iss_head_stmt = (
        select(AnalysisIssue, RepositoryFile.path.label("file_path"))
        .outerjoin(RepositoryFile, AnalysisIssue.file_id == RepositoryFile.id)
        .where(AnalysisIssue.analysis_id == head_uuid)
    )
    iss_head_rows = (await db.execute(iss_head_stmt)).all()
    iss_head_list = [issue.to_dict(file_path=fp) for issue, fp in iss_head_rows]

    # 7. Fetch cycles from dependencies / file_dependency_metrics or dependency_summary
    base_cycles = []
    if base_job.dependency_summary and "cycles" in base_job.dependency_summary:
        base_cycles = base_job.dependency_summary["cycles"]

    head_cycles = []
    if head_job.dependency_summary and "cycles" in head_job.dependency_summary:
        head_cycles = head_job.dependency_summary["cycles"]

    # Package analysis payloads
    base_payload = {
        "id": str(base_job.id),
        "health_score": hs_base.to_dict() if hs_base else {},
        "issues": iss_base_list,
        "cycles": base_cycles,
    }

    head_payload = {
        "id": str(head_job.id),
        "health_score": hs_head.to_dict() if hs_head else {},
        "issues": iss_head_list,
        "cycles": head_cycles,
    }

    diff_engine = AnalysisDiffEngine()
    diff_result = diff_engine.compare_analyses(base_payload, head_payload)

    return diff_result.to_dict()
