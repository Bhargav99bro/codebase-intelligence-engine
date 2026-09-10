import logging
import posixpath
from typing import Any, Dict, List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.database import get_db
from app.dependencies.graph import DirectedDependencyGraph
from app.dependencies.impact import ImpactAnalyzer
from app.models.analysis import AnalysisJob
from app.models.dependency import Dependency, FileDependencyMetric
from app.models.file import RepositoryFile
from app.schemas.dependency import (
    ArchitectureHotspotsResponse,
    CycleItemResponse,
    CyclesListResponse,
    DependenciesListResponse,
    DependencyGraphEdge,
    DependencyGraphNode,
    DependencyGraphResponse,
    DependencyItemResponse,
    DependencySummaryResponse,
    ImpactAnalysisResponse,
    ImpactedItemResponse,
    TopNodeMetric,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/{analysis_id}/dependencies",
    response_model=DependencySummaryResponse,
    summary="Get repository-level dependency summary metrics and architecture indicators",
)
async def get_dependency_summary(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> DependencySummaryResponse:
    job = await db.get(AnalysisJob, analysis_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis job {analysis_id} not found",
        )

    summary = job.dependency_summary or {}
    hotspots = summary.get("architecture_hotspots", {})

    return DependencySummaryResponse(
        analysis_id=job.id,
        total_dependencies=summary.get("total_dependencies", 0),
        internal_dependencies=summary.get("internal_dependencies", 0),
        external_dependencies=summary.get("external_dependencies", 0),
        unresolved_dependencies=summary.get("unresolved_dependencies", 0),
        analyzed_files=summary.get("analyzed_files", job.total_files),
        isolated_files_count=summary.get("isolated_files_count", 0),
        average_fan_in=summary.get("average_fan_in", 0.0),
        average_fan_out=summary.get("average_fan_out", 0.0),
        max_fan_in=summary.get("max_fan_in", 0),
        max_fan_out=summary.get("max_fan_out", 0),
        average_instability=summary.get("average_instability", 0.0),
        circular_dependency_count=summary.get("circular_dependency_count", 0),
        cycle_cap_reached=summary.get("cycle_cap_reached", False),
        top_fan_in=[TopNodeMetric(**m) for m in summary.get("top_fan_in", [])],
        top_fan_out=[TopNodeMetric(**m) for m in summary.get("top_fan_out", [])],
        architecture_hotspots=ArchitectureHotspotsResponse(
            core_foundation=hotspots.get("core_foundation", []),
            high_coupling=hotspots.get("high_coupling", []),
            cyclic_modules=hotspots.get("cyclic_modules", []),
            isolated_modules=hotspots.get("isolated_modules", []),
        ),
    )


@router.get(
    "/{analysis_id}/dependencies/edges",
    response_model=DependenciesListResponse,
    summary="Get paginated and filterable dependency edges",
)
async def get_dependency_edges(
    analysis_id: uuid.UUID,
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=200, description="Items per page"),
    source_file_id: Optional[uuid.UUID] = Query(None, description="Filter by source file ID"),
    target_file_id: Optional[uuid.UUID] = Query(None, description="Filter by target file ID"),
    resolution_status: Optional[str] = Query(None, description="Filter by resolution: internal, external, unresolved"),
    dependency_type: Optional[str] = Query(None, description="Filter by type: import, from_import, require, re_export"),
    search: Optional[str] = Query(None, description="Search target module or file name"),
    sort_by: str = Query("line_number", description="Field to sort by: line_number, target_module, created_at"),
    order: str = Query("asc", pattern="^(asc|desc)$", description="Sort order: asc or desc"),
    db: AsyncSession = Depends(get_db),
) -> DependenciesListResponse:
    job = await db.get(AnalysisJob, analysis_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis job {analysis_id} not found",
        )

    SourceFile = aliased(RepositoryFile)
    TargetFile = aliased(RepositoryFile)

    query = (
        select(Dependency, SourceFile.path.label("source_path"), TargetFile.path.label("target_path"))
        .join(SourceFile, Dependency.source_file_id == SourceFile.id)
        .outerjoin(TargetFile, Dependency.target_file_id == TargetFile.id)
        .where(Dependency.analysis_id == analysis_id)
    )

    if source_file_id:
        query = query.where(Dependency.source_file_id == source_file_id)
    if target_file_id:
        query = query.where(Dependency.target_file_id == target_file_id)
    if resolution_status:
        query = query.where(Dependency.resolution_status == resolution_status.lower())
    if dependency_type:
        query = query.where(Dependency.dependency_type == dependency_type.lower())
    if search:
        search_pattern = f"%{search.lower()}%"
        query = query.where(
            or_(
                func.lower(Dependency.target_module).like(search_pattern),
                func.lower(SourceFile.path).like(search_pattern),
                func.lower(TargetFile.path).like(search_pattern),
            )
        )

    # Count matching
    count_query = select(func.count()).select_from(query.subquery())
    count_res = await db.execute(count_query)
    total = count_res.scalar() or 0

    # Sorting
    sort_map = {
        "line_number": Dependency.line_number,
        "target_module": Dependency.target_module,
        "created_at": Dependency.created_at,
    }
    sort_col = sort_map.get(sort_by, Dependency.line_number)
    query = query.order_by(sort_col.desc() if order == "desc" else sort_col.asc())

    # Pagination
    query = query.offset(skip).limit(limit)
    res = await db.execute(query)
    rows = res.all()

    items: List[DependencyItemResponse] = []
    for dep, src_path, tgt_path in rows:
        items.append(
            DependencyItemResponse(
                id=dep.id,
                source_file_id=dep.source_file_id,
                source_file_path=src_path,
                target_file_id=dep.target_file_id,
                target_file_path=tgt_path,
                target_module=dep.target_module,
                dependency_type=dep.dependency_type,
                imported_symbols=dep.imported_symbols or [],
                line_number=dep.line_number,
                resolution_status=dep.resolution_status,
                is_type_only=dep.is_type_only,
                created_at=dep.created_at,
            )
        )

    return DependenciesListResponse(
        analysis_id=job.id,
        items=items,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/{analysis_id}/dependencies/graph",
    response_model=DependencyGraphResponse,
    summary="Get nodes and edges formatted for interactive graph visualization",
)
async def get_dependency_graph(
    analysis_id: uuid.UUID,
    max_nodes: int = Query(60, ge=5, le=200, description="Maximum nodes to return to prevent clutter"),
    min_degree: int = Query(0, ge=0, description="Minimum fan-in + fan-out to include a node"),
    focus_file_id: Optional[uuid.UUID] = Query(None, description="If specified, centers graph on this file and its direct neighborhood"),
    db: AsyncSession = Depends(get_db),
) -> DependencyGraphResponse:
    job = await db.get(AnalysisJob, analysis_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis job {analysis_id} not found",
        )

    # 1. Fetch internal files with their metrics
    stmt_files = (
        select(RepositoryFile, FileDependencyMetric)
        .outerjoin(FileDependencyMetric, RepositoryFile.id == FileDependencyMetric.file_id)
        .where(RepositoryFile.analysis_id == analysis_id)
    )
    res_files = await db.execute(stmt_files)
    file_rows = res_files.all()

    # 2. Fetch internal dependency edges
    SourceFile = aliased(RepositoryFile)
    TargetFile = aliased(RepositoryFile)
    stmt_edges = (
        select(Dependency, SourceFile.path.label("src_path"), TargetFile.path.label("tgt_path"))
        .join(SourceFile, Dependency.source_file_id == SourceFile.id)
        .join(TargetFile, Dependency.target_file_id == TargetFile.id)
        .where(Dependency.analysis_id == analysis_id)
        .where(Dependency.resolution_status == "internal")
        .where(Dependency.target_file_id.isnot(None))
    )
    res_edges = await db.execute(stmt_edges)
    edge_rows = res_edges.all()

    # Map file metadata
    file_map: Dict[uuid.UUID, Dict[str, Any]] = {}
    for rf, fdm in file_rows:
        fan_in = fdm.fan_in if fdm else 0
        fan_out = fdm.fan_out if fdm else 0
        file_map[rf.id] = {
            "id": str(rf.id),
            "label": posixpath.basename(rf.path),
            "path": rf.path,
            "language": rf.language,
            "fan_in": fan_in,
            "fan_out": fan_out,
            "total_degree": fan_in + fan_out,
            "instability": fdm.instability if fdm else 0.0,
            "in_cycle": fdm.in_cycle if fdm else False,
            "cycle_count": fdm.cycle_count if fdm else 0,
        }

    # Filter by focus_file_id if requested
    allowed_file_ids: Set[uuid.UUID] = set()
    if focus_file_id:
        if focus_file_id not in file_map:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Focus file {focus_file_id} not found in this analysis",
            )
        allowed_file_ids.add(focus_file_id)
        for dep, _, _ in edge_rows:
            if dep.source_file_id == focus_file_id:
                allowed_file_ids.add(dep.target_file_id)
            elif dep.target_file_id == focus_file_id:
                allowed_file_ids.add(dep.source_file_id)
    else:
        # Sort by total_degree descending and take top max_nodes
        sorted_files = sorted(file_map.values(), key=lambda x: x["total_degree"], reverse=True)
        filtered_files = [f for f in sorted_files if f["total_degree"] >= min_degree]
        allowed_file_ids = {uuid.UUID(f["id"]) for f in filtered_files[:max_nodes]}

    # Build response nodes
    response_nodes: List[DependencyGraphNode] = []
    for fid in allowed_file_ids:
        if fid in file_map:
            f = file_map[fid]
            response_nodes.append(
                DependencyGraphNode(
                    id=f["id"],
                    label=f["label"],
                    path=f["path"],
                    language=f["language"],
                    fan_in=f["fan_in"],
                    fan_out=f["fan_out"],
                    instability=f["instability"],
                    in_cycle=f["in_cycle"],
                    cycle_count=f["cycle_count"],
                )
            )

    # Build response edges where both endpoints are in allowed_file_ids
    response_edges: List[DependencyGraphEdge] = []
    seen_edge_pairs = set()
    for dep, src_path, tgt_path in edge_rows:
        if dep.source_file_id in allowed_file_ids and dep.target_file_id in allowed_file_ids:
            pair = (dep.source_file_id, dep.target_file_id)
            if pair not in seen_edge_pairs:
                seen_edge_pairs.add(pair)
                response_edges.append(
                    DependencyGraphEdge(
                        id=str(dep.id),
                        source=str(dep.source_file_id),
                        target=str(dep.target_file_id),
                        source_path=src_path,
                        target_path=tgt_path,
                        type=dep.dependency_type,
                        symbols=dep.imported_symbols or [],
                        line_number=dep.line_number,
                    )
                )

    return DependencyGraphResponse(
        analysis_id=job.id,
        nodes=response_nodes,
        edges=response_edges,
        total_nodes=len(response_nodes),
        total_edges=len(response_edges),
    )


