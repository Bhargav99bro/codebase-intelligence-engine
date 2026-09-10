import uuid
import pytest

from app.dependencies.base import DependencyType, ExtractedDependency, ResolutionStatus
from app.dependencies.extractors.js_ts_extractor import JsTsDependencyExtractor
from app.dependencies.resolvers.js_ts_resolver import JsTsDependencyResolver


def test_js_extractor_es_imports_and_require():
    extractor = JsTsDependencyExtractor()
    code = """import express from 'express';
import { get, post as postHandler } from './routes';
const debug = require('./lib/debug');
const auth = require('basic-auth');
export { helper } from './utils';
"""
    deps = extractor.extract("src/index.js", code)
    assert len(deps) == 5

    # 1. import express from 'express'
    assert deps[0].target_module == "express"
    assert deps[0].dependency_type == DependencyType.IMPORT.value

    # 2. import { get, post } from './routes'
    assert deps[1].target_module == "./routes"
    assert deps[1].dependency_type == DependencyType.IMPORT.value
    assert "get" in deps[1].imported_symbols

    # 3. require('./lib/debug')
    assert deps[2].target_module == "./lib/debug"
    assert deps[2].dependency_type == DependencyType.REQUIRE.value

    # 4. require('basic-auth')
    assert deps[3].target_module == "basic-auth"
    assert deps[3].dependency_type == DependencyType.REQUIRE.value

    # 5. export { helper } from './utils'
    assert deps[4].target_module == "./utils"
    assert deps[4].dependency_type == DependencyType.RE_EXPORT.value


def test_ts_extractor_type_only_imports():
    extractor = JsTsDependencyExtractor()
    code = """import type { Request, Response } from 'express';
import { service } from './service';
export type { Config } from './types';
"""
    deps = extractor.extract("src/server.ts", code)
    assert len(deps) == 3

    assert deps[0].target_module == "express"
    assert deps[0].is_type_only is True

    assert deps[1].target_module == "./service"
    assert deps[1].is_type_only is False

    assert deps[2].target_module == "./types"
    assert deps[2].is_type_only is True


def test_js_ts_resolver_internal_builtins_and_packages():
    repo_files = {
        "src/index.ts": uuid.uuid4(),
        "src/routes.ts": uuid.uuid4(),
        "src/lib/debug.js": uuid.uuid4(),
        "src/components/index.tsx": uuid.uuid4(),
    }
    resolver = JsTsDependencyResolver(repo_files)

    # A. Relative extensionless import: ./routes -> src/routes.ts
    dep_routes = ExtractedDependency(
        source_file_path="src/index.ts",
        target_module="./routes",
        dependency_type="import",
        imported_symbols=["get"],
        line_number=2,
    )
    res_routes = resolver.resolve(dep_routes)
    assert res_routes.resolution_status == ResolutionStatus.INTERNAL.value
    assert res_routes.target_file_id == repo_files["src/routes.ts"]

    # B. Relative subfolder: ./lib/debug -> src/lib/debug.js
    dep_debug = ExtractedDependency(
        source_file_path="src/index.ts",
        target_module="./lib/debug",
        dependency_type="require",
        imported_symbols=["*"],
        line_number=3,
    )
    res_debug = resolver.resolve(dep_debug)
    assert res_debug.resolution_status == ResolutionStatus.INTERNAL.value
    assert res_debug.target_file_id == repo_files["src/lib/debug.js"]

    # C. Index resolution: ./components -> src/components/index.tsx
    dep_comp = ExtractedDependency(
        source_file_path="src/index.ts",
        target_module="./components",
        dependency_type="import",
        imported_symbols=["*"],
        line_number=4,
    )
    res_comp = resolver.resolve(dep_comp)
    assert res_comp.resolution_status == ResolutionStatus.INTERNAL.value
    assert res_comp.target_file_id == repo_files["src/components/index.tsx"]

    # D. Node built-in: fs and node:path
    dep_fs = ExtractedDependency(
        source_file_path="src/index.ts",
        target_module="fs",
        dependency_type="import",
        imported_symbols=["*"],
        line_number=1,
    )
    res_fs = resolver.resolve(dep_fs)
    assert res_fs.resolution_status == ResolutionStatus.EXTERNAL.value
    assert "built-in" in (res_fs.resolution_note or "").lower()

    dep_path = ExtractedDependency(
        source_file_path="src/index.ts",
        target_module="node:path",
        dependency_type="import",
        imported_symbols=["*"],
        line_number=2,
    )
    res_path = resolver.resolve(dep_path)
    assert res_path.resolution_status == ResolutionStatus.EXTERNAL.value

    # E. External npm package: express
    dep_pkg = ExtractedDependency(
        source_file_path="src/index.ts",
        target_module="express",
        dependency_type="import",
        imported_symbols=["*"],
        line_number=1,
    )
    res_pkg = resolver.resolve(dep_pkg)
    assert res_pkg.resolution_status == ResolutionStatus.EXTERNAL.value

    # F. Missing relative path -> unresolved
    dep_bad = ExtractedDependency(
        source_file_path="src/index.ts",
        target_module="./non_existent_file",
        dependency_type="import",
        imported_symbols=["*"],
        line_number=5,
    )
    res_bad = resolver.resolve(dep_bad)
    assert res_bad.resolution_status == ResolutionStatus.UNRESOLVED.value
