from datetime import datetime
from typing import Dict, Optional
from pydantic import BaseModel, Field


class ServiceComponentStatus(BaseModel):
    status: str = Field(..., description="Component status: connected, disconnected, degraded, etc.")
    details: Optional[str] = Field(None, description="Optional diagnostic details")


class HealthResponse(BaseModel):
    status: str = Field(..., description="Overall system status: healthy, degraded, or unhealthy")
    project: str = Field(..., description="Project name")
    version: str = Field(..., description="Application version")
    environment: str = Field(..., description="Deployment environment")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="UTC timestamp of the health check")
    services: Dict[str, ServiceComponentStatus] = Field(
        ..., description="Health status of underlying subsystem dependencies"
    )
