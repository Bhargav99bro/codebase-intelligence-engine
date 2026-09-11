import ast
import math
from typing import Any, Dict, List, Optional, Set, Tuple

from app.analyzers.base import ExtractedSymbol
from app.metrics.base import BaseMetricsAnalyzer, FileMetrics, SymbolMetrics
from app.metrics.thresholds import evaluate_file_quality, evaluate_function_quality


class PythonFunctionMetricsVisitor:
    """Calculates metrics for a single Python function or method scope."""

    def __init__(self, func_node: ast.AST, file_path: str) -> None:
        self.func_node = func_node
        self.file_path = file_path
        self.name = getattr(func_node, "name", "anonymous")
        self.start_line = getattr(func_node, "lineno", 1)
        self.end_line = getattr(func_node, "end_lineno", self.start_line)
        self.lines_of_code = max(1, self.end_line - self.start_line + 1)

        self.cyclomatic_complexity = 1
        self.max_nesting_depth = 0
        self.return_count = 0
        self.branch_count = 0
        self.loop_count = 0
        self.exception_handler_count = 0
        self.boolean_condition_count = 0

    def compute(self) -> SymbolMetrics:
        # Parameter count
        args = getattr(self.func_node, "args", None)
        param_count = 0
        if args:
            param_count = len(args.args) + len(args.kwonlyargs)
            if args.vararg:
                param_count += 1
            if args.kwarg:
                param_count += 1

        # Traverse function AST, staying within this function's scope (ignoring nested functions)
        self._traverse_scope(self.func_node, current_depth=0)

        location = f"{self.file_path}:{self.start_line}"
        quality_flags = evaluate_function_quality(
            name=self.name,
            location=location,
            cyclomatic_complexity=self.cyclomatic_complexity,
            lines_of_code=self.lines_of_code,
            nesting_depth=self.max_nesting_depth,
            parameter_count=param_count,
            branch_count=self.branch_count,
        )

        return SymbolMetrics(
            name=self.name,
            symbol_type="function",  # updated by caller if method
            start_line=self.start_line,
            end_line=self.end_line,
            lines_of_code=self.lines_of_code,
            cyclomatic_complexity=self.cyclomatic_complexity,
            nesting_depth=self.max_nesting_depth,
            parameter_count=param_count,
            return_count=self.return_count,
            branch_count=self.branch_count,
            loop_count=self.loop_count,
            exception_handler_count=self.exception_handler_count,
            boolean_condition_count=self.boolean_condition_count,
            quality_flags=quality_flags,
            metric_status="calculated",
        )

    def _traverse_scope(self, node: ast.AST, current_depth: int) -> None:
        self.max_nesting_depth = max(self.max_nesting_depth, current_depth)

        for child in ast.iter_child_nodes(node):
            # Nested functions/classes have their own scopes; do not traverse inside them for CC
            if child is not self.func_node and isinstance(
                child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
            ):
                continue

            increments_depth = False

            if isinstance(child, (ast.If, ast.IfExp)):
                self.cyclomatic_complexity += 1
                self.branch_count += 1
                increments_depth = True

            elif isinstance(child, (ast.For, ast.AsyncFor, ast.While)):
                self.cyclomatic_complexity += 1
                self.loop_count += 1
                increments_depth = True

            elif isinstance(child, ast.ExceptHandler):
                self.cyclomatic_complexity += 1
                self.exception_handler_count += 1
                increments_depth = True

            elif isinstance(child, (ast.Try, ast.With, ast.AsyncWith)):
                increments_depth = True

            elif isinstance(child, ast.BoolOp):
                # Each extra operand adds a decision path: (a and b) -> 2 values, +1 path
                self.cyclomatic_complexity += max(0, len(child.values) - 1)
                self.boolean_condition_count += max(0, len(child.values) - 1)

            elif isinstance(child, ast.UnaryOp) and isinstance(child.op, ast.Not):
                self.boolean_condition_count += 1

            elif isinstance(child, ast.comprehension):
                # Each 'if' clause in comprehension adds a decision path
                if child.ifs:
                    self.cyclomatic_complexity += len(child.ifs)
                    self.branch_count += len(child.ifs)

            elif hasattr(ast, "Match") and isinstance(child, getattr(ast, "Match")):
                increments_depth = True

            elif hasattr(ast, "MatchCase") and isinstance(child, getattr(ast, "MatchCase")):
                self.cyclomatic_complexity += 1
                self.branch_count += 1

            elif isinstance(child, ast.Return):
                self.return_count += 1

            next_depth = current_depth + 1 if increments_depth else current_depth
            self._traverse_scope(child, next_depth)


