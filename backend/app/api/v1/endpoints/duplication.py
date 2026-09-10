import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.analysis import AnalysisJob
from app.models.duplication import CodeDuplicate
from app.models.issue import AnalysisHealthScore
from app.models.repository import Repository

router = APIRouter()


@router.get(
    "/{analysis_id}/duplication",
    status_code=status.HTTP_200_OK,
    summary="Get Code Duplication Intelligence",
    description="Returns detected Type-1 and Type-2 code duplicate blocks, duplication ratio, and duplication score.",
)
async def get_analysis_duplication(
    analysis_id: str,
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of duplicate pairs to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    clone_type: Optional[str] = Query(None, description="Filter by clone type: 'TYPE_1' or 'TYPE_2'"),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    try:
        analysis_uuid = uuid.UUID(analysis_id.strip())
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid UUID format: '{analysis_id}'.",
        )

    # 1. Fetch analysis and associated repository
    stmt = select(AnalysisJob).where(AnalysisJob.id == analysis_uuid)
    res = await db.execute(stmt)
    job = res.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis job with ID '{analysis_id}' was not found.",
        )

    repo_stmt = select(Repository).where(Repository.id == job.repository_id)
    repo = (await db.execute(repo_stmt)).scalar_one_or_none()
    repo_url = repo.url if repo else None
    commit_hash = job.commit_hash

    # 2. Fetch health score for duplication metrics
    hs_stmt = select(AnalysisHealthScore).where(AnalysisHealthScore.analysis_id == analysis_uuid)
    hs = (await db.execute(hs_stmt)).scalar_one_or_none()

    # 3. Query code duplicate records
    dup_stmt = select(CodeDuplicate).where(CodeDuplicate.analysis_id == analysis_uuid)
    if clone_type:
        dup_stmt = dup_stmt.where(CodeDuplicate.clone_type == clone_type.upper())

    dup_stmt = (
        dup_stmt.order_by(
            desc(CodeDuplicate.line_count),
            CodeDuplicate.source_file_path.asc(),
            CodeDuplicate.source_start_line.asc(),
            CodeDuplicate.target_file_path.asc(),
            CodeDuplicate.target_start_line.asc(),
        )
        .offset(offset)
        .limit(limit)
    )

    dup_records = (await db.execute(dup_stmt)).scalars().all()

    # Total count query
    count_stmt = select(CodeDuplicate).where(CodeDuplicate.analysis_id == analysis_uuid)
    if clone_type:
        count_stmt = count_stmt.where(CodeDuplicate.clone_type == clone_type.upper())
    total_matches = len((await db.execute(count_stmt)).scalars().all())

    return {
        "analysis_id": str(job.id),
        "duplication_score": hs.duplication_score if hs else 100.0,
        "duplication_ratio": hs.duplication_ratio if hs else 0.0,
        "duplicate_blocks_count": hs.duplicate_blocks_count if hs else 0,
        "duplicate_lines_count": hs.duplicate_lines_count if hs else 0,
        "total_matches": total_matches,
        "limit": limit,
        "offset": offset,
        "duplicates": [d.to_dict(repo_url=repo_url, commit_hash=commit_hash) for d in dup_records],
    }
