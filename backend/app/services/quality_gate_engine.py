from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union


@dataclass
class ConditionResult:
    condition_id: str
    metric: str
    actual_value: Union[float, int]
    threshold: Union[float, int]
    operator: str
    severity: str  # "fail" | "warn"
    passed: bool
    message: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "condition_id": self.condition_id,
            "metric": self.metric,
            "actual_value": self.actual_value,
            "threshold": self.threshold,
            "operator": self.operator,
            "severity": self.severity,
            "passed": self.passed,
            "message": self.message,
        }


@dataclass
class QualityGateResult:
    status: str  # "PASSED" | "WARNING" | "FAILED"
    passed: bool
    overall_score: float
    total_conditions: int
    passed_count: int
    failed_count: int
    warning_count: int
    conditions: List[ConditionResult]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "passed": self.passed,
            "overall_score": self.overall_score,
            "total_conditions": self.total_conditions,
            "passed_count": self.passed_count,
            "failed_count": self.failed_count,
            "warning_count": self.warning_count,
            "conditions": [c.to_dict() for c in self.conditions],
        }


class QualityGateEngine:
    """Evaluates repository readiness against structured engineering standards."""

    DEFAULT_THRESHOLDS = {
        "min_score": 80.0,
        "max_blockers": 0,
        "max_cycles": 0,
        "max_criticals": 2,
        "min_mi": 55.0,
        "max_crit_funcs": 3,
    }

    @classmethod
    def evaluate(
        cls,
        overall_score: float,
        blocker_count: int,
        critical_count: int,
        circular_dependencies_count: int,
        average_maintainability_index: float,
        critical_complexity_functions_count: int,
        custom_thresholds: Optional[Dict[str, Any]] = None,
    ) -> QualityGateResult:
        """Evaluates all 6 quality-gate conditions with exact boundary semantics."""
        thresholds = dict(cls.DEFAULT_THRESHOLDS)
        if custom_thresholds:
            for k, v in custom_thresholds.items():
                if v is not None and k in thresholds:
                    thresholds[k] = type(thresholds[k])(v)

        conditions: List[ConditionResult] = []

        # 1. QG-001: Overall Health Score >= min_score
        t_score = float(thresholds["min_score"])
        act_score = round(float(overall_score), 1)
        pass_qg1 = act_score >= t_score
        msg_qg1 = (
            f"Overall health score {act_score:.1f} meets minimum threshold of {t_score:.1f}"
            if pass_qg1
            else f"Overall health score {act_score:.1f} is below minimum threshold of {t_score:.1f}"
        )
        conditions.append(
            ConditionResult(
                condition_id="QG-001",
                metric="overall_health_score",
                actual_value=act_score,
                threshold=t_score,
                operator=">=",
                severity="fail",
                passed=pass_qg1,
                message=msg_qg1,
            )
        )

        # 2. QG-002: Blocker Issues == max_blockers (default 0)
        t_blocker = int(thresholds["max_blockers"])
        act_blocker = int(blocker_count)
        pass_qg2 = act_blocker <= t_blocker if t_blocker > 0 else act_blocker == 0
        op_qg2 = "<=" if t_blocker > 0 else "=="
        msg_qg2 = (
            f"Blocker issue count {act_blocker} satisfies threshold of {t_blocker}"
            if pass_qg2
            else f"Detected {act_blocker} blocker issues (threshold {op_qg2} {t_blocker})"
        )
        conditions.append(
            ConditionResult(
                condition_id="QG-002",
                metric="blocker_issues_count",
                actual_value=act_blocker,
                threshold=t_blocker,
                operator=op_qg2,
                severity="fail",
                passed=pass_qg2,
                message=msg_qg2,
            )
        )

        # 3. QG-003: Circular Dependencies == max_cycles (default 0)
        t_cycles = int(thresholds["max_cycles"])
        act_cycles = int(circular_dependencies_count)
        pass_qg3 = act_cycles <= t_cycles if t_cycles > 0 else act_cycles == 0
        op_qg3 = "<=" if t_cycles > 0 else "=="
        msg_qg3 = (
            f"Circular dependency count {act_cycles} satisfies threshold of {t_cycles}"
            if pass_qg3
            else f"Detected {act_cycles} circular dependency cycles (threshold {op_qg3} {t_cycles})"
        )
        conditions.append(
            ConditionResult(
                condition_id="QG-003",
                metric="circular_dependencies_count",
                actual_value=act_cycles,
                threshold=t_cycles,
                operator=op_qg3,
                severity="fail",
                passed=pass_qg3,
                message=msg_qg3,
            )
        )

        # 4. QG-004: Critical Issues <= max_criticals (default 2)
        t_crit = int(thresholds["max_criticals"])
        act_crit = int(critical_count)
        pass_qg4 = act_crit <= t_crit
        msg_qg4 = (
            f"Critical issue count {act_crit} is within allowed threshold of {t_crit}"
            if pass_qg4
            else f"Detected {act_crit} critical issues exceeding threshold of {t_crit}"
        )
        conditions.append(
            ConditionResult(
                condition_id="QG-004",
                metric="critical_issues_count",
                actual_value=act_crit,
                threshold=t_crit,
                operator="<=",
                severity="warn",
                passed=pass_qg4,
                message=msg_qg4,
            )
        )

        # 5. QG-005: Average Maintainability Index >= min_mi (default 55.0)
        t_mi = float(thresholds["min_mi"])
        act_mi = round(float(average_maintainability_index), 1)
        pass_qg5 = act_mi >= t_mi
        msg_qg5 = (
            f"Average Maintainability Index {act_mi:.1f} meets minimum threshold of {t_mi:.1f}"
            if pass_qg5
            else f"Average Maintainability Index {act_mi:.1f} is below minimum threshold of {t_mi:.1f}"
        )
        conditions.append(
            ConditionResult(
                condition_id="QG-005",
                metric="average_maintainability_index",
                actual_value=act_mi,
                threshold=t_mi,
                operator=">=",
                severity="warn",
                passed=pass_qg5,
                message=msg_qg5,
            )
        )

        # 6. QG-006: Critical Complexity Functions <= max_crit_funcs (default 3)
        t_cc_func = int(thresholds["max_crit_funcs"])
        act_cc_func = int(critical_complexity_functions_count)
        pass_qg6 = act_cc_func <= t_cc_func
        msg_qg6 = (
            f"Critical complexity function count {act_cc_func} is within threshold of {t_cc_func}"
            if pass_qg6
            else f"Detected {act_cc_func} functions with critical cyclomatic complexity (threshold <= {t_cc_func})"
        )
        conditions.append(
            ConditionResult(
                condition_id="QG-006",
                metric="critical_complexity_functions_count",
                actual_value=act_cc_func,
                threshold=t_cc_func,
                operator="<=",
                severity="warn",
                passed=pass_qg6,
                message=msg_qg6,
            )
        )

        # Compute Verdicts:
        # FAILED: any condition with severity 'fail' failed
        # WARNING: any condition with severity 'warn' failed, and 0 fail
        # PASSED: all conditions passed
        failed_failures = [c for c in conditions if not c.passed and c.severity == "fail"]
        warning_failures = [c for c in conditions if not c.passed and c.severity == "warn"]

        if failed_failures:
            status = "FAILED"
            passed = False
        elif warning_failures:
            status = "WARNING"
            passed = True  # passes with warnings
        else:
            status = "PASSED"
            passed = True

        passed_count = sum(1 for c in conditions if c.passed)
        failed_count = len(failed_failures)
        warning_count = len(warning_failures)

        return QualityGateResult(
            status=status,
            passed=passed,
            overall_score=act_score,
            total_conditions=len(conditions),
            passed_count=passed_count,
            failed_count=failed_count,
            warning_count=warning_count,
            conditions=conditions,
        )
