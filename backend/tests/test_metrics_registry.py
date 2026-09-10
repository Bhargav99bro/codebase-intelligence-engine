from app.metrics.registry import metrics_registry


def test_metrics_registry_supported_languages() -> None:
    languages = metrics_registry.supported_languages()
    assert "Python" in languages
    assert "JavaScript" in languages
    assert "TypeScript" in languages


def test_metrics_registry_lookup_by_extension() -> None:
    py_analyzer = metrics_registry.get_metrics_analyzer_for_file("app/main.py")
    assert py_analyzer is not None
    assert py_analyzer.language_name == "Python"

    js_analyzer = metrics_registry.get_metrics_analyzer_for_file("src/index.js")
    assert js_analyzer is not None
    assert js_analyzer.language_name == "JavaScript"

    ts_analyzer = metrics_registry.get_metrics_analyzer_for_file("src/app.tsx")
    assert ts_analyzer is not None
    assert ts_analyzer.language_name == "TypeScript"


def test_metrics_registry_unsupported_language() -> None:
    rs_analyzer = metrics_registry.get_metrics_analyzer_for_file("main.rs", language="Rust")
    assert rs_analyzer is None

    cpp_analyzer = metrics_registry.get_metrics_analyzer_for_file("main.cpp", language="C++")
    assert cpp_analyzer is None
