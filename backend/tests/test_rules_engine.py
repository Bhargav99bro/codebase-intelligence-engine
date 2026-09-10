from typing import List
import pytest
from app.rules.base import BaseRule, CodebaseIssue, RuleContext
from app.rules.engine import RulesEngine


class GoodRule(BaseRule):
    rule_id = "GOOD-001"
    rule_name = "Good Rule"
    category = "hygiene"
    severity = "minor"

    def evaluate(self, context: RuleContext) -> List[CodebaseIssue]:
        return [
            CodebaseIssue(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                category=self.category,
                severity=self.severity,
                title="Good Issue",
                description="Everything is fine",
            )
        ]


class CrashingRule(BaseRule):
    rule_id = "CRASH-001"
    rule_name = "Crashing Rule"
    category = "hygiene"
    severity = "blocker"

    def evaluate(self, context: RuleContext) -> List[CodebaseIssue]:
        raise RuntimeError("Simulated crash in diagnostic rule!")


def test_rules_engine_fault_isolation():
    engine = RulesEngine(rules=[CrashingRule(), GoodRule()])
    dummy_ctx = RuleContext(
        parsed_files_data=[],
        file_metrics_map={},
        graph=None,
        file_id_map={},
    )
    issues = engine.run(dummy_ctx)

    # CrashingRule must not fail the run, and GoodRule's output must be collected
    assert len(issues) == 1
    assert issues[0].rule_id == "GOOD-001"


def test_rules_engine_default_rules_registered():
    engine = RulesEngine()
    assert len(engine.rules) >= 15
    rule_ids = {r.rule_id for r in engine.rules}
    assert "ARCH-001" in rule_ids
    assert "COMPLEX-001" in rule_ids
    assert "MAINT-001" in rule_ids
    assert "HYGIENE-001" in rule_ids
    assert "SEC-001" in rule_ids
