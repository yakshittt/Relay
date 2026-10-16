"""Incident management service.
Handles incident creation, lifecycle state changes, timeline generation, and audit trails.
"""
from typing import Any, Dict, List, Optional
from app import storage
from app.schemas import DiagnosisReport, IncidentDetailResponse


def create_incident_from_diagnosis(
    site_id: str,
    user_report: str,
    report: DiagnosisReport,
) -> Dict[str, Any]:
    """Persist a new incident from a diagnosis execution."""
    raw_dict = report.model_dump()
    incident = storage.create_incident(site_id, user_report, raw_dict)
    
    storage.record_audit(
        action="INCIDENT_OPENED",
        actor="system:diagnostic_engine",
        details={
            "incident_id": incident["id"],
            "site_id": site_id,
            "status": incident["status"],
            "user_report": user_report,
        },
    )
    return incident


def get_incident_details(incident_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve full incident record including timeline and recovery action history."""
    return storage.get_incident(incident_id)


def list_site_incidents(
    site_id: Optional[str] = None, status: Optional[str] = None, limit: int = 50
) -> List[Dict[str, Any]]:
    """List incidents with filtering."""
    return storage.list_incidents(site_id=site_id, status=status, limit=limit)
