import uuid
from datetime import datetime, timezone
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.analysis import AnalysisJob
    from app.models.dependency import Dependency, FileDependencyMetric
    from app.models.issue import AnalysisIssue
    from app.models.metrics import FileMetric
    from app.models.symbol import Symbol


class RepositoryFile(Base):
    __tablename__ = "repository_files"

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

    path: Mapped[str] = mapped_column(String(1024), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    extension: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    language: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    size_bytes: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    line_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_analyzable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Phase 3: Code Structure Analysis per-file status
    parser_status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    parser_error: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    symbol_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    analysis: Mapped["AnalysisJob"] = relationship("AnalysisJob", back_populates="files")
    symbols: Mapped[List["Symbol"]] = relationship(
        "Symbol",
        back_populates="file",
        cascade="all, delete-orphan",
    )
    file_metric: Mapped[Optional["FileMetric"]] = relationship(
        "FileMetric",
        back_populates="file",
        cascade="all, delete-orphan",
        uselist=False,
    )
    outgoing_dependencies: Mapped[List["Dependency"]] = relationship(
        "Dependency",
        foreign_keys="[Dependency.source_file_id]",
        back_populates="source_file",
        cascade="all, delete-orphan",
    )
    incoming_dependencies: Mapped[List["Dependency"]] = relationship(
        "Dependency",
        foreign_keys="[Dependency.target_file_id]",
        back_populates="target_file",
    )
    dependency_metric: Mapped[Optional["FileDependencyMetric"]] = relationship(
        "FileDependencyMetric",
        back_populates="file",
        cascade="all, delete-orphan",
        uselist=False,
    )
    issues: Mapped[List["AnalysisIssue"]] = relationship(
        "AnalysisIssue",
        back_populates="file",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<RepositoryFile {self.path} ({self.language})>"
