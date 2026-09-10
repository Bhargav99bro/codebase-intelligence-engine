import uuid
import pytest

from app.dependencies.base import DependencyType, ExtractedDependency, ResolutionStatus
from app.dependencies.extractors.python_extractor import PythonDependencyExtractor
from app.dependencies.resolvers.python_resolver import PythonDependencyResolver


def test_python_extractor_basic_and_relative_imports():
    extractor = PythonDependencyExtractor()
    code = """import os
import sys as system
from math import sqrt, pi as PI
from .utils import helper
from ..core.database import get_db
from . import local_mod
"""
    deps = extractor.extract("app/services/user_service.py", code)
    assert len(deps) == 6

    # 1. import os
    assert deps[0].target_module == "os"
    assert deps[0].dependency_type == DependencyType.IMPORT.value
    assert deps[0].level == 0

    # 2. import sys as system
    assert deps[1].target_module == "sys"
    assert deps[1].imported_symbols == ["system"]

    # 3. from math import sqrt, pi
    assert deps[2].target_module == "math"
    assert deps[2].dependency_type == DependencyType.FROM_IMPORT.value
    assert set(deps[2].imported_symbols) == {"sqrt", "pi"}

    # 4. from .utils import helper (level 1)
    assert deps[3].target_module == "utils"
    assert deps[3].level == 1
    assert deps[3].imported_symbols == ["helper"]

    # 5. from ..core.database import get_db (level 2)
    assert deps[4].target_module == "core.database"
    assert deps[4].level == 2

    # 6. from . import local_mod
    assert deps[5].target_module == ""
    assert deps[5].level == 1
    assert deps[5].imported_symbols == ["local_mod"]


def test_python_extractor_syntax_error_isolation():
    extractor = PythonDependencyExtractor()
    broken_code = "import os\ndef broken_func(\n  invalid python!!"
    deps = extractor.extract("broken.py", broken_code)
    # Syntax error must not raise; returns empty list gracefully
    assert deps == []


def test_python_resolver_internal_and_external():
    repo_files = {
        "app/services/user_service.py": uuid.uuid4(),
        "app/services/utils.py": uuid.uuid4(),
        "app/core/database.py": uuid.uuid4(),
        "bottle.py": uuid.uuid4(),
    }
    resolver = PythonDependencyResolver(repo_files)

    # A. Relative import: from .utils import helper
    dep_rel = ExtractedDependency(
        source_file_path="app/services/user_service.py",
        target_module="utils",
        dependency_type="from_import",
        imported_symbols=["helper"],
        line_number=4,
        level=1,
    )
    res_rel = resolver.resolve(dep_rel, source_file_id=repo_files["app/services/user_service.py"])
    assert res_rel.resolution_status == ResolutionStatus.INTERNAL.value
    assert res_rel.target_file_id == repo_files["app/services/utils.py"]

    # B. Relative import: from ..core.database import get_db
    dep_rel2 = ExtractedDependency(
        source_file_path="app/services/user_service.py",
        target_module="core.database",
        dependency_type="from_import",
        imported_symbols=["get_db"],
        line_number=5,
        level=2,
    )
    res_rel2 = resolver.resolve(dep_rel2, source_file_id=repo_files["app/services/user_service.py"])
    assert res_rel2.resolution_status == ResolutionStatus.INTERNAL.value
    assert res_rel2.target_file_id == repo_files["app/core/database.py"]

    # C. Absolute internal import: import bottle
    dep_bottle = ExtractedDependency(
        source_file_path="app/services/user_service.py",
        target_module="bottle",
        dependency_type="import",
        imported_symbols=["bottle"],
        line_number=6,
        level=0,
    )
    res_bottle = resolver.resolve(dep_bottle)
    assert res_bottle.resolution_status == ResolutionStatus.INTERNAL.value
    assert res_bottle.target_file_id == repo_files["bottle.py"]

    # D. Standard library external import: import json
    dep_json = ExtractedDependency(
        source_file_path="app/services/user_service.py",
        target_module="json",
        dependency_type="import",
        imported_symbols=["json"],
        line_number=1,
        level=0,
    )
    res_json = resolver.resolve(dep_json)
    assert res_json.resolution_status == ResolutionStatus.EXTERNAL.value
    assert "standard library" in (res_json.resolution_note or "").lower()

    # E. Third party external import: import fastapi
    dep_fastapi = ExtractedDependency(
        source_file_path="app/services/user_service.py",
        target_module="fastapi",
        dependency_type="import",
        imported_symbols=["fastapi"],
        line_number=2,
        level=0,
    )
    res_fastapi = resolver.resolve(dep_fastapi)
    assert res_fastapi.resolution_status == ResolutionStatus.EXTERNAL.value

    # F. Relative import to non-existent file -> unresolved
    dep_missing = ExtractedDependency(
        source_file_path="app/services/user_service.py",
        target_module="nonexistent",
        dependency_type="from_import",
        imported_symbols=["missing"],
        line_number=10,
        level=1,
    )
    res_missing = resolver.resolve(dep_missing)
    assert res_missing.resolution_status == ResolutionStatus.UNRESOLVED.value
