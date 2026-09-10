import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.analysis import AnalysisJob
from app.models.issue import AnalysisHealthScore, AnalysisIssue
from app.models.metrics import FileMetric, SymbolMetric
from app.services.quality_gate_engine import QualityGateEngine

router = APIRouter()


@router.get(
    "/{analysis_id}/quality-gate",
    status_code=status.HTTP_200_OK,
    summary="Get Analysis Quality Gate Evaluation",
    description="Evaluates codebase against structured engineering standards (health score, blockers, cycles, critical issues, maintainability, high-complexity functions). Supports custom query threshold overrides.",
)
async def get_quality_gate(
    analysis_id: str,
    min_score: Optional[float] = Query(None, ge=0.0, le=100.0, description="Minimum overall health score (default 80.0)"),
    max_blockers: Optional[int] = Query(None, ge=0, description="Maximum blocker issues allowed (default 0)"),
    max_cycles: Optional[int] = Query(None, ge=0, description="Maximum circular dependency cycles allowed (default 0)"),
    max_criticals: Optional[int] = Query(None, ge=0, description="Maximum critical issues allowed (default 2)"),
    min_mi: Optional[float] = Query(None, ge=0.0, le=100.0, description="Minimum average maintainability index (default 55.0)"),
    max_crit_funcs: Optional[int] = Query(None, ge=0, description="Maximum functions with CC >= 20 allowed (default 3)"),
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

    has_custom_overrides = any(
        x is not None
        for x in [min_score, max_blockers, max_cycles, max_criticals, min_mi, max_crit_funcs]
    )

    # If no custom overrides and job has stored quality_gate_details, return immediately
    if not has_custom_overrides and job.quality_gate_details:
        return job.quality_gate_details

    # Gather required metrics for dynamic evaluation
    overall_score = 0.0
    if job.health_summary and isinstance(job.health_summary, dict):
        overall_score = float(job.health_summary.get("overall_score", 0.0))
    else:
        hs_stmt = select(AnalysisHealthScore).where(AnalysisHealthScore.analysis_id == job_uuid)
        hs_res = await db.execute(hs_stmt)
        hs_row = hs_res.scalar_one_or_none()
        if hs_row and hs_row.overall_score is not None:
            overall_score = float(hs_row.overall_score)

    # Blocker issues count
    b_stmt = select(func.count(AnalysisIssue.id)).where(
        AnalysisIssue.analysis_id == job_uuid,
        AnalysisIssue.severity == "blocker",
    )
    b_res = await db.execute(b_stmt)
    blocker_count = b_res.scalar() or 0

    # Critical issues count
    c_stmt = select(func.count(AnalysisIssue.id)).where(
        AnalysisIssue.analysis_id == job_uuid,
        AnalysisIssue.severity == "critical",
    )
    c_res = await db.execute(c_stmt)
    critical_count = c_res.scalar() or 0

    # Circular dependencies count
    cycles_count = 0
    if job.health_summary and isinstance(job.health_summary, dict):
        arch_details = job.health_summary.get("architecture", {})
        cycles_count = arch_details.get("total_cycles", 0)
    elif job.dependency_summary and isinstance(job.dependency_summary, dict):
        cycles_count = job.dependency_summary.get("total_cycles", 0)

    # Average maintainability index
    mi_stmt = select(func.avg(FileMetric.maintainability_score)).where(
        FileMetric.analysis_id == job_uuid
    )
    mi_res = await db.execute(mi_stmt)
    avg_mi = mi_res.scalar()
    if avg_mi is None:
        avg_mi = 100.0
    else:
        avg_mi = float(avg_mi)

    # Critical complexity functions count (CC >= 20)
    crit_funcs_stmt = select(func.count(SymbolMetric.id)).where(
        SymbolMetric.analysis_id == job_uuid,
        SymbolMetric.cyclomatic_complexity >= 20,
    )
    crit_funcs_res = await db.execute(crit_funcs_stmt)
    crit_func_count = crit_funcs_res.scalar() or 0

    custom_thresholds = {}
    if min_score is not None:
        custom_thresholds["min_score"] = min_score
    if max_blockers is not None:
        custom_thresholds["max_blockers"] = max_blockers
    if max_cycles is not None:
        custom_thresholds["max_cycles"] = max_cycles
    if max_criticals is not None:
        custom_thresholds["max_criticals"] = max_criticals
    if min_mi is not None:
        custom_thresholds["min_mi"] = min_mi
    if max_crit_funcs is not None:
        custom_thresholds["max_crit_funcs"] = max_crit_funcs

    qg_res = QualityGateEngine.evaluate(
        overall_score=overall_score,
        blocker_count=blocker_count,
        critical_count=critical_count,
        circular_dependencies_count=cycles_count,
        average_maintainability_index=avg_mi,
        critical_complexity_functions_count=crit_func_count,
        custom_thresholds=custom_thresholds if custom_thresholds else None,
    )

    return qg_res.to_dict()
