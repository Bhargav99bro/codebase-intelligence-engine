import uuid
import pytest
from app.analyzers.base import ExtractedSymbol
from app.services.file_discovery import DiscoveredFile
from app.rules.base import RuleContext
from app.rules.hygiene_rules import (
    DeadPrivateSymbolRule,
    EmptyExceptionHandlerRule,
)
from app.rules.security_rules import (
    DynamicExecutionSinkRule,
    HardcodedSecretPatternRule,
)


from app.metrics.base import FileMetrics


def make_context(path, content, language, symbols=None, file_metrics=None):
    df = DiscoveredFile(
        path=path,
        filename=path.split("/")[-1],
        extension="." + path.split(".")[-1],
        size_bytes=len(content),
        line_count=content.count("\n") + 1,
        language=language,
        is_analyzable=True,
    )
    fid = uuid.uuid4()
    item = {
        "df": df,
        "content": content,
        "symbols": symbols or [],
        "symbols_metrics": [],
        "parser_status": "success",
        "parser_error": None,
        "symbol_count": len(symbols or []),
    }
    fm_map = {path: file_metrics} if file_metrics else {}
    return RuleContext(
        parsed_files_data=[item],
        file_metrics_map=fm_map,
        graph=None,
        file_id_map={path: fid},
    )


def test_empty_exception_handler_python():
    rule = EmptyExceptionHandlerRule()
    py_code = """
def fetch_data():
    try:
        do_risky_io()
    except KeyError:
        pass
    except Exception:
        "Silent ignore"
"""
    ctx = make_context("handler.py", py_code, "Python")
    issues = rule.evaluate(ctx)

    assert len(issues) >= 1
    assert any(i.rule_id == "HYGIENE-001" and "KeyError" in i.title for i in issues)
    assert any(i.severity == "major" for i in issues)


def test_empty_exception_handler_javascript():
    rule = EmptyExceptionHandlerRule()
    js_code = """
function processData() {
    try {
        parseJson();
    } catch (e) {
    }
}
"""
    ctx = make_context("handler.js", js_code, "JavaScript")
    issues = rule.evaluate(ctx)

    assert len(issues) == 1
    assert issues[0].rule_id == "HYGIENE-001"
    assert issues[0].severity == "major"


def test_dead_private_symbol():
    rule = DeadPrivateSymbolRule()
    py_code = """
def public_api():
    return 42

def _used_private():
    return 1

def _dead_private():
    return 2

# public_api uses _used_private
x = _used_private()
"""
    sym1 = ExtractedSymbol(name="public_api", symbol_type="function", start_line=2, start_column=0, end_line=3, end_column=0)
    sym2 = ExtractedSymbol(name="_used_private", symbol_type="function", start_line=5, start_column=0, end_line=6, end_column=0)
    sym3 = ExtractedSymbol(name="_dead_private", symbol_type="function", start_line=8, start_column=0, end_line=9, end_column=0)

    fm = FileMetrics(file_path="utils.py", language="Python", sloc=60, total_lines=60)
    ctx = make_context("utils.py", py_code, "Python", symbols=[sym1, sym2, sym3], file_metrics=fm)
    issues = rule.evaluate(ctx)

    assert len(issues) == 1
    assert issues[0].rule_id == "HYGIENE-002"
    assert issues[0].symbol_name == "_dead_private"
    assert issues[0].severity == "minor"


def test_hardcoded_secret_pattern():
    rule = HardcodedSecretPatternRule()
    py_code = """
# AWS Key in code
AWS_KEY = "AKIA1234567890ABCDEF"
GITHUB_TOKEN = "ghp_1234567890abcdefghijklmnopqrstuvwxyz"
"""
    ctx = make_context("config.py", py_code, "Python")
    issues = rule.evaluate(ctx)

    assert len(issues) == 2
    rule_ids = [i.rule_id for i in issues]
    assert rule_ids == ["SEC-001", "SEC-001"]
    assert any(i.severity == "blocker" for i in issues)


def test_dynamic_execution_sink():
    rule = DynamicExecutionSinkRule()
    py_code = """
def run_user_input(code_str):
    eval(code_str)
    exec("print('hello')")
"""
    ctx = make_context("dynamic.py", py_code, "Python")
    issues = rule.evaluate(ctx)

    assert len(issues) == 2
    rule_ids = [i.rule_id for i in issues]
    assert rule_ids == ["SEC-002", "SEC-002"]
    assert all(i.severity == "blocker" for i in issues)
    assert any(i.metadata_json.get("sink_type") == "eval" for i in issues)
    assert any(i.metadata_json.get("sink_type") == "exec" for i in issues)


def test_dynamic_execution_sink_distinguishes_all_four_sinks():
    rule = DynamicExecutionSinkRule()

    # 1. Python eval & exec
    py_code = """
eval("2 + 2")
exec("x = 1")
"""
    ctx_py = make_context("sample.py", py_code, "python")
    py_issues = rule.evaluate(ctx_py)
    assert len(py_issues) == 2

    eval_issue = next(i for i in py_issues if i.metadata_json.get("sink_type") == "eval")
    exec_issue = next(i for i in py_issues if i.metadata_json.get("sink_type") == "exec")

    assert eval_issue.title == "Dynamic Expression Evaluation via eval()"
    assert eval_issue.metadata_json["vulnerability_class"] == "code_injection_eval"
    assert "eval()" in eval_issue.description

    assert exec_issue.title == "Arbitrary Code Execution via exec()"
    assert exec_issue.metadata_json["vulnerability_class"] == "code_execution_exec"
    assert "exec()" in exec_issue.description

    # 2. JavaScript / TypeScript Function constructor & dangerouslySetInnerHTML
    js_code = """
const fn = new Function('a', 'b', 'return a + b');
const element = <div dangerouslySetInnerHTML={{ __html: rawHtml }} />;
"""
    ctx_js = make_context("component.tsx", js_code, "typescript")
    js_issues = rule.evaluate(ctx_js)
    assert len(js_issues) == 2

    fn_issue = next(i for i in js_issues if i.metadata_json.get("sink_type") == "Function")
    dom_issue = next(i for i in js_issues if i.metadata_json.get("sink_type") == "dangerouslySetInnerHTML")

    assert fn_issue.title == "Dynamic Function Construction via new Function()"
    assert fn_issue.metadata_json["vulnerability_class"] == "dynamic_function_constructor"
    assert "new Function()" in fn_issue.description

    assert dom_issue.title == "Direct DOM HTML Injection via dangerouslySetInnerHTML"
    assert dom_issue.metadata_json["vulnerability_class"] == "dom_xss_injection"
    assert "dangerouslySetInnerHTML" in dom_issue.description

    # Assert all 4 sinks have completely distinct titles, vuln classes, and descriptions
    all_titles = {eval_issue.title, exec_issue.title, fn_issue.title, dom_issue.title}
    all_vulns = {
        eval_issue.metadata_json["vulnerability_class"],
        exec_issue.metadata_json["vulnerability_class"],
        fn_issue.metadata_json["vulnerability_class"],
        dom_issue.metadata_json["vulnerability_class"],
    }
    assert len(all_titles) == 4
    assert len(all_vulns) == 4

