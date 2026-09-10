from datetime import datetime, timezone
import pytest
from app.services.json_exporter import JsonExporter


def test_json_export_schema_and_fields():
    payload = JsonExporter.generate_payload(
        analysis_id="11111111-2222-3333-4444-555555555555",
        repository_url="https://github.com/example/repo",
        commit_hash="deadbeef",
        analysis_date=datetime(2026, 9, 8, 12, 0, 0, tzinfo=timezone.utc),
        health_summary={
            "overall_score": 88.5,
            "grade": "B",
            "maintainability_score": 85.0,
            "complexity_score": 90.0,
            "architecture_score": 92.0,
            "hygiene_score": 87.0,
        },
        quality_gate={
            "status": "PASSED",
            "passed": True,
            "total_conditions": 6,
        },
        hotspots=[
            {"rank": 1, "file_path": "main.py", "hotspot_score": 75.0},
        ],
        recommendations=[
            {"rank": 1, "rule_id": "ARCH-001", "estimated_delta_score": 3.2},
        ],
        issues_summary={"total": 5, "blocker": 0, "critical": 0},
        dependency_summary={"total_dependencies": 12, "total_cycles": 0},
        files_data=[{"path": "main.py", "sloc": 250}],
    )

    # 1. Non-negotiable schema version
    assert payload["schema_version"] == "1.0"
    assert payload["analysis_id"] == "11111111-2222-3333-4444-555555555555"

    # 2. Required sections
    assert "repository" in payload
    assert payload["repository"]["url"] == "https://github.com/example/repo"
    assert payload["repository"]["commit_hash"] == "deadbeef"

    assert "health" in payload
    assert payload["health"]["overall_score"] == 88.5

    assert "quality_gate" in payload
    assert payload["quality_gate"]["status"] == "PASSED"

    assert "hotspots" in payload
    assert len(payload["hotspots"]) == 1
    assert payload["hotspots"][0]["file_path"] == "main.py"

    assert "recommendations" in payload
    assert len(payload["recommendations"]) == 1

    assert "issue_summary" in payload
    assert "dependency_summary" in payload
    assert "file_intelligence" in payload
    assert "metadata" in payload
    assert payload["metadata"]["engine_version"] == "1.0.0"
