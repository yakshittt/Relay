"""Pydantic schemas and typed data contracts for RELAY."""
from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    UNKNOWN = "unknown"


class ProbeStatus(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"


class ActionStatus(str, Enum):
    PROPOSED = "PROPOSED"
    APPROVED = "APPROVED"
    EXECUTING = "EXECUTING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    REJECTED = "REJECTED"


class ProbeResult(BaseModel):
    name: str = Field(description="Probe identifier (e.g. dns, https_egress, gateway_ping)")
    target: str = Field(description="Target hostname, IP, or URL")
    status: ProbeStatus = Field(default=ProbeStatus.UNKNOWN)
    ok: bool = Field(description="Backward-compatible boolean result")
    latency_ms: float = Field(ge=0.0, description="Observed round-trip time in milliseconds")
    detail: str = Field(description="Human-readable probe observation")
    evidence: Dict[str, Any] = Field(default_factory=dict, description="Raw structured evidence payload")
    error_category: Optional[str] = Field(default=None, description="Categorized failure mode if failed")
    timestamp: str = Field(description="ISO-8601 UTC timestamp")
    is_simulated: bool = Field(default=False, description="Flag indicating simulated or fault-injected measurement")


class ProbableCause(BaseModel):
    cause: str
    confidence: Literal["HIGH", "MEDIUM", "LOW"]
    evidence_summary: str


class DiagnoseRequest(BaseModel):
    site_id: str = Field(default="jio-lab", min_length=1, max_length=80)
    user_report: str = Field(default="Run a routine connectivity check", max_length=1000)
    target_service: Optional[str] = Field(default=None, max_length=120)


class DeviceHeartbeatView(BaseModel):
    device_id: str
    site_id: str
    received_at: str
    wifi_rssi_dbm: Optional[int] = None
    uptime_seconds: Optional[int] = None
    firmware_version: Optional[str] = None
    free_heap: Optional[int] = None
    cycle_count: Optional[int] = None
    age_seconds: Optional[int] = None
    online: bool = False
    status: Literal["ONLINE", "STALE", "UNKNOWN"] = "UNKNOWN"


class DiagnosisReport(BaseModel):
    site_id: str
    observed_at: str
    status: HealthStatus
    summary: str
    diagnosis: str
    observations: List[str]
    checks: List[ProbeResult]
    probable_causes: List[ProbableCause]
    unresolved_questions: List[str]
    recommended_next_step: str
    devices: List[DeviceHeartbeatView]
    demo_dns_fault_active: bool = False
    demo_mode_active: bool = False


class DiagnoseResponse(DiagnosisReport):
    incident_id: int


class HeartbeatRequest(BaseModel):
    device_id: str = Field(min_length=1, max_length=80)
    site_id: str = Field(default="jio-lab", min_length=1, max_length=80)
    wifi_rssi_dbm: Optional[int] = Field(default=None, ge=-127, le=0)
    uptime_seconds: Optional[int] = Field(default=None, ge=0)
    firmware_version: Optional[str] = Field(default="1.1.0", max_length=30)
    free_heap: Optional[int] = Field(default=None, ge=0)
    cycle_count: Optional[int] = Field(default=None, ge=0)


class RecoveryProposalRequest(BaseModel):
    incident_id: int
    action_type: str = Field(description="Allowlisted action type, e.g. clear_demo_dns_fault")
    parameters: Dict[str, Any] = Field(default_factory=dict)


class RecoveryProposalResponse(BaseModel):
    action_id: str
    incident_id: int
    action_type: str
    parameters: Dict[str, Any]
    impact_description: str
    required_approval_level: str
    approval_token: str
    token_expires_at: str
    status: ActionStatus


class RecoveryExecuteRequest(BaseModel):
    action_id: str
    approval_token: str
    idempotency_key: Optional[str] = None


class RecoveryExecuteResponse(BaseModel):
    ok: bool
    action_id: str
    status: ActionStatus
    message: str
    verification_passed: bool
    verification_details: Dict[str, Any]
    executed_at: str
    warning: str


# Legacy Recovery Request for starter compatibility
class RecoveryRequest(BaseModel):
    incident_id: int
    action: Literal["clear_demo_dns_fault"]
    user_confirmed: bool = False


class DemoFaultToggleRequest(BaseModel):
    fault_type: Literal["dns_outage", "business_http_503", "stale_heartbeat", "gateway_loss"]
    enabled: bool = True


class IncidentTimelineItem(BaseModel):
    id: int
    incident_id: int
    event_type: str
    description: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: str


class IncidentDetailResponse(BaseModel):
    id: int
    site_id: str
    created_at: str
    updated_at: str
    status: str
    user_report: str
    summary: str
    diagnosis: str
    report: Dict[str, Any]
    timeline: List[IncidentTimelineItem]
    recovery_actions: List[Dict[str, Any]]
