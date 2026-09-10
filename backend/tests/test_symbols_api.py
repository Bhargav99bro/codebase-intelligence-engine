import uuid
import pytest

from app.models.analysis import AnalysisJob, AnalysisStatus
from app.models.file import RepositoryFile
from app.models.repository import Repository
from app.models.symbol import Symbol


@pytest.mark.asyncio
async def test_get_analysis_symbols_endpoint(async_client, test_db):
    # Setup DB data
    repo = Repository(
        url="https://github.com/api-test/symbols-repo",
        owner="api-test",
        name="symbols-repo",
        default_branch="main",
    )
    test_db.add(repo)
    await test_db.flush()

    job = AnalysisJob(
        repository_id=repo.id,
        status=AnalysisStatus.COMPLETED.value,
        stage="completed",
        progress=100,
        message="Completed",
        total_symbols=3,
    )
    test_db.add(job)
    await test_db.flush()

    rf = RepositoryFile(
        analysis_id=job.id,
        path="src/service.py",
        filename="service.py",
        extension=".py",
        language="Python",
        parser_status="parsed",
        symbol_count=3,
    )
    test_db.add(rf)
    await test_db.flush()

    cls_sym = Symbol(
        analysis_id=job.id,
        file_id=rf.id,
        name="AuthService",
        symbol_type="class",
        qualified_name="src.service.AuthService",
        start_line=10,
        start_column=0,
        end_line=30,
        end_column=0,
        signature="class AuthService",
    )
    test_db.add(cls_sym)
    await test_db.flush()

    method_sym = Symbol(
        analysis_id=job.id,
        file_id=rf.id,
        name="login",
        symbol_type="method",
        qualified_name="src.service.AuthService.login",
        start_line=15,
        start_column=4,
        end_line=20,
        end_column=0,
        parent_symbol_id=cls_sym.id,
        signature="def login(self, username, password)",
    )
    test_db.add(method_sym)

    fn_sym = Symbol(
        analysis_id=job.id,
        file_id=rf.id,
        name="hash_password",
        symbol_type="function",
        qualified_name="src.service.hash_password",
        start_line=32,
        start_column=0,
        end_line=35,
        end_column=0,
        signature="def hash_password(password)",
    )
    test_db.add(fn_sym)
    await test_db.commit()

    # 1. Fetch all symbols
    res = await async_client.get(f"/api/v1/analyses/{job.id}/symbols")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3
    assert data["items"][0]["file_path"] == "src/service.py"

    # 2. Filter by symbol_type
    res_filtered = await async_client.get(f"/api/v1/analyses/{job.id}/symbols?symbol_type=class")
    assert res_filtered.status_code == 200
    data_filtered = res_filtered.json()
    assert data_filtered["total"] == 1
    assert data_filtered["items"][0]["name"] == "AuthService"

    # 3. Filter by search query
    res_search = await async_client.get(f"/api/v1/analyses/{job.id}/symbols?search=hash")
    assert res_search.status_code == 200
    data_search = res_search.json()
    assert data_search["total"] == 1
    assert data_search["items"][0]["name"] == "hash_password"

    # 4. Pagination
    res_page = await async_client.get(f"/api/v1/analyses/{job.id}/symbols?skip=0&limit=2")
    assert res_page.status_code == 200
    assert len(res_page.json()["items"]) == 2
    assert res_page.json()["total"] == 3

    # 5. Invalid UUID format
    res_bad = await async_client.get("/api/v1/analyses/not-a-uuid/symbols")
    assert res_bad.status_code == 400
