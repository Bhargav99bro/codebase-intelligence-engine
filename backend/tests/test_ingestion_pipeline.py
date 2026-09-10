import subprocess
import tempfile
import uuid
from unittest.mock import patch
import pytest

from app.models.analysis import AnalysisJob, AnalysisStatus
from app.models.file import RepositoryFile
from app.models.repository import Repository
from app.services.cloner import ClonedRepository
from app.services.ingestion_orchestrator import execute_ingestion_pipeline


@pytest.fixture
def local_git_repo(tmp_path):
    """Creates a local mock git repository for pipeline testing."""
    repo_dir = tmp_path / "mock_repo"
    repo_dir.mkdir()

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "tester@example.com"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Tester"], cwd=repo_dir, check=True, capture_output=True)

    # Add source files
    src_dir = repo_dir / "src"
    src_dir.mkdir()
    (src_dir / "app.py").write_text("def run():\n    print('Running app')\n    return 42\n")
    (src_dir / "index.ts").write_text("export const PI: number = 3.14159;\n")
    (repo_dir / "README.md").write_text("# Mock Ingestion Repo\n")

    # Add vendor / ignored directory
    vendor_dir = repo_dir / "vendor"
    vendor_dir.mkdir()
    (vendor_dir / "ignored.py").write_text("ignore_me = True\n")

    # Commit
    subprocess.run(["git", "add", "."], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial mock commit"], cwd=repo_dir, check=True, capture_output=True)

    return repo_dir


@pytest.mark.asyncio
async def test_full_ingestion_pipeline_execution(test_db, local_git_repo):
    """Integration test verifying end-to-end repository ingestion pipeline and persistence."""
    # 1. Setup repository and job in database
    repo = Repository(
        url="https://github.com/mock-org/mock-repo",
        owner="mock-org",
        name="mock-repo",
        default_branch="main",
    )
    test_db.add(repo)
    await test_db.flush()

    job = AnalysisJob(
        repository_id=repo.id,
        status=AnalysisStatus.QUEUED.value,
        stage="queued",
        progress=0,
        message="Queued for test",
    )
    test_db.add(job)
    await test_db.commit()

    # 2. Mock clone_repository to return ClonedRepository pointing to local_git_repo without deleting it
    cloned_wrapper = ClonedRepository(
        temp_dir=str(local_git_repo),
        commit_hash="deadbeef12345678",
        commit_message="Initial mock commit",
        commit_author="Tester <tester@example.com>",
        default_branch="main",
    )

    with patch("app.services.ingestion_orchestrator.clone_repository") as mock_clone, \
         patch.object(cloned_wrapper, "cleanup") as mock_cleanup, \
         patch("app.services.ingestion_orchestrator.AsyncSessionLocal") as mock_session_local:

        mock_clone.return_value = cloned_wrapper

        # Ensure orchestrator uses our test_db session
        class MockSessionContext:
            async def __aenter__(self):
                return test_db
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

        mock_session_local.side_effect = lambda: MockSessionContext()

        # Execute pipeline
        await execute_ingestion_pipeline(str(job.id))

        # Assert cleanup was called
        assert mock_cleanup.called

    # 3. Verify job state after ingestion
    await test_db.refresh(job)
    assert job.status == AnalysisStatus.COMPLETED.value
    assert job.stage == "completed"
    assert job.progress == 100
    assert job.commit_hash == "deadbeef12345678"
    assert job.commit_author == "Tester <tester@example.com>"
    assert job.total_files == 3  # app.py, index.ts, README.md (vendor is ignored)
    assert job.analyzable_files == 2
    assert "Python" in job.language_distribution
    assert "TypeScript" in job.language_distribution
    assert job.completed_at is not None
