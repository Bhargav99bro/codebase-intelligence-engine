import re
from typing import Any, Dict, List, Optional

from app.rules.base import IssueSeverity


def sanitize_repo_path(raw_path: Optional[str]) -> str:
    """Sanitizes file paths to repository-relative paths, stripping any Docker/temp prefixes."""
    if not raw_path:
        return "repository"

    # Replace backslashes
    path = raw_path.replace("\\", "/")

    # Strip any /tmp/cie_repos/cie_repo_XXXXXX/ prefix or similar
    path = re.sub(r"^.*?/tmp/cie_repos/[^/]+/", "", path)
    path = re.sub(r"^/tmp/[^/]+/", "", path)
    path = re.sub(r"^[A-Za-z]:/", "", path)

    # Strip leading slash
    return path.lstrip("/")


def map_severity_to_sarif_level(severity: Optional[str]) -> str:
    """Maps diagnostic severity to OASIS SARIF level ('error' | 'warning' | 'note')."""
    sev = (severity or "").lower()
    if sev in (IssueSeverity.BLOCKER.value, IssueSeverity.CRITICAL.value):
        return "error"
    if sev == IssueSeverity.MAJOR.value:
        return "warning"
    if sev in (IssueSeverity.MINOR.value, IssueSeverity.INFO.value):
        return "note"
    return "warning"


