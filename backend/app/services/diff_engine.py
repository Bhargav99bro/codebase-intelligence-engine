import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class PRGateStatus(str, Enum):
    PASSED = "PASSED"
    WARNING = "WARNING"
    FAILED = "FAILED"


def compute_issue_fingerprint(
    rule_id: str,
    file_path: Optional[str],
    symbol_name: Optional[str] = None,
    metadata_json: Optional[Dict[str, Any]] = None,
) -> str:
    """Computes deterministic canonical issue fingerprint: SHA256(rule_id:norm_path:norm_scope).

    Line numbers or line buckets are strictly NOT included so that line shifts preserve the fingerprint.
    """
    rule_id_clean = (rule_id or "").strip()
    norm_path = (file_path or "").replace("\\", "/").lstrip("./").strip()

    if symbol_name and symbol_name.strip():
        norm_scope = symbol_name.strip()
    elif metadata_json and metadata_json.get("target_identifier"):
        norm_scope = str(metadata_json["target_identifier"]).strip()
    elif metadata_json and metadata_json.get("target_file_path"):
        norm_scope = f"dup_{metadata_json.get('target_file_path')}_{metadata_json.get('target_start_line')}_{metadata_json.get('target_end_line')}"
    else:
        norm_scope = "file"

    raw = f"{rule_id_clean}:{norm_path}:{norm_scope}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def canonicalize_cycle(file_paths: List[str]) -> Tuple[str, ...]:
    """Canonicalizes a directed dependency cycle by rotating so that the lexicographically minimum node is at index 0."""
    if not file_paths:
        return ()

    clean = [p.replace("\\", "/").lstrip("./") for p in file_paths]
    # Remove duplicate trailing element if closed cycle representation
    if len(clean) > 1 and clean[0] == clean[-1]:
        clean = clean[:-1]

    if not clean:
        return ()

    min_val = min(clean)
    min_idx = clean.index(min_val)
    return tuple(clean[min_idx:] + clean[:min_idx])


@dataclass
class QualityGateResult:
    status: PRGateStatus
    reasons: List[str]
    new_blocker_count: int
    new_critical_count: int
    new_cycles_count: int
    delta_health: float
    delta_duplication_ratio: float

    @property
    def passed(self) -> bool:
        return self.status == PRGateStatus.PASSED

    @property
    def new_blocker_critical_count(self) -> int:
        return self.new_blocker_count + self.new_critical_count

    @property
    def new_major_count(self) -> int:
        return 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "passed": self.status == PRGateStatus.PASSED,
            "reasons": self.reasons,
            "new_blocker_count": self.new_blocker_count,
            "new_critical_count": self.new_critical_count,
            "new_blocker_critical_count": self.new_blocker_count + self.new_critical_count,
            "new_cycles_count": self.new_cycles_count,
            "delta_health": self.delta_health,
            "delta_duplication_ratio": self.delta_duplication_ratio,
        }


@dataclass
class AnalysisDiffResult:
    base_id: str
    head_id: str
    delta_health_score: float
    delta_debt_minutes: int
    pillar_deltas: Dict[str, float]
    new_issues: List[Dict[str, Any]]
    fixed_issues: List[Dict[str, Any]]
    persistent_issues: List[Dict[str, Any]]
    new_cycles: List[List[str]]
    resolved_cycles: List[List[str]]
    persistent_cycles: List[List[str]]
    quality_gate: QualityGateResult

    @property
    def base_analysis_id(self) -> str:
        return self.base_id

    @property
    def current_analysis_id(self) -> str:
        return self.head_id

    def to_dict(self) -> Dict[str, Any]:
        return {
            "base_id": self.base_id,
            "head_id": self.head_id,
            "base_analysis_id": self.base_id,
            "current_analysis_id": self.head_id,
            "delta_health_score": self.delta_health_score,
            "delta_debt_minutes": self.delta_debt_minutes,
            "pillar_deltas": self.pillar_deltas,
            "new_issues_count": len(self.new_issues),
            "fixed_issues_count": len(self.fixed_issues),
            "persistent_issues_count": len(self.persistent_issues),
            "new_issues": self.new_issues,
            "fixed_issues": self.fixed_issues,
            "persistent_issues": self.persistent_issues,
            "new_cycles": self.new_cycles,
            "resolved_cycles": self.resolved_cycles,
            "persistent_cycles": self.persistent_cycles,
            "quality_gate": self.quality_gate.to_dict(),
        }


