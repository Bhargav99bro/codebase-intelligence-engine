import logging
import posixpath
import sys
from typing import Dict, List, Optional, Set
import uuid

from app.dependencies.base import ExtractedDependency, ResolutionStatus, ResolvedDependency

logger = logging.getLogger(__name__)

# Standard library module names (sys.stdlib_module_names in Python 3.10+)
PYTHON_STDLIB_MODULES: Set[str] = getattr(
    sys,
    "stdlib_module_names",
    {
        "abc", "argparse", "array", "ast", "asyncio", "base64", "binascii", "bisect",
        "builtins", "calendar", "cmath", "collections", "concurrent", "configparser",
        "contextlib", "contextvars", "copy", "csv", "ctypes", "dataclasses", "datetime",
        "decimal", "difflib", "dis", "doctest", "email", "enum", "errno", "faulthandler",
        "filecmp", "fileinput", "fnmatch", "fractions", "functools", "gc", "getopt",
        "getpass", "gettext", "glob", "gzip", "hashlib", "heapq", "hmac", "html",
        "http", "idlelib", "imaplib", "importlib", "inspect", "io", "ipaddress",
        "itertools", "json", "keyword", "linecache", "locale", "logging", "lzma",
        "math", "mimetypes", "mmap", "multiprocessing", "netrc", "numbers", "operator",
        "os", "pathlib", "pdb", "pickle", "pkgutil", "platform", "plistlib", "poplib",
        "posix", "pprint", "profile", "pstats", "pty", "pwd", "py_compile", "pyclbr",
        "pydoc", "queue", "quopri", "random", "re", "readline", "reprlib", "resource",
        "sched", "secrets", "select", "selectors", "shelve", "shlex", "shutil",
        "signal", "site", "smtplib", "socket", "socketserver", "sqlite3", "ssl",
        "stat", "statistics", "string", "struct", "subprocess", "sys", "sysconfig",
        "tarfile", "tempfile", "termios", "textwrap", "threading", "time", "timeit",
        "tkinter", "token", "tokenize", "trace", "traceback", "tracemalloc", "tty",
        "types", "typing", "unicodedata", "unittest", "urllib", "uuid", "venv",
        "warnings", "wave", "weakref", "webbrowser", "xml", "xmlrpc", "zipfile",
        "zipimport", "zlib", "_thread",
    },
)


