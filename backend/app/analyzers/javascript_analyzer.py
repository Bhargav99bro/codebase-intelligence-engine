import logging
from typing import Any, Dict, List, Optional, Tuple

import tree_sitter_javascript as tsjs
from tree_sitter import Language, Node, Parser

from app.analyzers.base import BaseLanguageAnalyzer, ExtractedSymbol, FileAnalysisResult

logger = logging.getLogger(__name__)


class JavaScriptAnalyzer(BaseLanguageAnalyzer):
    """Static structural analyzer for JavaScript source files using Tree-sitter."""

    def __init__(self) -> None:
        self._language = Language(tsjs.language())
        self._parser = Parser(self._language)

    @property
    def language_name(self) -> str:
        return "JavaScript"

    @property
    def supported_extensions(self) -> List[str]:
        return [".js", ".jsx", ".mjs", ".cjs"]

    @staticmethod
    def _get_children(node: Node) -> List[Node]:
        """Safely get child nodes using ts_node_child to prevent C heap munmap corruption."""
        return [node.child(i) for i in range(node.child_count)]

    @staticmethod
    def _get_location(node: Node, content: bytes) -> Tuple[int, int, int, int]:
        """Calculates 1-indexed start and end line/column from byte offsets."""
        start_byte = node.start_byte
        end_byte = node.end_byte

        start_line = content[:start_byte].count(b"\n") + 1
        last_nl = content.rfind(b"\n", 0, start_byte)
        start_col = start_byte - (last_nl + 1 if last_nl != -1 else 0)

        end_line = content[:end_byte].count(b"\n") + 1
        last_nl_end = content.rfind(b"\n", 0, end_byte)
        end_col = end_byte - (last_nl_end + 1 if last_nl_end != -1 else 0)

        return start_line, start_col, end_line, end_col

    def analyze(self, file_path: str, content: str) -> FileAnalysisResult:
        if not content.strip():
            return FileAnalysisResult(
                file_path=file_path,
                language=self.language_name,
                parser_status="parsed",
                symbols=[],
            )

        try:
            content_bytes = content.encode("utf-8")
            tree = self._parser.parse(content_bytes)
        except Exception as exc:
            return FileAnalysisResult(
                file_path=file_path,
                language=self.language_name,
                parser_status="failed",
                parser_error=f"Tree-sitter parse error: {str(exc)}",
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
        )

    def _get_text(self, node: Node, content: bytes) -> str:
        return content[node.start_byte:node.end_byte].decode("utf-8", errors="ignore")

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

            if node_type == "import_statement":
                self._extract_import(child, content, results)

            elif node_type == "export_statement":
                self._extract_export(child, content, qualifier, parent_name, results)

            elif node_type in ("function_declaration", "generator_function_declaration"):
                self._extract_function_decl(child, content, qualifier, parent_name, results)

            elif node_type in ("lexical_declaration", "variable_declaration"):
                self._extract_variable_functions(child, content, qualifier, parent_name, results)

            elif node_type == "class_declaration":
                self._extract_class(child, content, qualifier, parent_name, results)

            elif node_type in ("export_default_declaration",):
                self._extract_export_default(child, content, qualifier, parent_name, results)

            elif node_type not in ("statement_block", "class_body"):
                pass

    def _extract_import(self, node: Node, content: bytes, results: List[ExtractedSymbol]) -> None:
        raw_text = self._get_text(node, content).strip()
        source_node = node.child_by_field_name("source")
        source = self._get_text(source_node, content).strip("'\"") if source_node else ""
        sl, sc, el, ec = self._get_location(node, content)

        imported_names: List[str] = []
        for child in self._get_children(node):
            if child.type == "import_clause":
                for sub in self._get_children(child):
                    if sub.type == "identifier":
                        imported_names.append(self._get_text(sub, content))
                    elif sub.type == "named_imports":
                        for spec in self._get_children(sub):
                            if spec.type == "import_specifier":
                                name_node = spec.child_by_field_name("name")
                                if name_node:
                                    imported_names.append(self._get_text(name_node, content))
                    elif sub.type == "namespace_import":
                        for sub_id in self._get_children(sub):
                            if sub_id.type == "identifier":
                                imported_names.append(self._get_text(sub_id, content))

        name = ", ".join(imported_names) if imported_names else (source or "import")
        results.append(
            ExtractedSymbol(
                name=name,
                symbol_type="import",
                qualified_name=source,
                start_line=sl,
                start_column=sc,
                end_line=el,
                end_column=ec,
                parent_name=None,
                signature=raw_text.split("\n")[0],
                metadata_json={
                    "source": source,
                    "imported_names": imported_names,
                },
            )
        )

    def _extract_export(
        self,
        node: Node,
        content: bytes,
        qualifier: str,
        parent_name: Optional[str],
        results: List[ExtractedSymbol],
    ) -> None:
        raw_text = self._get_text(node, content).strip()
        declaration = node.child_by_field_name("declaration")
        sl, sc, el, ec = self._get_location(node, content)

        export_name = "export"
        if declaration and declaration.child_by_field_name("name"):
            export_name = f"export {self._get_text(declaration.child_by_field_name('name'), content)}"

        results.append(
            ExtractedSymbol(
                name=export_name,
                symbol_type="export",
                qualified_name=f"{qualifier}.{export_name}" if qualifier else export_name,
                start_line=sl,
                start_column=sc,
                end_line=el,
                end_column=ec,
                parent_name=parent_name,
                signature=raw_text.split("\n")[0][:120],
                metadata_json={"raw_export": raw_text.split("\n")[0]},
            )
        )

        if declaration:
            if declaration.type in ("function_declaration", "generator_function_declaration"):
                self._extract_function_decl(declaration, content, qualifier, parent_name, results, is_exported=True)
            elif declaration.type in ("lexical_declaration", "variable_declaration"):
                self._extract_variable_functions(declaration, content, qualifier, parent_name, results, is_exported=True)
            elif declaration.type == "class_declaration":
                self._extract_class(declaration, content, qualifier, parent_name, results, is_exported=True)
            else:
                self._extract_custom_declaration(declaration, content, qualifier, parent_name, results, is_exported=True)

    def _extract_custom_declaration(
        self,
        node: Node,
        content: bytes,
        qualifier: str,
        parent_name: Optional[str],
        results: List[ExtractedSymbol],
        is_exported: bool = False,
    ) -> None:
        """Hook for subclass (TypeScript) declarations."""
        pass

    def _extract_export_default(
        self,
        node: Node,
        content: bytes,
        qualifier: str,
        parent_name: Optional[str],
        results: List[ExtractedSymbol],
    ) -> None:
        raw_text = self._get_text(node, content).strip()
        sl, sc, el, ec = self._get_location(node, content)

        results.append(
            ExtractedSymbol(
                name="default",
                symbol_type="export",
                qualified_name=f"{qualifier}.default" if qualifier else "default",
                start_line=sl,
                start_column=sc,
                end_line=el,
                end_column=ec,
                parent_name=parent_name,
                signature=raw_text.split("\n")[0][:120],
                metadata_json={"is_default": True},
            )
        )

    def _extract_function_decl(
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
        params_node = node.child_by_field_name("parameters")
        params_text = self._get_text(params_node, content) if params_node else "()"
        sl, sc, el, ec = self._get_location(node, content)

        is_async = any(self._get_text(c, content) == "async" for c in self._get_children(node) if c.type == "async")
        sig_prefix = "async function" if is_async else "function"
        sig_str = f"{sig_prefix} {name}{params_text}"

        results.append(
            ExtractedSymbol(
                name=name,
                symbol_type="function",
                qualified_name=f"{qualifier}.{name}" if qualifier else name,
                start_line=sl,
                start_column=sc,
                end_line=el,
                end_column=ec,
                parent_name=parent_name,
                signature=sig_str,
                metadata_json={
                    "is_async": is_async,
                    "is_exported": is_exported,
                    "parameters": params_text,
                },
            )
        )

    def _extract_variable_functions(
        self,
        node: Node,
        content: bytes,
        qualifier: str,
        parent_name: Optional[str],
        results: List[ExtractedSymbol],
        is_exported: bool = False,
    ) -> None:
        for declarator in self._get_children(node):
            if declarator.type == "variable_declarator":
                name_node = declarator.child_by_field_name("name")
                value_node = declarator.child_by_field_name("value")

                if name_node and value_node and value_node.type in ("arrow_function", "function_expression"):
                    name = self._get_text(name_node, content)
                    params_node = value_node.child_by_field_name("parameters")
                    params_text = self._get_text(params_node, content) if params_node else "()"
                    is_async = any(self._get_text(c, content) == "async" for c in self._get_children(value_node) if c.type == "async")
                    sl, sc, el, ec = self._get_location(declarator, content)

                    sig_str = f"const {name} = {'async ' if is_async else ''}{params_text} => ..."
                    results.append(
                        ExtractedSymbol(
                            name=name,
                            symbol_type="function",
                            qualified_name=f"{qualifier}.{name}" if qualifier else name,
                            start_line=sl,
                            start_column=sc,
                            end_line=el,
                            end_column=ec,
                            parent_name=parent_name,
                            signature=sig_str,
                            metadata_json={
                                "is_arrow": value_node.type == "arrow_function",
                                "is_async": is_async,
                                "is_exported": is_exported,
                                "parameters": params_text,
                            },
                        )
                    )

    def _extract_class(
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
        qualified_name = f"{qualifier}.{name}" if qualifier else name
        sl, sc, el, ec = self._get_location(node, content)

        heritage: Optional[str] = None
        for child in self._get_children(node):
            if child.type == "class_heritage":
                heritage = self._get_text(child, content).strip()

        sig_str = f"class {name}"
        if heritage:
            sig_str += f" {heritage}"

        results.append(
            ExtractedSymbol(
                name=name,
                symbol_type="class",
                qualified_name=qualified_name,
                start_line=sl,
                start_column=sc,
                end_line=el,
                end_column=ec,
                parent_name=parent_name,
                signature=sig_str,
                metadata_json={
                    "is_exported": is_exported,
                    "heritage": heritage,
                },
            )
        )

        for child in self._get_children(node):
            if child.type == "class_body":
                for member in self._get_children(child):
                    if member.type == "method_definition":
                        self._extract_method(member, content, qualified_name, name, results)

    def _extract_method(
        self,
        node: Node,
        content: bytes,
        qualifier: str,
        class_name: str,
        results: List[ExtractedSymbol],
    ) -> None:
        name_node = node.child_by_field_name("name")
        if not name_node:
            return

        name = self._get_text(name_node, content)
        params_node = node.child_by_field_name("parameters")
        params_text = self._get_text(params_node, content) if params_node else "()"
        sl, sc, el, ec = self._get_location(node, content)

        is_async = any(self._get_text(c, content) == "async" for c in self._get_children(node) if c.type == "async")
        is_static = any(self._get_text(c, content) == "static" for c in self._get_children(node) if c.type == "static")

        prefix = []
        if is_static:
            prefix.append("static")
        if is_async:
            prefix.append("async")
        prefix_str = " ".join(prefix) + " " if prefix else ""
        sig_str = f"{prefix_str}{name}{params_text}"

        results.append(
            ExtractedSymbol(
                name=name,
                symbol_type="method",
                qualified_name=f"{qualifier}.{name}" if qualifier else name,
                start_line=sl,
                start_column=sc,
                end_line=el,
                end_column=ec,
                parent_name=class_name,
                signature=sig_str,
                metadata_json={
                    "is_async": is_async,
                    "is_static": is_static,
                    "parameters": params_text,
                },
            )
        )