@router.get(
    "/{analysis_id}/dependencies/cycles",
    response_model=CyclesListResponse,
    summary="Get detected circular dependencies with participating files and edges",
)
async def get_dependency_cycles(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> CyclesListResponse:
    job = await db.get(AnalysisJob, analysis_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis job {analysis_id} not found",
        )

    summary = job.dependency_summary or {}
    cycles_data = summary.get("cycles_summary", [])
    cycle_cap_reached = summary.get("cycle_cap_reached", False)

    cycle_items: List[CycleItemResponse] = []
    for c in cycles_data:
        files = c.get("files", [])
        edges = []
        for i in range(len(files) - 1):
            edges.append({"source": files[i], "target": files[i + 1]})

        cycle_items.append(
            CycleItemResponse(
                cycle_id=c.get("cycle_id", len(cycle_items) + 1),
                length=c.get("length", len(files)),
                files=files,
                edges=edges,
            )
        )

    return CyclesListResponse(
        analysis_id=job.id,
        total_cycles=len(cycle_items),
        cycle_cap_reached=cycle_cap_reached,
        cycles=cycle_items,
    )


@router.get(
    "/{analysis_id}/dependencies/impact/{file_id}",
    response_model=ImpactAnalysisResponse,
    summary="Perform direct and transitive change impact blast-radius analysis on a file",
)
async def get_impact_analysis(
    analysis_id: uuid.UUID,
    file_id: uuid.UUID,
    direction: str = Query("dependents", pattern="^(dependents|dependencies)$", description="Direction: dependents (who breaks) or dependencies (what is needed)"),
    max_depth: int = Query(5, ge=1, le=10, description="Max depth of transitive traversal (1 to 10)"),
    db: AsyncSession = Depends(get_db),
) -> ImpactAnalysisResponse:
    job = await db.get(AnalysisJob, analysis_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis job {analysis_id} not found",
        )

    target_file = await db.get(RepositoryFile, file_id)
    if not target_file or target_file.analysis_id != analysis_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File {file_id} not found in analysis {analysis_id}",
        )

    # 1. Fetch all internal files and edges to build graph in-memory for BFS
    stmt_files = select(RepositoryFile).where(RepositoryFile.analysis_id == analysis_id)
    res_files = await db.execute(stmt_files)
    files = res_files.scalars().all()

    stmt_edges = (
        select(Dependency)
        .where(Dependency.analysis_id == analysis_id)
        .where(Dependency.resolution_status == "internal")
        .where(Dependency.target_file_id.isnot(None))
    )
    res_edges = await db.execute(stmt_edges)
    edges = res_edges.scalars().all()

    # 2. Build graph
    graph = DirectedDependencyGraph()
    for f in files:
        graph.add_file_node(f.id, f.path, f.language)

    for dep in edges:
        graph.adjacency.setdefault(dep.source_file_id, set()).add(dep.target_file_id)
        graph.reverse_adjacency.setdefault(dep.target_file_id, set()).add(dep.source_file_id)

    # 3. Analyze impact
    analyzer = ImpactAnalyzer(graph)
    result = analyzer.analyze(file_id, direction=direction, max_depth=max_depth)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unable to analyze impact for file {file_id}",
        )

    items = [
        ImpactedItemResponse(
            file_id=it.file_id,
            file_path=it.file_path,
            depth=it.depth,
            is_direct=it.is_direct,
            relationship_path=it.relationship_path,
        )
        for it in result.items
    ]

    return ImpactAnalysisResponse(
        analysis_id=job.id,
        target_file_id=result.target_file_id,
        target_file_path=result.target_file_path,
        direction=result.direction,
        max_depth=result.max_depth,
        affected_files_count=result.affected_files_count,
        direct_count=result.direct_count,
        transitive_count=result.transitive_count,
        items=items,
    )
