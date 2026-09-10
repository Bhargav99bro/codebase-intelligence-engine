import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from app.core.config import settings

logger = logging.getLogger(__name__)


class FileDiscoveryLimitError(Exception):
    """Raised when repository exceeds file count or size constraints."""
    pass


# Directory names to completely skip
DEFAULT_IGNORED_DIRS: Set[str] = {
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "dist",
    "build",
    "coverage",
    ".next",
    ".nuxt",
    "target",
    "vendor",
    ".turbo",
    ".gradle",
    ".idea",
    ".vscode",
    "bin",
    "obj",
    ".tox",
    "eggs",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".cache",
    "out",
}

# File extensions to ignore (binaries, multimedia, archives, documents)
DEFAULT_IGNORED_EXTENSIONS: Set[str] = {
    # Binaries & compiled artifacts
    ".exe", ".dll", ".so", ".dylib", ".bin", ".pyc", ".pyo", ".pyd",
    ".class", ".jar", ".war", ".wasm", ".o", ".obj", ".a", ".lib",
    # Images & icons
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".webp", ".bmp", ".tiff",
    # Multimedia
    ".mp4", ".mov", ".avi", ".mkv", ".mp3", ".wav", ".flac",
    # Archives
    ".zip", ".tar", ".gz", ".7z", ".rar", ".bz2", ".tgz",
    # Documents
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    # Fonts
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
}

# Extension to Language mapping
EXTENSION_LANGUAGE_MAP: Dict[str, str] = {
    ".py": "Python",
    ".pyi": "Python",
    ".js": "JavaScript",
    ".mjs": "JavaScript",
    ".cjs": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".mts": "TypeScript",
    ".cts": "TypeScript",
    ".tsx": "TypeScript",
    ".java": "Java",
    ".c": "C",
    ".h": "C",
    ".cpp": "C++",
    ".cc": "C++",
    ".cxx": "C++",
    ".hpp": "C++",
    ".hh": "C++",
    ".hxx": "C++",
    ".go": "Go",
    ".rs": "Rust",
    ".html": "HTML",
    ".htm": "HTML",
    ".css": "CSS",
    ".scss": "CSS",
    ".sass": "CSS",
    ".less": "CSS",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".md": "Markdown",
    ".markdown": "Markdown",
    ".sh": "Shell",
    ".bash": "Shell",
    ".sql": "SQL",
    ".rb": "Ruby",
    ".php": "PHP",
    ".kt": "Kotlin",
    ".swift": "Swift",
}

# Special filename mappings
SPECIAL_FILENAMES: Dict[str, str] = {
    "dockerfile": "Dockerfile",
    "makefile": "Makefile",
    "gemfile": "Ruby",
    "cmakelists.txt": "CMake",
}


@dataclass
class DiscoveredFile:
    path: str
    filename: str
    extension: str
    language: Optional[str]
    size_bytes: int
    line_count: Optional[int]
    is_analyzable: bool


@dataclass
class FileDiscoveryResult:
    files: List[DiscoveredFile]
    total_files: int
    analyzable_files: int
    total_lines: int
    total_bytes: int
    language_distribution: Dict[str, float]


def detect_language(filename: str, extension: str) -> Optional[str]:
    """Detects programming language from filename and extension."""
    lower_fn = filename.lower()
    if lower_fn in SPECIAL_FILENAMES:
        return SPECIAL_FILENAMES[lower_fn]
    return EXTENSION_LANGUAGE_MAP.get(extension.lower())


def count_lines(filepath: str) -> Optional[int]:
    """Safely and efficiently counts the lines in a text file."""
    try:
        count = 0
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                count += chunk.count(b"\n")
        return count
    except Exception:
        return None


def discover_files(workspace_root: str) -> FileDiscoveryResult:
    """Recursively discovers files in a workspace while enforcing security and resource limits."""
    canonical_root = os.path.realpath(workspace_root)
    discovered: List[DiscoveredFile] = []

    total_bytes = 0
    total_lines = 0
    analyzable_count = 0
    language_line_counts: Dict[str, int] = {}

    for root, dirs, files in os.walk(canonical_root, topdown=True, followlinks=False):
        # Filter out ignored directories in-place to prevent traversing into them
        dirs[:] = [d for d in dirs if d.lower() not in DEFAULT_IGNORED_DIRS and not d.startswith(".git")]

        for filename in files:
            # Check file count quota
            if len(discovered) >= settings.MAX_FILE_COUNT:
                raise FileDiscoveryLimitError(
                    f"Repository file count exceeds maximum allowed limit of {settings.MAX_FILE_COUNT} files."
                )

            full_path = os.path.join(root, filename)

            # Security check: verify the file is not a symlink escaping the workspace root
            canonical_path = os.path.realpath(full_path)
            if not canonical_path.startswith(canonical_root):
                logger.warning("Skipping symlink escaping workspace root: %s -> %s", full_path, canonical_path)
                continue

            try:
                size = os.path.getsize(canonical_path)
            except (OSError, FileNotFoundError):
                continue

            _, ext = os.path.splitext(filename)
            ext_lower = ext.lower()

            # Skip explicitly ignored file extensions
            if ext_lower in DEFAULT_IGNORED_EXTENSIONS:
                continue

            # Relative path from repository root (using forward slashes for cross-platform consistency)
            rel_path = os.path.relpath(canonical_path, canonical_root).replace("\\", "/")

            # Detect language
            language = detect_language(filename, ext_lower)
            is_analyzable = language is not None and language not in ["Markdown"]

            # Calculate line counts for analyzable or readable files under size threshold
            line_count = None
            if size <= settings.MAX_SINGLE_FILE_SIZE_BYTES:
                line_count = count_lines(canonical_path)

            if line_count is not None:
                total_lines += line_count

            total_bytes += size
            if is_analyzable:
                analyzable_count += 1
                if language and line_count:
                    language_line_counts[language] = language_line_counts.get(language, 0) + line_count

            discovered.append(
                DiscoveredFile(
                    path=rel_path,
                    filename=filename,
                    extension=ext_lower,
                    language=language,
                    size_bytes=size,
                    line_count=line_count,
                    is_analyzable=is_analyzable,
                )
            )

    # Calculate language distribution percentages based on lines of code
    total_analyzable_lines = sum(language_line_counts.values())
    language_distribution: Dict[str, float] = {}

    if total_analyzable_lines > 0:
        for lang, count in language_line_counts.items():
            pct = round((count / total_analyzable_lines) * 100.0, 1)
            language_distribution[lang] = pct
    elif analyzable_count > 0:
        # Fallback: distribute by file count if line counts are unavailable
        lang_file_counts: Dict[str, int] = {}
        for f in discovered:
            if f.is_analyzable and f.language:
                lang_file_counts[f.language] = lang_file_counts.get(f.language, 0) + 1
        for lang, count in lang_file_counts.items():
            language_distribution[lang] = round((count / analyzable_count) * 100.0, 1)

    return FileDiscoveryResult(
        files=discovered,
        total_files=len(discovered),
        analyzable_files=analyzable_count,
        total_lines=total_lines,
        total_bytes=total_bytes,
        language_distribution=language_distribution,
    )
