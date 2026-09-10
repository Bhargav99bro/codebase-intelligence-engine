import json
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.router import api_v1_router
from app.core.config import settings
from app.core.logging import request_id_var, setup_logging
from app.core.middleware import CorrelationIdMiddleware, SecurityHeadersMiddleware
from app.core.redis import redis_client

logger = logging.getLogger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager for startup and shutdown hooks."""
    setup_logging()
    if settings.ENVIRONMENT == "production":
        settings.validate_production_configuration()

    logger.info("Initializing %s v%s in %s mode", settings.PROJECT_NAME, settings.VERSION, settings.ENVIRONMENT)

    yield

    logger.info("Shutting down %s...", settings.PROJECT_NAME)
    try:
        await redis_client.close()
    except Exception as exc:
        logger.warning("Error closing Redis client: %s", exc)


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "Production-grade Codebase Intelligence Engine providing AST parsing, "
        "dependency graph construction, code hotspots, and software health analytics."
    ),
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# 1. Correlation ID Middleware (outermost for accurate latency timing and request context)
app.add_middleware(CorrelationIdMiddleware)

# 2. Security Headers Middleware
if settings.ENABLE_SECURITY_HEADERS:
    app.add_middleware(SecurityHeadersMiddleware)

# 3. Configure CORS
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# --- Standardized Error Handlers ---
HTTP_STATUS_CODE_NAMES = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    408: "REQUEST_TIMEOUT",
    409: "CONFLICT",
    422: "VALIDATION_ERROR",
    429: "RATE_LIMIT_EXCEEDED",
    500: "INTERNAL_SERVER_ERROR",
    502: "BAD_GATEWAY",
    503: "SERVICE_UNAVAILABLE",
    504: "GATEWAY_TIMEOUT",
}


@app.exception_handler(StarletteHTTPException)
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    req_id = getattr(request.state, "request_id", None) or request_id_var.get("")
    code_name = getattr(exc, "error_code", None) or HTTP_STATUS_CODE_NAMES.get(exc.status_code, "HTTP_ERROR")
    msg = str(exc.detail) if not isinstance(exc.detail, (dict, list)) else json.dumps(exc.detail)

    return JSONResponse(
        status_code=exc.status_code,
        headers=getattr(exc, "headers", None),
        content={
            "detail": exc.detail,
            "error": {
                "code": code_name,
                "message": msg,
                "request_id": req_id,
            },
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    req_id = getattr(request.state, "request_id", None) or request_id_var.get("")
    return JSONResponse(
        status_code=422,
        content={
            "detail": exc.errors(),
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed.",
                "details": exc.errors(),
                "request_id": req_id,
            },
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    req_id = getattr(request.state, "request_id", None) or request_id_var.get("")
    logger.exception("Unhandled server exception: %s", exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error occurred.",
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "Internal server error occurred.",
                "request_id": req_id,
            },
        },
    )


# Include API v1 routers
app.include_router(api_v1_router, prefix=settings.API_V1_STR)

# Root-level health, ready, and live probe aliases
from app.api.v1.endpoints.health import get_health, get_live, get_ready

app.add_api_route("/health", get_health, methods=["GET"], include_in_schema=False)
app.add_api_route("/ready", get_ready, methods=["GET"], include_in_schema=False)
app.add_api_route("/live", get_live, methods=["GET"], include_in_schema=False)


@app.get("/", include_in_schema=False)
async def root_redirect() -> JSONResponse:
    return JSONResponse(
        content={
            "name": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "status": "online",
            "documentation": "/docs",
            "health_check": f"{settings.API_V1_STR}/health",
            "ready_check": f"{settings.API_V1_STR}/ready",
            "live_check": f"{settings.API_V1_STR}/live",
        }
    )
