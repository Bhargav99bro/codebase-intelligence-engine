import copy
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import uuid

from app.dependencies.graph import DirectedDependencyGraph
from app.health.calculator import HealthCalculator, HealthScoreBreakdown
from app.metrics.base import FileMetrics, SymbolMetrics
from app.rules.base import CodebaseIssue, IssueSeverity


@dataclass
class RecommendationItem:
    rank: int
    target_identifier: str
    target_type: str  # "symbol", "file", "cycle"
    file_path: Optional[str]
    title: str
    action_summary: str
    resolved_rule_ids: List[str]
    resolved_issue_count: int
    estimated_score_recovery: Optional[float]
    estimated_effort_minutes: int
    qualitative: bool = False
    metadata_json: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        target_name = self.target_identifier.split("::")[-1] if "::" in self.target_identifier else self.target_identifier
        return {
            "id": f"rec-{self.rank}-{self.target_type}",
            "rank": self.rank,
            "target_identifier": self.target_identifier,
            "target_id": self.target_identifier,
            "target_name": target_name,
            "target_type": self.target_type,
            "file_path": self.file_path,
            "title": self.title,
            "summary": self.action_summary,
            "action_summary": self.action_summary,
            "rationale": f"Resolves {self.resolved_issue_count} issues ({', '.join(self.resolved_rule_ids[:4])}).",
            "effort_hours": round(self.estimated_effort_minutes / 60.0, 1),
            "estimated_effort_minutes": self.estimated_effort_minutes,
            "current_health_impact": self.estimated_score_recovery or 0.0,
            "expected_score_recovery": self.estimated_score_recovery,
            "estimated_score_recovery": self.estimated_score_recovery,
            "primary_category": (
                "architecture" if self.target_type == "cycle" or any(r.startswith("ARCH-") for r in self.resolved_rule_ids)
                else "complexity" if any(r.startswith("COMPLEX-") for r in self.resolved_rule_ids)
                else "hygiene" if any(r.startswith("HYGIENE-") for r in self.resolved_rule_ids)
                else "security" if any(r.startswith("SEC-") for r in self.resolved_rule_ids)
                else "maintainability"
            ),
            "resolved_rule_ids": self.resolved_rule_ids,
            "related_issue_ids": self.resolved_rule_ids,
            "resolved_issue_count": self.resolved_issue_count,
            "qualitative": self.qualitative,
            "metadata_json": self.metadata_json,
        }


