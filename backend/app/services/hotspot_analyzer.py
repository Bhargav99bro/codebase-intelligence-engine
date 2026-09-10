from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import uuid

from app.dependencies.graph import DirectedDependencyGraph
from app.metrics.base import FileMetrics
from app.rules.base import CodebaseIssue, IssueSeverity


def clamp(val: float, low: float = 0.0, high: float = 100.0) -> float:
    """Clamps a floating point value to [low, high]."""
    return max(low, min(val, high))


def compute_c_norm(sloc: int, max_cc: int, max_nesting: int) -> float:
    """Calculates normalized complexity risk score C_norm in [0, 100]."""
    raw = ((sloc / 1000.0) * 40.0) + ((max_cc / 20.0) * 40.0) + ((max_nesting / 5.0) * 20.0)
    return round(clamp(raw, 0.0, 100.0), 1)


def compute_a_norm(fan_in: int, fan_out: int) -> float:
    """Calculates normalized architectural centrality A_norm in [0, 100]."""
    raw = ((fan_in / 10.0) * 60.0) + ((fan_out / 10.0) * 40.0)
    return round(clamp(raw, 0.0, 100.0), 1)


def compute_i_norm(n_blocker: int, n_critical: int, n_major: int, n_minor: int) -> float:
    """Calculates normalized issue severity burden I_norm in [0, 100]."""
    raw = (n_blocker * 40.0) + (n_critical * 25.0) + (n_major * 10.0) + (n_minor * 2.0)
    return round(clamp(raw, 0.0, 100.0), 1)


def compute_h(c_norm: float, a_norm: float, i_norm: float) -> float:
    """Calculates composite Hotspot Risk Score H in [0, 100]."""
    raw = (0.40 * c_norm) + (0.35 * a_norm) + (0.25 * i_norm)
    return round(clamp(raw, 0.0, 100.0), 1)


# Public aliases
calculate_complexity_risk = compute_c_norm
calculate_architectural_centrality = compute_a_norm
calculate_issue_severity_burden = compute_i_norm
calculate_composite_hotspot_score = compute_h


@dataclass
class HotspotRecord:
    rank: int
    file_path: str
    hotspot_score: float
    complexity_risk: float
    architectural_centrality: float
    issue_severity_burden: float
    sloc: int
    max_cyclomatic_complexity: int
    max_nesting_depth: int
    fan_in: int
    fan_out: int
    issues_count: int
    blocker_count: int
    critical_count: int
    major_count: int
    minor_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rank": self.rank,
            "file_path": self.file_path,
            "hotspot_score": self.hotspot_score,
            "complexity_risk": self.complexity_risk,
            "architectural_centrality": self.architectural_centrality,
            "issue_severity_burden": self.issue_severity_burden,
            "sloc": self.sloc,
            "max_cyclomatic_complexity": self.max_cyclomatic_complexity,
            "max_nesting_depth": self.max_nesting_depth,
            "fan_in": self.fan_in,
            "fan_out": self.fan_out,
            "issues_count": self.issues_count,
            "blocker_count": self.blocker_count,
            "critical_count": self.critical_count,
            "major_count": self.major_count,
            "minor_count": self.minor_count,
            "h_score": self.hotspot_score,
            "complexity_norm": self.complexity_risk,
            "architecture_norm": self.architectural_centrality,
            "hygiene_norm": self.issue_severity_burden,
            "risk_x": self.complexity_risk,
            "risk_y": self.architectural_centrality,
        }


