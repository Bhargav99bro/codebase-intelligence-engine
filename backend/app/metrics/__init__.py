"""Metrics analysis package."""
from app.metrics.base import (
    BaseMetricsAnalyzer,
    FileMetrics,
    QualityFlag,
    SymbolMetrics,
)
from app.metrics.javascript_metrics import JavaScriptMetricsAnalyzer
from app.metrics.python_metrics import PythonMetricsAnalyzer
from app.metrics.registry import MetricsRegistry, metrics_registry
from app.metrics.thresholds import MetricThresholds, evaluate_file_quality, evaluate_function_quality
from app.metrics.typescript_metrics import TypeScriptMetricsAnalyzer

# Register core supported languages
metrics_registry.register(PythonMetricsAnalyzer())
metrics_registry.register(JavaScriptMetricsAnalyzer())
metrics_registry.register(TypeScriptMetricsAnalyzer())

__all__ = [
    "BaseMetricsAnalyzer",
    "FileMetrics",
    "SymbolMetrics",
    "QualityFlag",
    "MetricThresholds",
    "evaluate_function_quality",
    "evaluate_file_quality",
    "MetricsRegistry",
    "metrics_registry",
    "PythonMetricsAnalyzer",
    "JavaScriptMetricsAnalyzer",
    "TypeScriptMetricsAnalyzer",
]
