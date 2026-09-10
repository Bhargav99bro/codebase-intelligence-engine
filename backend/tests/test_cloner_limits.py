import os
import shutil
import tempfile
import pytest
from unittest.mock import patch

from app.core.config import settings
from app.services.cloner import ClonedRepository, calculate_dir_size_bytes
from app.services.file_discovery import FileDiscoveryLimitError, discover_files


def test_calculate_dir_size(tmp_path):
    f1 = tmp_path / "f1.txt"
    f2 = tmp_path / "f2.txt"
    f1.write_bytes(b"A" * 1024)
    f2.write_bytes(b"B" * 2048)

    size = calculate_dir_size_bytes(str(tmp_path))
    assert size == 3072


def test_file_count_limit_exceeded(tmp_path):
    # Create 5 files
    for i in range(5):
        (tmp_path / f"test_{i}.py").write_text(f"x = {i}\n")

    # Patch MAX_FILE_COUNT to 3
    with patch.object(settings, "MAX_FILE_COUNT", 3):
        with pytest.raises(FileDiscoveryLimitError, match="file count exceeds maximum allowed limit"):
            discover_files(str(tmp_path))


def test_workspace_cleanup():
    temp_dir = tempfile.mkdtemp(prefix="cie_test_cleanup_")
    test_file = os.path.join(temp_dir, "file.txt")
    with open(test_file, "w") as f:
        f.write("content")

    cloned = ClonedRepository(
        temp_dir=temp_dir,
        commit_hash="abc1234",
        commit_message="test",
        commit_author="test",
        default_branch="main",
    )

    assert os.path.exists(temp_dir)
    cloned.cleanup()
    assert not os.path.exists(temp_dir)
