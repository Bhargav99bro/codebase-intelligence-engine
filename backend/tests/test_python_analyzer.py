import pytest
from app.analyzers.python_analyzer import PythonAnalyzer


@pytest.fixture
def analyzer():
    return PythonAnalyzer()


def test_python_function_extraction(analyzer):
    code = """
def calculate_total(items: list, tax: float = 0.05) -> float:
    \"\"\"Calculate total price with tax.\"\"\"
    return sum(items) * (1 + tax)
"""
    result = analyzer.analyze("src/calc.py", code)
    assert result.parser_status == "parsed"
    assert len(result.symbols) == 1

    sym = result.symbols[0]
    assert sym.name == "calculate_total"
    assert sym.symbol_type == "function"
    assert "def calculate_total" in sym.signature
    assert "tax: float = 0.05" in sym.signature
    assert "-> float" in sym.signature
    assert sym.start_line == 2
    assert sym.end_line == 4
    assert sym.parent_name is None
    assert sym.metadata_json.get("docstring") == "Calculate total price with tax."
    assert "items" in sym.metadata_json.get("parameters", [])


def test_python_async_function_extraction(analyzer):
    code = """
async def fetch_user(user_id: str) -> dict:
    return {"id": user_id}
"""
    result = analyzer.analyze("src/api.py", code)
    assert result.parser_status == "parsed"
    assert len(result.symbols) == 1

    sym = result.symbols[0]
    assert sym.name == "fetch_user"
    assert sym.symbol_type == "function"
    assert sym.metadata_json.get("is_async") is True
    assert "async def fetch_user" in sym.signature
    assert sym.start_line == 2


def test_python_class_and_methods_extraction(analyzer):
    code = """
@decorator_cls
class PaymentService(BaseService):
    \"\"\"Payment service handler.\"\"\"

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def process_payment(self, amount: float) -> bool:
        return True

    @classmethod
    def create_default(cls):
        return cls("default_key")
"""
    result = analyzer.analyze("src/services.py", code)
    assert result.parser_status == "parsed"

    # 1 class + 3 methods = 4 symbols
    assert len(result.symbols) == 4

    cls_sym = [s for s in result.symbols if s.symbol_type == "class"][0]
    assert cls_sym.name == "PaymentService"
    assert cls_sym.parent_name is None
    assert "BaseService" in cls_sym.metadata_json.get("bases", [])
    assert "@decorator_cls" in cls_sym.metadata_json.get("decorators", [])
    assert cls_sym.start_line == 3

    methods = [s for s in result.symbols if s.symbol_type == "method"]
    assert len(methods) == 3

    init_method = [m for m in methods if m.name == "__init__"][0]
    assert init_method.parent_name == "PaymentService"
    assert init_method.qualified_name == "src.services.PaymentService.__init__"
    assert init_method.start_line == 6

    process_method = [m for m in methods if m.name == "process_payment"][0]
    assert process_method.parent_name == "PaymentService"
    assert process_method.metadata_json.get("is_async") is True
    assert process_method.start_line == 9

    create_method = [m for m in methods if m.name == "create_default"][0]
    assert create_method.parent_name == "PaymentService"
    assert "@classmethod" in create_method.metadata_json.get("decorators", [])


def test_python_import_extraction(analyzer):
    code = """
import os
import sys as system
from fastapi import FastAPI, Depends, HTTPException
from app.core.config import settings as app_settings
"""
    result = analyzer.analyze("src/main.py", code)
    assert result.parser_status == "parsed"
    assert len(result.symbols) == 6

    names = [s.name for s in result.symbols]
    assert "os" in names
    assert "system" in names
    assert "FastAPI" in names
    assert "Depends" in names
    assert "HTTPException" in names
    assert "app_settings" in names

    from_imports = [s for s in result.symbols if s.metadata_json.get("is_from_import")]
    assert len(from_imports) == 4


def test_python_source_locations(analyzer):
    code = """# Header comment
def first_func():
    pass

def second_func():
    x = 1
    return x
"""
    result = analyzer.analyze("src/app.py", code)
    funcs = result.symbols
    assert len(funcs) == 2

    assert funcs[0].name == "first_func"
    assert funcs[0].start_line == 2
    assert funcs[0].end_line == 3

    assert funcs[1].name == "second_func"
    assert funcs[1].start_line == 5
    assert funcs[1].end_line == 7


def test_python_nested_symbol_relationships(analyzer):
    code = """
class Outer:
    class Inner:
        def inner_method(self):
            pass
"""
    result = analyzer.analyze("src/nested.py", code)
    assert result.parser_status == "parsed"
    assert len(result.symbols) == 3

    outer = [s for s in result.symbols if s.name == "Outer"][0]
    inner = [s for s in result.symbols if s.name == "Inner"][0]
    method = [s for s in result.symbols if s.name == "inner_method"][0]

    assert outer.parent_name is None
    assert inner.parent_name == "Outer"
    assert method.parent_name == "Inner"


def test_python_invalid_syntax_isolation(analyzer):
    broken_code = """
def broken_function(x, y:
    return x + y
"""
    result = analyzer.analyze("src/broken.py", broken_code)
    assert result.parser_status == "failed"
    assert "SyntaxError" in result.parser_error
    assert len(result.symbols) == 0


def test_python_empty_file(analyzer):
    result = analyzer.analyze("src/empty.py", "   \n\n   ")
    assert result.parser_status == "parsed"
    assert len(result.symbols) == 0
