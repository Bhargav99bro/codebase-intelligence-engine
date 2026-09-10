import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Integer, JSON, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.analysis import AnalysisJob
    from app.models.file import RepositoryFile
    from app.models.symbol import Symbol


class FileMetric(Base):
    __tablename__ = "file_metrics"

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
        index=True,
        unique=True,
    )

    # Line counts
    total_lines: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sloc: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    comment_lines: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    blank_lines: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Structural item counts
    statement_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    symbol_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    function_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    class_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    method_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    import_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    export_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Nesting depth metrics
    max_nesting_depth: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    average_nesting_depth: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Cyclomatic complexity aggregates
    total_cyclomatic_complexity: Mapped[int] = mapped_column(Integer, default=0, nullable=False, index=True)
    average_cyclomatic_complexity: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    max_cyclomatic_complexity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Maintainability score (0.0 to 100.0)
    maintainability_score: Mapped[float] = mapped_column(Float, default=100.0, nullable=False, index=True)

    # Status and error tracking
    metric_status: Mapped[str] = mapped_column(String(50), default="calculated", nullable=False, index=True)
    metric_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Quality and hotspot findings for this file
    quality_flags: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    analysis: Mapped["AnalysisJob"] = relationship("AnalysisJob", back_populates="file_metrics")
    file: Mapped["RepositoryFile"] = relationship("RepositoryFile", back_populates="file_metric")

    def __repr__(self) -> str:
        return f"<FileMetric file_id={self.file_id} sloc={self.sloc} cc={self.total_cyclomatic_complexity} mi={self.maintainability_score:.1f}>"


class SymbolMetric(Base):
    __tablename__ = "symbol_metrics"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    symbol_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("symbols.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        unique=True,
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
        index=True,
    )

    # Function/method metrics
    lines_of_code: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cyclomatic_complexity: Mapped[int] = mapped_column(Integer, default=1, nullable=False, index=True)
    nesting_depth: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    parameter_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    return_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    branch_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    loop_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    exception_handler_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    boolean_condition_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Quality / hotspot findings for this function
    quality_flags: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )

    metric_status: Mapped[str] = mapped_column(String(50), default="calculated", nullable=False)
    metric_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    analysis: Mapped["AnalysisJob"] = relationship("AnalysisJob", back_populates="symbol_metrics")
    symbol: Mapped["Symbol"] = relationship("Symbol", back_populates="metric")

    def __repr__(self) -> str:
        return f"<SymbolMetric symbol_id={self.symbol_id} loc={self.lines_of_code} cc={self.cyclomatic_complexity}>"
