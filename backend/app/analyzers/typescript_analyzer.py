import logging
from typing import Any, Dict, List, Optional

import tree_sitter_typescript as tsts
from tree_sitter import Language, Node, Parser

from app.analyzers.base import ExtractedSymbol, FileAnalysisResult
from app.analyzers.javascript_analyzer import JavaScriptAnalyzer

logger = logging.getLogger(__name__)


class TypeScriptAnalyzer(JavaScriptAnalyzer):
    """Static structural analyzer for TypeScript and TSX files using Tree-sitter."""

    def __init__(self) -> None:
        self._ts_language = Language(tsts.language_typescript())
        self._tsx_language = Language(tsts.language_tsx())
        self._ts_parser = Parser(self._ts_language)
        self._tsx_parser = Parser(self._tsx_language)

    @property
    def language_name(self) -> str:
        return "TypeScript"

    @property
    def supported_extensions(self) -> List[str]:
        return [".ts", ".tsx", ".mts", ".cts"]

    def analyze(self, file_path: str, content: str) -> FileAnalysisResult:
        if not content.strip():
            return FileAnalysisResult(
                file_path=file_path,
                language=self.language_name,
                parser_status="parsed",
                symbols=[],
            )

        parser = self._tsx_parser if file_path.endswith(".tsx") else self._ts_parser
        try:
            content_bytes = content.encode("utf-8")
            tree = parser.parse(content_bytes)
        except Exception as exc:
            return FileAnalysisResult(
                file_path=file_path,
                language=self.language_name,
                parser_status="failed",
                parser_error=f"Tree-sitter TS parse error: {str(exc)}",
                symbols=[],
            )

        if tree.root_node.has_error:
            root_children = self._get_children(tree.root_node)
            if tree.root_node.type == "ERROR" or (len(root_children) == 1 and root_children[0].type == "ERROR"):
                return FileAnalysisResult(
                    file_path=file_path,
                    language=self.language_name,
                    parser_status="failed",
                    parser_error=f"Syntax error in {file_path}",
                    symbols=[],
                )

        symbols: List[ExtractedSymbol] = []
        module_qualifier = file_path.replace("\\", "/").rsplit(".", 1)[0].replace("/", ".")

        self._traverse_node(tree.root_node, content_bytes, module_qualifier, None, symbols)

        return FileAnalysisResult(
            file_path=file_path,
            language=self.language_name,
            parser_status="parsed",
            symbols=symbols,
            ast_tree=tree,
        )

    def _traverse_node(
        self,
        node: Node,
        content: bytes,
        qualifier: str,
        parent_name: Optional[str],
        results: List[ExtractedSymbol],
    ) -> None:
        for child in self._get_children(node):
            node_type = child.type

            if node_type == "interface_declaration":
                self._extract_interface(child, content, qualifier, parent_name, results)
            elif node_type == "type_alias_declaration":
                self._extract_type_alias(child, content, qualifier, parent_name, results)
            elif node_type == "enum_declaration":
                self._extract_enum(child, content, qualifier, parent_name, results)
            else:
                # Delegate standard JS constructs (classes, functions, imports, exports)
                super()._traverse_node(NodeMock([child]), content, qualifier, parent_name, results)

    def _extract_custom_declaration(
        self,
        node: Node,
        content: bytes,
        qualifier: str,
        parent_name: Optional[str],
        results: List[ExtractedSymbol],
        is_exported: bool = False,
    ) -> None:
        """Handle TypeScript specific declarations wrapped inside export_statement."""
        if node.type == "interface_declaration":
            self._extract_interface(node, content, qualifier, parent_name, results, is_exported=is_exported)
        elif node.type == "type_alias_declaration":
            self._extract_type_alias(node, content, qualifier, parent_name, results, is_exported=is_exported)
        elif node.type == "enum_declaration":
            self._extract_enum(node, content, qualifier, parent_name, results, is_exported=is_exported)

    def _extract_interface(
        self,
        node: Node,
        content: bytes,
        qualifier: str,
        parent_name: Optional[str],
        results: List[ExtractedSymbol],
        is_exported: bool = False,
    ) -> None:
        name_node = node.child_by_field_name("name")
        if not name_node:
            return

        name = self._get_text(name_node, content)
        raw_text = self._get_text(node, content).strip()
        first_line = raw_text.split("\n")[0].rstrip(" {")
        sl, sc, el, ec = self._get_location(node, content)

        results.append(
            ExtractedSymbol(
                name=name,
                symbol_type="interface",
                qualified_name=f"{qualifier}.{name}" if qualifier else name,
                start_line=sl,
                start_column=sc,
                end_line=el,
                end_column=ec,
                parent_name=parent_name,
                signature=first_line,
                metadata_json={
                    "is_exported": is_exported,
                },
            )
        )

    def _extract_type_alias(
        self,
        node: Node,
        content: bytes,
        qualifier: str,
        parent_name: Optional[str],
        results: List[ExtractedSymbol],
        is_exported: bool = False,
    ) -> None:
        name_node = node.child_by_field_name("name")
        if not name_node:
            return

        name = self._get_text(name_node, content)
        raw_text = self._get_text(node, content).strip()
        first_line = raw_text.split("\n")[0][:100]
        sl, sc, el, ec = self._get_location(node, content)

        results.append(
            ExtractedSymbol(
                name=name,
                symbol_type="type",
                qualified_name=f"{qualifier}.{name}" if qualifier else name,
                start_line=sl,
                start_column=sc,
                end_line=el,
                end_column=ec,
                parent_name=parent_name,
                signature=first_line,
                metadata_json={
                    "is_exported": is_exported,
                },
            )
        )

    def _extract_enum(
        self,
        node: Node,
        content: bytes,
        qualifier: str,
        parent_name: Optional[str],
        results: List[ExtractedSymbol],
        is_exported: bool = False,
    ) -> None:
        name_node = node.child_by_field_name("name")
        if not name_node:
            return

        name = self._get_text(name_node, content)
        sig_str = f"enum {name}"
        sl, sc, el, ec = self._get_location(node, content)

        results.append(
            ExtractedSymbol(
                name=name,
                symbol_type="type",
                qualified_name=f"{qualifier}.{name}" if qualifier else name,
                start_line=sl,
                start_column=sc,
                end_line=el,
                end_column=ec,
                parent_name=parent_name,
                signature=sig_str,
                metadata_json={
                    "is_enum": True,
                    "is_exported": is_exported,
                },
            )
        )


class NodeMock:
    """Adapter to pass a list of child nodes to super()._traverse_node."""

    def __init__(self, children: List[Node]) -> None:
        self._children = children

    @property
    def child_count(self) -> int:
        return len(self._children)

    def child(self, i: int) -> Node:
        return self._children[i]