class PythonMetricsAnalyzer(BaseMetricsAnalyzer):
    """Calculates code complexity, nesting, and maintainability for Python source files."""

    @property
    def language_name(self) -> str:
        return "Python"

    @property
    def supported_extensions(self) -> List[str]:
        return [".py", ".pyw", ".pyi"]

    def calculate(
        self,
        file_path: str,
        content: str,
        symbols: List[ExtractedSymbol],
        ast_tree: Any = None,
    ) -> FileMetrics:
        # 1. Line analysis
        lines = content.splitlines()
        total_lines = len(lines)
        blank_lines = 0
        comment_lines = 0
        in_multiline_docstring = False
        quote_char = None

        for line in lines:
            stripped = line.strip()
            if not stripped:
                blank_lines += 1
                continue

            if in_multiline_docstring:
                comment_lines += 1
                if quote_char and quote_char in stripped:
                    in_multiline_docstring = False
                    quote_char = None
                continue

            if stripped.startswith("#"):
                comment_lines += 1
                continue

            if stripped.startswith('"""') or stripped.startswith("'''"):
                comment_lines += 1
                quote = stripped[:3]
                if stripped.count(quote) < 2:
                    in_multiline_docstring = True
                    quote_char = quote
                continue

        sloc = max(0, total_lines - blank_lines - comment_lines)

        # 2. Parse AST (reuse pre-parsed tree if provided)
        if ast_tree is not None:
            tree = ast_tree
        else:
            try:
                tree = ast.parse(content, filename=file_path)
            except SyntaxError as syn_err:
                return FileMetrics(
                    file_path=file_path,
                    language="Python",
                    total_lines=total_lines,
                    sloc=sloc,
                    comment_lines=comment_lines,
                    blank_lines=blank_lines,
                    metric_status="failed",
                    metric_error=f"Syntax error: {syn_err.msg} at line {syn_err.lineno}",
                )
            except Exception as exc:
                return FileMetrics(
                    file_path=file_path,
                    language="Python",
                    total_lines=total_lines,
                    sloc=sloc,
                    comment_lines=comment_lines,
                    blank_lines=blank_lines,
                    metric_status="failed",
                    metric_error=str(exc),
                )

        # 3. Analyze all functions and methods
        func_nodes: List[Tuple[ast.AST, bool]] = []  # (node, is_method)

        class FunctionFinder(ast.NodeVisitor):
            def __init__(self) -> None:
                self.current_class: Optional[str] = None
                self.statements = 0

            def visit_ClassDef(self, node: ast.ClassDef) -> None:
                prev = self.current_class
                self.current_class = node.name
                self.statements += 1
                self.generic_visit(node)
                self.current_class = prev

            def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
                func_nodes.append((node, self.current_class is not None))
                self.statements += 1
                self.generic_visit(node)

            def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
                func_nodes.append((node, self.current_class is not None))
                self.statements += 1
                self.generic_visit(node)

            def generic_visit(self, node: ast.AST) -> None:
                if isinstance(node, ast.stmt):
                    self.statements += 1
                super().generic_visit(node)

        finder = FunctionFinder()
        finder.visit(tree)

        symbol_metrics_list: List[SymbolMetrics] = []
        for node, is_method in func_nodes:
            visitor = PythonFunctionMetricsVisitor(node, file_path)
            sym_metric = visitor.compute()
            sym_metric.symbol_type = "method" if is_method else "function"
            symbol_metrics_list.append(sym_metric)

        # 4. Symbol counts from extracted symbols
        function_count = sum(1 for s in symbols if s.symbol_type == "function")
        method_count = sum(1 for s in symbols if s.symbol_type == "method")
        class_count = sum(1 for s in symbols if s.symbol_type == "class")
        import_count = sum(1 for s in symbols if s.symbol_type == "import")
        export_count = sum(1 for s in symbols if s.symbol_type == "export")
        symbol_count = len(symbols)

        # 5. File aggregates
        total_cc = sum(s.cyclomatic_complexity for s in symbol_metrics_list)
        num_funcs = len(symbol_metrics_list)
        avg_cc = round(total_cc / num_funcs, 2) if num_funcs > 0 else 1.0
        max_cc = max((s.cyclomatic_complexity for s in symbol_metrics_list), default=1)

        max_nesting = max((s.nesting_depth for s in symbol_metrics_list), default=0)
        avg_nesting = (
            round(sum(s.nesting_depth for s in symbol_metrics_list) / num_funcs, 2)
            if num_funcs > 0
            else 0.0
        )

        # 6. Maintainability Index calculation
        # Formula: MI = max(0, min(100, (171 - 5.2*ln(avg_LOC) - 0.23*avg_CC - 16.2*ln(total_lines) + 50*comment_ratio) * 100 / 171))
        avg_loc = (
            sum(s.lines_of_code for s in symbol_metrics_list) / num_funcs
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
            language="Python",
            total_lines=total_lines,
            sloc=sloc,
            comment_lines=comment_lines,
            blank_lines=blank_lines,
            statement_count=finder.statements,
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
            symbols_metrics=symbol_metrics_list,
            metric_status="calculated",
        )
