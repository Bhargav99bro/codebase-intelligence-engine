from dataclasses import dataclass, field
import math
from typing import Any, Dict, List, Optional, Tuple
import uuid

from app.dependencies.graph import DirectedDependencyGraph
from app.metrics.base import FileMetrics
from app.rules.base import CodebaseIssue, IssueCategory, IssueSeverity


def clamp(val: float, min_val: float, max_val: float) -> float:
    return max(min_val, min(max_val, val))


@dataclass
class HealthScoreBreakdown:
    overall_score: float
    grade: str
    maintainability_score: float
    complexity_score: float
    architecture_score: float
    hygiene_score: float
    duplication_score: float = 100.0
    duplication_ratio: float = 0.0
    duplicate_blocks_count: int = 0
    duplicate_lines_count: int = 0
    technical_debt_minutes: int = 0
    debt_ratio_hours_per_ksloc: float = 0.0
    total_issues_count: int = 0
    blocker_count: int = 0
    critical_count: int = 0
    major_count: int = 0
    minor_count: int = 0
    info_count: int = 0
    category_scores: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_score": self.overall_score,
            "grade": self.grade,
            "maintainability_score": self.maintainability_score,
            "complexity_score": self.complexity_score,
            "architecture_score": self.architecture_score,
            "hygiene_score": self.hygiene_score,
            "duplication_score": self.duplication_score,
            "duplication_ratio": self.duplication_ratio,
            "duplicate_blocks_count": self.duplicate_blocks_count,
            "duplicate_lines_count": self.duplicate_lines_count,
            "technical_debt_minutes": self.technical_debt_minutes,
            "debt_ratio_hours_per_ksloc": self.debt_ratio_hours_per_ksloc,
            "total_issues_count": self.total_issues_count,
            "blocker_count": self.blocker_count,
            "critical_count": self.critical_count,
            "major_count": self.major_count,
            "minor_count": self.minor_count,
            "info_count": self.info_count,
            "category_scores": self.category_scores,
        }


