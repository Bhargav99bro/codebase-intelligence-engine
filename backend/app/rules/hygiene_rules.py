import ast
import re
from typing import List
import uuid

from app.rules.base import BaseRule, CodebaseIssue, IssueCategory, IssueSeverity, RuleContext


class EmptyExceptionHandlerRule(BaseRule):
    rule_id = "HYGIENE-001"
    rule_name = "Empty Exception Handler"
    category = IssueCategory.HYGIENE
    severity = IssueSeverity.MAJOR
    default_remediation_minutes = 30

    def evaluate(self, context: RuleContext) -> List[CodebaseIssue]:
        issues: List[CodebaseIssue] = []

        for item in context.parsed_files_data:
            df = item["df"]
            content = item.get("content")
            fid = context.file_id_map.get(df.path)
            if not content or not df.is_analyzable:
                continue

            lang = (df.language or "").lower()

            if lang == "python":
                try:
                    tree = ast.parse(content, filename=df.path)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Try):
                            for h in node.handlers:
                                is_empty = False
                                if not h.body:
                                    is_empty = True
                                elif len(h.body) == 1 and isinstance(h.body[0], ast.Pass):
                                    is_empty = True
                                elif len(h.body) == 1 and isinstance(h.body[0], ast.Expr) and isinstance(h.body[0].value, ast.Constant) and isinstance(h.body[0].value.value, str):
                                    # Docstring / comment only inside except
                                    is_empty = True

                                if is_empty:
                                    exc_name = "Exception"
                                    if h.type:
                                        try:
                                            exc_name = ast.unparse(h.type)
                                        except Exception:
                                            exc_name = "Exception"

                                    issues.append(
                                        CodebaseIssue(
                                            id=uuid.uuid4(),
                                            rule_id=self.rule_id,
                                            rule_name=self.rule_name,
                                            category=self.category.value,
                                            severity=self.severity.value,
                                            title=f"Empty Exception Handler: except {exc_name}: pass",
                                            description=(
                                                f"Exception handler at line {h.lineno} in '{df.path}' swallows exceptions silently without logging or re-raising. "
                                                "Empty catch/except blocks conceal critical runtime failures and complicate debugging."
                                            ),
                                            file_id=fid,
                                            file_path=df.path,
                                            line_number=h.lineno,
                                            remediation_effort_minutes=self.default_remediation_minutes,
                                            metadata_json={
                                                "exception_type": exc_name,
                                                "target_type": "file",
                                                "target_identifier": df.path,
                                            },
                                        )
                                    )
                except Exception:
                    pass

            elif lang in ("javascript", "typescript"):
                # Regex search for empty catch blocks: catch (...) { }
                empty_catch_pattern = re.compile(r"catch\s*\([^)]*\)\s*\{\s*\}", re.MULTILINE)
                for match in empty_catch_pattern.finditer(content):
                    line_no = content[:match.start()].count("\n") + 1
                    issues.append(
                        CodebaseIssue(
                            id=uuid.uuid4(),
                            rule_id=self.rule_id,
                            rule_name=self.rule_name,
                            category=self.category.value,
                            severity=self.severity.value,
                            title="Empty Catch Block",
                            description=(
                                f"Empty catch block detected at line {line_no} in '{df.path}'. Swallowing errors without handling or logging "
                                "causes silent failures."
                            ),
                            file_id=fid,
                            file_path=df.path,
                            line_number=line_no,
                            remediation_effort_minutes=self.default_remediation_minutes,
                            metadata_json={
                                "target_type": "file",
                                "target_identifier": df.path,
                            },
                        )
                    )

        return issues


class DeadPrivateSymbolRule(BaseRule):
    rule_id = "HYGIENE-002"
    rule_name = "Dead Private Symbol"
    category = IssueCategory.HYGIENE
    severity = IssueSeverity.MINOR
    default_remediation_minutes = 20

    def evaluate(self, context: RuleContext) -> List[CodebaseIssue]:
        issues: List[CodebaseIssue] = []

        for item in context.parsed_files_data:
            df = item["df"]
            content = item.get("content")
            symbols = item.get("symbols", [])
            fid = context.file_id_map.get(df.path)
            fm = context.file_metrics_map.get(df.path)

            if not content or not fm or fm.sloc < 50:
                continue

            for sym in symbols:
                if sym.symbol_type in ("function", "method"):
                    name = sym.name
                    # Look for private helper _foo (not dunder __foo__)
                    if name.startswith("_") and not name.startswith("__"):
                        # Count word occurrences in file content
                        pattern = re.compile(r"\b" + re.escape(name) + r"\b")
                        matches = pattern.findall(content)
                        # If it appears only once, it's defined but never called
                        if len(matches) <= 1:
                            issues.append(
                                CodebaseIssue(
                                    id=uuid.uuid4(),
                                    rule_id=self.rule_id,
                                    rule_name=self.rule_name,
                                    category=self.category.value,
                                    severity=self.severity.value,
                                    title=f"Unused Private Helper: {name}()",
                                    description=(
                                        f"Private function '{name}' at line {sym.start_line} in '{df.path}' is declared but never referenced "
                                        "elsewhere in this file. Dead code adds maintenance burden and confusion."
                                    ),
                                    file_id=fid,
                                    file_path=df.path,
                                    line_number=sym.start_line,
                                    end_line_number=sym.end_line,
                                    symbol_name=name,
                                    remediation_effort_minutes=self.default_remediation_minutes,
                                    metadata_json={
                                        "occurrences": len(matches),
                                        "target_type": "symbol",
                                        "target_identifier": f"{df.path}::{name}",
                                    },
                                )
                            )
        return issues
