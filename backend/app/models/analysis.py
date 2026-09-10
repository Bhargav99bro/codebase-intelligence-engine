import enum
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.dependency import Dependency, FileDependencyMetric
    from app.models.file import RepositoryFile
    from app.models.issue import AnalysisHealthScore, AnalysisIssue
    from app.models.metrics import FileMetric, SymbolMetric
    from app.models.repository import Repository
    from app.models.symbol import Symbol


class AnalysisStatus(str, enum.Enum):
    QUEUED = "queued"
    CLONING = "cloning"
    ANALYZING_GIT_CHURN = "analyzing_git_churn"
    DISCOVERING = "discovering"
    PARSING = "parsing"
    EXTRACTING_SYMBOLS = "extracting_symbols"
    CALCULATING_METRICS = "calculating_metrics"
    DETECTING_DUPLICATION = "detecting_duplication"
    ANALYZING_DEPENDENCIES = "analyzing_dependencies"
    EVALUATING_HEALTH = "evaluating_health"
    PERSISTING = "persisting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLATION_REQUESTED = "cancellation_requested"
    CANCELLED = "cancelled"


class AnalysisJob(Base, TimestampMixin):
    __tablename__ = "analysis_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    repository_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        default=AnalysisStatus.QUEUED.value,
        index=True,
        nullable=False,
    )
    stage: Mapped[str] = mapped_column(String(50), default="queued", nullable=False)
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    message: Mapped[str] = mapped_column(Text, default="Queued for ingestion", nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Git metadata
    commit_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    commit_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    commit_author: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    commit_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    # Aggregated metrics for Phase 2
    total_files: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    analyzable_files: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_lines: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_bytes: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    language_distribution: Mapped[Dict[str, float]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )

    # Phase 3: Structural Analysis metrics
    total_symbols: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    symbol_distribution: Mapped[Dict[str, int]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )

    # Phase 4: Code Complexity & Quality summary aggregates
    summary_metrics: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        default=dict,
        nullable=True,
    )

    # Phase 5: Dependency & Architecture summary aggregates
    dependency_summary: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        default=dict,
        nullable=True,
    )

    # Phase 6: Health score and diagnostics summary
    health_summary: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        default=dict,
        nullable=True,
    )

    # Phase 7: Quality Gate & Cancellation support
    quality_gate_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)
    quality_gate_details: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        default=dict,
        nullable=True,
    )
    is_cancelled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Phase 8: Baseline lineage
    base_analysis_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("analysis_jobs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    repository: Mapped["Repository"] = relationship("Repository", back_populates="analyses")
    files: Mapped[List["RepositoryFile"]] = relationship(
        "RepositoryFile",
        back_populates="analysis",
        cascade="all, delete-orphan",
    )
    symbols: Mapped[List["Symbol"]] = relationship(
        "Symbol",
        back_populates="analysis",
        cascade="all, delete-orphan",
    )
    file_metrics: Mapped[List["FileMetric"]] = relationship(
        "FileMetric",
        back_populates="analysis",
        cascade="all, delete-orphan",
    )
    symbol_metrics: Mapped[List["SymbolMetric"]] = relationship(
        "SymbolMetric",
        back_populates="analysis",
        cascade="all, delete-orphan",
    )
    dependencies: Mapped[List["Dependency"]] = relationship(
        "Dependency",
        back_populates="analysis",
        cascade="all, delete-orphan",
    )
    file_dependency_metrics: Mapped[List["FileDependencyMetric"]] = relationship(
        "FileDependencyMetric",
        back_populates="analysis",
        cascade="all, delete-orphan",
    )
    issues: Mapped[List["AnalysisIssue"]] = relationship(
        "AnalysisIssue",
        back_populates="analysis",
        cascade="all, delete-orphan",
    )
    health_score: Mapped[Optional["AnalysisHealthScore"]] = relationship(
        "AnalysisHealthScore",
        back_populates="analysis",
        cascade="all, delete-orphan",
        uselist=False,
    )

    def __repr__(self) -> str:
        return f"<AnalysisJob {self.id} [{self.status}] {self.progress}%>"