class SarifExporter:
    """Generates OASIS SARIF v2.1.0 compliant reports for static analysis results."""

    SCHEMA_URI = "https://json.schemastore.org/sarif-2.1.0.json"
    SARIF_VERSION = "2.1.0"

    DEFAULT_RULES = [
        {"id": "ARCH-001", "name": "CyclicDependency", "desc": "Circular dependency cycle detected in the dependency graph.", "severity": "critical"},
        {"id": "ARCH-002", "name": "GodModule", "desc": "Module with excessive responsibility (fan-out >= 12 and SLOC >= 500).", "severity": "major"},
        {"id": "ARCH-003", "name": "UnstableHub", "desc": "Module with high bidirectional coupling (fan-in >= 8 and fan-out >= 8).", "severity": "major"},
        {"id": "ARCH-004", "name": "UnstableDependency", "desc": "Stable module depending on an unstable module (SAP violation).", "severity": "minor"},
        {"id": "COMPLEX-001", "name": "CriticalComplexityMethod", "desc": "Function/method declaring Cyclomatic Complexity >= 20.", "severity": "critical"},
        {"id": "COMPLEX-002", "name": "HighComplexityMethod", "desc": "Function/method declaring Cyclomatic Complexity 11-19.", "severity": "major"},
        {"id": "COMPLEX-003", "name": "DeepNestingSmell", "desc": "Code block nesting depth >= 5.", "severity": "major"},
        {"id": "COMPLEX-004", "name": "GiantFileLowCohesion", "desc": "File exceeding 800 source lines of code (SLOC >= 800).", "severity": "major"},
        {"id": "COMPLEX-005", "name": "LongParameterList", "desc": "Function/method declaring >= 6 parameters.", "severity": "minor"},
        {"id": "MAINT-001", "name": "VeryLowMaintainability", "desc": "File with Maintainability Index < 40.0.", "severity": "critical"},
        {"id": "MAINT-002", "name": "PoorMaintainability", "desc": "File with Maintainability Index 40.0 - 54.9.", "severity": "major"},
        {"id": "MAINT-003", "name": "UndocumentedPublicAPI", "desc": "Public API symbol lacking docstring documentation.", "severity": "minor"},
        {"id": "HYGIENE-001", "name": "EmptyExceptionHandler", "desc": "Empty except/catch block that silently swallows exceptions.", "severity": "major"},
        {"id": "HYGIENE-002", "name": "DeadPrivateSymbol", "desc": "Private helper symbol defined but never invoked in file.", "severity": "minor"},
        {"id": "SEC-001", "name": "HardcodedSecretPattern", "desc": "Pattern resembling embedded access credentials or private key.", "severity": "blocker"},
        {"id": "SEC-002", "name": "DynamicExecutionSink", "desc": "Dangerous dynamic code execution sink (eval, exec, new Function, dangerouslySetInnerHTML).", "severity": "blocker"},
    ]

    @classmethod
    def generate_sarif(
        cls,
        issues: List[Any],
        repository_url: str = "",
        commit_hash: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Builds an OASIS SARIF v2.1.0 document from detected issues."""
        # 1. Build driver rules dictionary
        rules_dict: Dict[str, Dict[str, Any]] = {}
        for r_def in cls.DEFAULT_RULES:
            level = map_severity_to_sarif_level(r_def["severity"])
            rules_dict[r_def["id"]] = {
                "id": r_def["id"],
                "name": r_def["name"],
                "shortDescription": {"text": r_def["name"]},
                "fullDescription": {"text": r_def["desc"]},
                "defaultConfiguration": {"level": level},
                "help": {"text": r_def["desc"]},
            }

        # Ensure any custom issue ruleId also exists in driver.rules
        for iss in issues:
            rid = getattr(iss, "rule_id", None) or (iss.get("rule_id") if isinstance(iss, dict) else None)
            rname = getattr(iss, "rule_name", None) or (iss.get("rule_name") if isinstance(iss, dict) else None) or rid or "CustomRule"
            rdesc = getattr(iss, "description", None) or (iss.get("description") if isinstance(iss, dict) else None) or rname
            sev = getattr(iss, "severity", None) or (iss.get("severity") if isinstance(iss, dict) else None)
            if rid and rid not in rules_dict:
                rules_dict[rid] = {
                    "id": rid,
                    "name": rname,
                    "shortDescription": {"text": rname},
                    "fullDescription": {"text": rdesc},
                    "defaultConfiguration": {"level": map_severity_to_sarif_level(sev)},
                }

        driver_rules = list(rules_dict.values())
        # Sort rules by ID for determinism
        driver_rules.sort(key=lambda r: r["id"])

        # 2. Build results list
        raw_results = []
        for iss in issues:
            rule_id = getattr(iss, "rule_id", None) or (iss.get("rule_id") if isinstance(iss, dict) else None) or "UNKNOWN"
            severity = getattr(iss, "severity", None) or (iss.get("severity") if isinstance(iss, dict) else None)
            raw_path = getattr(iss, "file_path", None) or (iss.get("file_path") if isinstance(iss, dict) else None)
            clean_path = sanitize_repo_path(raw_path)

            line_no = getattr(iss, "line_number", None) or (iss.get("line_number") if isinstance(iss, dict) else None) or 1
            end_line_no = getattr(iss, "end_line_number", None) or (iss.get("end_line_number") if isinstance(iss, dict) else None)

            start_line = max(1, int(line_no))
            end_line = max(start_line, int(end_line_no)) if end_line_no else start_line

            title = getattr(iss, "title", None) or (iss.get("title") if isinstance(iss, dict) else None) or rule_id
            description = getattr(iss, "description", None) or (iss.get("description") if isinstance(iss, dict) else None) or title

            level = map_severity_to_sarif_level(severity)

            region: Dict[str, Any] = {"startLine": start_line}
            if end_line > start_line:
                region["endLine"] = end_line

            raw_results.append({
                "ruleId": rule_id,
                "level": level,
                "message": {"text": f"{title}: {description}"},
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {
                                "uri": clean_path,
                                "uriBaseId": "%SRCROOT%",
                            },
                            "region": region,
                        }
                    }
                ],
                "_sort_key": (clean_path, start_line, rule_id),
            })

        # NON-NEGOTIABLE DETERMINISTIC RESULT ORDERING:
        # (file_path, start_line, rule_id)
        raw_results.sort(key=lambda item: item["_sort_key"])

        results = []
        for item in raw_results:
            d = dict(item)
            del d["_sort_key"]
            results.append(d)

        # 3. Construct SARIF payload
        return {
            "$schema": cls.SCHEMA_URI,
            "version": cls.SARIF_VERSION,
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "name": "Codebase Intelligence Engine",
                            "version": "1.0.0",
                            "informationUri": "https://github.com/codebase-intelligence-engine",
                            "rules": driver_rules,
                        }
                    },
                    "invocations": [
                        {
                            "executionSuccessful": True,
                        }
                    ],
                    "results": results,
                }
            ],
        }