class PythonDependencyResolver:
    """Statically resolves Python imports to repository files or standard/third-party modules."""

    def __init__(self, repo_files: Dict[str, uuid.UUID]) -> None:
        """
        Args:
            repo_files: Mapping of normalized relative file paths (e.g. 'src/app/main.py')
                        to their database UUIDs.
        """
        # Normalize all repository file paths with forward slashes
        self.repo_files: Dict[str, uuid.UUID] = {
            self._norm(p): fid for p, fid in repo_files.items()
        }

        # Discover candidate root source directories (e.g. '', 'src', 'lib')
        self.source_roots: Set[str] = {""}
        for p in self.repo_files:
            parts = p.split("/")
            if len(parts) > 1:
                # Top-level directory could be a source root (e.g. 'src', 'backend')
                self.source_roots.add(parts[0])
                if len(parts) > 2 and parts[0] in ("src", "lib", "backend", "app"):
                    self.source_roots.add(f"{parts[0]}/{parts[1]}")

    @staticmethod
    def _norm(path: str) -> str:
        return path.replace("\\", "/").lstrip("/")

    def resolve(
        self,
        dep: ExtractedDependency,
        source_file_id: Optional[uuid.UUID] = None,
    ) -> ResolvedDependency:
        norm_source = self._norm(dep.source_file_path)

        # 1. Relative Import (level > 0)
        if dep.level > 0:
            return self._resolve_relative(dep, norm_source, source_file_id)

        # 2. Absolute Import (level == 0)
        return self._resolve_absolute(dep, norm_source, source_file_id)

    def _resolve_relative(
        self,
        dep: ExtractedDependency,
        norm_source: str,
        source_file_id: Optional[uuid.UUID],
    ) -> ResolvedDependency:
        source_dir = posixpath.dirname(norm_source)

        # Navigate up (level - 1) directories
        curr_dir = source_dir
        for _ in range(dep.level - 1):
            curr_dir = posixpath.dirname(curr_dir)

        mod_subpath = dep.target_module.replace(".", "/") if dep.target_module else ""
        candidate_base = posixpath.normpath(posixpath.join(curr_dir, mod_subpath)) if mod_subpath else curr_dir

        # Case A: candidate_base is a file or package directory
        matched = self._find_matching_repo_file(candidate_base)
        if matched:
            return ResolvedDependency(
                source_file_path=dep.source_file_path,
                source_file_id=source_file_id,
                target_module=dep.target_module or candidate_base,
                dependency_type=dep.dependency_type,
                imported_symbols=dep.imported_symbols,
                line_number=dep.line_number,
                resolution_status=ResolutionStatus.INTERNAL.value,
                target_file_id=self.repo_files[matched],
                target_file_path=matched,
                is_type_only=dep.is_type_only,
                resolution_note="Resolved relative internal import",
            )

        # Case B: from . import helper (where helper is a file in curr_dir)
        if not dep.target_module and dep.imported_symbols:
            for sym in dep.imported_symbols:
                sym_path = posixpath.normpath(posixpath.join(curr_dir, sym))
                matched_sym = self._find_matching_repo_file(sym_path)
                if matched_sym:
                    return ResolvedDependency(
                        source_file_path=dep.source_file_path,
                        source_file_id=source_file_id,
                        target_module=f".{sym}",
                        dependency_type=dep.dependency_type,
                        imported_symbols=dep.imported_symbols,
                        line_number=dep.line_number,
                        resolution_status=ResolutionStatus.INTERNAL.value,
                        target_file_id=self.repo_files[matched_sym],
                        target_file_path=matched_sym,
                        is_type_only=dep.is_type_only,
                        resolution_note="Resolved relative symbol import",
                    )

        return ResolvedDependency(
            source_file_path=dep.source_file_path,
            source_file_id=source_file_id,
            target_module=dep.target_module or ".",
            dependency_type=dep.dependency_type,
            imported_symbols=dep.imported_symbols,
            line_number=dep.line_number,
            resolution_status=ResolutionStatus.UNRESOLVED.value,
            is_type_only=dep.is_type_only,
            resolution_note="Relative target not found in repository files",
        )

    def _resolve_absolute(
        self,
        dep: ExtractedDependency,
        norm_source: str,
        source_file_id: Optional[uuid.UUID],
    ) -> ResolvedDependency:
        if not dep.target_module:
            return ResolvedDependency(
                source_file_path=dep.source_file_path,
                source_file_id=source_file_id,
                target_module="",
                dependency_type=dep.dependency_type,
                imported_symbols=dep.imported_symbols,
                line_number=dep.line_number,
                resolution_status=ResolutionStatus.UNRESOLVED.value,
                is_type_only=dep.is_type_only,
                resolution_note="Empty target module",
            )

        mod_rel_path = dep.target_module.replace(".", "/")

        # 1. Check direct match relative to all candidate source roots in the repository
        for root in sorted(self.source_roots, key=len, reverse=True):
            candidate = posixpath.join(root, mod_rel_path) if root else mod_rel_path
            matched = self._find_matching_repo_file(candidate)
            if matched:
                return ResolvedDependency(
                    source_file_path=dep.source_file_path,
                    source_file_id=source_file_id,
                    target_module=dep.target_module,
                    dependency_type=dep.dependency_type,
                    imported_symbols=dep.imported_symbols,
                    line_number=dep.line_number,
                    resolution_status=ResolutionStatus.INTERNAL.value,
                    target_file_id=self.repo_files[matched],
                    target_file_path=matched,
                    is_type_only=dep.is_type_only,
                    resolution_note=f"Resolved internal import under root '{root}'",
                )

        # 2. Check if first symbol in from-import matches a repository file (e.g. from app.models import user)
        if dep.imported_symbols:
            for sym in dep.imported_symbols:
                sub_candidate = f"{mod_rel_path}/{sym}"
                for root in self.source_roots:
                    cand = posixpath.join(root, sub_candidate) if root else sub_candidate
                    matched = self._find_matching_repo_file(cand)
                    if matched:
                        return ResolvedDependency(
                            source_file_path=dep.source_file_path,
                            source_file_id=source_file_id,
                            target_module=f"{dep.target_module}.{sym}",
                            dependency_type=dep.dependency_type,
                            imported_symbols=dep.imported_symbols,
                            line_number=dep.line_number,
                            resolution_status=ResolutionStatus.INTERNAL.value,
                            target_file_id=self.repo_files[matched],
                            target_file_path=matched,
                            is_type_only=dep.is_type_only,
                            resolution_note="Resolved internal symbol module",
                        )

        # 3. Check Python Standard Library
        top_pkg = dep.target_module.split(".")[0]
        if top_pkg in PYTHON_STDLIB_MODULES:
            return ResolvedDependency(
                source_file_path=dep.source_file_path,
                source_file_id=source_file_id,
                target_module=dep.target_module,
                dependency_type=dep.dependency_type,
                imported_symbols=dep.imported_symbols,
                line_number=dep.line_number,
                resolution_status=ResolutionStatus.EXTERNAL.value,
                is_type_only=dep.is_type_only,
                resolution_note="Python standard library module",
            )

        # 4. Third-party package import
        return ResolvedDependency(
            source_file_path=dep.source_file_path,
            source_file_id=source_file_id,
            target_module=dep.target_module,
            dependency_type=dep.dependency_type,
            imported_symbols=dep.imported_symbols,
            line_number=dep.line_number,
            resolution_status=ResolutionStatus.EXTERNAL.value,
            is_type_only=dep.is_type_only,
            resolution_note="External third-party dependency",
        )

    def _find_matching_repo_file(self, candidate_path: str) -> Optional[str]:
        """Checks for candidate.py, candidate/__init__.py, candidate.pyi in repo files."""
        candidate_path = self._norm(candidate_path)
        tests = [
            f"{candidate_path}.py",
            f"{candidate_path}/__init__.py",
            f"{candidate_path}.pyi",
            candidate_path if candidate_path.endswith((".py", ".pyi")) else "",
        ]
        for t in tests:
            if t and t in self.repo_files:
                return t
        return None
