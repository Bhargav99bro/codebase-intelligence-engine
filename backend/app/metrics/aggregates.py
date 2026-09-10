from typing import Any, Dict, List
from app.metrics.base import FileMetrics


def calculate_repository_metrics(file_metrics_list: List[FileMetrics]) -> Dict[str, Any]:
    """Calculates repository-wide aggregated complexity, quality, and maintainability metrics."""
    total_sloc = sum(fm.sloc for fm in file_metrics_list)
    total_files = len(file_metrics_list)
    total_symbols = sum(fm.symbol_count for fm in file_metrics_list)
    total_functions = sum(fm.function_count for fm in file_metrics_list)
    total_classes = sum(fm.class_count for fm in file_metrics_list)
    total_methods = sum(fm.method_count for fm in file_metrics_list)

    # Collect all function/method symbol metrics
    all_func_metrics = [
        sm for fm in file_metrics_list for sm in fm.symbols_metrics
    ]
    num_funcs = len(all_func_metrics)

    # Complexity aggregates
    if num_funcs > 0:
        total_cc = sum(sm.cyclomatic_complexity for sm in all_func_metrics)
        avg_cc = round(total_cc / num_funcs, 2)
        max_cc = max(sm.cyclomatic_complexity for sm in all_func_metrics)

        total_func_loc = sum(sm.lines_of_code for sm in all_func_metrics)
        avg_func_size = round(total_func_loc / num_funcs, 1)
        max_func_size = max(sm.lines_of_code for sm in all_func_metrics)

        max_nesting = max((sm.nesting_depth for sm in all_func_metrics), default=0)
        avg_nesting = round(sum(sm.nesting_depth for sm in all_func_metrics) / num_funcs, 2)
    else:
        avg_cc = 1.0
        max_cc = 1
        avg_func_size = 0.0
        max_func_size = 0
        max_nesting = 0
        avg_nesting = 0.0

    # Complexity distribution across functions/methods
    distribution = {
        "low": sum(1 for sm in all_func_metrics if sm.cyclomatic_complexity <= 5),
        "moderate": sum(1 for sm in all_func_metrics if 6 <= sm.cyclomatic_complexity <= 10),
        "high": sum(1 for sm in all_func_metrics if 11 <= sm.cyclomatic_complexity <= 20),
        "very_high": sum(1 for sm in all_func_metrics if sm.cyclomatic_complexity > 20),
    }

    # Maintainability Indicator
    analyzable_files = [fm for fm in file_metrics_list if fm.metric_status == "calculated"]
    if analyzable_files:
        avg_mi = round(
            sum(fm.maintainability_score for fm in analyzable_files) / len(analyzable_files),
            1,
        )
    else:
        avg_mi = 100.0

    if avg_mi >= 70.0:
        mi_rating = "good"
        mi_label = "Good Maintainability"
    elif avg_mi >= 50.0:
        mi_rating = "moderate"
        mi_label = "Moderate Maintainability"
    else:
        mi_rating = "poor"
        mi_label = "Challenging / Technical Debt"

    # Quality Flags and Hotspots collection
    all_flags: List[Dict[str, Any]] = []
    for fm in file_metrics_list:
        all_flags.extend(fm.quality_flags)
        for sm in fm.symbols_metrics:
            all_flags.extend(sm.quality_flags)

    # Sort flags by severity priority: CRITICAL > HIGH > MEDIUM > LOW
    severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    sorted_flags = sorted(
        all_flags,
        key=lambda f: (severity_order.get(f.get("severity", "LOW"), 4), -f.get("metric_value", 0)),
    )

    flagged_files_count = sum(1 for fm in file_metrics_list if fm.quality_flags)
    flagged_functions_count = sum(
        1 for sm in all_func_metrics if sm.quality_flags
    )

    return {
        "repository_totals": {
            "total_sloc": total_sloc,
            "total_files": total_files,
            "total_symbols": total_symbols,
            "total_functions": total_functions,
            "total_classes": total_classes,
            "total_methods": total_methods,
        },
        "averages": {
            "average_cyclomatic_complexity": avg_cc,
            "average_function_size": avg_func_size,
            "average_nesting_depth": avg_nesting,
        },
        "maximums": {
            "max_cyclomatic_complexity": max_cc,
            "max_function_size": max_func_size,
            "max_nesting_depth": max_nesting,
        },
        "maintainability": {
            "score": avg_mi,
            "rating": mi_rating,
            "label": mi_label,
        },
        "complexity_distribution": distribution,
        "quality_summary": {
            "total_quality_flags": len(all_flags),
            "flagged_files_count": flagged_files_count,
            "flagged_functions_count": flagged_functions_count,
            "severity_counts": {
                "CRITICAL": sum(1 for f in all_flags if f.get("severity") == "CRITICAL"),
                "HIGH": sum(1 for f in all_flags if f.get("severity") == "HIGH"),
                "MEDIUM": sum(1 for f in all_flags if f.get("severity") == "MEDIUM"),
                "LOW": sum(1 for f in all_flags if f.get("severity") == "LOW"),
            },
            "top_hotspots": sorted_flags[:15],  # top 15 highest-severity issues
        },
    }
