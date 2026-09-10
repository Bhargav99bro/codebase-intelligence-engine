from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import enum
from typing import Any, Dict, List, Optional
import uuid

from app.dependencies.graph import DirectedDependencyGraph
from app.metrics.base import FileMetrics


class IssueCategory(str, enum.Enum):
    ARCHITECTURE = "architecture"
    COMPLEXITY = "complexity"
    MAINTAINABILITY = "maintainability"
    HYGIENE = "hygiene"
    SECURITY = "security"


class IssueSeverity(str, enum.Enum):
    BLOCKER = "blocker"
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    INFO = "info"


@dataclass
class CodebaseIssue:
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    rule_id: str = ""
    rule_name: str = ""
    category: str = ""
    severity: str = ""
    title: str = ""
    description: str = ""
    file_id: Optional[uuid.UUID] = None
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    end_line_number: Optional[int] = None
    symbol_name: Optional[str] = None
    remediation_effort_minutes: int = 30
    metadata_json: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "category": self.category,
            "severity": self.severity,
            "title": self.title,
            "description": self.description,
            "file_id": str(self.file_id) if self.file_id else None,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "end_line_number": self.end_line_number,
            "symbol_name": self.symbol_name,
            "remediation_effort_minutes": self.remediation_effort_minutes,
            "metadata_json": self.metadata_json,
        }


@dataclass
class RuleContext:
    parsed_files_data: List[Dict[str, Any]]
    file_metrics_map: Dict[str, FileMetrics]
    graph: DirectedDependencyGraph
    file_id_map: Dict[str, uuid.UUID]
    code_duplicates: List[Any] = field(default_factory=list)


class BaseRule(ABC):
    rule_id: str
    rule_name: str
    category: IssueCategory
    severity: IssueSeverity
    default_remediation_minutes: int = 30

    @abstractmethod
    def evaluate(self, context: RuleContext) -> List[CodebaseIssue]:
        """Evaluates rule against context and returns detected issues."""
        pass