class HealthCalculator:
    """Computes deterministic 0-100 repository health score and letter grades using exact formulas."""

    @staticmethod
    def calculate_grade(score: float) -> str:
        if score >= 95.0:
            return "A+"
        if score >= 90.0:
            return "A"
        if score >= 80.0:
            return "B"
        if score >= 70.0:
            return "C"
        if score >= 60.0:
            return "D"
        return "F"

    @staticmethod
    def calculate_maintainability_score(
        file_metrics_map: Dict[str, FileMetrics],
        parsed_files_data: Optional[List[Dict[str, Any]]] = None,
        public_symbol_counts: Optional[Tuple[int, int]] = None,
    ) -> float:
        analyzed_files = [fm for fm in file_metrics_map.values() if fm.total_lines > 0 or fm.sloc > 0]
        n_analyzed = len(analyzed_files)

        if n_analyzed == 0:
            return 100.0

        mean_mi = sum(fm.maintainability_score for fm in analyzed_files) / n_analyzed
        low_mi_count = sum(1 for fm in analyzed_files if fm.maintainability_score < 40.0)
        p_low_mi = low_mi_count / n_analyzed

        # Documentation ratio
        if public_symbol_counts is not None:
            total_public_symbols, documented_public_symbols = public_symbol_counts
        else:
            total_public_symbols = 0
            documented_public_symbols = 0

            if parsed_files_data:
                for item in parsed_files_data:
                    symbols = item.get("symbols", [])
                    for sym in symbols:
                        if sym.symbol_type in ("function", "class"):
                            if not sym.name.startswith("_"):
                                total_public_symbols += 1
                                if sym.metadata_json and sym.metadata_json.get("docstring"):
                                    documented_public_symbols += 1

        r_doc = (documented_public_symbols / total_public_symbols) if total_public_symbols > 0 else 1.0

        score = 0.70 * mean_mi + 0.30 * (r_doc * 100.0) - (p_low_mi * 25.0)
        return round(clamp(score, 0.0, 100.0), 1)

    @staticmethod
    def calculate_complexity_score(file_metrics_map: Dict[str, FileMetrics]) -> float:
        all_funcs = []
        for fm in file_metrics_map.values():
            all_funcs.extend(fm.symbols_metrics)

        n_funcs = len(all_funcs)
        if n_funcs == 0:
            return 100.0

        n_mod = sum(1 for s in all_funcs if 6 <= s.cyclomatic_complexity <= 10)
        n_high = sum(1 for s in all_funcs if 11 <= s.cyclomatic_complexity < 20)
        n_vhigh = sum(1 for s in all_funcs if s.cyclomatic_complexity >= 20)

        f_mod = n_mod / n_funcs
        f_high = n_high / n_funcs
        f_vhigh = n_vhigh / n_funcs

        cc_max = max((s.cyclomatic_complexity for s in all_funcs), default=1)
        d_nest_max = max((s.nesting_depth for s in all_funcs), default=0)

        deduction_dist = (f_mod * 10.0) + (f_high * 35.0) + (f_vhigh * 60.0)
        deduction_outliers = min(15.0, max(0, cc_max - 15) * 0.5) + min(10.0, max(0, d_nest_max - 4) * 2.0)

        score = 100.0 - (deduction_dist + deduction_outliers)
        return round(clamp(score, 0.0, 100.0), 1)

    @staticmethod
    def calculate_architecture_score(
        graph: DirectedDependencyGraph,
        issues: List[CodebaseIssue],
    ) -> float:
        n_files = len(graph.nodes)
        if n_files <= 1:
            return 100.0

        n_cycles = len(graph.cycles)
        cyclic_file_ids = set()
        for c in graph.cycles:
            cyclic_file_ids.update(c.file_ids)
        n_cyclic_files = len(cyclic_file_ids)

        n_god_modules = sum(1 for iss in issues if iss.rule_id == "ARCH-002")
        n_unstable_hubs = sum(1 for iss in issues if iss.rule_id == "ARCH-003")
        n_unstable_deps = sum(1 for iss in issues if iss.rule_id == "ARCH-004")

        penalty_cycles = min(45.0, (n_cycles * 12.0) + ((n_cyclic_files / n_files) * 25.0))
        penalty_coupling = min(30.0, (n_god_modules * 6.0) + (n_unstable_hubs * 8.0))
        penalty_sap = min(15.0, n_unstable_deps * 3.0)

        score = 100.0 - (penalty_cycles + penalty_coupling + penalty_sap)
        return round(clamp(score, 0.0, 100.0), 1)

    @staticmethod
    def calculate_hygiene_score(
        issues: List[CodebaseIssue],
        total_sloc: int,
    ) -> float:
        # Rules in Hygiene & Reliability and Security categories
        hygiene_and_sec_issues = [
            iss for iss in issues
            if iss.category in (IssueCategory.HYGIENE.value, IssueCategory.SECURITY.value)
        ]

        n_blocker = sum(1 for iss in hygiene_and_sec_issues if iss.severity == IssueSeverity.BLOCKER.value)
        n_critical = sum(1 for iss in hygiene_and_sec_issues if iss.severity == IssueSeverity.CRITICAL.value)
        n_major = sum(1 for iss in hygiene_and_sec_issues if iss.severity == IssueSeverity.MAJOR.value)
        n_minor = sum(1 for iss in hygiene_and_sec_issues if iss.severity == IssueSeverity.MINOR.value)

        weight_raw = (n_blocker * 25.0) + (n_critical * 12.0) + (n_major * 5.0) + (n_minor * 1.5)
        scale_factor = max(1.0, math.sqrt(max(0, total_sloc) / 1000.0))

        deduction = min(100.0, weight_raw / scale_factor)
        score = 100.0 - deduction
        return round(clamp(score, 0.0, 100.0), 1)

    @staticmethod
    def calculate_duplication_score(
        duplication_ratio: float,
        duplicate_blocks_count: int,
    ) -> float:
        score = 100.0 - (duplication_ratio * 1.5) - min(10.0, duplicate_blocks_count * 0.5)
        return round(clamp(score, 0.0, 100.0), 1)

    def compute(
        self,
        file_metrics_map: Dict[str, FileMetrics],
        parsed_files_data: Optional[List[Dict[str, Any]]] = None,
        graph: Optional[DirectedDependencyGraph] = None,
        issues: Optional[List[CodebaseIssue]] = None,
        duplication_ratio: float = 0.0,
        duplicate_blocks_count: int = 0,
        duplicate_lines_count: int = 0,
        public_symbol_counts: Optional[Tuple[int, int]] = None,
    ) -> HealthScoreBreakdown:
        if issues is None:
            issues = []
        total_sloc = sum(fm.sloc for fm in file_metrics_map.values())

        s_maint = self.calculate_maintainability_score(file_metrics_map, parsed_files_data, public_symbol_counts=public_symbol_counts)
        s_complex = self.calculate_complexity_score(file_metrics_map)
        s_arch = self.calculate_architecture_score(graph, issues)
        s_hygiene = self.calculate_hygiene_score(issues, total_sloc)
        s_dup = self.calculate_duplication_score(duplication_ratio, duplicate_blocks_count)

        s_overall = round(0.22 * s_maint + 0.22 * s_complex + 0.22 * s_arch + 0.22 * s_hygiene + 0.12 * s_dup, 1)
        s_overall = clamp(s_overall, 0.0, 100.0)
        grade = self.calculate_grade(s_overall)

        # Technical Debt
        total_debt_minutes = sum(iss.remediation_effort_minutes for iss in issues)
        debt_hours = total_debt_minutes / 60.0
        ksloc = max(0.1, total_sloc / 1000.0)
        debt_ratio = round(debt_hours / ksloc, 1)

        # Issue counts by severity
        blocker_c = sum(1 for i in issues if i.severity == IssueSeverity.BLOCKER.value)
        crit_c = sum(1 for i in issues if i.severity == IssueSeverity.CRITICAL.value)
        major_c = sum(1 for i in issues if i.severity == IssueSeverity.MAJOR.value)
        minor_c = sum(1 for i in issues if i.severity == IssueSeverity.MINOR.value)
        info_c = sum(1 for i in issues if i.severity == IssueSeverity.INFO.value)

        category_scores = {
            "maintainability": {
                "score": s_maint,
                "weight": 0.22,
            },
            "complexity": {
                "score": s_complex,
                "weight": 0.22,
            },
            "architecture": {
                "score": s_arch,
                "weight": 0.22,
            },
            "hygiene_and_reliability": {
                "score": s_hygiene,
                "weight": 0.22,
            },
            "duplication": {
                "score": s_dup,
                "weight": 0.12,
            },
        }

        return HealthScoreBreakdown(
            overall_score=s_overall,
            grade=grade,
            maintainability_score=s_maint,
            complexity_score=s_complex,
            architecture_score=s_arch,
            hygiene_score=s_hygiene,
            duplication_score=s_dup,
            duplication_ratio=duplication_ratio,
            duplicate_blocks_count=duplicate_blocks_count,
            duplicate_lines_count=duplicate_lines_count,
            technical_debt_minutes=total_debt_minutes,
            debt_ratio_hours_per_ksloc=debt_ratio,
            total_issues_count=len(issues),
            blocker_count=blocker_c,
            critical_count=crit_c,
            major_count=major_c,
            minor_count=minor_c,
            info_count=info_c,
            category_scores=category_scores,
        )
