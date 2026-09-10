"""Pluggable code analyzers for Codebase Intelligence Engine."""
from app.analyzers.base import BaseLanguageAnalyzer, ExtractedSymbol, FileAnalysisResult
from app.analyzers.javascript_analyzer import JavaScriptAnalyzer
from app.analyzers.python_analyzer import PythonAnalyzer
from app.analyzers.registry import AnalyzerRegistry, analyzer_registry
from app.analyzers.typescript_analyzer import TypeScriptAnalyzer

# Automatically register default analyzers
analyzer_registry.register(PythonAnalyzer())
analyzer_registry.register(JavaScriptAnalyzer())
analyzer_registry.register(TypeScriptAnalyzer())

__all__ = [
    "BaseLanguageAnalyzer",
    "ExtractedSymbol",
    "FileAnalysisResult",
    "AnalyzerRegistry",
    "analyzer_registry",
    "PythonAnalyzer",
    "JavaScriptAnalyzer",
    "TypeScriptAnalyzer",
]
