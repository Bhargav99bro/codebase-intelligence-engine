import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional, TYPE_CHECKING
from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.analysis import AnalysisJob
    from app.models.file import RepositoryFile


class CodeDuplicate(Base):
    """Represents a detected Type-1 or Type-2 code clone pair between two file fragments."""
    __tablename__ = "code_duplicates"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("analysis_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_file_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("repository_files.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    target_file_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("repository_files.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    source_file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    target_file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    clone_type: Mapped[str] = mapped_column(String(16), nullable=False)  # 'TYPE_1', 'TYPE_2'

    line_count: Mapped[int] = mapped_column(Integer, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)

    source_start_line: Mapped[int] = mapped_column(Integer, nullable=False)
    source_end_line: Mapped[int] = mapped_column(Integer, nullable=False)
    target_start_line: Mapped[int] = mapped_column(Integer, nullable=False)
    target_end_line: Mapped[int] = mapped_column(Integer, nullable=False)

    similarity_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    fragment_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    analysis: Mapped["AnalysisJob"] = relationship("AnalysisJob", foreign_keys=[analysis_id])
    source_file: Mapped[Optional["RepositoryFile"]] = relationship("RepositoryFile", foreign_keys=[source_file_id])
    target_file: Mapped[Optional["RepositoryFile"]] = relationship("RepositoryFile", foreign_keys=[target_file_id])

    __table_args__ = (
        Index("ix_code_duplicates_analysis_lines", "analysis_id", "line_count"),
        Index("ix_code_duplicates_analysis_paths", "analysis_id", "source_file_path", "target_file_path"),
    )

    def to_dict(self, repo_url: Optional[str] = None, commit_hash: Optional[str] = None) -> Dict[str, Any]:
        commit = commit_hash[:8] if commit_hash else "HEAD"
        base_url = (repo_url or "https://github.com/unknown/repo").rstrip("/")
        source_url = f"{base_url}/blob/{commit}/{self.source_file_path}#L{self.source_start_line}-L{self.source_end_line}"
        target_url = f"{base_url}/blob/{commit}/{self.target_file_path}#L{self.target_start_line}-L{self.target_end_line}"

        return {
            "id": str(self.id),
            "analysis_id": str(self.analysis_id),
            "clone_type": self.clone_type,
            "line_count": self.line_count,
            "token_count": self.token_count,
            "source_file_path": self.source_file_path,
            "source_start_line": self.source_start_line,
            "source_end_line": self.source_end_line,
            "target_file_path": self.target_file_path,
            "target_start_line": self.target_start_line,
            "target_end_line": self.target_end_line,
            "similarity_score": round(self.similarity_score, 2),
            "fragment_hash": self.fragment_hash,
            "source_url": source_url,
            "target_url": target_url,
        }


class GitChurnMetric(Base):
    """Stores Git history churn metrics and defect risk attributes per file."""
    __tablename__ = "git_churn_metrics"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("analysis_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("repository_files.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)

    commit_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    insertions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    deletions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    author_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    churn_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    last_modified_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    analysis: Mapped["AnalysisJob"] = relationship("AnalysisJob", foreign_keys=[analysis_id])
    file: Mapped[Optional["RepositoryFile"]] = relationship("RepositoryFile", foreign_keys=[file_id])

    __table_args__ = (
        Index("ix_git_churn_metrics_analysis_path", "analysis_id", "file_path"),
        Index("ix_git_churn_metrics_analysis_churn", "analysis_id", "churn_score"),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "analysis_id": str(self.analysis_id),
            "file_id": str(self.file_id) if self.file_id else None,
            "file_path": self.file_path,
            "commit_count": self.commit_count,
            "insertions": self.insertions,
            "deletions": self.deletions,
            "churn_lines": self.insertions + self.deletions,
            "author_count": self.author_count,
            "churn_score": round(self.churn_score, 1),
            "last_modified_date": self.last_modified_date.isoformat() if self.last_modified_date else None,
        }
