from typing import List
import uuid

from app.rules.base import BaseRule, CodebaseIssue, IssueCategory, IssueSeverity, RuleContext


class CriticalComplexityMethodRule(BaseRule):
    rule_id = "COMPLEX-001"
    rule_name = "Critical Complexity Method"
    category = IssueCategory.COMPLEXITY
    severity = IssueSeverity.CRITICAL
    default_remediation_minutes = 90

    def evaluate(self, context: RuleContext) -> List[CodebaseIssue]:
        issues: List[CodebaseIssue] = []
        for file_path, fm in context.file_metrics_map.items():
            fid = context.file_id_map.get(file_path)
            for sm in fm.symbols_metrics:
                if sm.cyclomatic_complexity >= 20:
                    issues.append(
                        CodebaseIssue(
                            id=uuid.uuid4(),
                            rule_id=self.rule_id,
                            rule_name=self.rule_name,
                            category=self.category.value,
                            severity=self.severity.value,
                            title=f"Critical Cyclomatic Complexity in {sm.name}() (CC={sm.cyclomatic_complexity})",
                            description=(
                                f"Function/method '{sm.name}' has a Cyclomatic Complexity of {sm.cyclomatic_complexity} (threshold >= 20). "
                                "Functions with critical complexity are error-prone, untestable without combinatorial test cases, and high maintenance risks."
                            ),
                            file_id=fid,
                            file_path=file_path,
                            line_number=sm.start_line,
                            end_line_number=sm.end_line,
                            symbol_name=sm.name,
                            remediation_effort_minutes=self.default_remediation_minutes,
                            metadata_json={
                                "cyclomatic_complexity": sm.cyclomatic_complexity,
                                "lines_of_code": sm.lines_of_code,
                                "nesting_depth": sm.nesting_depth,
                                "target_type": "symbol",
                                "target_identifier": f"{file_path}::{sm.name}",
                            },
                        )
                    )
        return issues


class HighComplexityMethodRule(BaseRule):
    rule_id = "COMPLEX-002"
    rule_name = "High Complexity Method"
    category = IssueCategory.COMPLEXITY
    severity = IssueSeverity.MAJOR
    default_remediation_minutes = 45

    def evaluate(self, context: RuleContext) -> List[CodebaseIssue]:
        issues: List[CodebaseIssue] = []
        for file_path, fm in context.file_metrics_map.items():
            fid = context.file_id_map.get(file_path)
            for sm in fm.symbols_metrics:
                if 11 <= sm.cyclomatic_complexity < 20:
                    issues.append(
                        CodebaseIssue(
                            id=uuid.uuid4(),
                            rule_id=self.rule_id,
                            rule_name=self.rule_name,
                            category=self.category.value,
                            severity=self.severity.value,
                            title=f"High Cyclomatic Complexity in {sm.name}() (CC={sm.cyclomatic_complexity})",
                            description=(
                                f"Function/method '{sm.name}' has a Cyclomatic Complexity of {sm.cyclomatic_complexity} (threshold 11-19). "
                                "Consider breaking down conditional branches into smaller helper functions."
                            ),
                            file_id=fid,
                            file_path=file_path,
                            line_number=sm.start_line,
                            end_line_number=sm.end_line,
                            symbol_name=sm.name,
                            remediation_effort_minutes=self.default_remediation_minutes,
                            metadata_json={
                                "cyclomatic_complexity": sm.cyclomatic_complexity,
                                "lines_of_code": sm.lines_of_code,
                                "target_type": "symbol",
                                "target_identifier": f"{file_path}::{sm.name}",
                            },
                        )
                    )
        return issues