class RecommendationEngine:
    """Ranks refactoring targets using deterministic counterfactual metric simulation."""

    def __init__(self, calculator: Optional[HealthCalculator] = None) -> None:
        self.calculator = calculator or HealthCalculator()

    def generate_recommendations(
        self,
        current_health: HealthScoreBreakdown,
        file_metrics_map: Dict[str, FileMetrics],
        parsed_files_data: List[Dict[str, Any]],
        graph: DirectedDependencyGraph,
        issues: List[CodebaseIssue],
        max_recommendations: int = 5,
        max_candidates: int = 25,
    ) -> List[RecommendationItem]:
        if not issues:
            return []

        # 1. Group issues by refactoring target
        target_groups: Dict[str, Dict[str, Any]] = {}
        for iss in issues:
            meta = iss.metadata_json or {}
            target_id = meta.get("target_identifier") or iss.file_path or "repository"
            target_type = meta.get("target_type") or "file"

            if target_id not in target_groups:
                target_groups[target_id] = {
                    "target_identifier": target_id,
                    "target_type": target_type,
                    "file_path": iss.file_path,
                    "symbol_name": iss.symbol_name,
                    "issues": [],
                }
            target_groups[target_id]["issues"].append(iss)

        # 2. Select top candidate targets for counterfactual simulation (capped at K=25)
        severity_weights = {
            IssueSeverity.BLOCKER.value: 4,
            IssueSeverity.CRITICAL.value: 3,
            IssueSeverity.MAJOR.value: 2,
            IssueSeverity.MINOR.value: 1,
            IssueSeverity.INFO.value: 0,
        }

        candidate_list = list(target_groups.values())
        candidate_list.sort(
            key=lambda grp: (
                -sum(1 for i in grp["issues"] if i.severity == IssueSeverity.BLOCKER.value),
                -sum(1 for i in grp["issues"] if i.severity == IssueSeverity.CRITICAL.value),
                -sum(1 for i in grp["issues"] if i.severity == IssueSeverity.MAJOR.value),
                -sum(1 for i in grp["issues"] if i.severity == IssueSeverity.MINOR.value),
                -sum(i.remediation_effort_minutes for i in grp["issues"]),
                grp["target_identifier"],
            ),
        )
        candidates = candidate_list[:max_candidates]

        # 2b. Precompute base public symbol documentation counts once (avoids 25x deepcopy of parsed_files_data)
        base_total_public_symbols = 0
        base_documented_public_symbols = 0
        if parsed_files_data:
            for item in parsed_files_data:
                for sym in item.get("symbols", []):
                    if sym.symbol_type in ("function", "class") and not sym.name.startswith("_"):
                        base_total_public_symbols += 1
                        if sym.metadata_json and sym.metadata_json.get("docstring"):
                            base_documented_public_symbols += 1

        # 3. Simulate counterfactual metric improvement for each candidate target
        evaluated_candidates = []

        for cand in candidates:
            target_id = cand["target_identifier"]
            target_type = cand["target_type"]
            cand_issues = cand["issues"]
            rule_ids = sorted(list(set(i.rule_id for i in cand_issues)))

            # Shallow copy the metrics map; only clone the single FileMetrics if modified
            simulated_metrics_map = dict(file_metrics_map)
            simulated_issues = [i for i in issues if i not in cand_issues]
            cand_total_pub = base_total_public_symbols
            cand_doc_pub = base_documented_public_symbols

            is_qualitative = False
            has_metric_change = False

            # Model Complexity Improvements
            if any(r.startswith("COMPLEX-") for r in rule_ids) and cand.get("file_path") and cand.get("symbol_name"):
                fp = cand["file_path"]
                sym_name = cand["symbol_name"]
                if fp in simulated_metrics_map:
                    fm = copy.deepcopy(file_metrics_map[fp])
                    simulated_metrics_map[fp] = fm
                    for sm in fm.symbols_metrics:
                        if sm.name == sym_name:
                            # Modeled refactoring reduces CC to threshold (10) and nesting to 3
                            sm.cyclomatic_complexity = min(sm.cyclomatic_complexity, 10)
                            sm.nesting_depth = min(sm.nesting_depth, 3)
                            has_metric_change = True

            # Model Architecture Cycle Improvements
            simulated_graph = graph
            if any(r == "ARCH-001" for r in rule_ids):
                # Simulate cycle elimination
                simulated_graph = copy.copy(graph)
                meta = cand_issues[0].metadata_json if cand_issues else {}
                cycle_id = meta.get("cycle_id")
                simulated_graph.cycles = [c for c in graph.cycles if c.cycle_id != cycle_id]
                has_metric_change = True

            # Model Maintainability Documentation Improvements
            if any(r == "MAINT-003" for r in rule_ids):
                cand_doc_pub = min(cand_total_pub, base_documented_public_symbols + 1)
                has_metric_change = True

            # Model Hygiene, Security & Duplication Improvements
            if any(r.startswith("SEC-") or r.startswith("HYGIENE-") or r.startswith("ARCH-002") or r.startswith("ARCH-003") or r == "DUP-001" for r in rule_ids):
                has_metric_change = True

            # Recalculate counterfactual health score
            if has_metric_change:
                dup_ratio = getattr(current_health, "duplication_ratio", 0.0)
                dup_blocks = getattr(current_health, "duplicate_blocks_count", 0)
                dup_lines = getattr(current_health, "duplicate_lines_count", 0)
                dup_resolved_count = sum(1 for i in cand_issues if i.rule_id == "DUP-001")
                if dup_resolved_count > 0:
                    dup_blocks = max(0, dup_blocks - dup_resolved_count)

                simulated_health = self.calculator.compute(
                    file_metrics_map=simulated_metrics_map,
                    parsed_files_data=None,
                    graph=simulated_graph,
                    issues=simulated_issues,
                    duplication_ratio=dup_ratio,
                    duplicate_blocks_count=dup_blocks,
                    duplicate_lines_count=dup_lines,
                    public_symbol_counts=(cand_total_pub, cand_doc_pub),
                )
                delta_s = round(max(0.0, simulated_health.overall_score - current_health.overall_score), 1)
            else:
                is_qualitative = True
                delta_s = None

            total_severity = sum(severity_weights.get(i.severity, 0) for i in cand_issues)
            total_debt_reduction = sum(i.remediation_effort_minutes for i in cand_issues)

            n_blocker = sum(1 for i in cand_issues if i.severity == IssueSeverity.BLOCKER.value)
            n_critical = sum(1 for i in cand_issues if i.severity == IssueSeverity.CRITICAL.value)
            n_major = sum(1 for i in cand_issues if i.severity == IssueSeverity.MAJOR.value)
            n_minor = sum(1 for i in cand_issues if i.severity == IssueSeverity.MINOR.value)

            # Generate descriptive title and action plan
            if target_type == "symbol":
                title = f"Refactor complex method {cand.get('symbol_name')}() in {cand.get('file_path')}"
                action = (
                    f"Decompose {cand.get('symbol_name')}() to reduce branching complexity, "
                    f"flatten nesting levels, and resolve {len(rule_ids)} flagged complexity smells."
                )
            elif target_type == "cycle":
                title = f"Break circular dependency in Cycle #{cand_issues[0].metadata_json.get('cycle_id', 1)}"
                action = (
                    "Invert or decouple imports between cyclical modules using dependency inversion or an interface module."
                )
            else:
                title = f"Address structural issues in {cand.get('file_path')}"
                action = f"Refactor {cand.get('file_path')} to eliminate {len(cand_issues)} issues ({', '.join(rule_ids[:3])})."

            evaluated_candidates.append({
                "target_identifier": target_id,
                "target_type": target_type,
                "file_path": cand.get("file_path"),
                "title": title,
                "action_summary": action,
                "resolved_rule_ids": rule_ids,
                "resolved_issue_count": len(cand_issues),
                "estimated_score_recovery": delta_s,
                "estimated_effort_minutes": total_debt_reduction,
                "qualitative": is_qualitative,
                "severity_score": total_severity,
                "n_blocker": n_blocker,
                "n_critical": n_critical,
                "n_major": n_major,
                "n_minor": n_minor,
            })

        # 4. Deterministic Ranking Tuple:
        # 1. Delta S descending (None / null last)
        # 2. Severity score descending: BLOCKER > CRITICAL > MAJOR > MINOR
        # 3. Debt reduction (remediation effort minutes) descending
        # 4. Canonical target identifier ascending (tie breaker)
        evaluated_candidates.sort(
            key=lambda it: (
                0 if it["estimated_score_recovery"] is not None else 1,
                -(it["estimated_score_recovery"] or 0.0),
                -it["n_blocker"],
                -it["n_critical"],
                -it["n_major"],
                -it["n_minor"],
                -it["estimated_effort_minutes"],
                it["target_identifier"],
            ),
        )

        results: List[RecommendationItem] = []
        for rank_idx, item in enumerate(evaluated_candidates[:max_recommendations], start=1):
            results.append(
                RecommendationItem(
                    rank=rank_idx,
                    target_identifier=item["target_identifier"],
                    target_type=item["target_type"],
                    file_path=item["file_path"],
                    title=item["title"],
                    action_summary=item["action_summary"],
                    resolved_rule_ids=item["resolved_rule_ids"],
                    resolved_issue_count=item["resolved_issue_count"],
                    estimated_score_recovery=item["estimated_score_recovery"],
                    estimated_effort_minutes=item["estimated_effort_minutes"],
                    qualitative=item["qualitative"],
                )
            )

        return results
