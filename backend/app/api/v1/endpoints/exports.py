import json
import uuid
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limiter import RateLimiter
from app.models.analysis import AnalysisJob
from app.models.dependency import Dependency, FileDependencyMetric
from app.models.file import RepositoryFile
from app.models.issue import AnalysisHealthScore, AnalysisIssue
from app.models.metrics import FileMetric, SymbolMetric
from app.models.repository import Repository
from app.services.hotspot_analyzer import HotspotAnalyzer
from app.services.json_exporter import JsonExporter
from app.services.markdown_exporter import MarkdownExporter
from app.services.quality_gate_engine import QualityGateEngine
from app.services.sarif_exporter import SarifExporter

router = APIRouter()


async def _get_analysis_context(analysis_id: str, db: AsyncSession):
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

    # Repository
    repo_stmt = select(Repository).where(Repository.id == job.repository_id)
    repo_res = await db.execute(repo_stmt)
    repo = repo_res.scalar_one_or_none()
    repo_url = repo.url if repo else "https://github.com/unknown/repository"

    return job_uuid, job, repo, repo_url


@router.get(
    "/{analysis_id}/export/sarif",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(RateLimiter(settings.RATE_LIMIT_EXPORT_PER_MINUTE, 60, "export"))],
    summary="Export Analysis Results in OASIS SARIF v2.1.0",
    description="Generates standard SARIF v2.1.0 output for GitHub Code Scanning and IDEs with sanitized repository-relative paths.",
)
async def export_sarif(
    analysis_id: str,
    db: AsyncSession = Depends(get_db),
):
    job_uuid, job, repo, repo_url = await _get_analysis_context(analysis_id, db)

    # Fetch issues joined with RepositoryFile for accurate file_path
    issues_stmt = (
        select(AnalysisIssue, RepositoryFile.path)
        .outerjoin(RepositoryFile, AnalysisIssue.file_id == RepositoryFile.id)
        .where(AnalysisIssue.analysis_id == job_uuid)
    )
    issues_res = await db.execute(issues_stmt)
    issues_rows = issues_res.all()

    issues_payload = []
    for iss, fpath in issues_rows:
        issues_payload.append({
            "rule_id": iss.rule_id,
            "rule_name": iss.rule_name,
            "category": iss.category,
            "severity": iss.severity,
            "title": iss.title,
            "description": iss.description,
            "file_path": fpath or getattr(iss, "file_path", None) or "repository",
            "line_number": iss.line_number,
            "end_line_number": iss.end_line_number,
            "symbol_name": iss.symbol_name,
        })

    sarif_doc = SarifExporter.generate_sarif(
        issues=issues_payload,
        repository_url=repo_url,
        commit_hash=job.commit_hash,
    )

    content = json.dumps(sarif_doc, indent=2)
    return Response(
        content=content,
        media_type="application/sarif+json",
        headers={
            "Content-Disposition": f'attachment; filename="analysis-{analysis_id}.sarif"',
        },
    )


@router.get(
    "/{analysis_id}/export/markdown",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(RateLimiter(settings.RATE_LIMIT_EXPORT_PER_MINUTE, 60, "export"))],
    summary="Export Executive Markdown Audit Report",
    description="Generates a GitHub-flavored Markdown report suitable for PR comments, wikis, or engineering architecture reviews.",
)
async def export_markdown(
    analysis_id: str,
    db: AsyncSession = Depends(get_db),
):
    job_uuid, job, repo, repo_url = await _get_analysis_context(analysis_id, db)

    # Fetch health score
    hs_stmt = select(AnalysisHealthScore).where(AnalysisHealthScore.analysis_id == job_uuid)
    hs_res = await db.execute(hs_stmt)
    health_score_row = hs_res.scalar_one_or_none()

    health_summary = (
        health_score_row.to_dict()
        if health_score_row
        else (job.health_summary or {})
    )

    # Quality gate details
    quality_gate = job.quality_gate_details
    if not quality_gate:
        # Fallback evaluation
        avg_mi = (job.summary_metrics or {}).get("average_maintainability_score", 100.0)
        cycles = (job.dependency_summary or {}).get("total_cycles", 0)
        quality_gate = QualityGateEngine.evaluate(
            overall_score=float(health_summary.get("overall_score", 0.0)),
            blocker_count=health_summary.get("blocker_count", 0),
            critical_count=health_summary.get("critical_count", 0),
            circular_dependencies_count=cycles,
            average_maintainability_index=avg_mi,
            critical_complexity_functions_count=0,
        ).to_dict()

    # Query metrics & issues for hotspots
    fm_stmt = select(FileMetric).where(FileMetric.analysis_id == job_uuid)
    fm_res = await db.execute(fm_stmt)
    fm_rows = fm_res.scalars().all()

    dm_stmt = select(FileDependencyMetric).where(FileDependencyMetric.analysis_id == job_uuid)
    dm_res = await db.execute(dm_stmt)
    dm_rows = dm_res.scalars().all()

    iss_stmt = select(AnalysisIssue).where(AnalysisIssue.analysis_id == job_uuid)
    iss_res = await db.execute(iss_stmt)
    iss_rows = iss_res.scalars().all()

    rf_stmt = select(RepositoryFile).where(RepositoryFile.analysis_id == job_uuid)
    rf_res = await db.execute(rf_stmt)
    rf_rows = rf_res.scalars().all()

    hotspots = HotspotAnalyzer.analyze_from_db_records(
        file_metrics_rows=fm_rows,
        dep_metrics_rows=dm_rows,
        issues_rows=iss_rows,
        files_rows=rf_rows,
        max_results=5,
    )

    recommendations = (
        health_score_row.recommendations_json
        if health_score_row and health_score_row.recommendations_json
        else []
    )

    total_sloc = sum(fm.sloc for fm in fm_rows) if fm_rows else (job.total_lines or 0)

    # Issues summary
    issues_summary = {
        "total": len(iss_rows),
        "blocker": sum(1 for i in iss_rows if i.severity == "blocker"),
        "critical": sum(1 for i in iss_rows if i.severity == "critical"),
        "major": sum(1 for i in iss_rows if i.severity == "major"),
        "minor": sum(1 for i in iss_rows if i.severity == "minor"),
        "info": sum(1 for i in iss_rows if i.severity == "info"),
    }

    report_md = MarkdownExporter.generate_report(
        repository_url=repo_url,
        commit_hash=job.commit_hash,
        analysis_date=job.completed_at or job.created_at,
        total_files=job.total_files or len(fm_rows),
        total_sloc=total_sloc,
        health_summary=health_summary,
        quality_gate=quality_gate,
        hotspots=hotspots,
        recommendations=recommendations,
        issues_summary=issues_summary,
    )

    return Response(
        content=report_md,
        media_type="text/markdown; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="analysis-{analysis_id}-report.md"',
        },
    )


