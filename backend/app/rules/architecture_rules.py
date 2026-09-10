from typing import List
import uuid

from app.rules.base import BaseRule, CodebaseIssue, IssueCategory, IssueSeverity, RuleContext


class CyclicDependencyRule(BaseRule):
    rule_id = "ARCH-001"
    rule_name = "Cyclic Dependency"
    category = IssueCategory.ARCHITECTURE
    severity = IssueSeverity.CRITICAL
    default_remediation_minutes = 120

    def evaluate(self, context: RuleContext) -> List[CodebaseIssue]:
        issues: List[CodebaseIssue] = []
        for cycle in context.graph.cycles:
            cycle_path_str = " -> ".join(cycle.file_paths) + f" -> {cycle.file_paths[0]}"
            primary_file_path = cycle.file_paths[0]
            primary_file_id = context.file_id_map.get(primary_file_path)

            issues.append(
                CodebaseIssue(
                    id=uuid.uuid4(),
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    category=self.category.value,
                    severity=self.severity.value,
                    title=f"Circular dependency loop: Cycle #{cycle.cycle_id} ({cycle.length} files)",
                    description=(
                        f"Detected mutually recursive or transitive circular import chain: {cycle_path_str}. "
                        "Circular dependencies introduce tight coupling, prevent modular testing, and cause initialization order bugs."
                    ),
                    file_id=primary_file_id,
                    file_path=primary_file_path,
                    remediation_effort_minutes=self.default_remediation_minutes,
                    metadata_json={
                        "cycle_id": cycle.cycle_id,
                        "length": cycle.length,
                        "file_paths": cycle.file_paths,
                        "target_type": "cycle",
                        "target_identifier": f"cycle::{cycle.cycle_id}",
                    },
                )
            )
        return issues


class GodModuleRule(BaseRule):
    rule_id = "ARCH-002"
    rule_name = "God Module / Component"
    category = IssueCategory.ARCHITECTURE
    severity = IssueSeverity.MAJOR
    default_remediation_minutes = 90

    def evaluate(self, context: RuleContext) -> List[CodebaseIssue]:
        issues: List[CodebaseIssue] = []
        for file_path, fm in context.file_metrics_map.items():
            fid = context.file_id_map.get(file_path)
            if not fid or fid not in context.graph.nodes:
                continue

            node = context.graph.nodes[fid]
            if node.fan_out >= 12 and fm.sloc >= 500:
                issues.append(
                    CodebaseIssue(
                        id=uuid.uuid4(),
                        rule_id=self.rule_id,
                        rule_name=self.rule_name,
                        category=self.category.value,
                        severity=self.severity.value,
                        title=f"God Module: {file_path} (Fan-Out: {node.fan_out}, SLOC: {fm.sloc})",
                        description=(
                            f"File '{file_path}' combines excessive responsibilities: it has {node.fan_out} outgoing dependencies "
                            f"and {fm.sloc} source lines of code. Consider decomposing into cohesive domain modules."
                        ),
                        file_id=fid,
                        file_path=file_path,
                        remediation_effort_minutes=self.default_remediation_minutes,
                        metadata_json={
                            "fan_out": node.fan_out,
                            "sloc": fm.sloc,
                            "target_type": "file",
                            "target_identifier": file_path,
                        },
                    )
                )
        return issues


class UnstableHubRule(BaseRule):
    rule_id = "ARCH-003"
    rule_name = "Unstable Hub"
    category = IssueCategory.ARCHITECTURE
    severity = IssueSeverity.MAJOR
    default_remediation_minutes = 90

    def evaluate(self, context: RuleContext) -> List[CodebaseIssue]:
        issues: List[CodebaseIssue] = []
        for fid, node in context.graph.nodes.items():
            if node.fan_in >= 8 and node.fan_out >= 8:
                issues.append(
                    CodebaseIssue(
                        id=uuid.uuid4(),
                        rule_id=self.rule_id,
                        rule_name=self.rule_name,
                        category=self.category.value,
                        severity=self.severity.value,
                        title=f"Unstable Hub: {node.file_path} (Fan-In: {node.fan_in}, Fan-Out: {node.fan_out})",
                        description=(
                            f"File '{node.file_path}' has high bidirectional coupling with {node.fan_in} incoming and "
                            f"{node.fan_out} outgoing internal dependencies. Changes to it cause wide ripple effects."
                        ),
                        file_id=fid,
                        file_path=node.file_path,
                        remediation_effort_minutes=self.default_remediation_minutes,
                        metadata_json={
                            "fan_in": node.fan_in,
                            "fan_out": node.fan_out,
                            "instability": node.instability,
                            "target_type": "file",
                            "target_identifier": node.file_path,
                        },
                    )
                )
        return issues


class UnstableDependencyRule(BaseRule):
    rule_id = "ARCH-004"
    rule_name = "Unstable Dependency (SAP Violation)"
    category = IssueCategory.ARCHITECTURE
    severity = IssueSeverity.MINOR
    default_remediation_minutes = 45

    def evaluate(self, context: RuleContext) -> List[CodebaseIssue]:
        issues: List[CodebaseIssue] = []
        seen_pairs = set()

        for edge in context.graph.edges:
            src_id = edge.source_file_id
            tgt_id = edge.target_file_id
            if (src_id, tgt_id) in seen_pairs:
                continue
            seen_pairs.add((src_id, tgt_id))

            src_node = context.graph.nodes.get(src_id)
            tgt_node = context.graph.nodes.get(tgt_id)

            if src_node and tgt_node:
                # Stable module depending on unstable module
                if src_node.instability < 0.25 and src_node.fan_in >= 5 and tgt_node.instability > 0.75:
                    issues.append(
                        CodebaseIssue(
                            id=uuid.uuid4(),
                            rule_id=self.rule_id,
                            rule_name=self.rule_name,
                            category=self.category.value,
                            severity=self.severity.value,
                            title=f"Unstable Dependency: {src_node.file_path} -> {tgt_node.file_path}",
                            description=(
                                f"Stable module '{src_node.file_path}' (I={src_node.instability:.2f}, Fan-In={src_node.fan_in}) "
                                f"depends on volatile module '{tgt_node.file_path}' (I={tgt_node.instability:.2f}). "
                                "This violates the Stable Dependencies Principle (SDP) and threatens system stability."
                            ),
                            file_id=src_id,
                            file_path=src_node.file_path,
                            line_number=edge.line_number,
                            remediation_effort_minutes=self.default_remediation_minutes,
                            metadata_json={
                                "source_instability": src_node.instability,
                                "target_instability": tgt_node.instability,
                                "target_file_path": tgt_node.file_path,
                                "target_type": "file",
                                "target_identifier": src_node.file_path,
                            },
                        )
                    )
        return issues
