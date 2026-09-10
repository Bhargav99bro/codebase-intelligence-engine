FROM python:3.13-slim

WORKDIR /app

# Install minimal OS dependencies for git cloning and health probing
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for deterministic, fast package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Create non-root application user for least-privilege security
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app /tmp/cie_repos && \
    chown -R appuser:appuser /app /tmp/cie_repos

COPY backend/pyproject.toml ./
RUN uv pip install --system --no-cache -e .

COPY backend/app ./app
COPY backend/alembic ./alembic
COPY backend/alembic.ini ./alembic.ini
COPY docker/entrypoint.prod.sh ./entrypoint.prod.sh
RUN chmod +x ./entrypoint.prod.sh && chown appuser:appuser ./entrypoint.prod.sh

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/ready || exit 1

ENTRYPOINT ["/app/entrypoint.prod.sh"]
