from datetime import datetime
from typing import Any, Dict, List, Optional


class MarkdownExporter:
    """Compiles a publication-ready Executive Markdown audit report for pull requests and wikis."""

    @classmethod
    def generate_report(
        cls,
        repository_url: str,
        commit_hash: Optional[str],
        analysis_date: Optional[datetime],
        total_files: int,
        total_sloc: int,
        health_summary: Optional[Dict[str, Any]],
        quality_gate: Optional[Dict[str, Any]],
        hotspots: List[Any],
        recommendations: List[Any],
        issues_summary: Optional[Dict[str, Any]],
    ) -> str:
        date_str = analysis_date.strftime("%Y-%m-%d %H:%M:%S UTC") if analysis_date else datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        commit_str = commit_hash[:8] if commit_hash else "HEAD"
        hs = health_summary or {}
        qg = quality_gate or {}
        iss_sum = issues_summary or {}

        overall_score = hs.get("overall_score", 0.0)
        grade = hs.get("grade", "N/A")
        debt_hours = round(hs.get("technical_debt_minutes", 0) / 60.0, 1)
        debt_ratio = hs.get("debt_ratio_hours_per_ksloc", 0.0)

        # Quality gate verdict badge
        qg_status = qg.get("status", "NOT_EVALUATED")
        qg_badge = "✅ **PASSED**" if qg_status == "PASSED" else "⚠️ **WARNING**" if qg_status == "WARNING" else "❌ **FAILED**"

        lines = [
            f"# Codebase Intelligence Audit Report",
            f"",
            f"> **Repository**: `{repository_url}`  ",
            f"> **Commit**: `{commit_str}` | **Analyzed At**: `{date_str}`  ",
            f"> **Volume**: `{total_files:,}` files | `{total_sloc:,}` SLOC",
            f"",
            f"---",
            f"",
            f"## 1. Executive Summary",
            f"",
            f"| Overall Health Score | Letter Grade | Quality Gate Verdict | Technical Debt | Debt Ratio |",
            f"| :---: | :---: | :---: | :---: | :---: |",
            f"| **{overall_score:.1f} / 100.0** | **`{grade}`** | {qg_badge} | **{debt_hours} hrs** | **{debt_ratio} hrs/kSLOC** |",
            f"",
            f"---",
            f"",
            f"## 2. Four Health Pillars",
            f"",
            f"| Health Pillar | Score | Weight | Status |",
            f"| :--- | :---: | :---: | :--- |",
            f"| **Maintainability** | `{hs.get('maintainability_score', 0.0):.1f} / 100.0` | 25% | {'🟢 Healthy' if hs.get('maintainability_score', 0) >= 70 else '🟡 Degraded' if hs.get('maintainability_score', 0) >= 50 else '🔴 Critical'} |",
            f"| **Complexity** | `{hs.get('complexity_score', 0.0):.1f} / 100.0` | 25% | {'🟢 Healthy' if hs.get('complexity_score', 0) >= 70 else '🟡 Moderate' if hs.get('complexity_score', 0) >= 50 else '🔴 High Risk'} |",
            f"| **Architecture** | `{hs.get('architecture_score', 0.0):.1f} / 100.0` | 25% | {'🟢 Decoupled' if hs.get('architecture_score', 0) >= 75 else '🟡 Coupling Concerns' if hs.get('architecture_score', 0) >= 50 else '🔴 Highly Coupled / Cycles'} |",
            f"| **Hygiene & Reliability** | `{hs.get('hygiene_score', 0.0):.1f} / 100.0` | 25% | {'🟢 Clean' if hs.get('hygiene_score', 0) >= 80 else '🟡 Minor Debt' if hs.get('hygiene_score', 0) >= 60 else '🔴 Blocker / Security Issues'} |",
            f"",
            f"---",
            f"",
            f"## 3. Quality Gate Evaluation",
            f"",
            f"**Status**: {qg_badge} ({qg.get('passed_count', 0)} passed, {qg.get('failed_count', 0)} failed, {qg.get('warning_count', 0)} warnings)",
            f"",
            f"| Rule ID | Evaluated Metric | Actual Value | Operator | Threshold | Verdict |",
            f"| :--- | :--- | :---: | :---: | :---: | :---: |",
        ]

        for cond in qg.get("conditions", []):
            cid = cond.get("condition_id", "QG")
            metric = cond.get("metric", "")
            act = cond.get("actual_value", "")
            op = cond.get("operator", "")
            thresh = cond.get("threshold", "")
            passed = cond.get("passed", False)
            status_tag = "✅ PASS" if passed else "❌ FAIL" if cond.get("severity") == "fail" else "⚠️ WARN"
            lines.append(f"| `{cid}` | `{metric}` | `{act}` | `{op}` | `{thresh}` | {status_tag} |")

        lines.extend([
            f"",
            f"---",
            f"",
            f"## 4. Top 5 Hotspots (Composite Complexity × Coupling × Issues)",
            f"",
            f"| Rank | File Path | Hotspot Score ($H$) | Complexity ($C_{{norm}}$) | Centrality ($A_{{norm}}$) | SLOC | Max CC | Fan-In / Fan-Out |",
            f"| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |",
        ])

        top_hotspots = hotspots[:5] if hotspots else []
        if top_hotspots:
            for hs_rec in top_hotspots:
                rank = getattr(hs_rec, "rank", None) or (hs_rec.get("rank") if isinstance(hs_rec, dict) else 1)
                fp = getattr(hs_rec, "file_path", None) or (hs_rec.get("file_path") if isinstance(hs_rec, dict) else "")
                h_score = getattr(hs_rec, "hotspot_score", None) or (hs_rec.get("hotspot_score") if isinstance(hs_rec, dict) else 0.0)
                c_risk = getattr(hs_rec, "complexity_risk", None) or (hs_rec.get("complexity_risk") if isinstance(hs_rec, dict) else 0.0)
                a_cent = getattr(hs_rec, "architectural_centrality", None) or (hs_rec.get("architectural_centrality") if isinstance(hs_rec, dict) else 0.0)
                sloc = getattr(hs_rec, "sloc", None) or (hs_rec.get("sloc") if isinstance(hs_rec, dict) else 0)
                max_cc = getattr(hs_rec, "max_cyclomatic_complexity", None) or (hs_rec.get("max_cyclomatic_complexity") if isinstance(hs_rec, dict) else 0)
                fi = getattr(hs_rec, "fan_in", None) or (hs_rec.get("fan_in") if isinstance(hs_rec, dict) else 0)
                fo = getattr(hs_rec, "fan_out", None) or (hs_rec.get("fan_out") if isinstance(hs_rec, dict) else 0)
                lines.append(f"| **{rank}** | `{fp}` | **{h_score:.1f}** | {c_risk:.1f} | {a_cent:.1f} | {sloc:,} | {max_cc} | {fi} in / {fo} out |")
        else:
            lines.append(f"| - | *No significant hotspots detected* | - | - | - | - | - | - |")

        lines.extend([
            f"",
            f"---",
            f"",
            f"## 5. Top 5 Prioritized Refactoring Recommendations",
            f"",
            f"| Rank | Target | Expected Score Recovery ($\\Delta S$) | Estimated Effort | Summary Action Plan |",
            f"| :---: | :--- | :---: | :---: | :--- |",
        ])

        top_recs = recommendations[:5] if recommendations else []
        if top_recs:
            for rec in top_recs:
                rank = getattr(rec, "rank", None) or (rec.get("rank") if isinstance(rec, dict) else 1)
                t_id = getattr(rec, "target_identifier", None) or (rec.get("target_identifier") if isinstance(rec, dict) else "")
                delta = getattr(rec, "estimated_score_recovery", None) or (rec.get("estimated_score_recovery") if isinstance(rec, dict) else None)
                delta_str = f"**+{delta:.1f} pts**" if delta is not None else "*Qualitative*"
                effort_min = getattr(rec, "estimated_effort_minutes", None) or (rec.get("estimated_effort_minutes") if isinstance(rec, dict) else 0)
                action = getattr(rec, "action_summary", None) or (rec.get("action_summary") if isinstance(rec, dict) else "")
                lines.append(f"| **{rank}** | `{t_id}` | {delta_str} | {round(effort_min / 60.0, 1)} hrs | {action} |")
        else:
            lines.append(f"| - | *No urgent recommendations* | - | - | Codebase meets quality baseline. |")

        lines.extend([
            f"",
            f"---",
            f"",
            f"## 6. Diagnostic Issues & Severity Distribution",
            f"",
            f"| Blocker | Critical | Major | Minor | Total Issues |",
            f"| :---: | :---: | :---: | :---: | :---: |",
            f"| **{hs.get('blocker_count', 0)}** | **{hs.get('critical_count', 0)}** | **{hs.get('major_count', 0)}** | **{hs.get('minor_count', 0)}** | **{hs.get('total_issues_count', 0)}** |",
            f"",
            f"Generated automatically by [Codebase Intelligence Engine](https://github.com/codebase-intelligence-engine).",
        ])

        return "\n".join(lines) + "\n"
