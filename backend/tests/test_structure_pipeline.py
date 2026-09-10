import subprocess
import uuid
from unittest.mock import patch
import pytest
from sqlalchemy import select

from app.models.analysis import AnalysisJob, AnalysisStatus
from app.models.file import RepositoryFile
from app.models.repository import Repository
from app.models.symbol import Symbol
from app.services.cloner import ClonedRepository
from app.services.ingestion_orchestrator import execute_ingestion_pipeline


@pytest.fixture
def structure_git_repo(tmp_path):
    """Creates a local mock git repository containing Python, JS, TS, and a broken file for error isolation."""
    repo_dir = tmp_path / "structure_repo"
    repo_dir.mkdir()

    subprocess.run(["git", "init"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "dev@example.com"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Developer"], cwd=repo_dir, check=True, capture_output=True)

    src_dir = repo_dir / "src"
    src_dir.mkdir()

    # 1. good.py: Class with methods and function
    (src_dir / "good.py").write_text("""
class UserService:
    def __init__(self, db_url: str):
        self.db_url = db_url

    async def get_user(self, user_id: int) -> dict:
        return {"id": user_id}

def calculate_hash(data: str) -> str:
    return data
""")

    # 2. broken.py: Invalid syntax file to test failure isolation
    (src_dir / "broken.py").write_text("""
def broken_syntax(x, y:
    return x +
""")

    # 3. another_good.py: Valid python file
    (src_dir / "another_good.py").write_text("""
import os
import sys

def helper():
    return True
""")

    # 4. service.ts: TypeScript interface and class
    (src_dir / "service.ts").write_text("""
export interface Config {
    port: number;
}

export class Server {
    start(): void {}
}
""")

    # 5. README.md: Non-code file (unsupported parser)
    (repo_dir / "README.md").write_text("# Project Title\n")

    subprocess.run(["git", "add", "."], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Structure test commit"], cwd=repo_dir, check=True, capture_output=True)

    return repo_dir


@pytest.mark.asyncio
async def test_structure_analysis_pipeline_and_error_isolation(test_db, structure_git_repo):
    """Verifies that Phase 3 extracts symbols, isolates broken files, and persists everything."""
    # 1. Setup repository and job
    repo = Repository(
        url="https://github.com/test-org/structure-repo",
        owner="test-org",
        name="structure-repo",
        default_branch="main",
    )
    test_db.add(repo)
    await test_db.flush()

    job = AnalysisJob(
        repository_id=repo.id,
        status=AnalysisStatus.QUEUED.value,
        stage="queued",
        progress=0,
        message="Queued for structural analysis",
    )
    test_db.add(job)
    await test_db.commit()

    # 2. Mock clone_repository
    cloned_wrapper = ClonedRepository(
        temp_dir=str(structure_git_repo),
        commit_hash="abc1234567890",
        commit_message="Structure test commit",
        commit_author="Developer <dev@example.com>",
        default_branch="main",
    )

    with patch("app.services.ingestion_orchestrator.clone_repository") as mock_clone, \
         patch.object(cloned_wrapper, "cleanup") as mock_cleanup, \
         patch("app.services.ingestion_orchestrator.AsyncSessionLocal") as mock_session_local:

        mock_clone.return_value = cloned_wrapper

        class MockSessionContext:
            async def __aenter__(self):
                return test_db
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

        mock_session_local.side_effect = lambda: MockSessionContext()

        # Execute Phase 3 pipeline
        await execute_ingestion_pipeline(str(job.id))
        assert mock_cleanup.called

    # 3. Verify job finalized successfully despite broken.py
    await test_db.refresh(job)
    assert job.status == AnalysisStatus.COMPLETED.value
    assert job.stage == "completed"
    assert job.progress == 100
    assert job.total_files == 5
    assert job.analyzable_files == 4  # good.py, broken.py, another_good.py, service.ts
    assert job.total_symbols > 0
    assert "class" in job.symbol_distribution
    assert "function" in job.symbol_distribution
    assert "method" in job.symbol_distribution
    assert "import" in job.symbol_distribution
    assert "interface" in job.symbol_distribution

    # 4. Verify per-file status & failure isolation
    files_stmt = select(RepositoryFile).where(RepositoryFile.analysis_id == job.id)
    files_res = await test_db.execute(files_stmt)
    files = files_res.scalars().all()

    file_status_map = {f.filename: f.parser_status for f in files}
    assert file_status_map["good.py"] == "parsed"
    assert file_status_map["another_good.py"] == "parsed"
    assert file_status_map["service.ts"] == "parsed"
    assert file_status_map["broken.py"] == "failed"
    assert file_status_map["README.md"] == "unsupported"

    broken_file = [f for f in files if f.filename == "broken.py"][0]
    assert broken_file.parser_error is not None
    assert "SyntaxError" in broken_file.parser_error
    assert broken_file.symbol_count == 0

    # 5. Verify database symbol persistence and parent-child nesting
    symbols_stmt = select(Symbol).where(Symbol.analysis_id == job.id)
    symbols_res = await test_db.execute(symbols_stmt)
    symbols = symbols_res.scalars().all()
    assert len(symbols) == job.total_symbols

    # Verify parent-child relationship for UserService -> __init__ and get_user
    user_service_cls = [s for s in symbols if s.name == "UserService" and s.symbol_type == "class"][0]
    user_methods = [s for s in symbols if s.parent_symbol_id == user_service_cls.id]
    assert len(user_methods) == 2
    method_names = [m.name for m in user_methods]
    assert "__init__" in method_names
    assert "get_user" in method_names

    # Verify TypeScript interface symbol
    ts_interface = [s for s in symbols if s.name == "Config" and s.symbol_type == "interface"][0]
    assert ts_interface.start_line == 2
