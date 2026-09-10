import logging
import posixpath
from typing import Dict, List, Optional, Set
import uuid

from app.dependencies.base import ExtractedDependency, ResolutionStatus, ResolvedDependency

logger = logging.getLogger(__name__)

NODE_BUILTINS: Set[str] = {
    "assert", "async_hooks", "buffer", "child_process", "cluster", "console",
    "constants", "crypto", "dgram", "diagnostics_channel", "dns", "domain",
    "events", "fs", "fs/promises", "http", "http2", "https", "inspector",
    "module", "net", "os", "path", "path/posix", "path/win32", "perf_hooks",
    "process", "punycode", "querystring", "readline", "readline/promises",
    "repl", "stream", "stream/consumers", "stream/promises", "stream/web",
    "string_decoder", "sys", "timers", "timers/promises", "tls", "trace_events",
    "tty", "url", "util", "util/types", "v8", "vm", "wasi", "worker_threads", "zlib",
}


class JsTsDependencyResolver:
    """Statically resolves JavaScript and TypeScript dependencies to internal files or external packages."""

    def __init__(self, repo_files: Dict[str, uuid.UUID]) -> None:
        self.repo_files: Dict[str, uuid.UUID] = {
            self._norm(p): fid for p, fid in repo_files.items()
        }

    @staticmethod
    def _norm(path: str) -> str:
        return path.replace("\\", "/").lstrip("/")

    def resolve(
        self,
        dep: ExtractedDependency,
        source_file_id: Optional[uuid.UUID] = None,
    ) -> ResolvedDependency:
        target = dep.target_module.strip()
        norm_source = self._norm(dep.source_file_path)

        # 1. Node.js built-ins (e.g. 'fs', 'node:fs', 'path')
        clean_target = target[5:] if target.startswith("node:") else target
        if clean_target in NODE_BUILTINS:
            return ResolvedDependency(
                source_file_path=dep.source_file_path,
                source_file_id=source_file_id,
                target_module=target,
                dependency_type=dep.dependency_type,
                imported_symbols=dep.imported_symbols,
                line_number=dep.line_number,
                resolution_status=ResolutionStatus.EXTERNAL.value,
                is_type_only=dep.is_type_only,
                resolution_note="Node.js built-in module",
            )

        # 2. Relative Imports: starts with '.' or '..'
        if target.startswith("./") or target.startswith("../") or target == "." or target == "..":
            source_dir = posixpath.dirname(norm_source)
            candidate_base = posixpath.normpath(posixpath.join(source_dir, target))
            matched = self._find_matching_repo_file(candidate_base)
            if matched:
                return ResolvedDependency(
                    source_file_path=dep.source_file_path,
                    source_file_id=source_file_id,
                    target_module=target,
                    dependency_type=dep.dependency_type,
                    imported_symbols=dep.imported_symbols,
                    line_number=dep.line_number,
                    resolution_status=ResolutionStatus.INTERNAL.value,
                    target_file_id=self.repo_files[matched],
                    target_file_path=matched,
                    is_type_only=dep.is_type_only,
                    resolution_note="Resolved internal relative import",
                )

            return ResolvedDependency(
                source_file_path=dep.source_file_path,
                source_file_id=source_file_id,
                target_module=target,
                dependency_type=dep.dependency_type,
                imported_symbols=dep.imported_symbols,
                line_number=dep.line_number,
                resolution_status=ResolutionStatus.UNRESOLVED.value,
                is_type_only=dep.is_type_only,
                resolution_note="Relative file path not found in repository",
            )

        # 3. Absolute path within repository (e.g. '/src/utils')
        if target.startswith("/"):
            candidate_base = posixpath.normpath(target.lstrip("/"))
            matched = self._find_matching_repo_file(candidate_base)
            if matched:
                return ResolvedDependency(
                    source_file_path=dep.source_file_path,
                    source_file_id=source_file_id,
                    target_module=target,
                    dependency_type=dep.dependency_type,
                    imported_symbols=dep.imported_symbols,
                    line_number=dep.line_number,
                    resolution_status=ResolutionStatus.INTERNAL.value,
                    target_file_id=self.repo_files[matched],
                    target_file_path=matched,
                    is_type_only=dep.is_type_only,
                    resolution_note="Resolved internal absolute import",
                )

        # 4. Check if bare module matches a repository file in 'src' or root (common in TS path aliases)
        matched_bare = self._find_matching_repo_file(target) or self._find_matching_repo_file(f"src/{target}")
        if matched_bare:
            return ResolvedDependency(
                source_file_path=dep.source_file_path,
                source_file_id=source_file_id,
                target_module=target,
                dependency_type=dep.dependency_type,
                imported_symbols=dep.imported_symbols,
                line_number=dep.line_number,
                resolution_status=ResolutionStatus.INTERNAL.value,
                target_file_id=self.repo_files[matched_bare],
                target_file_path=matched_bare,
                is_type_only=dep.is_type_only,
                resolution_note="Resolved internal module via path alias heuristic",
            )

        # 5. Third-party package import (e.g. 'express', 'lodash', '@types/node')
        return ResolvedDependency(
            source_file_path=dep.source_file_path,
            source_file_id=source_file_id,
            target_module=target,
            dependency_type=dep.dependency_type,
            imported_symbols=dep.imported_symbols,
            line_number=dep.line_number,
            resolution_status=ResolutionStatus.EXTERNAL.value,
            is_type_only=dep.is_type_only,
            resolution_note="External npm package",
        )

    def _find_matching_repo_file(self, candidate: str) -> Optional[str]:
        candidate = self._norm(candidate)

        # Direct exact match
        if candidate in self.repo_files:
            return candidate

        # Extensions to probe
        extensions = [".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".json"]
        for ext in extensions:
            test_path = f"{candidate}{ext}"
            if test_path in self.repo_files:
                return test_path

        # Directory index files to probe
        for ext in extensions:
            test_index = f"{candidate}/index{ext}"
            if test_index in self.repo_files:
                return test_index

        return None
