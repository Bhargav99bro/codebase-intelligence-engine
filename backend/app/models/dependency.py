import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.analysis import AnalysisJob
    from app.models.file import RepositoryFile


class Dependency(Base):
    """Represents a directed dependency edge from a source file to a target file or module."""
    __tablename__ = "dependencies"

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
    source_file_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("repository_files.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_file_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("repository_files.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Raw target module specifier (e.g. 'os', './utils', 'express', 'app.models.user')
    target_module: Mapped[str] = mapped_column(String(512), nullable=False)

    # Dependency type: 'import', 'from_import', 'require', 're_export', 'dynamic_import'
    dependency_type: Mapped[str] = mapped_column(String(50), nullable=False)

    # Specific symbols imported: e.g. ["get", "post"] or ["*"] or ["default"]
    imported_symbols: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)

    # 1-indexed source line number
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)

    # Resolution status: 'internal', 'external', 'unresolved'
    resolution_status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # TypeScript type-only import flag
    is_type_only: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    analysis: Mapped["AnalysisJob"] = relationship("AnalysisJob", back_populates="dependencies")
    source_file: Mapped["RepositoryFile"] = relationship(
        "RepositoryFile",
        foreign_keys=[source_file_id],
        back_populates="outgoing_dependencies",
    )
    target_file: Mapped[Optional["RepositoryFile"]] = relationship(
        "RepositoryFile",
        foreign_keys=[target_file_id],
        back_populates="incoming_dependencies",
    )

    __table_args__ = (
        Index("ix_dependencies_analysis_status", "analysis_id", "resolution_status"),
        Index("ix_dependencies_src_target", "source_file_id", "target_file_id"),
        Index(
            "uq_dependencies_edge",
            "analysis_id",
            "source_file_id",
            "target_module",
            "line_number",
            unique=True,
        ),
    )

    def __repr__(self) -> str:
        return f"<Dependency {self.source_file_id} -> {self.target_module} ({self.resolution_status})>"


class FileDependencyMetric(Base):
    """Stores precomputed graph metrics for a single repository file."""
    __tablename__ = "file_dependency_metrics"

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
    file_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("repository_files.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Graph degree metrics
    fan_in: Mapped[int] = mapped_column(Integer, default=0, nullable=False, index=True)
    fan_out: Mapped[int] = mapped_column(Integer, default=0, nullable=False, index=True)

    # Edge counts by category
    internal_dependencies_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    external_dependencies_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unresolved_dependencies_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Instability: I = fan_out / (fan_in + fan_out). Defined as 0.0 when (fan_in + fan_out) == 0
    instability: Mapped[float] = mapped_column(Float, default=0.0, nullable=False, index=True)

    # Cycle participation
    in_cycle: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    cycle_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    analysis: Mapped["AnalysisJob"] = relationship("AnalysisJob", back_populates="file_dependency_metrics")
    file: Mapped["RepositoryFile"] = relationship(
        "RepositoryFile",
        back_populates="dependency_metric",
    )

    def __repr__(self) -> str:
        return f"<FileDependencyMetric file={self.file_id} fan_in={self.fan_in} fan_out={self.fan_out} I={self.instability:.2f}>"
