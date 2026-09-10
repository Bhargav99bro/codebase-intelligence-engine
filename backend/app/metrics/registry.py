import os
from typing import Dict, List, Optional
from app.metrics.base import BaseMetricsAnalyzer


class MetricsRegistry:
    """Registry maintaining language-specific code complexity and metrics analyzers."""

    def __init__(self) -> None:
        self._analyzers_by_extension: Dict[str, BaseMetricsAnalyzer] = {}
        self._analyzers_by_language: Dict[str, BaseMetricsAnalyzer] = {}

    def register(self, analyzer: BaseMetricsAnalyzer) -> None:
        """Registers a metrics analyzer for its supported language and extensions."""
        self._analyzers_by_language[analyzer.language_name.lower()] = analyzer
        for ext in analyzer.supported_extensions:
            self._analyzers_by_extension[ext.lower()] = analyzer

    def get_metrics_analyzer_for_file(
        self,
        file_path: str,
        language: Optional[str] = None,
    ) -> Optional[BaseMetricsAnalyzer]:
        """Looks up the metrics analyzer for a given file path and optional detected language."""
        _, ext = os.path.splitext(file_path)
        if ext:
            analyzer = self._analyzers_by_extension.get(ext.lower())
            if analyzer:
                return analyzer

        if language:
            analyzer = self._analyzers_by_language.get(language.lower())
            if analyzer:
                return analyzer

        return None

    def supported_languages(self) -> List[str]:
        """Returns the list of currently supported programming language names."""
        return list(set(a.language_name for a in self._analyzers_by_language.values()))


# Singleton registry instance
metrics_registry = MetricsRegistry()