class DeepNestingRule(BaseRule):
    rule_id = "COMPLEX-003"
    rule_name = "Deep Nesting Smell"
    category = IssueCategory.COMPLEXITY
    severity = IssueSeverity.MAJOR
    default_remediation_minutes = 45

    def evaluate(self, context: RuleContext) -> List[CodebaseIssue]:
        issues: List[CodebaseIssue] = []
        for file_path, fm in context.file_metrics_map.items():
            fid = context.file_id_map.get(file_path)
            for sm in fm.symbols_metrics:
                if sm.nesting_depth >= 5:
                    issues.append(
                        CodebaseIssue(
                            id=uuid.uuid4(),
                            rule_id=self.rule_id,
                            rule_name=self.rule_name,
                            category=self.category.value,
                            severity=self.severity.value,
                            title=f"Deep Nesting in {sm.name}() (Depth={sm.nesting_depth})",
                            description=(
                                f"Function/method '{sm.name}' contains a maximum nesting depth of {sm.nesting_depth} (threshold >= 5). "
                                "Deeply nested code increases cognitive load and hides edge cases. Use guard clauses or extract helper methods."
                            ),
                            file_id=fid,
                            file_path=file_path,
                            line_number=sm.start_line,
                            end_line_number=sm.end_line,
                            symbol_name=sm.name,
                            remediation_effort_minutes=self.default_remediation_minutes,
                            metadata_json={
                                "nesting_depth": sm.nesting_depth,
                                "target_type": "symbol",
                                "target_identifier": f"{file_path}::{sm.name}",
                            },
                        )
                    )
        return issues


class GiantFileRule(BaseRule):
    rule_id = "COMPLEX-004"
    rule_name = "Giant File / Low Cohesion"
    category = IssueCategory.COMPLEXITY
    severity = IssueSeverity.MAJOR
    default_remediation_minutes = 60

    def evaluate(self, context: RuleContext) -> List[CodebaseIssue]:
        issues: List[CodebaseIssue] = []
        for file_path, fm in context.file_metrics_map.items():
            if fm.sloc >= 800:
                fid = context.file_id_map.get(file_path)
                issues.append(
                    CodebaseIssue(
                        id=uuid.uuid4(),
                        rule_id=self.rule_id,
                        rule_name=self.rule_name,
                        category=self.category.value,
                        severity=self.severity.value,
                        title=f"Giant File: {file_path} ({fm.sloc} SLOC)",
                        description=(
                            f"File '{file_path}' contains {fm.sloc} source lines of code (threshold >= 800 SLOC). "
                            "Large files often violate the Single Responsibility Principle and lead to merge conflicts."
                        ),
                        file_id=fid,
                        file_path=file_path,
                        remediation_effort_minutes=self.default_remediation_minutes,
                        metadata_json={
                            "sloc": fm.sloc,
                            "total_lines": fm.total_lines,
                            "target_type": "file",
                            "target_identifier": file_path,
                        },
                    )
                )
        return issues


class LongParameterListRule(BaseRule):
    rule_id = "COMPLEX-005"
    rule_name = "Long Parameter List"
    category = IssueCategory.COMPLEXITY
    severity = IssueSeverity.MINOR
    default_remediation_minutes = 30

    def evaluate(self, context: RuleContext) -> List[CodebaseIssue]:
        issues: List[CodebaseIssue] = []
        for file_path, fm in context.file_metrics_map.items():
            fid = context.file_id_map.get(file_path)
            for sm in fm.symbols_metrics:
                if sm.parameter_count >= 6:
                    issues.append(
                        CodebaseIssue(
                            id=uuid.uuid4(),
                            rule_id=self.rule_id,
                            rule_name=self.rule_name,
                            category=self.category.value,
                            severity=self.severity.value,
                            title=f"Long Parameter List in {sm.name}() ({sm.parameter_count} params)",
                            description=(
                                f"Function/method '{sm.name}' declares {sm.parameter_count} parameters (threshold >= 6). "
                                "Functions with too many parameters are difficult to understand and call correctly. Group related parameters into a config object or dataclass."
                            ),
                            file_id=fid,
                            file_path=file_path,
                            line_number=sm.start_line,
                            end_line_number=sm.end_line,
                            symbol_name=sm.name,
                            remediation_effort_minutes=self.default_remediation_minutes,
                            metadata_json={
                                "parameter_count": sm.parameter_count,
                                "target_type": "symbol",
                                "target_identifier": f"{file_path}::{sm.name}",
                            },
                        )
                    )
        return issues
