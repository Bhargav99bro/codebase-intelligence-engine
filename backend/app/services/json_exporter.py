from datetime import datetime
from typing import Any, Dict, List, Optional


class JsonExporter:
    """Serializes complete repository intelligence into a consolidated JSON payload."""

    SCHEMA_VERSION = "1.0"

    @classmethod
    def generate_payload(
        cls,
        analysis_id: str,
        repository_url: str,
        commit_hash: Optional[str],
        analysis_date: Optional[datetime],
        health_summary: Optional[Dict[str, Any]],
        quality_gate: Optional[Dict[str, Any]],
        hotspots: List[Any],
        recommendations: List[Any],
        issues_summary: Optional[Dict[str, Any]],
        dependency_summary: Optional[Dict[str, Any]],
        files_data: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Constructs the consolidated JSON intelligence export payload."""
        date_str = analysis_date.strftime("%Y-%m-%dT%H:%M:%SZ") if analysis_date else datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

        # Normalize hotspots to dicts
        normalized_hotspots = []
        for h in hotspots:
            if hasattr(h, "to_dict"):
                normalized_hotspots.append(h.to_dict())
            elif isinstance(h, dict):
                normalized_hotspots.append(h)

        # Normalize recommendations to dicts
        normalized_recs = []
        for r in recommendations:
            if hasattr(r, "to_dict"):
                normalized_recs.append(r.to_dict())
            elif isinstance(r, dict):
                normalized_recs.append(r)

        return {
            "schema_version": cls.SCHEMA_VERSION,
            "analysis_id": str(analysis_id),
            "repository": {
                "url": repository_url,
                "commit_hash": commit_hash,
                "analyzed_at": date_str,
            },
            "health": health_summary or {},
            "quality_gate": quality_gate or {},
            "hotspots": normalized_hotspots,
            "recommendations": normalized_recs,
            "issue_summary": issues_summary or {},
            "issues_summary": issues_summary or {},
            "dependency_summary": dependency_summary or {},
            "file_intelligence": files_data or [],
            "metadata": {
                "engine_version": "1.0.0",
                "exported_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "export_format": "consolidated_intelligence_v1",
            },
        }
