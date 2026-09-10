from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class DependencyItemResponse(BaseModel):
    id: uuid.UUID
    source_file_id: uuid.UUID
    source_file_path: str
    target_file_id: Optional[uuid.UUID] = None
    target_file_path: Optional[str] = None
    target_module: str
    dependency_type: str
    imported_symbols: List[str] = Field(default_factory=list)
    line_number: int
    resolution_status: str
    is_type_only: bool = False
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DependenciesListResponse(BaseModel):
    analysis_id: uuid.UUID
    items: List[DependencyItemResponse]
    total: int
    skip: int
    limit: int


class DependencyGraphNode(BaseModel):
    id: str
    label: str
    path: str
    language: Optional[str] = None
    fan_in: int = 0
    fan_out: int = 0
    instability: float = 0.0
    in_cycle: bool = False
    cycle_count: int = 0


class DependencyGraphEdge(BaseModel):
    id: str
    source: str
    target: str
    source_path: str
    target_path: str
    type: str
    symbols: List[str] = Field(default_factory=list)
    line_number: int


class DependencyGraphResponse(BaseModel):
    analysis_id: uuid.UUID
    nodes: List[DependencyGraphNode]
    edges: List[DependencyGraphEdge]
    total_nodes: int
    total_edges: int


class CycleItemResponse(BaseModel):
    cycle_id: int
    length: int
    files: List[str]
    edges: List[Dict[str, str]]


class CyclesListResponse(BaseModel):
    analysis_id: uuid.UUID
    total_cycles: int
    cycle_cap_reached: bool = False
    cycles: List[CycleItemResponse]


class ImpactedItemResponse(BaseModel):
    file_id: uuid.UUID
    file_path: str
    depth: int
    is_direct: bool
    relationship_path: List[str]


class ImpactAnalysisResponse(BaseModel):
    analysis_id: uuid.UUID
    target_file_id: uuid.UUID
    target_file_path: str
    direction: str
    max_depth: int
    affected_files_count: int
    direct_count: int
    transitive_count: int
    items: List[ImpactedItemResponse]


class TopNodeMetric(BaseModel):
    file_id: str
    file_path: str
    fan_in: int
    fan_out: int
    instability: float


class ArchitectureHotspotsResponse(BaseModel):
    core_foundation: List[str] = Field(default_factory=list)
    high_coupling: List[str] = Field(default_factory=list)
    cyclic_modules: List[str] = Field(default_factory=list)
    isolated_modules: List[str] = Field(default_factory=list)


class DependencySummaryResponse(BaseModel):
    analysis_id: uuid.UUID
    total_dependencies: int
    internal_dependencies: int
    external_dependencies: int
    unresolved_dependencies: int
    analyzed_files: int
    isolated_files_count: int
    average_fan_in: float
    average_fan_out: float
    max_fan_in: int
    max_fan_out: int
    average_instability: float
    circular_dependency_count: int
    cycle_cap_reached: bool = False
    top_fan_in: List[TopNodeMetric] = Field(default_factory=list)
    top_fan_out: List[TopNodeMetric] = Field(default_factory=list)
    architecture_hotspots: ArchitectureHotspotsResponse
