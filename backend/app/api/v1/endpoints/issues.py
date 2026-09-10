import logging
from typing import Any, Dict, List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.analysis import AnalysisJob
from app.models.file import RepositoryFile
from app.models.issue import AnalysisIssue
from app.schemas.issue import (
    IssueItemResponse,
    IssuesListResponse,
    IssuesSummaryResponse,
    TopRuleViolation,
)

logger = logging.getLogger(__name__)

router = APIRouter()

SEVERITY_ORDER = case(
    (AnalysisIssue.severity == "blocker", 1),
    (AnalysisIssue.severity == "critical", 2),
    (AnalysisIssue.severity == "major", 3),
    (AnalysisIssue.severity == "minor", 4),
    else_=5,
)


@router.get(
    "/{analysis_id}/issues",
    response_model=IssuesListResponse,
    summary="Get paginated diagnostic issues for an analysis job",
)
async def get_analysis_issues(
    analysis_id: uuid.UUID,
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    category: Optional[str] = Query(None, description="Filter by category (architecture, complexity, maintainability, hygiene, security)"),
    severity: Optional[str] = Query(None, description="Filter by severity (blocker, critical, major, minor, info)"),
    rule_id: Optional[str] = Query(None, description="Filter by rule ID (e.g. ARCH-001, COMPLEX-001)"),
    file_id: Optional[uuid.UUID] = Query(None, description="Filter by specific file ID"),
    search: Optional[str] = Query(None, description="Search term matching title, description, symbol name, or path"),
    db: AsyncSession = Depends(get_db),
) -> IssuesListResponse:
    job = await db.get(AnalysisJob, analysis_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis job {analysis_id} not found",
        )

    # Compute aggregate counts across all issues for this analysis job
    sev_stmt = (
        select(AnalysisIssue.severity, func.count(AnalysisIssue.id))
        .where(AnalysisIssue.analysis_id == analysis_id)
        .group_by(AnalysisIssue.severity)
    )
    sev_rows = (await db.execute(sev_stmt)).all()
    severity_counts = {row[0]: row[1] for row in sev_rows}

    cat_stmt = (
        select(AnalysisIssue.category, func.count(AnalysisIssue.id))
        .where(AnalysisIssue.analysis_id == analysis_id)
        .group_by(AnalysisIssue.category)
    )
    cat_rows = (await db.execute(cat_stmt)).all()
    category_counts = {row[0]: row[1] for row in cat_rows}

    # Filtered query
    base_stmt = (
        select(AnalysisIssue, RepositoryFile.path.label("file_path"))
        .outerjoin(RepositoryFile, AnalysisIssue.file_id == RepositoryFile.id)
        .where(AnalysisIssue.analysis_id == analysis_id)
    )

    if category:
        base_stmt = base_stmt.where(AnalysisIssue.category == category)
    if severity:
        base_stmt = base_stmt.where(AnalysisIssue.severity == severity)
    if rule_id:
        base_stmt = base_stmt.where(AnalysisIssue.rule_id == rule_id)
    if file_id:
        base_stmt = base_stmt.where(AnalysisIssue.file_id == file_id)
    if search and search.strip():
        search_pattern = f"%{search.strip()}%"
        base_stmt = base_stmt.where(
            or_(
                AnalysisIssue.title.ilike(search_pattern),
                AnalysisIssue.description.ilike(search_pattern),
                AnalysisIssue.symbol_name.ilike(search_pattern),
                RepositoryFile.path.ilike(search_pattern),
            )
        )

    # Count total filtered items
    count_stmt = select(func.count()).select_from(base_stmt.subquery())
    total_count = (await db.execute(count_stmt)).scalar() or 0

    # Paginate and order
    paginated_stmt = (
        base_stmt.order_by(SEVERITY_ORDER, AnalysisIssue.rule_id, AnalysisIssue.created_at)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    results = (await db.execute(paginated_stmt)).all()

    items = []
    for issue_obj, fpath in results:
        items.append(
            IssueItemResponse(
                id=issue_obj.id,
                analysis_id=issue_obj.analysis_id,
                file_id=issue_obj.file_id,
                file_path=fpath,
                rule_id=issue_obj.rule_id,
                rule_name=issue_obj.rule_name,
                category=issue_obj.category,
                severity=issue_obj.severity,
                title=issue_obj.title,
                description=issue_obj.description,
                line_number=issue_obj.line_number,
                end_line_number=issue_obj.end_line_number,
                symbol_name=issue_obj.symbol_name,
                remediation_effort_minutes=issue_obj.remediation_effort_minutes,
                metadata_json=issue_obj.metadata_json or {},
                created_at=issue_obj.created_at,
            )
        )

    total_pages = (total_count + page_size - 1) // page_size if page_size > 0 else 1

    return IssuesListResponse(
        analysis_id=analysis_id,
        items=items,
        total=total_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        severity_counts=severity_counts,
        category_counts=category_counts,
    )


@router.get(
    "/{analysis_id}/issues/summary",
    response_model=IssuesSummaryResponse,
    summary="Get aggregated issue counts, severity breakdown, and technical debt",
)
async def get_issues_summary(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> IssuesSummaryResponse:
    job = await db.get(AnalysisJob, analysis_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis job {analysis_id} not found",
        )

    # Severity counts
    sev_stmt = (
        select(AnalysisIssue.severity, func.count(AnalysisIssue.id))
        .where(AnalysisIssue.analysis_id == analysis_id)
        .group_by(AnalysisIssue.severity)
    )
    sev_rows = (await db.execute(sev_stmt)).all()
    severity_counts = {row[0]: row[1] for row in sev_rows}

    # Category counts
    cat_stmt = (
        select(AnalysisIssue.category, func.count(AnalysisIssue.id))
        .where(AnalysisIssue.analysis_id == analysis_id)
        .group_by(AnalysisIssue.category)
    )
    cat_rows = (await db.execute(cat_stmt)).all()
    category_counts = {row[0]: row[1] for row in cat_rows}

    # Total issues and debt
    total_stmt = (
        select(
            func.count(AnalysisIssue.id),
            func.coalesce(func.sum(AnalysisIssue.remediation_effort_minutes), 0),
        ).where(AnalysisIssue.analysis_id == analysis_id)
    )
    total_res = (await db.execute(total_stmt)).first()
    total_issues = total_res[0] if total_res else 0
    total_debt_minutes = int(total_res[1]) if total_res else 0

    # Top 10 violated rules
    top_rules_stmt = (
        select(
            AnalysisIssue.rule_id,
            AnalysisIssue.rule_name,
            AnalysisIssue.category,
            AnalysisIssue.severity,
            func.count(AnalysisIssue.id).label("cnt"),
        )
        .where(AnalysisIssue.analysis_id == analysis_id)
        .group_by(
            AnalysisIssue.rule_id,
            AnalysisIssue.rule_name,
            AnalysisIssue.category,
            AnalysisIssue.severity,
        )
        .order_by(func.count(AnalysisIssue.id).desc())
        .limit(10)
    )
    top_rules_rows = (await db.execute(top_rules_stmt)).all()
    top_violated_rules = [
        TopRuleViolation(
            rule_id=r[0],
            rule_name=r[1],
            category=r[2],
            severity=r[3],
            count=r[4],
        )
        for r in top_rules_rows
    ]

    return IssuesSummaryResponse(
        analysis_id=analysis_id,
        total_issues=total_issues,
        severity_counts=severity_counts,
        category_counts=category_counts,
        total_technical_debt_minutes=total_debt_minutes,
        top_violated_rules=top_violated_rules,
    )
