import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.analysis import AnalysisJob
from app.models.file import RepositoryFile
from app.models.issue import AnalysisIssue
from app.models.metrics import FileMetric
from app.services.treemap_builder import TreemapBuilder

router = APIRouter()


@router.get(
    "/{analysis_id}/treemap",
    status_code=status.HTTP_200_OK,
    summary="Get Hierarchical Codebase Treemap",
    description="Returns squarified multi-level directory/file tree with SLOC rollups, maintainability scores, complexity, and issue counts.",
)
async def get_analysis_treemap(
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

    # Fetch files and metrics
    files_stmt = (
        select(RepositoryFile, FileMetric)
        .outerjoin(FileMetric, (FileMetric.analysis_id == job_uuid) & (FileMetric.file_id == RepositoryFile.id))
        .where(RepositoryFile.analysis_id == job_uuid)
    )
    files_res = await db.execute(files_stmt)
    files_rows = files_res.all()

    # Fetch issues
    issues_stmt = select(AnalysisIssue).where(AnalysisIssue.analysis_id == job_uuid)
    issues_res = await db.execute(issues_stmt)
    issues_rows = issues_res.scalars().all()

    file_path_by_id = {rf.id: rf.path for rf, _ in files_rows}
    issues_by_file = {}
    for iss in issues_rows:
        fpath = file_path_by_id.get(iss.file_id) or getattr(iss, "file_path", None)
        if fpath:
            issues_by_file.setdefault(fpath, []).append({
                "rule_id": iss.rule_id,
                "severity": iss.severity,
                "title": iss.title,
            })

    files_data = []
    for rf, fm in files_rows:
        f_issues = issues_by_file.get(rf.path, [])
        files_data.append({
            "path": rf.path,
            "sloc": fm.sloc if fm else (rf.line_count or 0),
            "total_lines": rf.line_count or 0,
            "language": rf.language,
            "maintainability_score": fm.maintainability_score if fm else None,
            "max_cyclomatic_complexity": fm.max_cyclomatic_complexity if fm else None,
            "total_cyclomatic_complexity": fm.total_cyclomatic_complexity if fm else None,
            "issues": f_issues,
            "issue_count": len(f_issues),
        })

    treemap_root = TreemapBuilder.build_hierarchy(files_data, compute_layout=True)
    return {"root": treemap_root.to_dict()}
