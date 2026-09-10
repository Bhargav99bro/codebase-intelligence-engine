"""Dependency extractors package."""
from app.dependencies.extractors.python_extractor import PythonDependencyExtractor
from app.dependencies.extractors.js_ts_extractor import JsTsDependencyExtractor

__all__ = [
    "PythonDependencyExtractor",
    "JsTsDependencyExtractor",
]
