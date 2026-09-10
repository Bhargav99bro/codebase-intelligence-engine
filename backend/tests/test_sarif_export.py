import pytest
from app.services.sarif_exporter import SarifExporter, map_severity_to_sarif_level, sanitize_repo_path


def test_sanitize_repo_path():
    assert sanitize_repo_path(None) == "repository"
    assert sanitize_repo_path("") == "repository"

    # Docker temp repo path
    raw1 = "/tmp/cie_repos/cie_repo_12345/backend/app/main.py"
    assert sanitize_repo_path(raw1) == "backend/app/main.py"

    # Generic tmp path
    raw2 = "/tmp/abc123/src/index.ts"
    assert sanitize_repo_path(raw2) == "src/index.ts"

    # Windows style backslashes
    raw3 = "D:\\projects\\cie\\src\\utils.py"
    assert "/" in sanitize_repo_path(raw3)
    assert not sanitize_repo_path(raw3).startswith("D:")

    # Clean relative path
    assert sanitize_repo_path("src/core/router.py") == "src/core/router.py"


def test_map_severity_to_sarif_level():
    assert map_severity_to_sarif_level("blocker") == "error"
    assert map_severity_to_sarif_level("critical") == "error"
    assert map_severity_to_sarif_level("major") == "warning"
    assert map_severity_to_sarif_level("minor") == "note"
    assert map_severity_to_sarif_level("info") == "note"
    assert map_severity_to_sarif_level("unknown") == "warning"


def test_sarif_generator_structure_and_rule_integrity():
    mock_issues = [
        {
            "rule_id": "ARCH-001",
            "rule_name": "CyclicDependency",
            "severity": "critical",
            "title": "Circular dependency",
            "description": "Cycle found between A and B",
            "file_path": "/tmp/cie_repos/cie_repo_abc/app/services/a.py",
            "line_number": 12,
            "end_line_number": 15,
        },
        {
            "rule_id": "SEC-001",
            "rule_name": "HardcodedSecretPattern",
            "severity": "blocker",
            "title": "Hardcoded Secret",
            "description": "Found AWS access token",
            "file_path": "/tmp/cie_repos/cie_repo_abc/app/config.py",
            "line_number": 5,
            "end_line_number": 5,
        },
        {
            "rule_id": "CUSTOM-099",
            "rule_name": "CustomRule",
            "severity": "minor",
            "title": "Custom Issue",
            "description": "Custom notice",
            "file_path": "/tmp/cie_repos/cie_repo_abc/app/utils.py",
            "line_number": 42,
            "end_line_number": 43,
        },
    ]

    sarif = SarifExporter.generate_sarif(
        issues=mock_issues,
        repository_url="https://github.com/test/repo",
        commit_hash="abc12345",
    )

    # 1. Root structure
    assert sarif["version"] == "2.1.0"
    assert sarif["$schema"] == "https://json.schemastore.org/sarif-2.1.0.json"
    assert len(sarif["runs"]) == 1

    run = sarif["runs"][0]
    driver = run["tool"]["driver"]
    assert driver["name"] == "Codebase Intelligence Engine"

    # 2. Rule Integrity: all results ruleId MUST exist in driver.rules
    rule_ids_in_driver = {r["id"] for r in driver["rules"]}
    for res in run["results"]:
        assert res["ruleId"] in rule_ids_in_driver

    # 3. Path sanitization check: no /tmp host path in artifactLocation.uri
    for res in run["results"]:
        uri = res["locations"][0]["physicalLocation"]["artifactLocation"]["uri"]
        assert not uri.startswith("/tmp")
        assert not uri.startswith("cie_repo_")

    # 4. Result ordering check: deterministic sort by (file_path, start_line, rule_id)
    # config.py (app/config.py) should be first, then a.py (app/services/a.py), then utils.py (app/utils.py)
    uris = [r["locations"][0]["physicalLocation"]["artifactLocation"]["uri"] for r in run["results"]]
    assert uris == ["app/config.py", "app/services/a.py", "app/utils.py"]

    # 5. Level verification
    levels = [r["level"] for r in run["results"]]
    assert levels == ["error", "error", "note"]
