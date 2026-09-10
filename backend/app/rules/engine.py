import logging
from typing import List

from app.rules.architecture_rules import (
    CyclicDependencyRule,
    GodModuleRule,
    UnstableDependencyRule,
    UnstableHubRule,
)
from app.rules.base import BaseRule, CodebaseIssue, RuleContext
from app.rules.complexity_rules import (
    CriticalComplexityMethodRule,
    DeepNestingRule,
    GiantFileRule,
    HighComplexityMethodRule,
    LongParameterListRule,
)
from app.rules.hygiene_rules import DeadPrivateSymbolRule, EmptyExceptionHandlerRule
from app.rules.maintainability_rules import (
    DuplicateBlockRule,
    PoorMaintainabilityRule,
    UndocumentedPublicAPIRule,
    VeryLowMaintainabilityRule,
)
from app.rules.security_rules import DynamicExecutionSinkRule, HardcodedSecretPatternRule

logger = logging.getLogger(__name__)


class RulesEngine:
    """Executes registered static analysis diagnostic rules with per-rule fault isolation."""

    def __init__(self, rules: List[BaseRule] = None) -> None:
        if rules is not None:
            self.rules = rules
        else:
            self.rules = [
                # Architecture Rules
                CyclicDependencyRule(),
                GodModuleRule(),
                UnstableHubRule(),
                UnstableDependencyRule(),
                # Complexity Rules
                CriticalComplexityMethodRule(),
                HighComplexityMethodRule(),
                DeepNestingRule(),
                GiantFileRule(),
                LongParameterListRule(),
                # Maintainability Rules
                VeryLowMaintainabilityRule(),
                PoorMaintainabilityRule(),
                UndocumentedPublicAPIRule(),
                DuplicateBlockRule(),
                # Hygiene Rules
                EmptyExceptionHandlerRule(),
                DeadPrivateSymbolRule(),
                # Security Rules
                HardcodedSecretPatternRule(),
                DynamicExecutionSinkRule(),
            ]

    def run(self, context: RuleContext) -> List[CodebaseIssue]:
        all_issues: List[CodebaseIssue] = []

        for rule in self.rules:
            try:
                issues = rule.evaluate(context)
                all_issues.extend(issues)
            except Exception as exc:
                logger.warning("Rule '%s' (%s) failed during evaluation: %s", rule.rule_id, rule.rule_name, exc)

        # Sort issues by severity priority: blocker -> critical -> major -> minor -> info
        severity_order = {"blocker": 0, "critical": 1, "major": 2, "minor": 3, "info": 4}
        all_issues.sort(key=lambda it: (severity_order.get(it.severity, 5), it.file_path or "", it.line_number or 0))

        return all_issues
