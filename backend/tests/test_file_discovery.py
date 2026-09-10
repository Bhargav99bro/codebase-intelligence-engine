import os
import tempfile
import pytest

from app.services.file_discovery import (
    discover_files,
    detect_language,
    count_lines,
    DEFAULT_IGNORED_DIRS,
)


def test_detect_language():
    assert detect_language("app.py", ".py") == "Python"
    assert detect_language("index.ts", ".ts") == "TypeScript"
    assert detect_language("Component.tsx", ".tsx") == "TypeScript"
    assert detect_language("server.js", ".js") == "JavaScript"
    assert detect_language("Main.java", ".java") == "Java"
    assert detect_language("main.go", ".go") == "Go"
    assert detect_language("lib.rs", ".rs") == "Rust"
    assert detect_language("index.html", ".html") == "HTML"
    assert detect_language("style.css", ".css") == "CSS"
    assert detect_language("data.json", ".json") == "JSON"
    assert detect_language("config.yaml", ".yaml") == "YAML"
    assert detect_language("README.md", ".md") == "Markdown"
    assert detect_language("Dockerfile", "") == "Dockerfile"
    assert detect_language("unknown.xyz", ".xyz") is None


def test_count_lines(tmp_path):
    sample_file = tmp_path / "sample.py"
    sample_file.write_text("line 1\nline 2\nline 3\n")
    assert count_lines(str(sample_file)) == 3

    empty_file = tmp_path / "empty.py"
    empty_file.write_text("")
    assert count_lines(str(empty_file)) == 0


def test_discover_files_hierarchy_and_filtering(tmp_path):
    # 1. Create standard source files
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "main.py").write_text("def hello():\n    print('world')\n")
    (src_dir / "app.ts").write_text("const x: number = 42;\nconsole.log(x);\n")
    (tmp_path / "README.md").write_text("# Test Project\nSome description\n")

    # 2. Create ignored directories and files inside them
    for ignored_dir_name in [".git", "node_modules", "__pycache__", ".venv", "dist", "build", "vendor"]:
        ign_dir = tmp_path / ignored_dir_name
        ign_dir.mkdir(exist_ok=True)
        (ign_dir / "ignored_file.py").write_text("secret_code = True\n")

    # 3. Create ignored binary / asset files in root
    (tmp_path / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 100)
    (tmp_path / "app.exe").write_bytes(b"MZ" + b"0" * 100)
    (tmp_path / "archive.zip").write_bytes(b"PK" + b"0" * 100)

    # Execute discovery
    result = discover_files(str(tmp_path))

    # Verify discovered files
    discovered_paths = [f.path for f in result.files]
    assert "src/main.py" in discovered_paths
    assert "src/app.ts" in discovered_paths
    assert "README.md" in discovered_paths

    # Verify ignored directories were NOT visited
    for path in discovered_paths:
        for ign in [".git", "node_modules", "__pycache__", ".venv", "dist", "build", "vendor"]:
            assert not path.startswith(ign)

    # Verify binary extensions were ignored
    assert "logo.png" not in discovered_paths
    assert "app.exe" not in discovered_paths
    assert "archive.zip" not in discovered_paths

    # Verify language detection and counts
    assert result.total_files == 3
    assert result.analyzable_files == 2  # main.py, app.ts (README.md is Markdown/documentation)
    assert result.total_lines > 0

    # Verify language distribution
    assert "Python" in result.language_distribution
    assert "TypeScript" in result.language_distribution
    total_pct = sum(result.language_distribution.values())
    assert 99.0 <= total_pct <= 101.0  # Should sum to approx 100%
