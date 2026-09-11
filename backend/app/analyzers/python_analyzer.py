import ast
import logging
from typing import Any, Dict, List, Optional

import tree_sitter_python as tspython
from tree_sitter import Language, Parser

from app.analyzers.base import BaseLanguageAnalyzer, ExtractedSymbol, FileAnalysisResult

logger = logging.getLogger(__name__)


class PythonAnalyzer(BaseLanguageAnalyzer):
    """Static structural analyzer for Python source files using Tree-sitter & AST."""

    def __init__(self) -> None:
        self._language = Language(tspython.language())
        self._parser = Parser(self._language)

    @property
    def language_name(self) -> str:
        return "Python"

    @property
    def supported_extensions(self) -> List[str]:
        return [".py", ".pyi"]

    def analyze(self, file_path: str, content: str) -> FileAnalysisResult:
        if not content.strip():
            return FileAnalysisResult(
                file_path=file_path,
                language=self.language_name,
                parser_status="parsed",
                symbols=[],
            )

        # 1. Parse using Tree-sitter to ensure structural CST conformance
        try:
            tree = self._parser.parse(content.encode("utf-8"))
            if tree.root_node.has_error:
                # Tree-sitter flagged a syntax error in the file
                pass
        except Exception as exc:
            logger.debug("Tree-sitter parse warning on %s: %s", file_path, exc)

        # 2. Enrich with Python built-in AST for full semantic typing & decorators
        try:
            tree_ast = ast.parse(content, filename=file_path)
        except SyntaxError as exc:
            return FileAnalysisResult(
                file_path=file_path,
                language=self.language_name,
                parser_status="failed",
                parser_error=f"SyntaxError at line {exc.lineno}: {exc.msg}",
                symbols=[],
            )
        except Exception as exc:
            return FileAnalysisResult(
                file_path=file_path,
                language=self.language_name,
                parser_status="failed",
                parser_error=f"AST parse error: {str(exc)}",
                symbols=[],
            )

        symbols: List[ExtractedSymbol] = []
        module_qualifier = file_path.replace("\\", "/").rstrip(".py").rstrip(".pyi").replace("/", ".")

        self._extract_symbols_from_ast(tree_ast, module_qualifier, None, symbols)

        return FileAnalysisResult(
            file_path=file_path,
            language=self.language_name,
            parser_status="parsed",
            symbols=symbols,
            ast_tree=tree_ast,
        )

    def _extract_symbols_from_ast(
        self,
        node: ast.AST,
        parent_qualifier: str,
        parent_name: Optional[str],
        results: List[ExtractedSymbol],
    ) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._extract_function(child, parent_qualifier, parent_name, results)
            elif isinstance(child, ast.ClassDef):
                self._extract_class(child, parent_qualifier, parent_name, results)
            elif isinstance(child, ast.Import):
                self._extract_import(child, results)
            elif isinstance(child, ast.ImportFrom):
                self._extract_import_from(child, results)

    def _extract_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        parent_qualifier: str,
        parent_name: Optional[str],
        results: List[ExtractedSymbol],
    ) -> None:
        is_method = parent_name is not None
        symbol_type = "method" if is_method else "function"
        qualified_name = f"{parent_qualifier}.{node.name}" if parent_qualifier else node.name

        num_defaults = len(node.args.defaults)
        default_offset = len(node.args.args) - num_defaults
        params: List[str] = []
        for i, arg in enumerate(node.args.args):
            arg_str = arg.arg
            if arg.annotation:
                try:
                    arg_str += f": {ast.unparse(arg.annotation)}"
                except Exception:
                    pass
            if i >= default_offset:
                try:
                    arg_str += f" = {ast.unparse(node.args.defaults[i - default_offset])}"
                except Exception:
                    pass
            params.append(arg_str)

        if node.args.vararg:
            params.append(f"*{node.args.vararg.arg}")
        if node.args.kwarg:
            params.append(f"**{node.args.kwarg.arg}")

        return_annotation: Optional[str] = None
        if node.returns:
            try:
                return_annotation = ast.unparse(node.returns)
            except Exception:
                pass

        decorators: List[str] = []
        for dec in node.decorator_list:
            try:
                dec_str = ast.unparse(dec)
                if not dec_str.startswith("@"):
                    dec_str = f"@{dec_str}"
                decorators.append(dec_str)
            except Exception:
                pass

        # Format signature
        prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
        sig_str = f"{prefix} {node.name}({', '.join(params)})"
        if return_annotation:
            sig_str += f" -> {return_annotation}"

        metadata: Dict[str, Any] = {
            "parameters": [a.arg for a in node.args.args],
            "parameter_signatures": params,
            "return_type": return_annotation,
            "decorators": decorators,
            "is_async": isinstance(node, ast.AsyncFunctionDef),
            "docstring": ast.get_docstring(node),
        }

        results.append(
            ExtractedSymbol(
                name=node.name,
                symbol_type=symbol_type,
                qualified_name=qualified_name,
                start_line=node.lineno,
                start_column=node.col_offset,
                end_line=getattr(node, "end_lineno", node.lineno),
                end_column=getattr(node, "end_col_offset", node.col_offset),
                parent_name=parent_name,
                signature=sig_str,
                metadata_json=metadata,
            )
        )

        # Traverse nested functions or classes inside this function
        self._extract_symbols_from_ast(node, qualified_name, node.name, results)

    def _extract_class(
        self,
        node: ast.ClassDef,
        parent_qualifier: str,
        parent_name: Optional[str],
        results: List[ExtractedSymbol],
    ) -> None:
        qualified_name = f"{parent_qualifier}.{node.name}" if parent_qualifier else node.name

        bases: List[str] = []
        for base in node.bases:
            try:
                bases.append(ast.unparse(base))
            except Exception:
                pass

        decorators: List[str] = []
        for dec in node.decorator_list:
            try:
                dec_str = ast.unparse(dec)
                if not dec_str.startswith("@"):
                    dec_str = f"@{dec_str}"
                decorators.append(dec_str)
            except Exception:
                pass

        sig_str = f"class {node.name}"
        if bases:
            sig_str += f"({', '.join(bases)})"

        metadata: Dict[str, Any] = {
            "bases": bases,
            "decorators": decorators,
            "docstring": ast.get_docstring(node),
        }

        results.append(
            ExtractedSymbol(
                name=node.name,
                symbol_type="class",
                qualified_name=qualified_name,
                start_line=node.lineno,
                start_column=node.col_offset,
                end_line=getattr(node, "end_lineno", node.lineno),
                end_column=getattr(node, "end_col_offset", node.col_offset),
                parent_name=parent_name,
                signature=sig_str,
                metadata_json=metadata,
            )
        )

        # Extract nested methods and symbols inside this class
        self._extract_symbols_from_ast(node, qualified_name, node.name, results)

    def _extract_import(
        self,
        node: ast.Import,
        results: List[ExtractedSymbol],
    ) -> None:
        for alias in node.names:
            alias_name = alias.asname or alias.name
            signature = f"import {alias.name}" if not alias.asname else f"import {alias.name} as {alias.asname}"
            results.append(
                ExtractedSymbol(
                    name=alias_name,
                    symbol_type="import",
                    qualified_name=alias.name,
                    start_line=node.lineno,
                    start_column=node.col_offset,
                    end_line=getattr(node, "end_lineno", node.lineno),
                    end_column=getattr(node, "end_col_offset", node.col_offset),
                    parent_name=None,
                    signature=signature,
                    metadata_json={
                        "module": alias.name,
                        "alias": alias.asname,
                        "is_from_import": False,
                    },
                )
            )

    def _extract_import_from(
        self,
        node: ast.ImportFrom,
        results: List[ExtractedSymbol],
    ) -> None:
        module = node.module or ""
        for alias in node.names:
            alias_name = alias.asname or alias.name
            signature = f"from {module} import {alias.name}"
            if alias.asname:
                signature += f" as {alias.asname}"

            results.append(
                ExtractedSymbol(
                    name=alias_name,
                    symbol_type="import",
                    qualified_name=f"{module}.{alias.name}" if module else alias.name,
                    start_line=node.lineno,
                    start_column=node.col_offset,
                    end_line=getattr(node, "end_lineno", node.lineno),
                    end_column=getattr(node, "end_col_offset", node.col_offset),
                    parent_name=None,
                    signature=signature,
                    metadata_json={
                        "module": module,
                        "name": alias.name,
                        "alias": alias.asname,
                        "level": node.level,
                        "is_from_import": True,
                    },
                )
            )
