from datetime import datetime, timezone
from fastapi import APIRouter, Response, status
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import check_database_connection
from app.core.redis import check_redis_connection
from app.schemas.health import HealthResponse, ServiceComponentStatus

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="System Health & Subsystems Status",
    description="Returns the operational status of the API, PostgreSQL database, and Redis cache.",
)
async def get_health() -> HealthResponse:
    db_result = await check_database_connection()
    redis_result = await check_redis_connection()

    services = {
        "api": ServiceComponentStatus(status="connected", details="FastAPI ASGI engine operational"),
        "database": ServiceComponentStatus(
            status=db_result.get("status", "unknown"),
            details=db_result.get("details"),
        ),
        "redis": ServiceComponentStatus(
            status=redis_result.get("status", "unknown"),
            details=redis_result.get("details"),
        ),
    }

    # Determine overall status
    is_db_ok = services["database"].status == "connected"
    is_redis_ok = services["redis"].status == "connected"

    if is_db_ok and is_redis_ok:
        overall_status = "healthy"
    elif is_db_ok or is_redis_ok:
        overall_status = "degraded"
    else:
        overall_status = "unhealthy"

    return HealthResponse(
        status=overall_status,
        project=settings.PROJECT_NAME,
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        timestamp=datetime.now(timezone.utc),
        services=services,
    )


@router.get(
    "/ready",
    summary="Kubernetes / Orchestrator Readiness Probe",
    description="Verifies essential dependencies (PostgreSQL and Redis) are operational before routing traffic.",
)
async def get_ready():
    db_result = await check_database_connection()
    redis_result = await check_redis_connection()

    db_ok = db_result.get("status") == "connected"
    redis_ok = redis_result.get("status") == "connected"
    all_ready = db_ok and redis_ok

    payload = {
        "status": "ready" if all_ready else "not_ready",
        "database": db_result.get("status", "unknown"),
        "redis": redis_result.get("status", "unknown"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    if not all_ready:
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=payload)

    return JSONResponse(status_code=status.HTTP_200_OK, content=payload)


@router.get(
    "/live",
    summary="Kubernetes / Orchestrator Liveness Probe",
    description="Lightweight probe verifying that the application process is running and responsive.",
)
async def get_live():
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": "live",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": settings.VERSION,
        },
    )
