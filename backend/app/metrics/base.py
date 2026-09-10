from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from app.analyzers.base import ExtractedSymbol


@dataclass
class QualityFlag:
    flag: str
    description: str
    metric_value: float
    threshold: float
    severity: str  # "CRITICAL", "HIGH", "MEDIUM", "LOW"
    location: str  # "path/file.ext:line"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SymbolMetrics:
    name: str
    symbol_type: str
    start_line: int
    end_line: int
    lines_of_code: int
    cyclomatic_complexity: int = 1
    nesting_depth: int = 0
    parameter_count: int = 0
    return_count: int = 0
    branch_count: int = 0
    loop_count: int = 0
    exception_handler_count: int = 0
    boolean_condition_count: int = 0
    quality_flags: List[Dict[str, Any]] = field(default_factory=list)
    metric_status: str = "calculated"
    metric_error: Optional[str] = None


@dataclass
class FileMetrics:
    file_path: str
    language: Optional[str] = None
    total_lines: int = 0
    sloc: int = 0
    comment_lines: int = 0
    blank_lines: int = 0
    statement_count: int = 0
    symbol_count: int = 0
    function_count: int = 0
    class_count: int = 0
    method_count: int = 0
    import_count: int = 0
    export_count: int = 0
    max_nesting_depth: int = 0
    average_nesting_depth: float = 0.0
    total_cyclomatic_complexity: int = 0
    average_cyclomatic_complexity: float = 0.0
    max_cyclomatic_complexity: int = 0
    maintainability_score: float = 100.0
    quality_flags: List[Dict[str, Any]] = field(default_factory=list)
    symbols_metrics: List[SymbolMetrics] = field(default_factory=list)
    metric_status: str = "calculated"
    metric_error: Optional[str] = None


class BaseMetricsAnalyzer(ABC):
    """Abstract base class for language-specific code complexity and quality metrics analyzers."""

    @property
    @abstractmethod
    def language_name(self) -> str:
        """Name of the supported language."""
        pass

    @property
    @abstractmethod
    def supported_extensions(self) -> List[str]:
        """File extensions supported by this metrics analyzer."""
        pass

    @abstractmethod
    def calculate(
        self,
        file_path: str,
        content: str,
        symbols: List[ExtractedSymbol],
    ) -> FileMetrics:
        """Calculates complexity, nesting depth, and quality metrics for a single source file."""
        pass
