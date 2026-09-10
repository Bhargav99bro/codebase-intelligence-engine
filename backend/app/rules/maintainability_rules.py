from typing import List
import uuid

from app.rules.base import BaseRule, CodebaseIssue, IssueCategory, IssueSeverity, RuleContext


class VeryLowMaintainabilityRule(BaseRule):
    rule_id = "MAINT-001"
    rule_name = "Very Low Maintainability"
    category = IssueCategory.MAINTAINABILITY
    severity = IssueSeverity.CRITICAL
    default_remediation_minutes = 90

    def evaluate(self, context: RuleContext) -> List[CodebaseIssue]:
        issues: List[CodebaseIssue] = []
        for file_path, fm in context.file_metrics_map.items():
            if fm.maintainability_score < 40.0:
                fid = context.file_id_map.get(file_path)
                issues.append(
                    CodebaseIssue(
                        id=uuid.uuid4(),
                        rule_id=self.rule_id,
                        rule_name=self.rule_name,
                        category=self.category.value,
                        severity=self.severity.value,
                        title=f"Critically Low Maintainability: {file_path} (MI={fm.maintainability_score:.1f})",
                        description=(
                            f"File '{file_path}' has an unacceptably low Maintainability Index of {fm.maintainability_score:.1f} (threshold < 40.0). "
                            "Code in this range is severely complex, dense with branching, and represents an immediate technical debt hazard."
                        ),
                        file_id=fid,
                        file_path=file_path,
                        remediation_effort_minutes=self.default_remediation_minutes,
                        metadata_json={
                            "maintainability_score": fm.maintainability_score,
                            "sloc": fm.sloc,
                            "cyclomatic_complexity": fm.total_cyclomatic_complexity,
                            "target_type": "file",
                            "target_identifier": file_path,
                        },
                    )
                )
        return issues


class PoorMaintainabilityRule(BaseRule):
    rule_id = "MAINT-002"
    rule_name = "Poor Maintainability"
    category = IssueCategory.MAINTAINABILITY
    severity = IssueSeverity.MAJOR
    default_remediation_minutes = 45

    def evaluate(self, context: RuleContext) -> List[CodebaseIssue]:
        issues: List[CodebaseIssue] = []
        for file_path, fm in context.file_metrics_map.items():
            if 40.0 <= fm.maintainability_score < 55.0:
                fid = context.file_id_map.get(file_path)
                issues.append(
                    CodebaseIssue(
                        id=uuid.uuid4(),
                        rule_id=self.rule_id,
                        rule_name=self.rule_name,
                        category=self.category.value,
                        severity=self.severity.value,
                        title=f"Poor Maintainability: {file_path} (MI={fm.maintainability_score:.1f})",
                        description=(
                            f"File '{file_path}' has a low Maintainability Index of {fm.maintainability_score:.1f} (threshold 40.0-54.9). "
                            "Refactoring functions and simplifying control structures will significantly reduce maintenance cost."
                        ),
                        file_id=fid,
                        file_path=file_path,
                        remediation_effort_minutes=self.default_remediation_minutes,
                        metadata_json={
                            "maintainability_score": fm.maintainability_score,
                            "sloc": fm.sloc,
                            "cyclomatic_complexity": fm.total_cyclomatic_complexity,
                            "target_type": "file",
                            "target_identifier": file_path,
                        },
                    )
                )
        return issues


class UndocumentedPublicAPIRule(BaseRule):
    rule_id = "MAINT-003"
    rule_name = "Undocumented Public API"
    category = IssueCategory.MAINTAINABILITY
    severity = IssueSeverity.MINOR
    default_remediation_minutes = 15

    def evaluate(self, context: RuleContext) -> List[CodebaseIssue]:
        issues: List[CodebaseIssue] = []
        for item in context.parsed_files_data:
            df = item["df"]
            symbols = item.get("symbols", [])
            fid = context.file_id_map.get(df.path)

            for sym in symbols:
                if sym.symbol_type in ("function", "class"):
                    # Check if public (does not start with _)
                    if not sym.name.startswith("_"):
                        has_doc = bool(sym.metadata_json and sym.metadata_json.get("docstring"))
                        if not has_doc:
                            issues.append(
                                CodebaseIssue(
                                    id=uuid.uuid4(),
                                    rule_id=self.rule_id,
                                    rule_name=self.rule_name,
                                    category=self.category.value,
                                    severity=self.severity.value,
                                    title=f"Undocumented Public {sym.symbol_type.capitalize()}: {sym.name}",
                                    description=(
                                        f"Public {sym.symbol_type} '{sym.name}' in '{df.path}' has no docstring or documentation comment. "
                                        "Documenting public interfaces improves developer velocity and reduces onboarding time."
                                    ),
                                    file_id=fid,
                                    file_path=df.path,
                                    line_number=sym.start_line,
                                    end_line_number=sym.end_line,
                                    symbol_name=sym.name,
                                    remediation_effort_minutes=self.default_remediation_minutes,
                                    metadata_json={
                                        "symbol_type": sym.symbol_type,
                                        "target_type": "symbol",
                                        "target_identifier": f"{df.path}::{sym.name}",
                                    },
                                )
                            )
        return issues