class HotspotAnalyzer:
    """Deterministic static hotspot analyzer prioritizing high-risk codebase modules."""

    @staticmethod
    def analyze_from_dicts(
        candidates_data: List[Dict[str, Any]],
        max_results: int = 10,
    ) -> List[HotspotRecord]:
        """Calculates and ranks hotspots from raw dictionary candidate metrics."""
        candidates = []
        for item in candidates_data:
            file_path = item.get("path") or item.get("file_path") or "unknown"
            sloc = item.get("sloc", 0)
            max_cc = item.get("max_cc") or item.get("max_cyclomatic_complexity") or 0
            max_nesting = item.get("max_nesting") or item.get("max_nesting_depth") or 0
            fan_in = item.get("fan_in", 0)
            fan_out = item.get("fan_out", 0)

            raw_issues = item.get("issues", {})
            if isinstance(raw_issues, dict):
                n_blocker = raw_issues.get("blocker", 0)
                n_critical = raw_issues.get("critical", 0)
                n_major = raw_issues.get("major", 0)
                n_minor = raw_issues.get("minor", 0)
                issues_count = sum(raw_issues.values())
            elif isinstance(raw_issues, list):
                n_blocker = sum(1 for i in raw_issues if (i.get("severity") if isinstance(i, dict) else getattr(i, "severity", None)) == "blocker")
                n_critical = sum(1 for i in raw_issues if (i.get("severity") if isinstance(i, dict) else getattr(i, "severity", None)) == "critical")
                n_major = sum(1 for i in raw_issues if (i.get("severity") if isinstance(i, dict) else getattr(i, "severity", None)) == "major")
                n_minor = sum(1 for i in raw_issues if (i.get("severity") if isinstance(i, dict) else getattr(i, "severity", None)) == "minor")
                issues_count = len(raw_issues)
            else:
                n_blocker = item.get("blocker_count", 0)
                n_critical = item.get("critical_count", 0)
                n_major = item.get("major_count", 0)
                n_minor = item.get("minor_count", 0)
                issues_count = item.get("issues_count", 0)

            c_norm = compute_c_norm(sloc, max_cc, max_nesting)
            a_norm = compute_a_norm(fan_in, fan_out)
            i_norm = compute_i_norm(n_blocker, n_critical, n_major, n_minor)
            h = compute_h(c_norm, a_norm, i_norm)

            candidates.append({
                "file_path": file_path,
                "h": h,
                "c_norm": c_norm,
                "a_norm": a_norm,
                "i_norm": i_norm,
                "sloc": sloc,
                "max_cc": max_cc,
                "max_nesting": max_nesting,
                "fan_in": fan_in,
                "fan_out": fan_out,
                "issues_count": issues_count,
                "n_blocker": n_blocker,
                "n_critical": n_critical,
                "n_major": n_major,
                "n_minor": n_minor,
            })

        # Deterministic ranking:
        candidates.sort(
            key=lambda c: (
                -c["h"],
                -c["a_norm"],
                -c["c_norm"],
                -c["i_norm"],
                c["file_path"],
            )
        )

        results: List[HotspotRecord] = []
        for idx, item in enumerate(candidates[:max_results], start=1):
            results.append(
                HotspotRecord(
                    rank=idx,
                    file_path=item["file_path"],
                    hotspot_score=item["h"],
                    complexity_risk=item["c_norm"],
                    architectural_centrality=item["a_norm"],
                    issue_severity_burden=item["i_norm"],
                    sloc=item["sloc"],
                    max_cyclomatic_complexity=item["max_cc"],
                    max_nesting_depth=item["max_nesting"],
                    fan_in=item["fan_in"],
                    fan_out=item["fan_out"],
                    issues_count=item["issues_count"],
                    blocker_count=item["n_blocker"],
                    critical_count=item["n_critical"],
                    major_count=item["n_major"],
                    minor_count=item["n_minor"],
                )
            )
        return results

    # Alias for analyze
    analyze = analyze_from_dicts

    @staticmethod
    def analyze_from_in_memory(
        file_metrics_map: Dict[str, FileMetrics],
        graph: Optional[DirectedDependencyGraph],
        issues: List[CodebaseIssue],
        file_id_map: Optional[Dict[str, uuid.UUID]] = None,
        max_results: int = 10,
    ) -> List[HotspotRecord]:
        """Calculates hotspots from in-memory pipeline objects."""
        if not file_metrics_map:
            return []

        # Index issues by file path
        issues_by_file: Dict[str, List[CodebaseIssue]] = {}
        for iss in issues:
            if iss.file_path:
                issues_by_file.setdefault(iss.file_path, []).append(iss)

        # Graph node lookup (file_path -> node_id)
        path_to_node: Dict[str, uuid.UUID] = {}
        if graph and graph.nodes:
            for nid, node in graph.nodes.items():
                path_to_node[node.file_path] = nid

        candidates = []
        for file_path, fm in file_metrics_map.items():
            sloc = fm.sloc
            max_cc = fm.max_cyclomatic_complexity
            max_nesting = max((sm.nesting_depth for sm in fm.symbols_metrics), default=0)

            # Coupling from graph
            fan_in = 0
            fan_out = 0
            if graph and file_path in path_to_node:
                nid = path_to_node[file_path]
                fan_in = graph.in_degrees.get(nid, 0)
                fan_out = graph.out_degrees.get(nid, 0)

            # Issue severity breakdown
            file_issues = issues_by_file.get(file_path, [])
            n_blocker = sum(1 for i in file_issues if i.severity == IssueSeverity.BLOCKER.value)
            n_critical = sum(1 for i in file_issues if i.severity == IssueSeverity.CRITICAL.value)
            n_major = sum(1 for i in file_issues if i.severity == IssueSeverity.MAJOR.value)
            n_minor = sum(1 for i in file_issues if i.severity == IssueSeverity.MINOR.value)

            c_norm = compute_c_norm(sloc, max_cc, max_nesting)
            a_norm = compute_a_norm(fan_in, fan_out)
            i_norm = compute_i_norm(n_blocker, n_critical, n_major, n_minor)
            h = compute_h(c_norm, a_norm, i_norm)

            candidates.append({
                "file_path": file_path,
                "h": h,
                "c_norm": c_norm,
                "a_norm": a_norm,
                "i_norm": i_norm,
                "sloc": sloc,
                "max_cc": max_cc,
                "max_nesting": max_nesting,
                "fan_in": fan_in,
                "fan_out": fan_out,
                "issues_count": len(file_issues),
                "n_blocker": n_blocker,
                "n_critical": n_critical,
                "n_major": n_major,
                "n_minor": n_minor,
            })

        # Deterministic Ranking:
        # 1. H descending
        # 2. Anorm descending
        # 3. Cnorm descending
        # 4. Inorm descending
        # 5. file_path ascending
        candidates.sort(
            key=lambda c: (
                -c["h"],
                -c["a_norm"],
                -c["c_norm"],
                -c["i_norm"],
                c["file_path"],
            )
        )

        results: List[HotspotRecord] = []
        for idx, item in enumerate(candidates[:max_results], start=1):
            results.append(
                HotspotRecord(
                    rank=idx,
                    file_path=item["file_path"],
                    hotspot_score=item["h"],
                    complexity_risk=item["c_norm"],
                    architectural_centrality=item["a_norm"],
                    issue_severity_burden=item["i_norm"],
                    sloc=item["sloc"],
                    max_cyclomatic_complexity=item["max_cc"],
                    max_nesting_depth=item["max_nesting"],
                    fan_in=item["fan_in"],
                    fan_out=item["fan_out"],
                    issues_count=item["issues_count"],
                    blocker_count=item["n_blocker"],
                    critical_count=item["n_critical"],
                    major_count=item["n_major"],
                    minor_count=item["n_minor"],
                )
            )
        return results

    @staticmethod
    def analyze_from_db_records(
        file_metrics_rows: List[Any],
        dep_metrics_rows: List[Any],
        issues_rows: List[Any],
        files_rows: Optional[List[Any]] = None,
        max_results: int = 10,
    ) -> List[HotspotRecord]:
        """Calculates hotspots from SQLAlchemy DB query results."""
        if not file_metrics_rows:
            return []

        # Map file paths by file_id
        files_map: Dict[Any, str] = {}
        if files_rows:
            for f in files_rows:
                files_map[f.id] = f.path

        # Map dependencies by file_id
        deps_by_file: Dict[Any, Any] = {dm.file_id: dm for dm in dep_metrics_rows}

        # Map issues by file_id and file_path
        issues_by_file_id: Dict[Any, List[Any]] = {}
        issues_by_file_path: Dict[str, List[Any]] = {}
        for iss in issues_rows:
            fid = getattr(iss, "file_id", None) or (iss.get("file_id") if isinstance(iss, dict) else None)
            fpath = getattr(iss, "file_path", None) or (iss.get("file_path") if isinstance(iss, dict) else None)
            if not fpath and fid and files_map:
                fpath = files_map.get(fid)
            if fid:
                issues_by_file_id.setdefault(fid, []).append(iss)
            if fpath:
                issues_by_file_path.setdefault(fpath, []).append(iss)

        candidates = []
        for fm in file_metrics_rows:
            file_path = (
                getattr(fm, "file_path", None)
                or files_map.get(fm.file_id)
                or getattr(getattr(fm, "file", None), "path", None)
                or str(fm.file_id)
            )
            sloc = fm.sloc or 0
            max_cc = fm.max_cyclomatic_complexity or 0
            max_nesting = fm.max_nesting_depth or 0

            dm = deps_by_file.get(fm.file_id)
            fan_in = dm.fan_in if dm else 0
            fan_out = dm.fan_out if dm else 0

            file_issues = issues_by_file_id.get(fm.file_id) or issues_by_file_path.get(file_path, [])
            n_blocker = sum(1 for i in file_issues if getattr(i, "severity", None) == IssueSeverity.BLOCKER.value or (isinstance(i, dict) and i.get("severity") == IssueSeverity.BLOCKER.value))
            n_critical = sum(1 for i in file_issues if getattr(i, "severity", None) == IssueSeverity.CRITICAL.value or (isinstance(i, dict) and i.get("severity") == IssueSeverity.CRITICAL.value))
            n_major = sum(1 for i in file_issues if getattr(i, "severity", None) == IssueSeverity.MAJOR.value or (isinstance(i, dict) and i.get("severity") == IssueSeverity.MAJOR.value))
            n_minor = sum(1 for i in file_issues if getattr(i, "severity", None) == IssueSeverity.MINOR.value or (isinstance(i, dict) and i.get("severity") == IssueSeverity.MINOR.value))

            c_norm = compute_c_norm(sloc, max_cc, max_nesting)
            a_norm = compute_a_norm(fan_in, fan_out)
            i_norm = compute_i_norm(n_blocker, n_critical, n_major, n_minor)
            h = compute_h(c_norm, a_norm, i_norm)

            candidates.append({
                "file_path": file_path,
                "h": h,
                "c_norm": c_norm,
                "a_norm": a_norm,
                "i_norm": i_norm,
                "sloc": sloc,
                "max_cc": max_cc,
                "max_nesting": max_nesting,
                "fan_in": fan_in,
                "fan_out": fan_out,
                "issues_count": len(file_issues),
                "n_blocker": n_blocker,
                "n_critical": n_critical,
                "n_major": n_major,
                "n_minor": n_minor,
            })

        # Deterministic Ranking:
        # 1. H descending
        # 2. Anorm descending
        # 3. Cnorm descending
        # 4. Inorm descending
        # 5. file_path ascending
        candidates.sort(
            key=lambda c: (
                -c["h"],
                -c["a_norm"],
                -c["c_norm"],
                -c["i_norm"],
                c["file_path"],
            )
        )

        results: List[HotspotRecord] = []
        for idx, item in enumerate(candidates[:max_results], start=1):
            results.append(
                HotspotRecord(
                    rank=idx,
                    file_path=item["file_path"],
                    hotspot_score=item["h"],
                    complexity_risk=item["c_norm"],
                    architectural_centrality=item["a_norm"],
                    issue_severity_burden=item["i_norm"],
                    sloc=item["sloc"],
                    max_cyclomatic_complexity=item["max_cc"],
                    max_nesting_depth=item["max_nesting"],
                    fan_in=item["fan_in"],
                    fan_out=item["fan_out"],
                    issues_count=item["issues_count"],
                    blocker_count=item["n_blocker"],
                    critical_count=item["n_critical"],
                    major_count=item["n_major"],
                    minor_count=item["n_minor"],
                )
            )
        return results
