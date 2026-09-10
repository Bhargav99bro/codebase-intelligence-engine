from datetime import datetime, timezone
from unittest.mock import MagicMock
import pytest
from fastapi import HTTPException

from app.models.analysis import AnalysisJob, AnalysisStatus
from app.services.cancellation_manager import (
    AnalysisCancelledException,
    check_checkpoint,
    get_cancel_key,
    request_cancellation_sync,
)


def test_checkpoint_raises_cancelled_exception():
    mock_redis = MagicMock()
    mock_redis.get.return_value = "true"

    with pytest.raises(AnalysisCancelledException) as exc_info:
        check_checkpoint("test-job-id", "file_discovery", redis_client=mock_redis)

    assert "file_discovery" in str(exc_info.value)


def test_checkpoint_passes_when_not_cancelled():
    mock_redis = MagicMock()
    mock_redis.get.return_value = None

    # Should not raise
    check_checkpoint("test-job-id", "cloning", redis_client=mock_redis)


def test_cancellation_idempotency_matrix():
    session = MagicMock()

    # 1. Nonexistent job -> 404
    with pytest.raises(HTTPException) as exc:
        request_cancellation_sync(None, session)
    assert exc.value.status_code == 404

    # 2. Completed job -> 409
    job_completed = AnalysisJob(
        id="11111111-1111-1111-1111-111111111111",
        status=AnalysisStatus.COMPLETED.value,
    )
    with pytest.raises(HTTPException) as exc:
        request_cancellation_sync(job_completed, session)
    assert exc.value.status_code == 409

    # 3. Failed job -> 409
    job_failed = AnalysisJob(
        id="22222222-2222-2222-2222-222222222222",
        status=AnalysisStatus.FAILED.value,
    )
    with pytest.raises(HTTPException) as exc:
        request_cancellation_sync(job_failed, session)
    assert exc.value.status_code == 409

    # 4. Cancelled job -> 200 idempotent
    job_cancelled = AnalysisJob(
        id="33333333-3333-3333-3333-333333333333",
        status=AnalysisStatus.CANCELLED.value,
    )
    res = request_cancellation_sync(job_cancelled, session)
    assert res["status"] == "cancelled"

    # 5. Cancellation requested job -> 200 idempotent
    job_requested = AnalysisJob(
        id="44444444-4444-4444-4444-444444444444",
        status=AnalysisStatus.CANCELLATION_REQUESTED.value,
    )
    res = request_cancellation_sync(job_requested, session)
    assert res["status"] == "cancellation_requested"

    # 6. Queued job -> transitions immediately to cancelled
    job_queued = AnalysisJob(
        id="55555555-5555-5555-5555-555555555555",
        status=AnalysisStatus.QUEUED.value,
    )
    res = request_cancellation_sync(job_queued, session)
    assert res["status"] == "cancelled"
    assert job_queued.status == AnalysisStatus.CANCELLED.value
    assert job_queued.is_cancelled is True

    # 7. Running job -> transitions to cancellation_requested
    job_running = AnalysisJob(
        id="66666666-6666-6666-6666-666666666666",
        status=AnalysisStatus.PARSING.value,
    )
    res = request_cancellation_sync(job_running, session)
    assert res["status"] == "cancellation_requested"
    assert job_running.status == AnalysisStatus.CANCELLATION_REQUESTED.value
    assert job_running.is_cancelled is True
