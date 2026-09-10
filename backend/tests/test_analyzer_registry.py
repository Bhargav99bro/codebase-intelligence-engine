from app.analyzers import analyzer_registry


def test_registry_supported_languages():
    langs = analyzer_registry.supported_languages()
    assert "Python" in langs
    assert "JavaScript" in langs
    assert "TypeScript" in langs


def test_registry_lookup_by_extension():
    py_analyzer = analyzer_registry.get_analyzer_for_file("app/main.py")
    assert py_analyzer is not None
    assert py_analyzer.language_name == "Python"

    js_analyzer = analyzer_registry.get_analyzer_for_file("frontend/src/index.jsx")
    assert js_analyzer is not None
    assert js_analyzer.language_name == "JavaScript"

    ts_analyzer = analyzer_registry.get_analyzer_for_file("frontend/src/App.tsx")
    assert ts_analyzer is not None
    assert ts_analyzer.language_name == "TypeScript"


def test_registry_lookup_by_language_name():
    py = analyzer_registry.get_analyzer_for_language("python")
    assert py is not None
    assert py.language_name == "Python"

    ts = analyzer_registry.get_analyzer_for_language("TypeScript")
    assert ts is not None
    assert ts.language_name == "TypeScript"


def test_registry_unsupported_language_handling():
    rust_analyzer = analyzer_registry.get_analyzer_for_file("main.rs")
    assert rust_analyzer is None

    unknown_lang = analyzer_registry.get_analyzer_for_language("Rust")
    assert unknown_lang is None

    none_analyzer = analyzer_registry.get_analyzer_for_file("data.unknown_ext")
    assert none_analyzer is None