class AnalysisDiffEngine:
    """Performs deterministic diffing between baseline and head analyses."""

    def __init__(self, allowed_score_drop: float = 2.0) -> None:
        self.allowed_score_drop = float(allowed_score_drop)

    def compare_analyses(
        self,
        base_analysis_data: Dict[str, Any],
        current_analysis_data: Dict[str, Any],
    ) -> AnalysisDiffResult:
        base_id = str(base_analysis_data.get("id", ""))
        curr_id = str(current_analysis_data.get("id", ""))

        base_health = base_analysis_data.get("health_score") or {}
        curr_health = current_analysis_data.get("health_score") or {}

        # 1. Health & Debt deltas
        base_s = float(base_health.get("overall_score", 100.0))
        curr_s = float(curr_health.get("overall_score", 100.0))
        delta_health = round(curr_s - base_s, 1)

        base_debt = int(base_health.get("technical_debt_minutes", 0))
        curr_debt = int(curr_health.get("technical_debt_minutes", 0))
        delta_debt = curr_debt - base_debt

        # Pillar deltas
        base_maint = float(base_health.get("maintainability_score", 100.0))
        curr_maint = float(curr_health.get("maintainability_score", 100.0))

        base_complex = float(base_health.get("complexity_score", 100.0))
        curr_complex = float(curr_health.get("complexity_score", 100.0))

        base_arch = float(base_health.get("architecture_score", 100.0))
        curr_arch = float(curr_health.get("architecture_score", 100.0))

        base_hygiene = float(base_health.get("hygiene_score", 100.0))
        curr_hygiene = float(curr_health.get("hygiene_score", 100.0))

        base_dup = float(base_health.get("duplication_score", 100.0))
        curr_dup = float(curr_health.get("duplication_score", 100.0))

        pillar_deltas = {
            "maintainability": round(curr_maint - base_maint, 1),
            "complexity": round(curr_complex - base_complex, 1),
            "architecture": round(curr_arch - base_arch, 1),
            "hygiene_and_reliability": round(curr_hygiene - base_hygiene, 1),
            "duplication": round(curr_dup - base_dup, 1),
        }

        # 2. Issue Lifecycle (new, fixed, persistent)
        base_issues = base_analysis_data.get("issues", [])
        curr_issues = current_analysis_data.get("issues", [])

        base_fp_map: Dict[str, Dict[str, Any]] = {}
        for iss in base_issues:
            fp = compute_issue_fingerprint(
                iss.get("rule_id", ""),
                iss.get("file_path"),
                iss.get("symbol_name"),
                iss.get("metadata_json"),
            )
            base_fp_map[fp] = iss

        curr_fp_map: Dict[str, Dict[str, Any]] = {}
        for iss in curr_issues:
            fp = compute_issue_fingerprint(
                iss.get("rule_id", ""),
                iss.get("file_path"),
                iss.get("symbol_name"),
                iss.get("metadata_json"),
            )
            curr_fp_map[fp] = iss

        base_fps = set(base_fp_map.keys())
        curr_fps = set(curr_fp_map.keys())

        new_fps = curr_fps - base_fps
        fixed_fps = base_fps - curr_fps
        persistent_fps = curr_fps & base_fps

        new_issues = [curr_fp_map[fp] for fp in sorted(new_fps)]
        fixed_issues = [base_fp_map[fp] for fp in sorted(fixed_fps)]
        persistent_issues = [curr_fp_map[fp] for fp in sorted(persistent_fps)]

        # 3. Cycle Diffing
        base_cycles_raw = base_analysis_data.get("cycles", [])
        curr_cycles_raw = current_analysis_data.get("cycles", [])

        def _extract_cycle_nodes(item: Any) -> List[str]:
            if isinstance(item, (list, tuple)):
                return list(item)
            if isinstance(item, dict):
                return item.get("file_paths") or item.get("cycle") or []
            if hasattr(item, "file_paths"):
                return list(getattr(item, "file_paths", []))
            if hasattr(item, "cycle"):
                return list(getattr(item, "cycle", []))
            return []

        base_cycle_map: Dict[Tuple[str, ...], List[str]] = {}
        for c in base_cycles_raw:
            fps = _extract_cycle_nodes(c)
            canon = canonicalize_cycle(fps)
            if canon:
                base_cycle_map[canon] = list(canon)

        curr_cycle_map: Dict[Tuple[str, ...], List[str]] = {}
        for c in curr_cycles_raw:
            fps = _extract_cycle_nodes(c)
            canon = canonicalize_cycle(fps)
            if canon:
                curr_cycle_map[canon] = list(canon)

        base_c_set = set(base_cycle_map.keys())
        curr_c_set = set(curr_cycle_map.keys())

        new_c_keys = curr_c_set - base_c_set
        resolved_c_keys = base_c_set - curr_c_set
        persistent_c_keys = curr_c_set & base_c_set

        new_cycles = [list(k) for k in sorted(new_c_keys)]
        resolved_cycles = [list(k) for k in sorted(resolved_c_keys)]
        persistent_cycles = [list(k) for k in sorted(persistent_c_keys)]

        # 4. PR Quality Gate Evaluation
        new_blocker_cnt = sum(
            1 for iss in new_issues if iss.get("severity") == "blocker"
        )
        new_critical_cnt = sum(
            1 for iss in new_issues if iss.get("severity") == "critical"
        )
        new_cycles_cnt = len(new_cycles)

        base_dup_ratio = float(base_health.get("duplication_ratio", 0.0))
        curr_dup_ratio = float(curr_health.get("duplication_ratio", 0.0))
        delta_dup_ratio = round(curr_dup_ratio - base_dup_ratio, 2)

        gate_status = PRGateStatus.PASSED
        reasons: List[str] = []

        # Check FAILED criteria:
        # FAILED if ANY: new BLOCKER, new dependency cycle, or delta_health < -allowed_score_drop
        if new_blocker_cnt > 0:
            gate_status = PRGateStatus.FAILED
            reasons.append(f"{new_blocker_cnt} new Blocker issue(s) introduced")
        if new_cycles_cnt > 0:
            gate_status = PRGateStatus.FAILED
            reasons.append(f"{new_cycles_cnt} new circular dependency cycle(s) introduced")
        if delta_health < -self.allowed_score_drop:
            gate_status = PRGateStatus.FAILED
            reasons.append(f"Overall health score decreased by {abs(delta_health):.1f} points (threshold < -{self.allowed_score_drop:.1f})")

        # Check WARNING criteria if not already FAILED:
        # WARNING only if no FAILED condition AND ANY: new CRITICAL, or -allowed_score_drop <= delta_health < 0.0
        if gate_status != PRGateStatus.FAILED:
            if new_critical_cnt > 0:
                gate_status = PRGateStatus.WARNING
                reasons.append(f"{new_critical_cnt} new Critical issue(s) introduced")
            if -self.allowed_score_drop <= delta_health < 0.0:
                gate_status = PRGateStatus.WARNING
                reasons.append(f"Overall health score dropped by {abs(delta_health):.1f} points (warning range [-{self.allowed_score_drop:.1f}, 0.0))")

        if not reasons:
            reasons.append("Quality gate checks passed successfully with no regressions.")

        quality_gate = QualityGateResult(
            status=gate_status,
            reasons=reasons,
            new_blocker_count=new_blocker_cnt,
            new_critical_count=new_critical_cnt,
            new_cycles_count=new_cycles_cnt,
            delta_health=delta_health,
            delta_duplication_ratio=delta_dup_ratio,
        )

        return AnalysisDiffResult(
            base_id=base_id,
            head_id=curr_id,
            delta_health_score=delta_health,
            delta_debt_minutes=delta_debt,
            pillar_deltas=pillar_deltas,
            new_issues=new_issues,
            fixed_issues=fixed_issues,
            persistent_issues=persistent_issues,
            new_cycles=new_cycles,
            resolved_cycles=resolved_cycles,
            persistent_cycles=persistent_cycles,
            quality_gate=quality_gate,
        )
