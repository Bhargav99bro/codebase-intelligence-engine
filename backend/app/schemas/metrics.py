import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class QualityFlagResponse(BaseModel):
    flag: str
    description: str
    metric_value: float
    threshold: float
    severity: str
    location: str


class RepositoryTotals(BaseModel):
    total_sloc: int = 0
    total_files: int = 0
    total_symbols: int = 0
    total_functions: int = 0
    total_classes: int = 0
    total_methods: int = 0


class MetricsAverages(BaseModel):
    average_cyclomatic_complexity: float = 1.0
    average_function_size: float = 0.0
    average_nesting_depth: float = 0.0


class MetricsMaximums(BaseModel):
    max_cyclomatic_complexity: int = 1
    max_function_size: int = 0
    max_nesting_depth: int = 0


class MaintainabilitySummary(BaseModel):
    score: float = 100.0
    rating: str = "good"
    label: str = "Good Maintainability"


class ComplexityDistribution(BaseModel):
    low: int = 0
    moderate: int = 0
    high: int = 0
    very_high: int = 0


class QualitySummary(BaseModel):
    total_quality_flags: int = 0
    flagged_files_count: int = 0
    flagged_functions_count: int = 0
    severity_counts: Dict[str, int] = Field(default_factory=dict)
    top_hotspots: List[Dict[str, Any]] = Field(default_factory=list)


class RepositoryMetricsResponse(BaseModel):
    analysis_id: uuid.UUID
    repository_totals: RepositoryTotals
    averages: MetricsAverages
    maximums: MetricsMaximums
    maintainability: MaintainabilitySummary
    complexity_distribution: ComplexityDistribution
    quality_summary: QualitySummary


class FileMetricItemResponse(BaseModel):
    id: uuid.UUID
    file_id: uuid.UUID
    file_path: str
    language: Optional[str] = None
    total_lines: int
    sloc: int
    comment_lines: int
    blank_lines: int
    statement_count: int
    symbol_count: int
    function_count: int
    class_count: int
    method_count: int
    import_count: int
    export_count: int
    max_nesting_depth: int
    average_nesting_depth: float
    total_cyclomatic_complexity: int
    average_cyclomatic_complexity: float
    max_cyclomatic_complexity: int
    maintainability_score: float
    metric_status: str
    metric_error: Optional[str] = None
    quality_flags: List[Dict[str, Any]] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class FileMetricsListResponse(BaseModel):
    analysis_id: uuid.UUID
    items: List[FileMetricItemResponse]
    total: int
    skip: int
    limit: int


class SymbolMetricItemResponse(BaseModel):
    id: uuid.UUID
    symbol_id: uuid.UUID
    file_id: uuid.UUID
    symbol_name: str
    symbol_type: str
    signature: Optional[str] = None
    file_path: str
    start_line: int
    lines_of_code: int
    cyclomatic_complexity: int
    nesting_depth: int
    parameter_count: int
    return_count: int
    branch_count: int
    loop_count: int
    exception_handler_count: int
    boolean_condition_count: int
    quality_flags: List[Dict[str, Any]] = Field(default_factory=list)
    metric_status: str
    metric_error: Optional[str] = None

    model_config = {"from_attributes": True}


class SymbolMetricsListResponse(BaseModel):
    analysis_id: uuid.UUID
    items: List[SymbolMetricItemResponse]
    total: int
    skip: int
    limit: int
