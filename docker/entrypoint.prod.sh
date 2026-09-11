#!/bin/bash
set -eo pipefail

# If arguments were provided to the container (e.g. docker-compose command override), execute them directly
if [ "$#" -gt 0 ]; then
    exec "$@"
fi

echo "=================================================="
echo "Codebase Intelligence Engine - Unified Prod Boot"
echo "=================================================="

# 1. Run database migrations to ensure latest schema
echo "[ENTRYPOINT] Applying Alembic database migrations..."
alembic upgrade head
echo "[ENTRYPOINT] Database migrations successfully applied."

# 2. Start Celery worker in background for asynchronous ingestion
echo "[ENTRYPOINT] Starting Celery worker (queue: ingestion, concurrency: 2)..."
celery -A app.workers.celery_app.celery_app worker \
    --loglevel=info \
    -Q ingestion \
    --concurrency=2 &
CELERY_PID=$!
echo "[ENTRYPOINT] Celery worker started with PID ${CELERY_PID}."

# 3. Graceful shutdown handler for container stop signals
cleanup() {
    echo "[ENTRYPOINT] Termination signal received. Initiating graceful shutdown..."
    if [ -n "$UVICORN_PID" ]; then
        kill -TERM "$UVICORN_PID" 2>/dev/null || true
    fi
    if [ -n "$CELERY_PID" ]; then
        kill -TERM "$CELERY_PID" 2>/dev/null || true
    fi
    wait "$UVICORN_PID" 2>/dev/null || true
    wait "$CELERY_PID" 2>/dev/null || true
    echo "[ENTRYPOINT] All child processes terminated. Exiting."
    exit 0
}

trap cleanup SIGTERM SIGINT

# 4. Configure trusted proxy IPs safely without globbing expansion
export FORWARDED_ALLOW_IPS="${FORWARDED_ALLOW_IPS:-*}"

# 5. Start Uvicorn ASGI server as the primary long-running web process
PORT_NUM=${PORT:-10000}
echo "[ENTRYPOINT] Starting Uvicorn ASGI server on 0.0.0.0:${PORT_NUM}..."
uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "${PORT_NUM}" \
    --workers 2 \
    --proxy-headers &
UVICORN_PID=$!
echo "[ENTRYPOINT] Uvicorn server started with PID ${UVICORN_PID}."

# 6. Supervise Uvicorn as the primary HTTP process. Celery runs concurrently in the background.
wait "$UVICORN_PID"
EXIT_STATUS=$?
echo "[ENTRYPOINT] Uvicorn process exited with status ${EXIT_STATUS}. Shutting down container..."
cleanup
