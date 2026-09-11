import ast
import uuid
from unittest.mock import MagicMock, patch
import pytest
from httpx import AsyncClient

from app.analyzers.base import ExtractedSymbol
from app.analyzers.javascript_analyzer import JavaScriptAnalyzer
from app.core.config import settings
from app.dependencies.extractors.js_ts_extractor import JsTsDependencyExtractor
from app.dependencies.extractors.python_extractor import PythonDependencyExtractor
from app.dependencies.graph import DirectedDependencyGraph
from app.health.calculator import HealthCalculator
from app.health.recommendations import RecommendationEngine
from app.metrics.base import FileMetrics, SymbolMetrics
from app.metrics.javascript_metrics import JavaScriptMetricsAnalyzer
from app.metrics.python_metrics import PythonMetricsAnalyzer
from app.models.analysis import AnalysisJob, AnalysisStatus
from app.models.repository import Repository
from app.rules.base import CodebaseIssue, IssueCategory, IssueSeverity
from app.services.clone_detector import CloneDetector
from app.services.file_discovery import DiscoveredFile
from app.workers.celery_app import celery_app


def test_celery_and_uvicorn_resource_settings():
    """Validates that Celery and Uvicorn resource bounding settings are properly configured."""
    assert settings.CELERY_WORKER_CONCURRENCY == 1
    assert settings.UVICORN_WORKERS == 1
    assert settings.MAX_CONCURRENT_ANALYSES == 2

    # Check Celery app config defaults
    conf = celery_app.conf
    assert conf.worker_concurrency == 1
    assert conf.worker_max_tasks_per_child == 10
    assert conf.worker_max_memory_per_child == 200000


@pytest.mark.asyncio
async def test_admission_control_rate_limiting(async_client: AsyncClient, test_db):
    """Test that admission control rejects new requests with HTTP 429 when max concurrent analyses are active."""
    # Create an active repository and 2 active jobs (equal to MAX_CONCURRENT_ANALYSES)
    repo = Repository(
        id=uuid.uuid4(),
        url="https://github.com/test-org/active-repo",
        name="active-repo",
        owner="test-org",
        default_branch="main",
    )
    test_db.add(repo)
    await test_db.commit()

    job1 = AnalysisJob(
        id=uuid.uuid4(),
        repository_id=repo.id,
        status=AnalysisStatus.CLONING.value,
        stage="cloning",
    )
    job2 = AnalysisJob(
        id=uuid.uuid4(),
        repository_id=repo.id,
        status=AnalysisStatus.QUEUED.value,
        stage="queued",
    )
    test_db.add_all([job1, job2])
    await test_db.commit()

    # Now attempt to submit another analysis
    response = await async_client.post(
        "/api/v1/repositories/analyze",
        json={"repository_url": "https://github.com/test-org/new-repo"},
    )

    assert response.status_code == 429
    data = response.json()
    assert "Maximum concurrent analysis capacity reached" in data["detail"]
    assert response.headers.get("retry-after") == "30"


def test_python_ast_reuse():
    """Verify that passing pre-parsed AST to Python metrics and dependency extractors avoids re-parsing."""
    code = """
import os
import sys

def compute(x):
    if x > 0:
        return x * 2
    return 0
"""
    file_path = "test_code.py"
    parsed_tree = ast.parse(code, filename=file_path)

    metrics_analyzer = PythonMetricsAnalyzer()
    dep_extractor = PythonDependencyExtractor()

    # Pass pre-parsed AST
    with patch("ast.parse") as mock_parse:
        metrics = metrics_analyzer.calculate(file_path, code, symbols=[], ast_tree=parsed_tree)
        assert metrics.total_lines > 0
        assert metrics.metric_status == "calculated"
        assert metrics.total_cyclomatic_complexity >= 2
        # ast.parse must NOT be called when ast_tree is provided
        mock_parse.assert_not_called()

    with patch("ast.parse") as mock_parse:
        deps = dep_extractor.extract(file_path, code, ast_tree=parsed_tree)
        assert len(deps) == 2
        target_mods = {d.target_module for d in deps}
        assert "os" in target_mods
        assert "sys" in target_mods
        # ast.parse must NOT be called when ast_tree is provided
        mock_parse.assert_not_called()