@router.get(
    "/{analysis_id}/export/json",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(RateLimiter(settings.RATE_LIMIT_EXPORT_PER_MINUTE, 60, "export"))],
    summary="Export Consolidated JSON Intelligence Payload",
    description="Serializes the complete repository intelligence model into a unified JSON schema with schema_version: '1.0'.",
)
async def export_json(
    analysis_id: str,
    db: AsyncSession = Depends(get_db),
):
    job_uuid, job, repo, repo_url = await _get_analysis_context(analysis_id, db)

    # Fetch health score
    hs_stmt = select(AnalysisHealthScore).where(AnalysisHealthScore.analysis_id == job_uuid)
    hs_res = await db.execute(hs_stmt)
    health_score_row = hs_res.scalar_one_or_none()

    health_summary = (
        health_score_row.to_dict()
        if health_score_row
        else (job.health_summary or {})
    )

    quality_gate = job.quality_gate_details
    if not quality_gate:
        avg_mi = (job.summary_metrics or {}).get("average_maintainability_score", 100.0)
        cycles = (job.dependency_summary or {}).get("total_cycles", 0)
        quality_gate = QualityGateEngine.evaluate(
            overall_score=float(health_summary.get("overall_score", 0.0)),
            blocker_count=health_summary.get("blocker_count", 0),
            critical_count=health_summary.get("critical_count", 0),
            circular_dependencies_count=cycles,
            average_maintainability_index=avg_mi,
            critical_complexity_functions_count=0,
        ).to_dict()

    # Query metrics & issues
    fm_stmt = select(FileMetric).where(FileMetric.analysis_id == job_uuid)
    fm_res = await db.execute(fm_stmt)
    fm_rows = fm_res.scalars().all()

    dm_stmt = select(FileDependencyMetric).where(FileDependencyMetric.analysis_id == job_uuid)
    dm_res = await db.execute(dm_stmt)
    dm_rows = dm_res.scalars().all()

    iss_stmt = select(AnalysisIssue).where(AnalysisIssue.analysis_id == job_uuid)
    iss_res = await db.execute(iss_stmt)
    iss_rows = iss_res.scalars().all()

    rf_stmt = select(RepositoryFile).where(RepositoryFile.analysis_id == job_uuid)
    rf_res = await db.execute(rf_stmt)
    rf_rows = rf_res.scalars().all()
    files_map = {rf.id: rf.path for rf in rf_rows}

    hotspots = HotspotAnalyzer.analyze_from_db_records(
        file_metrics_rows=fm_rows,
        dep_metrics_rows=dm_rows,
        issues_rows=iss_rows,
        files_rows=rf_rows,
        max_results=10,
    )

    recommendations = (
        health_score_row.recommendations_json
        if health_score_row and health_score_row.recommendations_json
        else []
    )

    issues_summary = {
        "total": len(iss_rows),
        "blocker": sum(1 for i in iss_rows if i.severity == "blocker"),
        "critical": sum(1 for i in iss_rows if i.severity == "critical"),
        "major": sum(1 for i in iss_rows if i.severity == "major"),
        "minor": sum(1 for i in iss_rows if i.severity == "minor"),
        "info": sum(1 for i in iss_rows if i.severity == "info"),
    }

    files_data = [
        {
            "path": files_map.get(fm.file_id, str(fm.file_id)),
            "sloc": fm.sloc,
            "maintainability_score": fm.maintainability_score,
            "max_cyclomatic_complexity": fm.max_cyclomatic_complexity,
        }
        for fm in fm_rows
    ]

    payload = JsonExporter.generate_payload(
        analysis_id=analysis_id,
        repository_url=repo_url,
        commit_hash=job.commit_hash,
        analysis_date=job.completed_at or job.created_at,
        health_summary=health_summary,
        quality_gate=quality_gate,
        hotspots=hotspots,
        recommendations=recommendations,
        issues_summary=issues_summary,
        dependency_summary=job.dependency_summary or {},
        files_data=files_data,
    )

    content = json.dumps(payload, indent=2)
    return Response(
        content=content,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="analysis-{analysis_id}-export.json"',
        },
    )
