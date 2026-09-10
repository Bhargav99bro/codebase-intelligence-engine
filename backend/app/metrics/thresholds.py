from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from app.metrics.base import QualityFlag


@dataclass(frozen=True)
class MetricThresholds:
    """Centralized configurable thresholds for complexity and quality hotspot detection."""

    # Cyclomatic Complexity
    VERY_HIGH_COMPLEXITY: int = 20
    HIGH_COMPLEXITY: int = 10

    # Lines of Code (Function / Method)
    VERY_LARGE_FUNCTION_LOC: int = 100
    LARGE_FUNCTION_LOC: int = 50

    # File Size (SLOC)
    VERY_LARGE_FILE_SLOC: int = 1000
    LARGE_FILE_SLOC: int = 500

    # Structural Nesting Depth
    DEEP_NESTING: int = 4

    # Function Parameters
    HIGH_PARAMETER_COUNT: int = 5

    # Branches within function
    HIGH_BRANCH_COUNT: int = 8

    # Maintainability Index (0-100 scale)
    POOR_MAINTAINABILITY_INDEX: float = 50.0
    MODERATE_MAINTAINABILITY_INDEX: float = 70.0


DEFAULT_THRESHOLDS = MetricThresholds()


def evaluate_function_quality(
    name: str,
    location: str,
    cyclomatic_complexity: int,
    lines_of_code: int,
    nesting_depth: int,
    parameter_count: int,
    branch_count: int,
    thresholds: MetricThresholds = DEFAULT_THRESHOLDS,
) -> List[Dict[str, Any]]:
    """Evaluates function/method metrics against centralized thresholds and returns quality flags."""
    flags: List[Dict[str, Any]] = []

    # Cyclomatic Complexity checks
    if cyclomatic_complexity > thresholds.VERY_HIGH_COMPLEXITY:
        flags.append(
            QualityFlag(
                flag="VERY_HIGH_COMPLEXITY",
                description=f"Function '{name}' cyclomatic complexity ({cyclomatic_complexity}) exceeds critical threshold ({thresholds.VERY_HIGH_COMPLEXITY}).",
                metric_value=float(cyclomatic_complexity),
                threshold=float(thresholds.VERY_HIGH_COMPLEXITY),
                severity="CRITICAL",
                location=location,
            ).to_dict()
        )
    elif cyclomatic_complexity > thresholds.HIGH_COMPLEXITY:
        flags.append(
            QualityFlag(
                flag="HIGH_COMPLEXITY",
                description=f"Function '{name}' cyclomatic complexity ({cyclomatic_complexity}) exceeds high threshold ({thresholds.HIGH_COMPLEXITY}).",
                metric_value=float(cyclomatic_complexity),
                threshold=float(thresholds.HIGH_COMPLEXITY),
                severity="HIGH",
                location=location,
            ).to_dict()
        )

    # Function LOC checks
    if lines_of_code > thresholds.VERY_LARGE_FUNCTION_LOC:
        flags.append(
            QualityFlag(
                flag="VERY_LARGE_FUNCTION",
                description=f"Function '{name}' length ({lines_of_code} LOC) exceeds critical size threshold ({thresholds.VERY_LARGE_FUNCTION_LOC}).",
                metric_value=float(lines_of_code),
                threshold=float(thresholds.VERY_LARGE_FUNCTION_LOC),
                severity="HIGH",
                location=location,
            ).to_dict()
        )
    elif lines_of_code > thresholds.LARGE_FUNCTION_LOC:
        flags.append(
            QualityFlag(
                flag="LARGE_FUNCTION",
                description=f"Function '{name}' length ({lines_of_code} LOC) exceeds large function threshold ({thresholds.LARGE_FUNCTION_LOC}).",
                metric_value=float(lines_of_code),
                threshold=float(thresholds.LARGE_FUNCTION_LOC),
                severity="MEDIUM",
                location=location,
            ).to_dict()
        )

    # Nesting depth checks
    if nesting_depth > thresholds.DEEP_NESTING:
        flags.append(
            QualityFlag(
                flag="DEEP_NESTING",
                description=f"Function '{name}' nesting depth ({nesting_depth}) exceeds threshold ({thresholds.DEEP_NESTING}).",
                metric_value=float(nesting_depth),
                threshold=float(thresholds.DEEP_NESTING),
                severity="HIGH",
                location=location,
            ).to_dict()
        )

    # Parameter count checks
    if parameter_count > thresholds.HIGH_PARAMETER_COUNT:
        flags.append(
            QualityFlag(
                flag="HIGH_PARAMETER_COUNT",
                description=f"Function '{name}' has {parameter_count} parameters, exceeding threshold ({thresholds.HIGH_PARAMETER_COUNT}).",
                metric_value=float(parameter_count),
                threshold=float(thresholds.HIGH_PARAMETER_COUNT),
                severity="MEDIUM",
                location=location,
            ).to_dict()
        )

    # Branch count checks
    if branch_count > thresholds.HIGH_BRANCH_COUNT:
        flags.append(
            QualityFlag(
                flag="HIGH_BRANCH_COUNT",
                description=f"Function '{name}' contains {branch_count} branching decision paths, exceeding threshold ({thresholds.HIGH_BRANCH_COUNT}).",
                metric_value=float(branch_count),
                threshold=float(thresholds.HIGH_BRANCH_COUNT),
                severity="MEDIUM",
                location=location,
            ).to_dict()
        )

    return flags


def evaluate_file_quality(
    file_path: str,
    sloc: int,
    maintainability_score: float,
    max_nesting_depth: int,
    max_cyclomatic_complexity: int,
    thresholds: MetricThresholds = DEFAULT_THRESHOLDS,
) -> List[Dict[str, Any]]:
    """Evaluates file-level metrics against centralized thresholds and returns quality flags."""
    flags: List[Dict[str, Any]] = []

    # File SLOC checks
    if sloc > thresholds.VERY_LARGE_FILE_SLOC:
        flags.append(
            QualityFlag(
                flag="VERY_LARGE_FILE",
                description=f"File '{file_path}' has {sloc} SLOC, exceeding critical threshold ({thresholds.VERY_LARGE_FILE_SLOC}).",
                metric_value=float(sloc),
                threshold=float(thresholds.VERY_LARGE_FILE_SLOC),
                severity="HIGH",
                location=f"{file_path}:1",
            ).to_dict()
        )
    elif sloc > thresholds.LARGE_FILE_SLOC:
        flags.append(
            QualityFlag(
                flag="LARGE_FILE",
                description=f"File '{file_path}' has {sloc} SLOC, exceeding large file threshold ({thresholds.LARGE_FILE_SLOC}).",
                metric_value=float(sloc),
                threshold=float(thresholds.LARGE_FILE_SLOC),
                severity="MEDIUM",
                location=f"{file_path}:1",
            ).to_dict()
        )

    # Maintainability index checks
    if maintainability_score < thresholds.POOR_MAINTAINABILITY_INDEX:
        flags.append(
            QualityFlag(
                flag="POOR_MAINTAINABILITY",
                description=f"File '{file_path}' has low maintainability index ({maintainability_score:.1f}/100), below threshold ({thresholds.POOR_MAINTAINABILITY_INDEX}).",
                metric_value=maintainability_score,
                threshold=thresholds.POOR_MAINTAINABILITY_INDEX,
                severity="HIGH",
                location=f"{file_path}:1",
            ).to_dict()
        )

    return flags