def test_js_ts_ast_reuse():
    """Verify that passing pre-parsed Tree-sitter tree to JS/TS metrics and extractors avoids re-parsing."""
    js_code = """
const path = require('path');
import express from 'express';

function handleRequest(req, res) {
    if (req.method === 'GET') {
        return res.send('OK');
    }
    return res.status(400).send('Bad');
}
"""
    file_path = "server.js"
    js_analyzer = JavaScriptAnalyzer()
    analysis_res = js_analyzer.analyze(file_path, js_code)
    assert analysis_res.ast_tree is not None

    js_metrics = JavaScriptMetricsAnalyzer()
    mock_parser = MagicMock()
    js_metrics._parser = mock_parser

    metrics = js_metrics.calculate(file_path, js_code, symbols=analysis_res.symbols, ast_tree=analysis_res.ast_tree)
    assert metrics.metric_status == "calculated"
    assert metrics.total_cyclomatic_complexity >= 2
    # mock_parser.parse must not be called because ast_tree was provided
    mock_parser.parse.assert_not_called()

    js_extractor = JsTsDependencyExtractor()
    mock_ext_parser = MagicMock()
    js_extractor._js_parser = mock_ext_parser

    deps = js_extractor.extract(file_path, js_code, ast_tree=analysis_res.ast_tree)
    assert len(deps) >= 2
    mock_ext_parser.parse.assert_not_called()


def test_clone_detector_cache_cleanup():
    """Verify that CloneDetector frees internal index caches after clone detection."""
    detector = CloneDetector(min_lines=3, min_tokens=5)
    files = {
        "file_a.py": "def foo():\n    a = 1\n    b = 2\n    return a + b\n",
        "file_b.py": "def bar():\n    a = 1\n    b = 2\n    return a + b\n",
    }

    result = detector.detect_clones(files)
    assert len(result.duplicates) >= 1

    # Internal caches must be cleared to avoid retaining heavy file token lists & indexes in memory
    assert len(detector._vocab) == 0
    assert detector._vocab_counter == 1


def test_recommendation_simulation_without_deepcopy():
    """Verify that RecommendationEngine simulation generates accurate recommendations without mutating input."""
    calc = HealthCalculator()
    rec_engine = RecommendationEngine(calc)

    fid = uuid.uuid4()
    fpath = "app/complex.py"
    df = DiscoveredFile(
        path=fpath,
        filename="complex.py",
        extension=".py",
        size_bytes=1000,
        line_count=200,
        language="Python",
        is_analyzable=True,
    )

    sm = SymbolMetrics(
        name="huge_handler",
        symbol_type="function",
        start_line=10,
        end_line=150,
        lines_of_code=140,
        cyclomatic_complexity=35,
        nesting_depth=5,
        parameter_count=3,
    )
    fm = FileMetrics(
        file_path=fpath,
        language="Python",
        total_lines=200,
        sloc=150,
        comment_lines=10,
        blank_lines=40,
        statement_count=100,
        maintainability_score=45.0,
        total_cyclomatic_complexity=35,
        average_cyclomatic_complexity=35.0,
        max_cyclomatic_complexity=35,
        symbols_metrics=[sm],
    )

    sym = ExtractedSymbol(
        name="huge_handler",
        symbol_type="function",
        start_line=10,
        start_column=0,
        end_line=150,
        end_column=0,
    )
    parsed_files_data = [{
        "df": df,
        "symbols": [sym],
        "symbols_metrics": [sm],
        "content": "",
    }]

    graph = DirectedDependencyGraph()
    graph.add_file_node(fid, fpath, "Python")

    issue = CodebaseIssue(
        id=uuid.uuid4(),
        rule_id="COMPLEX-001",
        rule_name="Critical Complexity",
        category=IssueCategory.COMPLEXITY.value,
        severity=IssueSeverity.CRITICAL.value,
        title="Critical Complexity",
        description="CC=35",
        file_id=fid,
        file_path=fpath,
        symbol_name="huge_handler",
        remediation_effort_minutes=90,
        metadata_json={
            "target_type": "symbol",
            "target_identifier": f"{fpath}::huge_handler",
        },
    )

    fmap = {fpath: fm}
    current_health = calc.compute(fmap, parsed_files_data, graph, [issue])

    recs = rec_engine.generate_recommendations(
        current_health=current_health,
        file_metrics_map=fmap,
        parsed_files_data=parsed_files_data,
        graph=graph,
        issues=[issue],
        max_recommendations=5,
    )

    assert len(recs) == 1
    rec = recs[0]
    assert rec.target_type == "symbol"
    assert rec.target_identifier == f"{fpath}::huge_handler"
    assert rec.estimated_score_recovery is not None
    assert rec.estimated_score_recovery > 0.0

    # Ensure input parsed_files_data was preserved intact
    assert len(parsed_files_data) == 1
    assert parsed_files_data[0]["symbols"][0].name == "huge_handler"