class DuplicateBlockRule(BaseRule):
    rule_id = "DUP-001"
    rule_name = "Duplicate Code Block Detected"
    category = IssueCategory.MAINTAINABILITY
    severity = IssueSeverity.MAJOR
    default_remediation_minutes = 45

    SEVERITY_THRESHOLDS = {
        IssueSeverity.CRITICAL.value: {"min_lines": 50, "threshold_effort_minutes": 120},
        IssueSeverity.MAJOR.value: {"min_lines": 15, "threshold_effort_minutes": 45},
        IssueSeverity.MINOR.value: {"min_lines": 10, "threshold_effort_minutes": 30},
    }

    def evaluate(self, context: RuleContext) -> List[CodebaseIssue]:
        issues: List[CodebaseIssue] = []
        if not context.code_duplicates:
            return issues

        for dup in context.code_duplicates:
            line_count = getattr(dup, "line_count", 0) if not isinstance(dup, dict) else dup.get("line_count", 0)
            if line_count >= 50:
                sev = IssueSeverity.CRITICAL.value
                threshold_effort = 120
            elif line_count >= 15:
                sev = IssueSeverity.MAJOR.value
                threshold_effort = 45
            elif line_count >= 10:
                sev = IssueSeverity.MINOR.value
                threshold_effort = 30
            else:
                continue

            remediation = line_count * 2
            source_file = getattr(dup, "source_file_path", "") if not isinstance(dup, dict) else dup.get("source_file_path", "")
            target_file = getattr(dup, "target_file_path", "") if not isinstance(dup, dict) else dup.get("target_file_path", "")
            source_start = getattr(dup, "source_start_line", 1) if not isinstance(dup, dict) else dup.get("source_start_line", 1)
            source_end = getattr(dup, "source_end_line", 1) if not isinstance(dup, dict) else dup.get("source_end_line", 1)
            target_start = getattr(dup, "target_start_line", 1) if not isinstance(dup, dict) else dup.get("target_start_line", 1)
            target_end = getattr(dup, "target_end_line", 1) if not isinstance(dup, dict) else dup.get("target_end_line", 1)
            clone_type = getattr(dup, "clone_type", 1) if not isinstance(dup, dict) else dup.get("clone_type", 1)
            token_count = getattr(dup, "token_count", 0) if not isinstance(dup, dict) else dup.get("token_count", 0)

            fid = context.file_id_map.get(source_file)

            issues.append(
                CodebaseIssue(
                    id=uuid.uuid4(),
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    category=self.category.value,
                    severity=sev,
                    title=f"Duplicate Code Block ({line_count} lines, Type-{clone_type})",
                    description=(
                        f"A code block of {line_count} lines ({token_count} tokens) in '{source_file}' "
                        f"(lines {source_start}-{source_end}) is duplicated in '{target_file}' (lines {target_start}-{target_end}). "
                        f"Duplicated logic increases maintenance overhead and bug propagation risks. Refactor into a shared abstraction."
                    ),
                    file_id=fid,
                    file_path=source_file,
                    line_number=source_start,
                    end_line_number=source_end,
                    symbol_name=None,
                    remediation_effort_minutes=remediation,
                    metadata_json={
                        "clone_type": clone_type,
                        "line_count": line_count,
                        "token_count": token_count,
                        "target_file_path": target_file,
                        "target_start_line": target_start,
                        "target_end_line": target_end,
                        "target_type": "code_block",
                        "target_identifier": f"{source_file}:{source_start}-{source_end}",
                        "threshold_remediation_minutes": threshold_effort,
                        "severity_threshold_effort_minutes": {
                            k: v["threshold_effort_minutes"] for k, v in self.SEVERITY_THRESHOLDS.items()
                        },
                    },
                )
            )
        return issues
