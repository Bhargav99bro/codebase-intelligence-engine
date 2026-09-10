import uuid
import pytest
from app.analyzers.base import ExtractedSymbol
from app.metrics.base import FileMetrics
from app.services.file_discovery import DiscoveredFile
from app.rules.base import RuleContext
from app.rules.maintainability_rules import (
    PoorMaintainabilityRule,
    UndocumentedPublicAPIRule,
    VeryLowMaintainabilityRule,
)


def make_maint_context(file_metrics_map=None, parsed_files_data=None, file_id_map=None):
    return RuleContext(
        parsed_files_data=parsed_files_data or [],
        file_metrics_map=file_metrics_map or {},
        graph=None,
        file_id_map=file_id_map or {},
    )


def test_very_low_maintainability_rule():
    rule = VeryLowMaintainabilityRule()
    fpath = "legacy.py"
    fid = uuid.uuid4()
    fm = FileMetrics(
        file_path=fpath,
        language="Python",
        total_lines=600,
        sloc=500,
        comment_lines=10,
        blank_lines=90,
        statement_count=350,
        maintainability_score=32.5,
        total_cyclomatic_complexity=45,
        average_cyclomatic_complexity=5.0,
        max_cyclomatic_complexity=15,
        symbols_metrics=[],
    )

    ctx = make_maint_context(
        file_metrics_map={fpath: fm},
        file_id_map={fpath: fid},
    )
    issues = rule.evaluate(ctx)

    assert len(issues) == 1
    iss = issues[0]
    assert iss.rule_id == "MAINT-001"
    assert iss.severity == "critical"
    assert iss.metadata_json["maintainability_score"] == 32.5


def test_poor_maintainability_rule():
    rule = PoorMaintainabilityRule()
    fpath = "moderate.py"
    fid = uuid.uuid4()
    fm = FileMetrics(
        file_path=fpath,
        language="Python",
        total_lines=300,
        sloc=220,
        comment_lines=25,
        blank_lines=55,
        statement_count=160,
        maintainability_score=48.0,
        total_cyclomatic_complexity=22,
        average_cyclomatic_complexity=3.0,
        max_cyclomatic_complexity=7,
        symbols_metrics=[],
    )

    ctx = make_maint_context(
        file_metrics_map={fpath: fm},
        file_id_map={fpath: fid},
    )
    issues = rule.evaluate(ctx)

    assert len(issues) == 1
    iss = issues[0]
    assert iss.rule_id == "MAINT-002"
    assert iss.severity == "major"
    assert iss.metadata_json["maintainability_score"] == 48.0


def test_undocumented_public_api_rule():
    rule = UndocumentedPublicAPIRule()
    fpath = "api.py"
    fid = uuid.uuid4()
    df = DiscoveredFile(
        path=fpath,
        filename="api.py",
        extension=".py",
        size_bytes=500,
        line_count=40,
        language="Python",
        is_analyzable=True,
    )
    sym_undoc = ExtractedSymbol(
        name="public_handler",
        symbol_type="function",
        start_line=10,
        start_column=0,
        end_line=25,
        end_column=0,
        metadata_json={},
    )
    sym_doc = ExtractedSymbol(
        name="documented_handler",
        symbol_type="function",
        start_line=26,
        start_column=0,
        end_line=35,
        end_column=0,
        metadata_json={"docstring": "Handles the request cleanly."},
    )
    sym_private = ExtractedSymbol(
        name="_private_helper",
        symbol_type="function",
        start_line=36,
        start_column=0,
        end_line=40,
        end_column=0,
        metadata_json={},
    )

    parsed_files_data = [{
        "df": df,
        "symbols": [sym_undoc, sym_doc, sym_private],
        "symbols_metrics": [],
        "parser_status": "success",
        "parser_error": None,
        "symbol_count": 3,
        "content": "",
    }]

    ctx = make_maint_context(
        parsed_files_data=parsed_files_data,
        file_id_map={fpath: fid},
    )
    issues = rule.evaluate(ctx)

    assert len(issues) == 1
    iss = issues[0]
    assert iss.rule_id == "MAINT-003"
    assert iss.symbol_name == "public_handler"
    assert iss.severity == "minor"
