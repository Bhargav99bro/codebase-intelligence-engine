import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class RepositoryAnalyzeRequest(BaseModel):
    repository_url: str = Field(
        ...,
        description="Public GitHub HTTPS repository URL (e.g. https://github.com/pallets/flask)",
        json_schema_extra={"example": "https://github.com/pallets/flask"},
    )


class RepositoryAnalyzeResponse(BaseModel):
    analysis_id: uuid.UUID = Field(..., description="Unique ID for the initiated analysis job")
    status: str = Field(..., description="Initial status of the queued job ('queued')")
    repository_url: str = Field(..., description="Normalized repository URL")
    message: str = Field(..., description="Status summary message")


class RepositoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    url: str
    owner: str
    name: str
    default_branch: str
    created_at: datetime
