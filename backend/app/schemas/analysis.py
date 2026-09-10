import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field


class AnalysisJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    repository_id: uuid.UUID
    repository_url: str
    owner: str
    name: str
    status: str = Field(..., description="Current status: queued, cloning, discovering, completed, failed")
    stage: str = Field(..., description="Current pipeline execution stage")
    progress: int = Field(..., ge=0, le=100, description="Progress percentage (0-100)")
    message: str
    error_message: Optional[str] = None
    commit_hash: Optional[str] = None
    total_files: int = 0
    analyzable_files: int = 0
    total_lines: int = 0
    total_bytes: int = 0
    language_distribution: Dict[str, float] = Field(default_factory=dict)
    total_symbols: int = 0
    symbol_distribution: Dict[str, int] = Field(default_factory=dict)
    metadata_json: Dict[str, Any] = Field(default_factory=dict)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
