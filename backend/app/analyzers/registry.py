import os
from typing import Dict, List, Optional

from app.analyzers.base import BaseLanguageAnalyzer


class AnalyzerRegistry:
    """Pluggable registry for language-specific static analyzers."""

    def __init__(self) -> None:
        self._analyzers_by_lang: Dict[str, BaseLanguageAnalyzer] = {}
        self._analyzers_by_ext: Dict[str, BaseLanguageAnalyzer] = {}

    def register(self, analyzer: BaseLanguageAnalyzer) -> None:
        """Register a language analyzer instance."""
        lang_key = analyzer.language_name.lower().strip()
        self._analyzers_by_lang[lang_key] = analyzer

        for ext in analyzer.supported_extensions:
            ext_key = ext.lower().strip()
            if not ext_key.startswith("."):
                ext_key = f".{ext_key}"
            self._analyzers_by_ext[ext_key] = analyzer

    def get_analyzer_for_language(self, language: Optional[str]) -> Optional[BaseLanguageAnalyzer]:
        """Lookup an analyzer by language name."""
        if not language:
            return None
        return self._analyzers_by_lang.get(language.lower().strip())

    def get_analyzer_for_file(self, file_path: str, language: Optional[str] = None) -> Optional[BaseLanguageAnalyzer]:
        """Lookup an analyzer by detected language or file extension."""
        if language:
            analyzer = self.get_analyzer_for_language(language)
            if analyzer:
                return analyzer

        _, ext = os.path.splitext(file_path)
        if ext:
            return self._analyzers_by_ext.get(ext.lower())

        return None

    def supported_languages(self) -> List[str]:
        """List all currently supported canonical language names."""
        return sorted([a.language_name for a in set(self._analyzers_by_lang.values())])


# Global singleton registry instance
analyzer_registry = AnalyzerRegistry()
