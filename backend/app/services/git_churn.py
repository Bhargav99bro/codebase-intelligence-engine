import logging
import os
import subprocess
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


def clamp(val: float, min_val: float, max_val: float) -> float:
    return max(min_val, min(max_val, val))


@dataclass
class FileChurnMetric:
    file_path: str
    commit_count: int
    added_lines: int
    deleted_lines: int
    author_count: int
    relative_churn: float  # C_churn: 0.0 - 100.0

    @property
    def churn_lines(self) -> int:
        return self.added_lines + self.deleted_lines

    @property
    def raw_churn(self) -> int:
        return self.added_lines + self.deleted_lines

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "commit_count": self.commit_count,
            "added_lines": self.added_lines,
            "deleted_lines": self.deleted_lines,
            "churn_lines": self.added_lines + self.deleted_lines,
            "author_count": self.author_count,
            "relative_churn": self.relative_churn,
        }


@dataclass
class GitChurnResult:
    has_git_history: bool
    metrics: Dict[str, FileChurnMetric]
    max_churn: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "has_git_history": self.has_git_history,
            "metrics": {fp: m.to_dict() for fp, m in self.metrics.items()},
            "max_churn": self.max_churn,
        }


class GitChurnAnalyzer:
    """Extracts machine-readable commit, author, and line churn metrics via git log."""

    def __init__(self, timeout_seconds: int = 30) -> None:
        self.timeout_seconds = timeout_seconds

    @staticmethod
    def calculate_churn_score(
        commit_count: int,
        insertions: int,
        deletions: int,
        author_count: int,
    ) -> float:
        """Calculates C_churn based on exact specification:
        Cchurn = clamp(
            (commit_count / 20) * 50.0
            + ((insertions + deletions) / 1000) * 30.0
            + (author_count / 5) * 20.0,
            0.0,
            100.0
        )
        """
        score = (
            (commit_count / 20.0) * 50.0
            + ((insertions + deletions) / 1000.0) * 30.0
            + (author_count / 5.0) * 20.0
        )
        return round(clamp(score, 0.0, 100.0), 1)

    def analyze_churn(self, repo_path: str) -> GitChurnResult:
        """Parses git log with null-byte separation to compute per-file churn metrics."""
        git_dir = os.path.join(repo_path, ".git")
        if not os.path.exists(git_dir):
            logger.debug("No .git directory found at %s, returning empty churn result", repo_path)
            return GitChurnResult(has_git_history=False, metrics={}, max_churn=0.0)

        cmd = [
            "git",
            "log",
            "-z",
            "--numstat",
            "--no-merges",
            "--format=tformat:COMMIT%x00%H%x00%aN",
        ]

        try:
            res = subprocess.run(
                cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout_seconds,
            )
            if res.returncode != 0 or not res.stdout.strip():
                logger.debug("git log failed or empty in %s: %s", repo_path, res.stderr)
                return GitChurnResult(has_git_history=False, metrics={}, max_churn=0.0)

            return self._parse_git_log_output(res.stdout)
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as exc:
            logger.warning("Failed to execute git log in %s: %s", repo_path, exc)
            return GitChurnResult(has_git_history=False, metrics={}, max_churn=0.0)

    def _parse_git_log_output(self, stdout: str) -> GitChurnResult:
        tokens = stdout.split("\0")

        file_commits: Dict[str, Set[str]] = {}
        file_authors: Dict[str, Set[str]] = {}
        file_added: Dict[str, int] = {}
        file_deleted: Dict[str, int] = {}

        current_commit: Optional[str] = None
        current_author: Optional[str] = None
        idx = 0
        n = len(tokens)

        while idx < n:
            tok = tokens[idx]
            idx += 1

            if not tok:
                continue

            if tok == "COMMIT":
                if idx < n:
                    current_commit = tokens[idx].strip()
                    idx += 1
                if idx < n:
                    current_author = tokens[idx].strip()
                    idx += 1
                continue

            lines = tok.split("\n")
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                if line == "COMMIT":
                    if idx < n:
                        current_commit = tokens[idx].strip()
                        idx += 1
                    if idx < n:
                        current_author = tokens[idx].strip()
                        idx += 1
                    break

                parts = line.split("\t")
                if len(parts) >= 3:
                    added_str, deleted_str, fpath = parts[0], parts[1], parts[2]
                    added = int(added_str) if added_str.isdigit() else 0
                    deleted = int(deleted_str) if deleted_str.isdigit() else 0

                    if not fpath and idx < n:
                        old_p = tokens[idx]
                        idx += 1
                        new_p = tokens[idx] if idx < n else old_p
                        idx += 1
                        fpath = new_p

                    norm_path = fpath.replace("\\", "/").lstrip("./")
                    if not norm_path:
                        continue

                    file_commits.setdefault(norm_path, set())
                    file_authors.setdefault(norm_path, set())
                    if current_commit:
                        file_commits[norm_path].add(current_commit)
                    if current_author:
                        file_authors[norm_path].add(current_author)

                    file_added[norm_path] = file_added.get(norm_path, 0) + added
                    file_deleted[norm_path] = file_deleted.get(norm_path, 0) + deleted
                elif len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                    added = int(parts[0])
                    deleted = int(parts[1])
                    if idx < n:
                        old_p = tokens[idx]
                        idx += 1
                        new_p = tokens[idx] if idx < n else old_p
                        idx += 1
                        norm_path = new_p.replace("\\", "/").lstrip("./")
                        if norm_path:
                            file_commits.setdefault(norm_path, set())
                            file_authors.setdefault(norm_path, set())
                            if current_commit:
                                file_commits[norm_path].add(current_commit)
                            if current_author:
                                file_authors[norm_path].add(current_author)
                            file_added[norm_path] = file_added.get(norm_path, 0) + added
                            file_deleted[norm_path] = file_deleted.get(norm_path, 0) + deleted

        if not file_commits:
            return GitChurnResult(has_git_history=False, metrics={}, max_churn=0.0)

        metrics: Dict[str, FileChurnMetric] = {}
        for fpath, commits in file_commits.items():
            c_count = len(commits)
            a_count = len(file_authors.get(fpath, set()))
            if a_count == 0 and c_count > 0:
                a_count = 1
            add = file_added.get(fpath, 0)
            dele = file_deleted.get(fpath, 0)

            c_churn = self.calculate_churn_score(
                commit_count=c_count,
                insertions=add,
                deletions=dele,
                author_count=a_count,
            )

            metrics[fpath] = FileChurnMetric(
                file_path=fpath,
                commit_count=c_count,
                added_lines=add,
                deleted_lines=dele,
                author_count=a_count,
                relative_churn=c_churn,
            )

        max_churn = max((m.relative_churn for m in metrics.values()), default=0.0)

        return GitChurnResult(
            has_git_history=True,
            metrics=metrics,
            max_churn=max_churn,
        )

    @staticmethod
    def calculate_defect_hotspot_score(
        static_hotspot_score: float,
        churn_metric: Optional[FileChurnMetric],
        has_git_history: bool,
    ) -> float:
        """H_defect = clamp(0.60 * H_static + 0.40 * C_churn, 0.0, 100.0) if git history exists else H_static."""
        if not has_git_history or churn_metric is None:
            return round(clamp(static_hotspot_score, 0.0, 100.0), 1)

        c_churn = churn_metric.relative_churn
        score = 0.60 * static_hotspot_score + 0.40 * c_churn
        return round(clamp(score, 0.0, 100.0), 1)

