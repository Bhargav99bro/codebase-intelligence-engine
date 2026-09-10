import logging
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from app.core.config import settings
from app.services.url_validator import ValidatedRepositoryUrl

logger = logging.getLogger(__name__)


class RepositoryCloningError(Exception):
    """Raised when repository cloning or resource quota verification fails."""
    pass


@dataclass
class ClonedRepository:
    temp_dir: str
    commit_hash: Optional[str]
    commit_message: Optional[str]
    commit_author: Optional[str]
    default_branch: str
    commit_date: Optional[datetime] = None

    def cleanup(self) -> None:
        """Removes the temporary workspace directory."""
        if os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir, ignore_errors=True)
                logger.info("Cleaned up workspace at %s", self.temp_dir)
            except Exception as exc:
                logger.warning("Failed to remove temporary workspace %s: %s", self.temp_dir, exc)


def calculate_dir_size_bytes(directory: str) -> int:
    """Calculates total size of all files in a directory in bytes."""
    total_size = 0
    for root, _, files in os.walk(directory):
        for f in files:
            fp = os.path.join(root, f)
            try:
                if not os.path.islink(fp):
                    total_size += os.path.getsize(fp)
            except (OSError, FileNotFoundError):
                continue
    return total_size


def clone_repository(
    validated_url: ValidatedRepositoryUrl,
    custom_target_dir: Optional[str] = None,
) -> ClonedRepository:
    """Clones a GitHub repository into an isolated temporary workspace.

    Enforces:
    - Shallow clone (--depth 1 --single-branch)
    - Timeout limit (settings.CLONE_TIMEOUT_SECONDS)
    - Maximum directory size quota (settings.MAX_REPO_SIZE_MB)
    - No shell command injection (shell=False)
    """
    if custom_target_dir:
        temp_dir = custom_target_dir
        os.makedirs(temp_dir, exist_ok=True)
    else:
        # Create unique temporary directory
        os.makedirs(settings.ANALYSIS_STORAGE_PATH, exist_ok=True)
        temp_dir = tempfile.mkdtemp(prefix="cie_repo_", dir=settings.ANALYSIS_STORAGE_PATH)

    logger.info("Initiating shallow clone for %s into %s", validated_url.url, temp_dir)

    # Controlled git arguments (NEVER shell=True)
    clone_cmd_100 = [
        "git",
        "-c",
        "http.postBuffer=524288000",
        "clone",
        "--depth",
        "100",
        "--single-branch",
        validated_url.url,
        temp_dir,
    ]
    clone_cmd_1 = [
        "git",
        "-c",
        "http.postBuffer=524288000",
        "clone",
        "--depth",
        "1",
        "--single-branch",
        validated_url.url,
        temp_dir,
    ]

    max_attempts = 3
    last_err = ""

    for attempt in range(1, max_attempts + 1):
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
        os.makedirs(temp_dir, exist_ok=True)

        cmd_to_run = clone_cmd_100 if attempt <= 2 else clone_cmd_1
        try:
            result = subprocess.run(
                cmd_to_run,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=settings.CLONE_TIMEOUT_SECONDS,
                shell=False,
            )

            if result.returncode == 0:
                last_err = ""
                break

            # If depth 100 failed on attempt 1, try depth 1 immediately as fallback
            if cmd_to_run == clone_cmd_100:
                shutil.rmtree(temp_dir, ignore_errors=True)
                os.makedirs(temp_dir, exist_ok=True)
                result_fb = subprocess.run(
                    clone_cmd_1,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=settings.CLONE_TIMEOUT_SECONDS,
                    shell=False,
                )
                if result_fb.returncode == 0:
                    last_err = ""
                    break

            last_err = result.stderr.strip()
            shutil.rmtree(temp_dir, ignore_errors=True)
            if "not found" in last_err.lower() or "repository not found" in last_err.lower():
                raise RepositoryCloningError("Repository not found or is private.")
            if "authentication failed" in last_err.lower():
                raise RepositoryCloningError("Authentication failed: Private repositories are not currently accessible.")

            logger.warning("Git clone attempt %d failed: %s. Retrying...", attempt, last_err)
            import time
            time.sleep(1.5)

        except subprocess.TimeoutExpired:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise RepositoryCloningError(
                f"Git clone operation timed out after {settings.CLONE_TIMEOUT_SECONDS} seconds."
            )
        except Exception as exc:
            shutil.rmtree(temp_dir, ignore_errors=True)
            if not isinstance(exc, RepositoryCloningError):
                raise RepositoryCloningError(f"Failed to clone repository: {exc}") from exc
            raise

    if last_err:
        raise RepositoryCloningError(f"Git clone failed: {last_err}")

    # Verify maximum repository size quota
    total_bytes = calculate_dir_size_bytes(temp_dir)
    max_bytes = settings.MAX_REPO_SIZE_MB * 1024 * 1024
    if total_bytes > max_bytes:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise RepositoryCloningError(
            f"Repository size ({total_bytes / (1024 * 1024):.1f} MB) exceeds maximum allowed size "
            f"quota of {settings.MAX_REPO_SIZE_MB} MB."
        )

    # Extract Git metadata (commit hash, author, message, branch)
    commit_hash = None
    commit_message = None
    commit_author = None
    default_branch = "main"

    try:
        rev_result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=temp_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5,
            shell=False,
        )
        if rev_result.returncode == 0:
            commit_hash = rev_result.stdout.strip()

        branch_result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=temp_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5,
            shell=False,
        )
        if branch_result.returncode == 0 and branch_result.stdout.strip():
            default_branch = branch_result.stdout.strip()

        log_result = subprocess.run(
            ["git", "log", "-1", "--pretty=format:%an <%ae>%n%B"],
            cwd=temp_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5,
            shell=False,
        )
        if log_result.returncode == 0:
            lines = log_result.stdout.strip().split("\n", 1)
            commit_author = lines[0] if lines else None
            commit_message = lines[1].strip() if len(lines) > 1 else None

        commit_date = None
        date_result = subprocess.run(
            ["git", "log", "-1", "--pretty=format:%cI"],
            cwd=temp_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5,
            shell=False,
        )
        if date_result.returncode == 0 and date_result.stdout.strip():
            try:
                commit_date = datetime.fromisoformat(date_result.stdout.strip())
            except Exception:
                commit_date = None

    except Exception as exc:
        logger.warning("Failed to extract git commit metadata: %s", exc)

    return ClonedRepository(
        temp_dir=temp_dir,
        commit_hash=commit_hash,
        commit_message=commit_message,
        commit_author=commit_author,
        default_branch=default_branch,
        commit_date=commit_date,
    )
