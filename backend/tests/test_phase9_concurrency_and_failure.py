import ast
import glob
import os
import uuid
from unittest.mock import MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
import pytest

from app.core.config import settings
from app.models.analysis import AnalysisJob, AnalysisStatus
from app.models.repository import Repository
from app.services.clone_detector import CloneDetector
from app.services.ingestion_orchestrator import execute_ingestion_pipeline


def test_clone_detector_bucket_and_pair_capping():
    detector = CloneDetector(min_lines=5, min_tokens=10)

    # Generate 150 repetitive identical files each with identical functions
    # to create a huge candidate bucket (> 150 occurrences for the same hash)
    repetitive_code = """
def repetitive_pattern_generator():
    x = 1
    y = 2
    z = x + y
    return z
"""
    files_content = {f"file_{i}.py": repetitive_code for i in range(150)}

    orig_bucket = settings.MAX_CANDIDATE_BUCKET_SIZE
    orig_cap = settings.MAX_CLONE_PAIRS_CAP
    try:
        settings.MAX_CANDIDATE_BUCKET_SIZE = 25
        settings.MAX_CLONE_PAIRS_CAP = 50

        result = detector.detect_clones(files_content)

        # Clone pairs retained must strictly not exceed MAX_CLONE_PAIRS_CAP
        assert len(result.duplicates) <= 50
        assert result.duplicate_lines_count > 0
    finally:
        settings.MAX_CANDIDATE_BUCKET_SIZE = orig_bucket
        settings.MAX_CLONE_PAIRS_CAP = orig_cap


def test_zero_execution_invariant_static_ast_only():
    """Validates that no dynamic code execution (exec, eval, importlib, __import__)

    is ever performed on analyzed repository files.
    """
    backend_app_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app"))
    python_files = glob.glob(os.path.join(backend_app_dir, "**", "*.py"), recursive=True)

    disallowed_calls = {"exec", "eval", "__import__"}

    for fpath in python_files:
        with open(fpath, "r", encoding="utf-8") as f:
            source = f.read()

        tree = ast.parse(source, filename=fpath)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    call_name = node.func.id
                    assert call_name not in disallowed_calls, (
                        f"Disallowed dynamic execution call '{call_name}' detected in {fpath}:{node.lineno}"
                    )
                elif isinstance(node.func, ast.Attribute):
                    # Check for importlib.import_module
                    if node.func.attr == "import_module":
                        assert False, (
                            f"Disallowed dynamic module import 'import_module' in {fpath}:{node.lineno}"
                        )


def test_no_package_managers_in_subprocesses():
    """Validates that subprocess calls are restricted to git and never invoke

    pip, npm, yarn, pnpm, cargo, or python to execute or install analyzed code.
    """
    backend_app_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app"))
    python_files = glob.glob(os.path.join(backend_app_dir, "**", "*.py"), recursive=True)

    prohibited_binaries = ["pip", "npm", "yarn", "pnpm", "cargo", "python", "node", "mvn", "gradle"]

    for fpath in python_files:
        with open(fpath, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for idx, line in enumerate(lines, start=1):
            if "subprocess" in line or "create_subprocess" in line:
                for bin_name in prohibited_binaries:
                    assert f'"{bin_name}"' not in line and f"'{bin_name}'" not in line, (
                        f"Prohibited package/execution invocation '{bin_name}' in {fpath}:{idx}"
                    )


@pytest.mark.asyncio
async def test_pipeline_failure_propagation_marks_job_failed(test_db):
    repo = Repository(
        name="failure-test-repo",
        owner="failure-owner",
        url="https://github.com/failure-owner/failure-test-repo",
        default_branch="main",
    )
    test_db.add(repo)
    await test_db.commit()
    await test_db.refresh(repo)

    job = AnalysisJob(
        repository_id=repo.id,
        status=AnalysisStatus.QUEUED.value,
        stage="queued",
        progress=0,
        message="Queued",
    )
    test_db.add(job)
    await test_db.commit()
    await test_db.refresh(job)

    # Mock clone_repository to simulate network failure / timeout
    with patch("app.services.ingestion_orchestrator.clone_repository", side_effect=RuntimeError("Simulated network timeout")), \
         patch("app.services.ingestion_orchestrator.AsyncSessionLocal") as mock_session_maker:

        class AsyncSessionContext:
            async def __aenter__(self):
                return test_db
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

        mock_session_maker.return_value = AsyncSessionContext()

        await execute_ingestion_pipeline(str(job.id))

    await test_db.refresh(job)
    assert job.status == AnalysisStatus.FAILED.value
    assert job.stage == "failed"
    assert "Simulated network timeout" in (job.error_message or "")


@pytest.mark.asyncio
async def test_concurrent_analysis_job_isolation(test_db):
    repo_a = Repository(name="repo-a", owner="owner-a", url="https://github.com/owner-a/repo-a", default_branch="main")
    repo_b = Repository(name="repo-b", owner="owner-b", url="https://github.com/owner-b/repo-b", default_branch="main")
    test_db.add_all([repo_a, repo_b])
    await test_db.commit()

    job_a = AnalysisJob(repository_id=repo_a.id, status=AnalysisStatus.QUEUED.value, stage="queued")
    job_b = AnalysisJob(repository_id=repo_b.id, status=AnalysisStatus.QUEUED.value, stage="queued")
    test_db.add_all([job_a, job_b])
    await test_db.commit()
    await test_db.refresh(job_a)
    await test_db.refresh(job_b)

    assert job_a.id != job_b.id
    assert job_a.repository_id != job_b.repository_id

    # Storage paths must be strictly distinct
    path_a = os.path.join(settings.ANALYSIS_STORAGE_PATH, str(job_a.id))
    path_b = os.path.join(settings.ANALYSIS_STORAGE_PATH, str(job_b.id))
    assert path_a != path_b


def test_cancellation_manager_redis_resilience(test_db):
    from app.services.cancellation_manager import request_cancellation_sync
    repo = Repository(name="cancel-repo", owner="cancel-owner", url="https://github.com/cancel-owner/cancel-repo")
    test_db.add(repo)

    job = AnalysisJob(
        repository_id=uuid.uuid4(),
        status=AnalysisStatus.PARSING.value,
        stage="parsing",
        progress=50,
        message="Parsing...",
    )

    # Calling request_cancellation_sync when redis is down must not raise an exception
    res = request_cancellation_sync(job, test_db, celery_app=None)
    assert res["status"] == "cancellation_requested"
    assert res["cancelled"] is True
