from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid


class ResolutionStatus(str, Enum):
    INTERNAL = "internal"
    EXTERNAL = "external"
    UNRESOLVED = "unresolved"


class DependencyType(str, Enum):
    IMPORT = "import"
    FROM_IMPORT = "from_import"
    REQUIRE = "require"
    RE_EXPORT = "re_export"
    DYNAMIC_IMPORT = "dynamic_import"


@dataclass
class ExtractedDependency:
    """Represents a raw dependency extracted from a file AST/CST before resolution."""
    source_file_path: str
    target_module: str
    dependency_type: str
    imported_symbols: List[str] = field(default_factory=list)
    line_number: int = 1
    is_type_only: bool = False
    level: int = 0  # Python relative import level: 0 for absolute, 1 for ., 2 for ..


@dataclass
class ResolvedDependency:
    """Represents a statically resolved dependency with target mapping and status."""
    source_file_path: str
    target_module: str
    dependency_type: str
    imported_symbols: List[str]
    line_number: int
    resolution_status: str  # "internal", "external", "unresolved"
    source_file_id: Optional[uuid.UUID] = None
    target_file_id: Optional[uuid.UUID] = None
    target_file_path: Optional[str] = None
    is_type_only: bool = False
    resolution_note: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_file_path": self.source_file_path,
            "target_module": self.target_module,
            "dependency_type": self.dependency_type,
            "imported_symbols": self.imported_symbols,
            "line_number": self.line_number,
            "resolution_status": self.resolution_status,
            "source_file_id": str(self.source_file_id) if self.source_file_id else None,
            "target_file_id": str(self.target_file_id) if self.target_file_id else None,
            "target_file_path": self.target_file_path,
            "is_type_only": self.is_type_only,
            "resolution_note": self.resolution_note,
        }
