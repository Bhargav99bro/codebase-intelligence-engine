from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TYPE_CHECKING
import uuid

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.analysis import AnalysisJob
    from app.models.file import RepositoryFile


class AnalysisIssue(Base):
    __tablename__ = "analysis_issues"

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
        ForeignKey("repository_files.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    rule_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    rule_name: Mapped[str] = mapped_column(String(128), nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    line_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    end_line_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    symbol_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    remediation_effort_minutes: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    analysis: Mapped["AnalysisJob"] = relationship("AnalysisJob", back_populates="issues")
    file: Mapped[Optional["RepositoryFile"]] = relationship("RepositoryFile", back_populates="issues")

    __table_args__ = (
        Index("ix_analysis_issues_lookup", "analysis_id", "severity", "category"),
        Index("ix_analysis_issues_file", "analysis_id", "file_id"),
    )

    def to_dict(self, file_path: Optional[str] = None) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "analysis_id": str(self.analysis_id),
            "file_id": str(self.file_id) if self.file_id else None,
            "file_path": file_path,
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "category": self.category,
            "severity": self.severity,
            "title": self.title,
            "description": self.description,
            "line_number": self.line_number,
            "end_line_number": self.end_line_number,
            "symbol_name": self.symbol_name,
            "remediation_effort_minutes": self.remediation_effort_minutes,
            "metadata_json": self.metadata_json or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class AnalysisHealthScore(Base):
    __tablename__ = "analysis_health_scores"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("analysis_jobs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    grade: Mapped[str] = mapped_column(String(4), nullable=False)
    maintainability_score: Mapped[float] = mapped_column(Float, nullable=False)
    complexity_score: Mapped[float] = mapped_column(Float, nullable=False)
    architecture_score: Mapped[float] = mapped_column(Float, nullable=False)
    hygiene_score: Mapped[float] = mapped_column(Float, nullable=False)

    # Phase 8: Duplication Metrics
    duplication_score: Mapped[float] = mapped_column(Float, default=100.0, nullable=False)
    duplication_ratio: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    duplicate_blocks_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duplicate_lines_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    technical_debt_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    debt_ratio_hours_per_ksloc: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    total_issues_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    blocker_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    critical_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    major_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    minor_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    info_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    category_scores_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    recommendations_json: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    analysis: Mapped["AnalysisJob"] = relationship("AnalysisJob", back_populates="health_score")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "analysis_id": str(self.analysis_id),
            "overall_score": self.overall_score,
            "grade": self.grade,
            "maintainability_score": self.maintainability_score,
            "complexity_score": self.complexity_score,
            "architecture_score": self.architecture_score,
            "hygiene_score": self.hygiene_score,
            "duplication_score": self.duplication_score,
            "duplication_ratio": self.duplication_ratio,
            "duplicate_blocks_count": self.duplicate_blocks_count,
            "duplicate_lines_count": self.duplicate_lines_count,
            "technical_debt_minutes": self.technical_debt_minutes,
            "debt_ratio_hours_per_ksloc": self.debt_ratio_hours_per_ksloc,
            "total_issues_count": self.total_issues_count,
            "blocker_count": self.blocker_count,
            "critical_count": self.critical_count,
            "major_count": self.major_count,
            "minor_count": self.minor_count,
            "info_count": self.info_count,
            "category_scores": self.category_scores_json,
            "recommendations": self.recommendations_json,
        }
