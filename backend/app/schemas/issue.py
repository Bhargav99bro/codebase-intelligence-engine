from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class IssueItemResponse(BaseModel):
    id: uuid.UUID
    analysis_id: uuid.UUID
    file_id: Optional[uuid.UUID] = None
    file_path: Optional[str] = None
    rule_id: str
    rule_name: str
    category: str
    severity: str
    title: str
    description: str
    line_number: Optional[int] = None
    end_line_number: Optional[int] = None
    symbol_name: Optional[str] = None
    remediation_effort_minutes: int = 15
    metadata_json: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IssuesListResponse(BaseModel):
    analysis_id: uuid.UUID
    items: List[IssueItemResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    severity_counts: Dict[str, int] = Field(default_factory=dict)
    category_counts: Dict[str, int] = Field(default_factory=dict)


class TopRuleViolation(BaseModel):
    rule_id: str
    rule_name: str
    category: str
    severity: str
    count: int


class IssuesSummaryResponse(BaseModel):
    analysis_id: uuid.UUID
    total_issues: int
    severity_counts: Dict[str, int] = Field(default_factory=dict)
    category_counts: Dict[str, int] = Field(default_factory=dict)
    total_technical_debt_minutes: int
    top_violated_rules: List[TopRuleViolation] = Field(default_factory=list)


class RecommendationItemResponse(BaseModel):
    id: str
    target_type: str
    target_id: Optional[str] = None
    target_name: str
    file_id: Optional[uuid.UUID] = None
    file_path: Optional[str] = None
    title: str
    summary: str
    rationale: str
    effort_hours: float
    current_health_impact: float
    expected_score_recovery: Optional[float] = None
    action_type: str
    primary_category: str
    related_issue_ids: List[str] = Field(default_factory=list)
    modeled_metric_changes: Dict[str, Any] = Field(default_factory=dict)
    qualitative: bool = False


class HealthScoreResponse(BaseModel):
    analysis_id: uuid.UUID
    overall_score: float
    grade: str
    maintainability_score: float
    complexity_score: float
    architecture_score: float
    hygiene_score: float
    technical_debt_minutes: int
    debt_ratio_hours_per_ksloc: float
    total_issues_count: int
    blocker_count: int
    critical_count: int
    major_count: int
    minor_count: int
    info_count: int
    category_scores: Dict[str, Any] = Field(default_factory=dict)
    recommendations: List[RecommendationItemResponse] = Field(default_factory=list)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
