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

# 3. Graceful shutdown handler for container stop signals
cleanup() {
    echo "[ENTRYPOINT] Termination signal received. Initiating graceful shutdown..."
    kill -TERM "$CELERY_PID" 2>/dev/null || true
    kill -TERM "$UVICORN_PID" 2>/dev/null || true
    wait "$CELERY_PID" 2>/dev/null || true
    wait "$UVICORN_PID" 2>/dev/null || true
    echo "[ENTRYPOINT] All child processes terminated. Exiting."
    exit 0
}

trap cleanup SIGTERM SIGINT

# 4. Start Uvicorn ASGI server
PORT_NUM=${PORT:-8000}
echo "[ENTRYPOINT] Starting Uvicorn ASGI server on port ${PORT_NUM}..."
uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "${PORT_NUM}" \
    --workers 2 \
    --proxy-headers \
    --forwarded-allow-ips "*" &
UVICORN_PID=$!

# 5. Monitor processes - if either process exits, trigger cleanup and exit
wait -n "$CELERY_PID" "$UVICORN_PID"
EXIT_STATUS=$?
echo "[ENTRYPOINT] A core process exited with status ${EXIT_STATUS}. Shutting down container..."
cleanup
