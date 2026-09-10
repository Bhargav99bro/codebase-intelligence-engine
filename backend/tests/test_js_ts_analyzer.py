import pytest
from app.analyzers.javascript_analyzer import JavaScriptAnalyzer
from app.analyzers.typescript_analyzer import TypeScriptAnalyzer


@pytest.fixture
def js_analyzer():
    return JavaScriptAnalyzer()


@pytest.fixture
def ts_analyzer():
    return TypeScriptAnalyzer()


def test_js_function_extraction(js_analyzer):
    code = """
function calculateTotal(items, tax) {
    return items.reduce((a, b) => a + b, 0) * (1 + tax);
}

const formatCurrency = (val) => `$${val.toFixed(2)}`;
"""
    result = js_analyzer.analyze("src/utils.js", code)
    assert result.parser_status == "parsed"
    funcs = [s for s in result.symbols if s.symbol_type == "function"]
    assert len(funcs) == 2

    calc_fn = [f for f in funcs if f.name == "calculateTotal"][0]
    assert "calculateTotal(items, tax)" in calc_fn.signature
    assert calc_fn.start_line == 2

    format_fn = [f for f in funcs if f.name == "formatCurrency"][0]
    assert "formatCurrency" in format_fn.name
    assert format_fn.metadata_json.get("is_arrow") is True


def test_js_class_and_methods_extraction(js_analyzer):
    code = """
class PaymentProcessor extends BaseProcessor {
    constructor(gateway) {
        this.gateway = gateway;
    }

    async charge(amount) {
        return this.gateway.pay(amount);
    }

    static getVersion() {
        return "1.0.0";
    }
}
"""
    result = js_analyzer.analyze("src/processor.js", code)
    assert result.parser_status == "parsed"

    cls_sym = [s for s in result.symbols if s.symbol_type == "class"][0]
    assert cls_sym.name == "PaymentProcessor"
    assert "BaseProcessor" in cls_sym.signature

    methods = [s for s in result.symbols if s.symbol_type == "method"]
    assert len(methods) == 3

    names = [m.name for m in methods]
    assert "constructor" in names
    assert "charge" in names
    assert "getVersion" in names

    charge_m = [m for m in methods if m.name == "charge"][0]
    assert charge_m.parent_name == "PaymentProcessor"
    assert charge_m.metadata_json.get("is_async") is True

    static_m = [m for m in methods if m.name == "getVersion"][0]
    assert static_m.metadata_json.get("is_static") is True


def test_js_import_export_extraction(js_analyzer):
    code = """
import React, { useState, useEffect } from 'react';
import * as api from './api';

export function runTask() {
    return true;
}

export default runTask;
"""
    result = js_analyzer.analyze("src/index.js", code)
    assert result.parser_status == "parsed"

    imports = [s for s in result.symbols if s.symbol_type == "import"]
    assert len(imports) == 2
    react_import = [i for i in imports if "react" in i.signature][0]
    assert "React" in react_import.metadata_json.get("imported_names", [])

    exports = [s for s in result.symbols if s.symbol_type == "export"]
    assert len(exports) == 2


def test_ts_interface_and_type_extraction(ts_analyzer):
    code = """
export interface UserProfile {
    id: string;
    email: string;
    isActive: boolean;
}

export type Status = 'active' | 'inactive' | 'pending';

export enum Role {
    Admin = 'ADMIN',
    User = 'USER',
}
"""
    result = ts_analyzer.analyze("src/types.ts", code)
    assert result.parser_status == "parsed"

    interfaces = [s for s in result.symbols if s.symbol_type == "interface"]
    assert len(interfaces) == 1
    assert interfaces[0].name == "UserProfile"
    assert "interface UserProfile" in interfaces[0].signature

    types = [s for s in result.symbols if s.symbol_type == "type"]
    assert len(types) == 2
    type_names = [t.name for t in types]
    assert "Status" in type_names
    assert "Role" in type_names


def test_ts_function_and_class_extraction(ts_analyzer):
    code = """
export class OrderService {
    private db: Database;

    constructor(db: Database) {
        this.db = db;
    }

    async getOrder(orderId: string): Promise<Order> {
        return this.db.find(orderId);
    }
}

export function validateOrder(order: Order): boolean {
    return order.amount > 0;
}
"""
    result = ts_analyzer.analyze("src/order.ts", code)
    assert result.parser_status == "parsed"

    cls = [s for s in result.symbols if s.symbol_type == "class"][0]
    assert cls.name == "OrderService"

    methods = [s for s in result.symbols if s.symbol_type == "method"]
    assert len(methods) == 2
    assert all(m.parent_name == "OrderService" for m in methods)

    funcs = [s for s in result.symbols if s.symbol_type == "function"]
    assert len(funcs) == 1
    assert funcs[0].name == "validateOrder"


def test_js_invalid_syntax_isolation(js_analyzer):
    code = """
const broken = ( => {
"""
    result = js_analyzer.analyze("src/broken.js", code)
    assert result.parser_status == "failed"
    assert result.parser_error is not None
    assert len(result.symbols) == 0


def test_js_empty_file(js_analyzer):
    result = js_analyzer.analyze("src/empty.js", "   \n  ")
    assert result.parser_status == "parsed"
    assert len(result.symbols) == 0
