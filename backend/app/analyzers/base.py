from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ExtractedSymbol:
    """Represents a structural code symbol extracted from an AST."""

    name: str
    symbol_type: str  # function, class, method, import, export, interface, type
    start_line: int  # 1-indexed
    start_column: int  # 0-indexed
    end_line: int  # 1-indexed
    end_column: int  # 0-indexed
    qualified_name: Optional[str] = None
    parent_name: Optional[str] = None
    signature: Optional[str] = None
    metadata_json: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FileAnalysisResult:
    """The result of parsing and extracting symbols from a single source file."""

    file_path: str
    language: str
    parser_status: str  # "parsed", "unsupported", "failed"
    parser_error: Optional[str] = None
    symbols: List[ExtractedSymbol] = field(default_factory=list)


class BaseLanguageAnalyzer(ABC):
    """Abstract base class for all pluggable language analyzers."""

    @property
    @abstractmethod
    def language_name(self) -> str:
        """The canonical name of the programming language."""
        pass

    @property
    @abstractmethod
    def supported_extensions(self) -> List[str]:
        """List of file extensions supported by this analyzer (e.g. ['.py', '.pyi'])."""
        pass

    @abstractmethod
    def analyze(self, file_path: str, content: str) -> FileAnalysisResult:
        """Parse source content and return extracted structural symbols.

        Must be completely static: never execute repository code.
        Must isolate errors: if parsing fails, set parser_status='failed' with details.
        """
        pass
