import ast
import logging
from typing import Any, List

from app.dependencies.base import DependencyType, ExtractedDependency

logger = logging.getLogger(__name__)


class PythonDependencyExtractor:
    """Statically extracts dependency statements from Python source using standard AST."""

    def extract(self, file_path: str, content: str, ast_tree: Any = None) -> List[ExtractedDependency]:
        """Extracts imports and from-imports from Python code with line numbers and aliases."""
        if not content.strip():
            return []

        if ast_tree is not None:
            tree = ast_tree
        else:
            try:
                tree = ast.parse(content, filename=file_path)
            except SyntaxError as exc:
                logger.warning("Syntax error extracting dependencies from %s: %s", file_path, exc)
                return []
            except Exception as exc:
                logger.warning("AST parse error extracting dependencies from %s: %s", file_path, exc)
                return []

        dependencies: List[ExtractedDependency] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    dependencies.append(
                        ExtractedDependency(
                            source_file_path=file_path,
                            target_module=alias.name,
                            dependency_type=DependencyType.IMPORT.value,
                            imported_symbols=[alias.asname or alias.name],
                            line_number=node.lineno,
                            level=0,
                        )
                    )
            elif isinstance(node, ast.ImportFrom):
                target_mod = node.module or ""
                symbols = [a.name for a in node.names]
                dependencies.append(
                    ExtractedDependency(
                        source_file_path=file_path,
                        target_module=target_mod,
                        dependency_type=DependencyType.FROM_IMPORT.value,
                        imported_symbols=symbols,
                        line_number=node.lineno,
                        level=node.level or 0,
                    )
                )

        # Sort stably by line number
        dependencies.sort(key=lambda d: (d.line_number, d.target_module))
        return dependencies
