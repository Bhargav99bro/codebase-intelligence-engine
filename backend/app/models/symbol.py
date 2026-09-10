import enum
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.analysis import AnalysisJob
    from app.models.file import RepositoryFile
    from app.models.metrics import SymbolMetric


class SymbolType(str, enum.Enum):
    FUNCTION = "function"
    CLASS = "class"
    METHOD = "method"
    IMPORT = "import"
    EXPORT = "export"
    INTERFACE = "interface"
    TYPE = "type"


class Symbol(Base):
    __tablename__ = "symbols"

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
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    symbol_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    qualified_name: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True, index=True)

    start_line: Mapped[int] = mapped_column(Integer, nullable=False)
    start_column: Mapped[int] = mapped_column(Integer, nullable=False)
    end_line: Mapped[int] = mapped_column(Integer, nullable=False)
    end_column: Mapped[int] = mapped_column(Integer, nullable=False)

    parent_symbol_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("symbols.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    signature: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    analysis: Mapped["AnalysisJob"] = relationship("AnalysisJob", back_populates="symbols")
    file: Mapped["RepositoryFile"] = relationship("RepositoryFile", back_populates="symbols")
    parent: Mapped[Optional["Symbol"]] = relationship(
        "Symbol",
        remote_side=[id],
        back_populates="children",
    )
    children: Mapped[List["Symbol"]] = relationship(
        "Symbol",
        back_populates="parent",
        cascade="all, delete-orphan",
    )
    metric: Mapped[Optional["SymbolMetric"]] = relationship(
        "SymbolMetric",
        back_populates="symbol",
        cascade="all, delete-orphan",
        uselist=False,
    )

    def __repr__(self) -> str:
        return f"<Symbol {self.name} [{self.symbol_type}] L{self.start_line}-L{self.end_line}>"
