import subprocess
from unittest.mock import patch
import uuid
import pytest
from sqlalchemy import select

from app.models.analysis import AnalysisJob, AnalysisStatus
from app.models.dependency import Dependency, FileDependencyMetric
from app.models.file import RepositoryFile
from app.models.repository import Repository
from app.services.cloner import ClonedRepository
from app.services.ingestion_orchestrator import execute_ingestion_pipeline


@pytest.fixture
def dep_pipeline_repo(tmp_path):
    """Creates a local mock git repo with Python and TypeScript dependencies."""
    repo_dir = tmp_path / "dep_repo"
    repo_dir.mkdir()

    subprocess.run(["git", "init"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "dev@example.com"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "DepDev"], cwd=repo_dir, check=True, capture_output=True)

    src_dir = repo_dir / "src"
    src_dir.mkdir()

    # 1. config.py
    (src_dir / "config.py").write_text("""import os
APP_ENV = os.getenv("APP_ENV", "development")
""")

    # 2. service.py (imports config.py)
    (src_dir / "service.py").write_text("""from .config import APP_ENV
import json

def get_status():
    return {"env": APP_ENV}
""")

    # 3. broken.py (syntax error for fault isolation)
    (src_dir / "broken.py").write_text("""def unclosed_parenthesis(
    this is invalid python code!
""")

    # 4. app.ts (imports express and local types)
    (src_dir / "types.ts").write_text("""export interface User {
    id: string;
    name: string;
}
""")

    (src_dir / "app.ts").write_text("""import type { User } from './types';
import express from 'express';

export const app = express();
""")

    subprocess.run(["git", "add", "."], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit for dependency pipeline"], cwd=repo_dir, check=True, capture_output=True)

    return repo_dir


@pytest.mark.asyncio
async def test_dependency_pipeline_execution(test_db, dep_pipeline_repo):
    """Verifies that Stage 6 executes, isolates syntax error, and populates dependencies table."""
    repo = Repository(
        id=uuid.uuid4(),
        url="https://github.com/dep-pipeline/repo",
        owner="dep-pipeline",
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
        temp_dir=str(dep_pipeline_repo),
        commit_hash="c0ffee9876543210",
        commit_message="Initial commit for dependency pipeline",
        commit_author="DepDev <dev@example.com>",
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
    assert job.dependency_summary is not None

    summary = job.dependency_summary
    assert summary["total_dependencies"] > 0
    assert summary["internal_dependencies"] >= 2  # service -> config, app -> types
    assert summary["external_dependencies"] >= 2  # os, json, express

    # Check dependencies table records
    stmt_deps = select(Dependency).where(Dependency.analysis_id == job.id)
    res_deps = await test_db.execute(stmt_deps)
    deps = res_deps.scalars().all()
    assert len(deps) >= 4

    # Verify service -> config internal dependency
    svc_to_cfg = [d for d in deps if "config" in d.target_module and d.resolution_status == "internal"]
    assert len(svc_to_cfg) >= 1
    assert svc_to_cfg[0].target_file_id is not None

    # Check file_dependency_metrics table records
    stmt_fdm = select(FileDependencyMetric).where(FileDependencyMetric.analysis_id == job.id)
    res_fdm = await test_db.execute(stmt_fdm)
    metrics = res_fdm.scalars().all()
    assert len(metrics) == 5  # config.py, service.py, broken.py, types.ts, app.ts
