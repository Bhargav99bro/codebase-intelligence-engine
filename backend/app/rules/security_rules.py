import re
from typing import List
import uuid

from app.rules.base import BaseRule, CodebaseIssue, IssueCategory, IssueSeverity, RuleContext


class HardcodedSecretPatternRule(BaseRule):
    rule_id = "SEC-001"
    rule_name = "Hardcoded Secret Pattern"
    category = IssueCategory.SECURITY
    severity = IssueSeverity.BLOCKER
    default_remediation_minutes = 60

    SECRET_PATTERNS = [
        ("AWS Access Key", re.compile(r"\b(AKIA[0-9A-Z]{16})\b")),
        ("Private Key Header", re.compile(r"-----BEGIN (?:RSA|EC|OPENSSH|DSA|PGP)?\s*PRIVATE KEY-----")),
        ("GitHub Token", re.compile(r"\b(ghp_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9_]{82})\b")),
        ("Generic Secret Assignment", re.compile(r'''(?i)(?:api_key|secret_key|auth_token|bearer_token)\s*=\s*['"][a-zA-Z0-9_\-\.]{24,}['"]''')),
    ]

    def evaluate(self, context: RuleContext) -> List[CodebaseIssue]:
        issues: List[CodebaseIssue] = []

        for item in context.parsed_files_data:
            df = item["df"]
            content = item.get("content")
            fid = context.file_id_map.get(df.path)
            if not content or not df.is_analyzable:
                continue

            for pattern_name, pattern in self.SECRET_PATTERNS:
                for match in pattern.finditer(content):
                    line_no = content[:match.start()].count("\n") + 1
                    issues.append(
                        CodebaseIssue(
                            id=uuid.uuid4(),
                            rule_id=self.rule_id,
                            rule_name=self.rule_name,
                            category=self.category.value,
                            severity=self.severity.value,
                            title=f"Potential Hardcoded Secret: {pattern_name}",
                            description=(
                                f"Detected pattern resembling an embedded credential or private key at line {line_no} in '{df.path}'. "
                                "Hardcoded secrets in source code risk unauthorized access if committed to version control. Use environment variables or a secrets manager."
                            ),
                            file_id=fid,
                            file_path=df.path,
                            line_number=line_no,
                            remediation_effort_minutes=self.default_remediation_minutes,
                            metadata_json={
                                "pattern_type": pattern_name,
                                "target_type": "file",
                                "target_identifier": df.path,
                            },
                        )
                    )
        return issues


class DynamicExecutionSinkRule(BaseRule):
    rule_id = "SEC-002"
    rule_name = "Dangerous Dynamic Execution / Unsafe Code Injection Sink"
    category = IssueCategory.SECURITY
    severity = IssueSeverity.BLOCKER
    default_remediation_minutes = 60

    # Distinct sink configuration mapping (title, vuln_class, description, pattern)
    SINK_CONFIGS = {
        "eval": {
            "title": "Dynamic Expression Evaluation via eval()",
            "vuln_class": "code_injection_eval",
            "description": "Detected call to 'eval()' at line {line_no} in '{file_path}'. Direct runtime evaluation of strings risks remote code execution (RCE) and uncontrolled local scope access if inputs are untrusted. Replace with safe serializers or ast.literal_eval.",
            "pattern": re.compile(r"\beval\s*\("),
            "languages": None,  # all languages
        },
        "exec": {
            "title": "Arbitrary Code Execution via exec()",
            "vuln_class": "code_execution_exec",
            "description": "Detected call to 'exec()' at line {line_no} in '{file_path}'. Executing multiline dynamic statements allows arbitrary system execution and variable alteration. Refactor to avoid dynamic statement generation.",
            "pattern": re.compile(r"\bexec\s*\("),
            "languages": {"python"},
        },
        "Function": {
            "title": "Dynamic Function Construction via new Function()",
            "vuln_class": "dynamic_function_constructor",
            "description": "Detected runtime constructor 'new Function()' at line {line_no} in '{file_path}'. Compiling arbitrary code strings dynamically risks script injection and circumvents static safety analysis. Use statically declared functions.",
            "pattern": re.compile(r"\bnew\s+Function\s*\("),
            "languages": {"javascript", "typescript"},
        },
        "dangerouslySetInnerHTML": {
            "title": "Direct DOM HTML Injection via dangerouslySetInnerHTML",
            "vuln_class": "dom_xss_injection",
            "description": "Detected usage of 'dangerouslySetInnerHTML' at line {line_no} in '{file_path}'. Bypassing component XSS sanitation by inserting raw HTML into the DOM introduces Cross-Site Scripting (XSS) risks. Sanitize content with DOMPurify before rendering.",
            "pattern": re.compile(r"\bdangerouslySetInnerHTML\b"),
            "languages": {"javascript", "typescript"},
        },
    }

    def evaluate(self, context: RuleContext) -> List[CodebaseIssue]:
        issues: List[CodebaseIssue] = []

        for item in context.parsed_files_data:
            df = item["df"]
            content = item.get("content")
            fid = context.file_id_map.get(df.path)
            if not content or not df.is_analyzable:
                continue

            lang = (df.language or "").lower()

            for sink_type, cfg in self.SINK_CONFIGS.items():
                if cfg["languages"] is not None and lang not in cfg["languages"]:
                    continue

                for match in cfg["pattern"].finditer(content):
                    line_no = content[:match.start()].count("\n") + 1
                    issues.append(
                        CodebaseIssue(
                            id=uuid.uuid4(),
                            rule_id=self.rule_id,
                            rule_name=self.rule_name,
                            category=self.category.value,
                            severity=self.severity.value,
                            title=cfg["title"],
                            description=cfg["description"].format(line_no=line_no, file_path=df.path),
                            file_id=fid,
                            file_path=df.path,
                            line_number=line_no,
                            remediation_effort_minutes=self.default_remediation_minutes,
                            metadata_json={
                                "sink_type": sink_type,
                                "vulnerability_class": cfg["vuln_class"],
                                "is_heuristic": True,
                                "target_type": "file",
                                "target_identifier": df.path,
                            },
                        )
                    )
        return issues
