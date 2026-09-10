import subprocess
import uuid
from unittest.mock import patch
import pytest
from sqlalchemy import select

from app.models.analysis import AnalysisJob, AnalysisStatus
from app.models.file import RepositoryFile
from app.models.metrics import FileMetric, SymbolMetric
from app.models.repository import Repository
from app.models.symbol import Symbol
from app.services.cloner import ClonedRepository
from app.services.ingestion_orchestrator import execute_ingestion_pipeline


@pytest.fixture
def metrics_test_repo(tmp_path):
    """Creates a local mock git repository containing Python, TS, and a broken file for error isolation."""
    repo_dir = tmp_path / "metrics_repo"
    repo_dir.mkdir()

    subprocess.run(["git", "init"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "metrics@example.com"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "MetricsDev"], cwd=repo_dir, check=True, capture_output=True)

    src_dir = repo_dir / "src"
    src_dir.mkdir()

    # 1. math_service.py: contains simple and complex functions
    (src_dir / "math_service.py").write_text("""# Math Service Module
def calculate_factorial(n: int) -> int:
    \"\"\"Compute factorial with loop and branch.\"\"\"
    if n < 0:
        raise ValueError("Negative input")
    result = 1
    for i in range(1, n + 1):
        result *= i
    return result

def is_prime(num: int) -> bool:
    if num <= 1:
        return False
    for i in range(2, int(num ** 0.5) + 1):
        if num % i == 0:
            return False
    return True
""")

    # 2. broken.py: Syntax error file for fault isolation
    (src_dir / "broken.py").write_text("""def unclosed_parenthesis(
    this is invalid python code!
""")

    # 3. app.ts: TypeScript with function and interface
    (src_dir / "app.ts").write_text("""interface AppConfig {
    env: string;
    port: number;
}

function startServer(config: AppConfig): boolean {
    if (config.port > 1024 && config.env === "production") {
        return true;
    }
    return false;
}
""")

    subprocess.run(["git", "add", "."], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial metrics test commit"], cwd=repo_dir, check=True, capture_output=True)

    return repo_dir


from sqlalchemy.orm import selectinload


@pytest.mark.asyncio
async def test_metrics_pipeline_execution_and_fault_isolation(test_db, metrics_test_repo):
    """Verifies that Stage 5 executes, populates FileMetric & SymbolMetric, and isolates broken files."""
    repo = Repository(
        id=uuid.uuid4(),
        url="https://github.com/metrics-test/repo",
        owner="metrics-test",
        name="repo",
        default_branch="main",
    )
    test_db.add(repo)
    await test_db.flush()

    job = AnalysisJob(
        id=uuid.uuid4(),
        repository_id=repo.id,
        status=AnalysisStatus.QUEUED.value,
        stage="queued",
        progress=0,
    )
    test_db.add(job)
    await test_db.commit()

    mock_cloned = ClonedRepository(
        temp_dir=str(metrics_test_repo),
        commit_hash="c0ffee1234567890",
        commit_message="Initial metrics test commit",
        commit_author="MetricsDev <metrics@example.com>",
        default_branch="main",
    )

    class MockSessionContext:
        async def __aenter__(self):
            return test_db

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    with patch("app.services.ingestion_orchestrator.clone_repository", return_value=mock_cloned), \
         patch.object(mock_cloned, "cleanup"), \
         patch("app.services.ingestion_orchestrator.AsyncSessionLocal", side_effect=lambda: MockSessionContext()):
        await execute_ingestion_pipeline(str(job.id))

    # Refresh job
    await test_db.refresh(job)
    assert job.status == "completed"
    assert job.stage == "completed"
    assert job.progress == 100
    assert job.summary_metrics is not None

    # Check summary metrics structure
    summary = job.summary_metrics
    assert "repository_totals" in summary
    assert "averages" in summary
    assert "maximums" in summary
    assert "maintainability" in summary
    assert "complexity_distribution" in summary
    assert "quality_summary" in summary
    assert summary["repository_totals"]["total_sloc"] > 0

    # Query FileMetric records with file relationship loaded
    stmt_fm = (
        select(FileMetric)
        .options(selectinload(FileMetric.file))
        .where(FileMetric.analysis_id == job.id)
    )
    res_fm = await test_db.execute(stmt_fm)
    file_metrics = res_fm.scalars().all()
    assert len(file_metrics) == 3

    # Broken file must have metric_status == "failed"
    broken_fm = next(fm for fm in file_metrics if "broken.py" in fm.file.path)
    assert broken_fm.metric_status == "failed"
    assert broken_fm.metric_error is not None

    # Math service must have metric_status == "calculated"
    math_fm = next(fm for fm in file_metrics if "math_service.py" in fm.file.path)
    assert math_fm.metric_status == "calculated"
    assert math_fm.sloc > 0
    assert math_fm.total_cyclomatic_complexity >= 5
    assert math_fm.maintainability_score > 0

    # Query SymbolMetric records with symbol relationship loaded
    stmt_sm = (
        select(SymbolMetric)
        .options(selectinload(SymbolMetric.symbol))
        .where(SymbolMetric.analysis_id == job.id)
    )
    res_sm = await test_db.execute(stmt_sm)
    symbol_metrics = res_sm.scalars().all()

    assert len(symbol_metrics) >= 3  # calculate_factorial, is_prime, startServer
    fact_sm = next(sm for sm in symbol_metrics if sm.symbol.name == "calculate_factorial")
    assert fact_sm.cyclomatic_complexity >= 3  # base 1 + if 1 + for 1 = 3
    assert fact_sm.lines_of_code > 5
