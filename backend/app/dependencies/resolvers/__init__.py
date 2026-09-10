"""Dependency resolvers package."""
from app.dependencies.resolvers.python_resolver import PythonDependencyResolver
from app.dependencies.resolvers.js_ts_resolver import JsTsDependencyResolver

__all__ = [
    "PythonDependencyResolver",
    "JsTsDependencyResolver",
]
