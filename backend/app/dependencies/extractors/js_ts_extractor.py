import logging
from typing import List, Optional

import tree_sitter_javascript as tsjs
import tree_sitter_typescript as tsts
from tree_sitter import Language, Node, Parser

from app.dependencies.base import DependencyType, ExtractedDependency

logger = logging.getLogger(__name__)


class JsTsDependencyExtractor:
    """Statically extracts dependencies from JavaScript and TypeScript using Tree-sitter."""

    def __init__(self) -> None:
        self._js_language = Language(tsjs.language())
        self._js_parser = Parser(self._js_language)

        # TypeScript grammar includes both typescript and tsx
        self._ts_language = Language(tsts.language_typescript())
        self._ts_parser = Parser(self._ts_language)

        self._tsx_language = Language(tsts.language_tsx())
        self._tsx_parser = Parser(self._tsx_language)

    def _get_parser_for_path(self, file_path: str) -> Parser:
        ext = file_path.lower()
        if ext.endswith(".tsx"):
            return self._tsx_parser
        if ext.endswith(".ts"):
            return self._ts_parser
        return self._js_parser

    @staticmethod
    def _get_children(node: Node) -> List[Node]:
        return [node.child(i) for i in range(node.child_count)]

    @staticmethod
    def _get_text(node: Node, content_bytes: bytes) -> str:
        return content_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace")

    @staticmethod
    def _get_line_number(node: Node, content_bytes: bytes) -> int:
        return content_bytes[:node.start_byte].count(b"\n") + 1

    def extract(self, file_path: str, content: str) -> List[ExtractedDependency]:
        """Extracts ES imports, re-exports, require() calls, and dynamic imports."""
        if not content.strip():
            return []

        parser = self._get_parser_for_path(file_path)
        content_bytes = content.encode("utf-8")

        try:
            tree = parser.parse(content_bytes)
        except Exception as exc:
            logger.warning("Tree-sitter parse error extracting dependencies from %s: %s", file_path, exc)
            return []

        dependencies: List[ExtractedDependency] = []
        self._traverse_node(tree.root_node, file_path, content_bytes, dependencies)

        dependencies.sort(key=lambda d: (d.line_number, d.target_module))
        return dependencies

    def _traverse_node(
        self,
        node: Node,
        file_path: str,
        content_bytes: bytes,
        results: List[ExtractedDependency],
    ) -> None:
        node_type = node.type

        # 1. ES Import Statement: import ... from 'source'
        if node_type == "import_statement":
            self._handle_import_statement(node, file_path, content_bytes, results)

        # 2. ES Re-export: export ... from 'source'
        elif node_type == "export_statement":
            self._handle_export_statement(node, file_path, content_bytes, results)

        # 3. Call Expressions: require('...') or import('...')
        elif node_type == "call_expression":
            self._handle_call_expression(node, file_path, content_bytes, results)

        # Recurse child nodes
        for child in self._get_children(node):
            self._traverse_node(child, file_path, content_bytes, results)

    def _handle_import_statement(
        self,
        node: Node,
        file_path: str,
        content_bytes: bytes,
        results: List[ExtractedDependency],
    ) -> None:
        source_node = node.child_by_field_name("source")
        if not source_node:
            return

        target_module = self._clean_string(self._get_text(source_node, content_bytes))
        if not target_module:
            return

        line_number = self._get_line_number(node, content_bytes)
        raw_text = self._get_text(node, content_bytes)

        # Check if type-only import in TypeScript
        is_type_only = raw_text.strip().startswith("import type")

        imported_symbols: List[str] = []
        for child in self._get_children(node):
            if child.type == "import_clause":
                for sub in self._get_children(child):
                    if sub.type == "identifier":
                        imported_symbols.append(self._get_text(sub, content_bytes))
                    elif sub.type == "named_imports":
                        for spec in self._get_children(sub):
                            if spec.type == "import_specifier":
                                name_node = spec.child_by_field_name("name")
                                if name_node:
                                    imported_symbols.append(self._get_text(name_node, content_bytes))
                    elif sub.type == "namespace_import":
                        imported_symbols.append("*")

        results.append(
            ExtractedDependency(
                source_file_path=file_path,
                target_module=target_module,
                dependency_type=DependencyType.IMPORT.value,
                imported_symbols=imported_symbols or ["*"],
                line_number=line_number,
                is_type_only=is_type_only,
            )
        )

    def _handle_export_statement(
        self,
        node: Node,
        file_path: str,
        content_bytes: bytes,
        results: List[ExtractedDependency],
    ) -> None:
        source_node = node.child_by_field_name("source")
        if not source_node:
            return

        target_module = self._clean_string(self._get_text(source_node, content_bytes))
        if not target_module:
            return

        line_number = self._get_line_number(node, content_bytes)
        raw_text = self._get_text(node, content_bytes)
        is_type_only = raw_text.strip().startswith("export type")

        symbols: List[str] = []
        for child in self._get_children(node):
            if child.type == "export_clause":
                for spec in self._get_children(child):
                    if spec.type == "export_specifier":
                        name_node = spec.child_by_field_name("name")
                        if name_node:
                            symbols.append(self._get_text(name_node, content_bytes))

        results.append(
            ExtractedDependency(
                source_file_path=file_path,
                target_module=target_module,
                dependency_type=DependencyType.RE_EXPORT.value,
                imported_symbols=symbols or ["*"],
                line_number=line_number,
                is_type_only=is_type_only,
            )
        )

    def _handle_call_expression(
        self,
        node: Node,
        file_path: str,
        content_bytes: bytes,
        results: List[ExtractedDependency],
    ) -> None:
        function_node = node.child_by_field_name("function")
        args_node = node.child_by_field_name("arguments")
        if not function_node or not args_node:
            return

        func_name = self._get_text(function_node, content_bytes).strip()

        # Handle require('...')
        if func_name == "require":
            args = [c for c in self._get_children(args_node) if c.type in ("string", "string_fragment")]
            if not args:
                # In tree-sitter, arguments might wrap string
                for child in self._get_children(args_node):
                    if "string" in child.type:
                        args.append(child)
                        break

            if args:
                target_module = self._clean_string(self._get_text(args[0], content_bytes))
                if target_module:
                    line_number = self._get_line_number(node, content_bytes)
                    results.append(
                        ExtractedDependency(
                            source_file_path=file_path,
                            target_module=target_module,
                            dependency_type=DependencyType.REQUIRE.value,
                            imported_symbols=["*"],
                            line_number=line_number,
                        )
                    )

        # Handle dynamic import('...')
        elif func_name == "import":
            args = [c for c in self._get_children(args_node) if "string" in c.type]
            if args:
                target_module = self._clean_string(self._get_text(args[0], content_bytes))
                if target_module:
                    line_number = self._get_line_number(node, content_bytes)
                    results.append(
                        ExtractedDependency(
                            source_file_path=file_path,
                            target_module=target_module,
                            dependency_type=DependencyType.DYNAMIC_IMPORT.value,
                            imported_symbols=["*"],
                            line_number=line_number,
                        )
                    )

    @staticmethod
    def _clean_string(val: str) -> str:
        """Strips surrounding quotes and backticks from string literals."""
        val = val.strip()
        if (val.startswith("'") and val.endswith("'")) or \
           (val.startswith('"') and val.endswith('"')) or \
           (val.startswith('`') and val.endswith('`')):
            return val[1:-1]
        return val
