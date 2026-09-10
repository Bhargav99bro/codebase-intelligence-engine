import pytest
from app.analyzers.base import ExtractedSymbol
from app.metrics.javascript_metrics import JavaScriptMetricsAnalyzer
from app.metrics.typescript_metrics import TypeScriptMetricsAnalyzer


@pytest.fixture
def js_analyzer() -> JavaScriptMetricsAnalyzer:
    return JavaScriptMetricsAnalyzer()


@pytest.fixture
def ts_analyzer() -> TypeScriptMetricsAnalyzer:
    return TypeScriptMetricsAnalyzer()


def test_js_function_and_arrow_metrics(js_analyzer: JavaScriptMetricsAnalyzer) -> None:
    code = """function calculate(a, b) {
    if (a > b) {
        return a - b;
    }
    return a + b;
}

const multiply = (x, y) => {
    return x * y;
};
"""
    symbols = [
        ExtractedSymbol(name="calculate", symbol_type="function", start_line=1, start_column=0, end_line=6, end_column=1),
        ExtractedSymbol(name="multiply", symbol_type="function", start_line=8, start_column=0, end_line=10, end_column=2),
    ]
    res = js_analyzer.calculate("calc.js", code, symbols)

    assert res.metric_status == "calculated"
    assert len(res.symbols_metrics) == 2

    calc_sm = next(s for s in res.symbols_metrics if s.name == "calculate")
    assert calc_sm.cyclomatic_complexity == 2  # base 1 + if 1
    assert calc_sm.branch_count == 1
    assert calc_sm.parameter_count == 2

    mul_sm = next(s for s in res.symbols_metrics if s.name == "multiply")
    assert mul_sm.cyclomatic_complexity == 1
    assert mul_sm.parameter_count == 2


def test_js_loops_switch_and_ternary(js_analyzer: JavaScriptMetricsAnalyzer) -> None:
    code = """function dispatchAction(action, data) {
    let result = null;
    switch (action) {
        case "create":
            result = 1;
            break;
        case "update":
            result = 2;
            break;
        default:
            result = 0;
    }

    for (let i = 0; i < 5; i++) {
        result += i;
    }

    return result > 10 ? "high" : "low";
}
"""
    symbols = [ExtractedSymbol(name="dispatchAction", symbol_type="function", start_line=1, start_column=0, end_line=19, end_column=1)]
    res = js_analyzer.calculate("dispatcher.js", code, symbols)

    sm = res.symbols_metrics[0]
    # base 1 + 2 cases + 1 for-loop + 1 ternary = 5
    assert sm.cyclomatic_complexity == 5
    assert sm.branch_count == 3  # 2 switch cases + 1 ternary
    assert sm.loop_count == 1


def test_ts_types_and_interfaces_do_not_inflate_complexity(ts_analyzer: TypeScriptMetricsAnalyzer) -> None:
    code = """interface UserProfile {
    id: string;
    username: string;
    isActive: boolean;
}

type IDType = string | number;

function getUser(id: IDType): UserProfile {
    if (typeof id === "string") {
        return { id, username: "user", isActive: true };
    }
    return { id: String(id), username: "user", isActive: false };
}
"""
    symbols = [
        ExtractedSymbol(name="UserProfile", symbol_type="interface", start_line=1, start_column=0, end_line=5, end_column=1),
        ExtractedSymbol(name="getUser", symbol_type="function", start_line=9, start_column=0, end_line=14, end_column=1),
    ]
    res = ts_analyzer.calculate("user.ts", code, symbols)

    assert res.metric_status == "calculated"
    # Only getUser is an executable function scope
    assert len(res.symbols_metrics) == 1
    sm = res.symbols_metrics[0]
    assert sm.name == "getUser"
    # Base 1 + if 1 = 2. Interfaces and union types do not contribute to CC
    assert sm.cyclomatic_complexity == 2


def test_ts_class_method_complexity(ts_analyzer: TypeScriptMetricsAnalyzer) -> None:
    code = """class OrderService {
    processOrder(amount: number, discountCode?: string): number {
        let finalAmount = amount;
        if (discountCode && discountCode.startsWith("VIP")) {
            finalAmount *= 0.8;
        }
        return finalAmount;
    }
}
"""
    symbols = [
        ExtractedSymbol(name="OrderService", symbol_type="class", start_line=1, start_column=0, end_line=9, end_column=1),
        ExtractedSymbol(name="processOrder", symbol_type="method", start_line=2, start_column=4, end_line=8, end_column=5, parent_name="OrderService"),
    ]
    res = ts_analyzer.calculate("order.ts", code, symbols)

    assert len(res.symbols_metrics) == 1
    sm = res.symbols_metrics[0]
    assert sm.name == "processOrder"
    assert sm.symbol_type == "method"
    # Base 1 + if 1 + && 1 = 3
    assert sm.cyclomatic_complexity == 3
    assert sm.boolean_condition_count == 1
