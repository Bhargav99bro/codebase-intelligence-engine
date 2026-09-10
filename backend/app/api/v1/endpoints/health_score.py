import logging
from typing import Any, Dict, List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.analysis import AnalysisJob
from app.models.issue import AnalysisHealthScore
from app.schemas.issue import HealthScoreResponse, RecommendationItemResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/{analysis_id}/health",
    response_model=HealthScoreResponse,
    summary="Get codebase health score, pillar breakdown, and prioritized recommendations",
)
async def get_health_score(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> HealthScoreResponse:
    job = await db.get(AnalysisJob, analysis_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis job {analysis_id} not found",
        )

    stmt = select(AnalysisHealthScore).where(AnalysisHealthScore.analysis_id == analysis_id)
    result = await db.execute(stmt)
    health_score = result.scalar_one_or_none()

    if not health_score:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Health score for analysis job {analysis_id} has not been computed or is unavailable",
        )

    recs_data = health_score.recommendations_json or []
    recommendations = []
    for r in recs_data:
        recommendations.append(
            RecommendationItemResponse(
                id=r.get("id", str(uuid.uuid4())),
                target_type=r.get("target_type", "file"),
                target_id=r.get("target_id"),
                target_name=r.get("target_name", ""),
                file_id=uuid.UUID(r["file_id"]) if r.get("file_id") else None,
                file_path=r.get("file_path"),
                title=r.get("title", ""),
                summary=r.get("summary", ""),
                rationale=r.get("rationale", ""),
                effort_hours=float(r.get("effort_hours", 0.0)),
                current_health_impact=float(r.get("current_health_impact", 0.0)),
                expected_score_recovery=float(r["expected_score_recovery"]) if r.get("expected_score_recovery") is not None else None,
                action_type=r.get("action_type", "refactor"),
                primary_category=r.get("primary_category", "maintainability"),
                related_issue_ids=r.get("related_issue_ids", []),
                modeled_metric_changes=r.get("modeled_metric_changes", {}),
                qualitative=bool(r.get("qualitative", False)),
            )
        )

    return HealthScoreResponse(
        analysis_id=health_score.analysis_id,
        overall_score=health_score.overall_score,
        grade=health_score.grade,
        maintainability_score=health_score.maintainability_score,
        complexity_score=health_score.complexity_score,
        architecture_score=health_score.architecture_score,
        hygiene_score=health_score.hygiene_score,
        technical_debt_minutes=health_score.technical_debt_minutes,
        debt_ratio_hours_per_ksloc=health_score.debt_ratio_hours_per_ksloc,
        total_issues_count=health_score.total_issues_count,
        blocker_count=health_score.blocker_count,
        critical_count=health_score.critical_count,
        major_count=health_score.major_count,
        minor_count=health_score.minor_count,
        info_count=health_score.info_count,
        category_scores=health_score.category_scores_json or {},
        recommendations=recommendations,
        created_at=health_score.created_at,
    )
