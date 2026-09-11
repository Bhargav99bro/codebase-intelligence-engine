from typing import List, Literal, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Codebase Intelligence Engine"
    VERSION: str = "0.1.0"
    ENVIRONMENT: Literal["development", "test", "production"] = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: Literal["text", "json"] = "text"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "insecure-dev-secret-key-change-in-production"

    # CORS
    BACKEND_CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://localhost:80",
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    # PostgreSQL
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres_secure_password"
    POSTGRES_DB: str = "codebase_intelligence"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres_secure_password@localhost:5432/codebase_intelligence"

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_database_url(cls, v: str) -> str:
        if isinstance(v, str):
            if v.startswith("postgres://"):
                v = "postgresql+asyncpg://" + v[len("postgres://"):]
            elif v.startswith("postgresql://") and not v.startswith("postgresql+asyncpg://"):
                v = "postgresql+asyncpg://" + v[len("postgresql://"):]
            if "sslmode=" in v:
                v = v.replace("sslmode=", "ssl=")
        return v

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0
    REDIS_URL: str = "redis://localhost:6379/0"

    @field_validator("REDIS_URL", mode="before")
    @classmethod
    def assemble_redis_url(cls, v: str) -> str:
        if isinstance(v, str):
            import re

            def _normalize_cert_reqs(match):
                val = match.group(1).lower()
                if "required" in val:
                    return "ssl_cert_reqs=required"
                elif "optional" in val:
                    return "ssl_cert_reqs=optional"
                elif "none" in val:
                    return "ssl_cert_reqs=none"
                return match.group(0)

            v = re.sub(r"ssl_cert_reqs=([a-zA-Z_]+)", _normalize_cert_reqs, v, flags=re.IGNORECASE)
        return v

    # Repository analysis limits & storage
    ANALYSIS_STORAGE_PATH: str = "./scratch/repos"
    MAX_REPO_SIZE_MB: int = 500
    CLONE_TIMEOUT_SECONDS: int = 60
    MAX_FILE_COUNT: int = 10000
    MAX_SINGLE_FILE_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB limit per file

    # Security & SSRF Controls
    ALLOWED_GIT_HOSTS: List[str] = [
        "github.com",
        "www.github.com",
        "gitlab.com",
        "www.gitlab.com",
    ]
    ENABLE_SECURITY_HEADERS: bool = True

    # Rate Limiting / Abuse Protection
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_ANALYSIS_PER_MINUTE: int = 20
    RATE_LIMIT_COMPARE_PER_MINUTE: int = 60
    RATE_LIMIT_EXPORT_PER_MINUTE: int = 60
    RATE_LIMIT_ALLOW_MEMORY_FALLBACK: bool = True

    # Resource Governance
    MAX_CONCURRENT_ANALYSES: int = 2
    CELERY_WORKER_CONCURRENCY: int = 1
    UVICORN_WORKERS: int = 1
    MAX_CLONE_PAIRS_CAP: int = 10000
    MAX_CANDIDATE_BUCKET_SIZE: int = 100
    STALE_JOB_THRESHOLD_MINUTES: int = 30
    MAX_PAGE_SIZE: int = 100

    def validate_production_configuration(self) -> None:
        """Enforces mandatory production security invariants."""
        if self.ENVIRONMENT == "production":
            errors = []
            if self.DEBUG:
                errors.append("DEBUG must be False in production.")
            if self.SECRET_KEY in ("insecure-dev-secret-key-change-in-production", "", "secret"):
                errors.append("SECRET_KEY must be set to a secure random string in production.")
            if "postgres_secure_password" in self.DATABASE_URL:
                errors.append("Default database password cannot be used in production.")
            if isinstance(self.BACKEND_CORS_ORIGINS, list):
                for origin in self.BACKEND_CORS_ORIGINS:
                    if origin == "*":
                        errors.append("Wildcard '*' CORS origin is strictly forbidden in production.")
                    if "localhost" in origin or "127.0.0.1" in origin:
                        errors.append(f"Localhost CORS origin '{origin}' is forbidden in production.")
            if errors:
                raise ValueError("Production configuration validation failed:\n - " + "\n - ".join(errors))

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
