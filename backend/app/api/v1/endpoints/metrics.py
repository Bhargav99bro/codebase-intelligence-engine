import logging
import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.analysis import AnalysisJob
from app.models.file import RepositoryFile
from app.models.metrics import FileMetric, SymbolMetric
from app.models.symbol import Symbol
from app.schemas.metrics import (
    FileMetricItemResponse,
    FileMetricsListResponse,
    RepositoryMetricsResponse,
    SymbolMetricItemResponse,
    SymbolMetricsListResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/{analysis_id}/metrics",
    response_model=RepositoryMetricsResponse,
    summary="Get repository-level complexity and quality metrics",
)
async def get_repository_metrics(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> RepositoryMetricsResponse:
    """Retrieves repository-wide complexity, maintainability score, and quality hotspot summaries."""
    job = await db.get(AnalysisJob, analysis_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis job {analysis_id} not found",
        )

    summary = job.summary_metrics or {}
    if not summary:
        # Construct fallback empty response if metrics have not yet completed
        summary = {
            "repository_totals": {
                "total_sloc": job.total_lines,
                "total_files": job.total_files,
                "total_symbols": job.total_symbols,
                "total_functions": 0,
                "total_classes": 0,
                "total_methods": 0,
            },
            "averages": {
                "average_cyclomatic_complexity": 1.0,
                "average_function_size": 0.0,
                "average_nesting_depth": 0.0,
            },
            "maximums": {
                "max_cyclomatic_complexity": 1,
                "max_function_size": 0,
                "max_nesting_depth": 0,
            },
            "maintainability": {
                "score": 100.0,
                "rating": "good",
                "label": "Good Maintainability",
            },
            "complexity_distribution": {"low": 0, "moderate": 0, "high": 0, "very_high": 0},
            "quality_summary": {
                "total_quality_flags": 0,
                "flagged_files_count": 0,
                "flagged_functions_count": 0,
                "severity_counts": {},
                "top_hotspots": [],
            },
        }

    return RepositoryMetricsResponse(
        analysis_id=job.id,
        repository_totals=summary.get("repository_totals", {}),
        averages=summary.get("averages", {}),
        maximums=summary.get("maximums", {}),
        maintainability=summary.get("maintainability", {}),
        complexity_distribution=summary.get("complexity_distribution", {}),
        quality_summary=summary.get("quality_summary", {}),
    )


@router.get(
    "/{analysis_id}/metrics/files",
    response_model=FileMetricsListResponse,
    summary="Get paginated file complexity and maintainability metrics",
)
async def get_file_metrics(
    analysis_id: uuid.UUID,
    skip: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(50, ge=1, le=200, description="Number of items to return"),
    sort_by: str = Query(
        "total_cyclomatic_complexity",
        description="Field to sort by: total_cyclomatic_complexity, sloc, maintainability_score, max_nesting_depth, function_count",
    ),
    order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order: asc or desc"),
    min_complexity: Optional[int] = Query(None, ge=0, description="Minimum cyclomatic complexity"),
    language: Optional[str] = Query(None, description="Filter by programming language"),
    flagged_only: bool = Query(False, description="Only return files with quality/hotspot flags"),
    db: AsyncSession = Depends(get_db),
) -> FileMetricsListResponse:
    """Returns paginated, filterable, and sortable file-level metrics for an analysis job."""
    job = await db.get(AnalysisJob, analysis_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis job {analysis_id} not found",
        )

    # Base query joining FileMetric and RepositoryFile
    query = (
        select(FileMetric, RepositoryFile.path, RepositoryFile.language)
        .join(RepositoryFile, FileMetric.file_id == RepositoryFile.id)
        .where(FileMetric.analysis_id == analysis_id)
    )

    if min_complexity is not None:
        query = query.where(FileMetric.total_cyclomatic_complexity >= min_complexity)

    if language:
        query = query.where(func.lower(RepositoryFile.language) == language.lower())

    if flagged_only:
        # Files where quality_flags JSON array is not empty
        query = query.where(func.json_array_length(FileMetric.quality_flags) > 0)

    # Count total matching
    count_query = select(func.count()).select_from(query.subquery())
    count_res = await db.execute(count_query)
    total = count_res.scalar() or 0

    # Sorting
    sort_column_map = {
        "total_cyclomatic_complexity": FileMetric.total_cyclomatic_complexity,
        "sloc": FileMetric.sloc,
        "maintainability_score": FileMetric.maintainability_score,
        "max_nesting_depth": FileMetric.max_nesting_depth,
        "function_count": FileMetric.function_count,
    }
    sort_col = sort_column_map.get(sort_by, FileMetric.total_cyclomatic_complexity)
    query = query.order_by(sort_col.desc() if order == "desc" else sort_col.asc())

    # Pagination
    query = query.offset(skip).limit(limit)
    res = await db.execute(query)
    rows = res.all()

    items: List[FileMetricItemResponse] = []
    for fm, path, lang in rows:
        items.append(
            FileMetricItemResponse(
                id=fm.id,
                file_id=fm.file_id,
                file_path=path,
                language=lang,
                total_lines=fm.total_lines,
                sloc=fm.sloc,
                comment_lines=fm.comment_lines,
                blank_lines=fm.blank_lines,
                statement_count=fm.statement_count,
                symbol_count=fm.symbol_count,
                function_count=fm.function_count,
                class_count=fm.class_count,
                method_count=fm.method_count,
                import_count=fm.import_count,
                export_count=fm.export_count,
                max_nesting_depth=fm.max_nesting_depth,
                average_nesting_depth=fm.average_nesting_depth,
                total_cyclomatic_complexity=fm.total_cyclomatic_complexity,
                average_cyclomatic_complexity=fm.average_cyclomatic_complexity,
                max_cyclomatic_complexity=fm.max_cyclomatic_complexity,
                maintainability_score=fm.maintainability_score,
                metric_status=fm.metric_status,
                metric_error=fm.metric_error,
                quality_flags=fm.quality_flags or [],
            )
        )

    return FileMetricsListResponse(
        analysis_id=job.id,
        items=items,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/{analysis_id}/metrics/symbols",
    response_model=SymbolMetricsListResponse,
    summary="Get paginated function and method complexity metrics",
)
async def get_symbol_metrics(
    analysis_id: uuid.UUID,
    skip: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(50, ge=1, le=200, description="Number of items to return"),
    sort_by: str = Query(
        "cyclomatic_complexity",
        description="Field to sort by: cyclomatic_complexity, lines_of_code, nesting_depth, parameter_count",
    ),
    order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order: asc or desc"),
    min_complexity: Optional[int] = Query(None, ge=0, description="Minimum cyclomatic complexity"),
    symbol_type: Optional[str] = Query(None, description="Filter by symbol type (e.g. function, method)"),
    file_id: Optional[uuid.UUID] = Query(None, description="Filter by file ID"),
    search: Optional[str] = Query(None, description="Search query for function name"),
    flagged_only: bool = Query(False, description="Only return functions with quality/hotspot flags"),
    db: AsyncSession = Depends(get_db),
) -> SymbolMetricsListResponse:
    """Returns paginated, filterable, and sortable function/method metrics for an analysis job."""
    job = await db.get(AnalysisJob, analysis_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis job {analysis_id} not found",
        )

    query = (
        select(
            SymbolMetric,
            Symbol.name.label("symbol_name"),
            Symbol.symbol_type.label("symbol_type"),
            Symbol.signature.label("signature"),
            Symbol.start_line.label("start_line"),
            RepositoryFile.path.label("file_path"),
        )
        .join(Symbol, SymbolMetric.symbol_id == Symbol.id)
        .join(RepositoryFile, SymbolMetric.file_id == RepositoryFile.id)
        .where(SymbolMetric.analysis_id == analysis_id)
    )

    if min_complexity is not None:
        query = query.where(SymbolMetric.cyclomatic_complexity >= min_complexity)

    if symbol_type:
        query = query.where(Symbol.symbol_type == symbol_type.lower())

    if file_id:
        query = query.where(SymbolMetric.file_id == file_id)

    if search:
        query = query.where(Symbol.name.ilike(f"%{search.strip()}%"))

    if flagged_only:
        query = query.where(func.json_array_length(SymbolMetric.quality_flags) > 0)

    # Count matching
    count_query = select(func.count()).select_from(query.subquery())
    count_res = await db.execute(count_query)
    total = count_res.scalar() or 0

    # Sorting
    sort_column_map = {
        "cyclomatic_complexity": SymbolMetric.cyclomatic_complexity,
        "lines_of_code": SymbolMetric.lines_of_code,
        "nesting_depth": SymbolMetric.nesting_depth,
        "parameter_count": SymbolMetric.parameter_count,
    }
    sort_col = sort_column_map.get(sort_by, SymbolMetric.cyclomatic_complexity)
    query = query.order_by(sort_col.desc() if order == "desc" else sort_col.asc())

    # Pagination
    query = query.offset(skip).limit(limit)
    res = await db.execute(query)
    rows = res.all()

    items: List[SymbolMetricItemResponse] = []
    for sm, s_name, s_type, s_sig, s_line, f_path in rows:
        items.append(
            SymbolMetricItemResponse(
                id=sm.id,
                symbol_id=sm.symbol_id,
                file_id=sm.file_id,
                symbol_name=s_name,
                symbol_type=s_type,
                signature=s_sig,
                file_path=f_path,
                start_line=s_line,
                lines_of_code=sm.lines_of_code,
                cyclomatic_complexity=sm.cyclomatic_complexity,
                nesting_depth=sm.nesting_depth,
                parameter_count=sm.parameter_count,
                return_count=sm.return_count,
                branch_count=sm.branch_count,
                loop_count=sm.loop_count,
                exception_handler_count=sm.exception_handler_count,
                boolean_condition_count=sm.boolean_condition_count,
                quality_flags=sm.quality_flags or [],
                metric_status=sm.metric_status,
                metric_error=sm.metric_error,
            )
        )

    return SymbolMetricsListResponse(
        analysis_id=job.id,
        items=items,
        total=total,
        skip=skip,
        limit=limit,
    )
