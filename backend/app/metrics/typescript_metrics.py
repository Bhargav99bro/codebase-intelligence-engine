import math
from typing import Any, Dict, List, Optional, Tuple

import tree_sitter
import tree_sitter_typescript as tsts

from app.analyzers.base import ExtractedSymbol
from app.metrics.base import FileMetrics, SymbolMetrics
from app.metrics.javascript_metrics import JavaScriptMetricsAnalyzer
from app.metrics.thresholds import evaluate_file_quality, evaluate_function_quality


class TypeScriptMetricsAnalyzer(JavaScriptMetricsAnalyzer):
    """Calculates code complexity, nesting depth, and maintainability for TypeScript and TSX source files."""

    def __init__(self) -> None:
        self._ts_language = tree_sitter.Language(tsts.language_typescript())
        self._tsx_language = tree_sitter.Language(tsts.language_tsx())
        self._ts_parser = tree_sitter.Parser()
        self._ts_parser.language = self._ts_language
        self._tsx_parser = tree_sitter.Parser()
        self._tsx_parser.language = self._tsx_language

    @property
    def language_name(self) -> str:
        return "TypeScript"

    @property
    def supported_extensions(self) -> List[str]:
        return [".ts", ".tsx", ".mts", ".cts"]

    def calculate(
        self,
        file_path: str,
        content: str,
        symbols: List[ExtractedSymbol],
    ) -> FileMetrics:
        # 1. Line analysis
        lines = content.splitlines()
        total_lines = len(lines)
        blank_lines = 0
        comment_lines = 0
        in_multiline_comment = False

        for line in lines:
            stripped = line.strip()
            if not stripped:
                blank_lines += 1
                continue

            if in_multiline_comment:
                comment_lines += 1
                if "*/" in stripped:
                    in_multiline_comment = False
                continue

            if stripped.startswith("//"):
                comment_lines += 1
                continue

            if stripped.startswith("/*"):
                comment_lines += 1
                if "*/" not in stripped:
                    in_multiline_comment = True
                continue

        sloc = max(0, total_lines - blank_lines - comment_lines)
        content_bytes = content.encode("utf-8")

        # 2. Parse Tree-sitter CST
        parser = self._tsx_parser if file_path.endswith(".tsx") else self._ts_parser
        try:
            tree = parser.parse(content_bytes)
        except Exception as exc:
            return FileMetrics(
                file_path=file_path,
                language=self.language_name,
                total_lines=total_lines,
                sloc=sloc,
                comment_lines=comment_lines,
                blank_lines=blank_lines,
                metric_status="failed",
                metric_error=str(exc),
            )

        root = tree.root_node

        # 3. Discover all functions and methods (ignoring type-only constructs for CC)
        func_nodes: List[Tuple[tree_sitter.Node, str, str]] = []  # (node, name, symbol_type)
        statement_count = 0

        def discover_functions(node: tree_sitter.Node) -> None:
            nonlocal statement_count
            ntype = node.type

            # Type constructs count as statements/structural elements, but not executable functions
            if (
                ntype.endswith("_statement")
                or ntype.endswith("_declaration")
                or ntype in ("interface_declaration", "type_alias_declaration", "enum_declaration")
            ):
                statement_count += 1

            if ntype == "function_declaration":
                name_node = node.child_by_field_name("name")
                name = (
                    content_bytes[name_node.start_byte : name_node.end_byte].decode("utf-8", errors="replace")
                    if name_node
                    else "anonymous"
                )
                func_nodes.append((node, name, "function"))

            elif ntype == "method_definition":
                name_node = node.child_by_field_name("name")
                name = (
                    content_bytes[name_node.start_byte : name_node.end_byte].decode("utf-8", errors="replace")
                    if name_node
                    else "method"
                )
                func_nodes.append((node, name, "method"))

            elif ntype == "arrow_function" or (
                ntype in ("function", "function_expression") and node.child_by_field_name("body") is not None
            ):
                parent = node.parent
                name = "anonymous"
                if parent and parent.type == "variable_declarator":
                    id_node = parent.child_by_field_name("name")
                    if id_node:
                        name = content_bytes[id_node.start_byte : id_node.end_byte].decode("utf-8", errors="replace")
                elif parent and parent.type == "pair":
                    key_node = parent.child_by_field_name("key")
                    if key_node:
                        name = content_bytes[key_node.start_byte : key_node.end_byte].decode("utf-8", errors="replace")
                func_nodes.append((node, name, "function"))

            for child in self._get_children(node):
                discover_functions(child)

        discover_functions(root)

        # 4. Calculate metrics for each function
        symbols_metrics: List[SymbolMetrics] = []
        for func_node, func_name, sym_type in func_nodes:
            start_line, start_col, end_line, end_col = self._get_location(func_node, content_bytes)
            loc = max(1, end_line - start_line + 1)

            param_count = 0
            params_node = func_node.child_by_field_name("parameters")
            if params_node:
                for p_child in self._get_children(params_node):
                    if p_child.type not in ("(", ")", ",", "{", "}"):
                        param_count += 1

            cc = 1
            max_depth = 0
            return_cnt = 0
            branch_cnt = 0
            loop_cnt = 0
            exception_cnt = 0
            bool_cnt = 0

            def walk_func_scope(n: tree_sitter.Node, current_depth: int) -> None:
                nonlocal cc, max_depth, return_cnt, branch_cnt, loop_cnt, exception_cnt, bool_cnt
                max_depth = max(max_depth, current_depth)

                for ch in self._get_children(n):
                    if ch is not func_node and ch.type in (
                        "function_declaration",
                        "method_definition",
                        "arrow_function",
                        "function",
                    ):
                        continue

                    # Pure TypeScript type annotations do not add executable complexity
                    if ch.type in (
                        "type_annotation",
                        "type_arguments",
                        "type_parameters",
                        "as_expression",
                        "type_assertion",
                    ):
                        continue

                    increments = False
                    ctype = ch.type

                    if ctype == "if_statement":
                        cc += 1
                        branch_cnt += 1
                        increments = True

                    elif ctype == "ternary_expression":
                        cc += 1
                        branch_cnt += 1

                    elif ctype in (
                        "for_statement",
                        "for_in_statement",
                        "for_of_statement",
                        "while_statement",
                        "do_statement",
                    ):
                        cc += 1
                        loop_cnt += 1
                        increments = True

                    elif ctype == "switch_case":
                        if ch.child_by_field_name("value"):
                            cc += 1
                            branch_cnt += 1

                    elif ctype == "catch_clause":
                        cc += 1
                        exception_cnt += 1
                        increments = True

                    elif ctype in ("switch_statement", "try_statement"):
                        increments = True

                    elif ctype == "binary_expression":
                        op_node = ch.child_by_field_name("operator")
                        if op_node:
                            op = content_bytes[op_node.start_byte : op_node.end_byte].decode("utf-8", errors="replace")
                            if op in ("&&", "||", "??"):
                                cc += 1
                                bool_cnt += 1

                    elif ctype == "unary_expression":
                        op_node = ch.child_by_field_name("operator")
                        if op_node:
                            op = content_bytes[op_node.start_byte : op_node.end_byte].decode("utf-8", errors="replace")
                            if op == "!":
                                bool_cnt += 1

                    elif ctype == "logical_assignment_expression":
                        cc += 1
                        bool_cnt += 1

                    elif ctype == "return_statement":
                        return_cnt += 1

                    next_d = current_depth + 1 if increments else current_depth
                    walk_func_scope(ch, next_d)

            body_node = func_node.child_by_field_name("body")
            if body_node:
                walk_func_scope(body_node, current_depth=1)
            else:
                walk_func_scope(func_node, current_depth=0)

            loc_str = f"{file_path}:{start_line}"
            flags = evaluate_function_quality(
                name=func_name,
                location=loc_str,
                cyclomatic_complexity=cc,
                lines_of_code=loc,
                nesting_depth=max_depth,
                parameter_count=param_count,
                branch_count=branch_cnt,
            )

            symbols_metrics.append(
                SymbolMetrics(
                    name=func_name,
                    symbol_type=sym_type,
                    start_line=start_line,
                    end_line=end_line,
                    lines_of_code=loc,
                    cyclomatic_complexity=cc,
                    nesting_depth=max_depth,
                    parameter_count=param_count,
                    return_count=return_cnt,
                    branch_count=branch_cnt,
                    loop_count=loop_cnt,
                    exception_handler_count=exception_cnt,
                    boolean_condition_count=bool_cnt,
                    quality_flags=flags,
                    metric_status="calculated",
                )
            )

        # 5. Counts and file aggregates
        function_count = sum(1 for s in symbols if s.symbol_type == "function")
        method_count = sum(1 for s in symbols if s.symbol_type == "method")
        class_count = sum(1 for s in symbols if s.symbol_type == "class")
        import_count = sum(1 for s in symbols if s.symbol_type == "import")
        export_count = sum(1 for s in symbols if s.symbol_type == "export")
        symbol_count = len(symbols)

        num_funcs = len(symbols_metrics)
        total_cc = sum(s.cyclomatic_complexity for s in symbols_metrics)
        avg_cc = round(total_cc / num_funcs, 2) if num_funcs > 0 else 1.0
        max_cc = max((s.cyclomatic_complexity for s in symbols_metrics), default=1)

        max_nesting = max((s.nesting_depth for s in symbols_metrics), default=0)
        avg_nesting = (
            round(sum(s.nesting_depth for s in symbols_metrics) / num_funcs, 2)
            if num_funcs > 0
            else 0.0
        )

        # 6. Maintainability Index
        avg_loc = (
            sum(s.lines_of_code for s in symbols_metrics) / num_funcs
            if num_funcs > 0
            else max(1, sloc)
        )
        comment_ratio = comment_lines / max(1, total_lines)
        log_loc = math.log(max(1.0, float(avg_loc)))
        log_lines = math.log(max(1.0, float(total_lines)))

        raw_mi = (
            171.0
            - 5.2 * log_loc
            - 0.23 * float(avg_cc)
            - 16.2 * log_lines
            + 50.0 * comment_ratio
        )
        normalized_mi = round(max(0.0, min(100.0, raw_mi * (100.0 / 171.0))), 2)

        file_flags = evaluate_file_quality(
            file_path=file_path,
            sloc=sloc,
            maintainability_score=normalized_mi,
            max_nesting_depth=max_nesting,
            max_cyclomatic_complexity=max_cc,
        )

        return FileMetrics(
            file_path=file_path,
            language=self.language_name,
            total_lines=total_lines,
            sloc=sloc,
            comment_lines=comment_lines,
            blank_lines=blank_lines,
            statement_count=statement_count,
            symbol_count=symbol_count,
            function_count=function_count,
            class_count=class_count,
            method_count=method_count,
            import_count=import_count,
            export_count=export_count,
            max_nesting_depth=max_nesting,
            average_nesting_depth=avg_nesting,
            total_cyclomatic_complexity=total_cc,
            average_cyclomatic_complexity=avg_cc,
            max_cyclomatic_complexity=max_cc,
            maintainability_score=normalized_mi,
            quality_flags=file_flags,
            symbols_metrics=symbols_metrics,
            metric_status="calculated",
        )
