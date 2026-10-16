"""RELAY Incident Resolution Backend API.
Provides typed, authenticated endpoints for operators, probes, ESP32 devices,
recovery policy executors, and Bolna Voice AI custom functions.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.config import settings
from app.schemas import (
    DiagnoseRequest,
    DiagnoseResponse,
    DiagnosisReport,
    HeartbeatRequest,
    IncidentDetailResponse,
    RecoveryExecuteRequest,
    RecoveryExecuteResponse,
    RecoveryProposalRequest,
    RecoveryProposalResponse,
    RecoveryRequest,
    DemoFaultToggleRequest,
)
from app.security import require_bearer, require_device_token
from app.services.probes import default_probe_engine
from app.services.devices import get_site_devices, record_heartbeat
from app.services.diagnosis import classify_incident
from app.services.incidents import (
    create_incident_from_diagnosis,
    get_incident_details,
    list_site_incidents,
)
from app.services.demo import demo_fault_manager
from app.services.recovery_policy import propose_recovery_action, RecoveryPolicyError
from app.services.recovery_executor import execute_action, ExecutionError
from app.services.bolna import (
    get_bolna_tool_schemas,
    format_voice_diagnosis,
    format_voice_recovery,
)
from app import storage

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(application: FastAPI):
    storage.init_db()
    yield

# Initialize database tables
storage.init_db()

# Initialize FastAPI application
app = FastAPI(
    title="RELAY Incident Resolution Engine",
    version="1.2.0",
    description="Voice-native incident resolution platform for physical business locations.",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Configure CORS for frontend web application
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins if "*" not in settings.cors_origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



# -----------------------------------------------------------------------------
# Health & Overview
# -----------------------------------------------------------------------------
@app.get("/health", tags=["System"])
def health() -> Dict[str, Any]:
    """Unauthenticated health check for monitoring probes and load balancers."""
    return {
        "ok": True,
        "service": "relay-api",
        "version": "1.2.0",
        "demo_mode": settings.demo_mode,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/v1/overview/stats", dependencies=[Depends(require_bearer)], tags=["Operations"])
def overview_stats() -> Dict[str, Any]:
    """Retrieve aggregate operational statistics for the console dashboard."""
    return storage.get_overview_stats()


# -----------------------------------------------------------------------------
# Diagnostic Probes & Incidents
# -----------------------------------------------------------------------------
@app.post("/v1/tools/diagnose", dependencies=[Depends(require_bearer)], response_model=DiagnoseResponse, tags=["Diagnostics"])
def diagnose(request: DiagnoseRequest) -> DiagnoseResponse:
    """Run real diagnostic probes from the API host, evaluate evidence, and persist an incident."""
    # 1. Execute probes
    checks = default_probe_engine.execute_all_probes()

    # 2. Collect hardware sentinel telemetry
    devices = get_site_devices(request.site_id)

    # 3. Deterministic rule-based classification
    classification = classify_incident(checks, devices, request.user_report)

    # 4. Construct diagnosis report
    report = DiagnosisReport(
        site_id=request.site_id,
        observed_at=datetime.now(timezone.utc).isoformat(),
        status=classification["status"],
        summary=classification["summary"],
        diagnosis=classification["diagnosis"],
        observations=classification["observations"],
        checks=checks,
        probable_causes=classification["probable_causes"],
        unresolved_questions=classification["unresolved_questions"],
        recommended_next_step=classification["recommended_next_step"],
        devices=devices,
        demo_dns_fault_active=demo_fault_manager.is_active("dns_outage"),
        demo_mode_active=settings.demo_mode,
    )

    # 5. Persist incident
    incident = create_incident_from_diagnosis(request.site_id, request.user_report, report)

    return DiagnoseResponse(incident_id=incident["id"], **report.model_dump())


@app.get("/v1/tools/incidents/{incident_id}", dependencies=[Depends(require_bearer)], response_model=IncidentDetailResponse, tags=["Incidents"])
def get_incident(incident_id: int) -> IncidentDetailResponse:
    """Retrieve full incident details, timeline events, and recovery action history."""
    incident = get_incident_details(incident_id)
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Incident #{incident_id} not found")
    return IncidentDetailResponse(**incident)


@app.get("/v1/tools/incidents", dependencies=[Depends(require_bearer)], tags=["Incidents"])
def list_incidents(
    site_id: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
) -> List[Dict[str, Any]]:
    """List incidents filtered by site and status."""
    return list_site_incidents(site_id=site_id, status=status, limit=limit)


# -----------------------------------------------------------------------------
# Site & Device Monitoring
# -----------------------------------------------------------------------------
@app.get("/v1/sites", dependencies=[Depends(require_bearer)], tags=["Sites"])
def list_sites() -> List[str]:
    """List all monitored site identifiers."""
    return storage.get_all_sites()


@app.get("/v1/sites/{site_id}/status", dependencies=[Depends(require_bearer)], tags=["Sites"])
def get_site_status(site_id: str) -> Dict[str, Any]:
    """Retrieve current site health, latest incident, and active hardware sentinels."""
    latest = storage.latest_incident(site_id)
    devices = get_site_devices(site_id)
    return {
        "site_id": site_id,
        "latest_incident": latest,
        "devices": [d.model_dump() for d in devices],
        "demo_faults": demo_fault_manager.get_all_faults(),
    }


@app.post("/v1/devices/heartbeat", dependencies=[Depends(require_device_token)], tags=["Devices"])
def device_heartbeat(request: HeartbeatRequest) -> Dict[str, Any]:
    """Ingest hardware sentinel heartbeat telemetry from ESP32."""
    saved = record_heartbeat(request)
    return {"ok": True, "device": saved}


@app.get("/v1/devices", dependencies=[Depends(require_bearer)], tags=["Devices"])
def list_devices() -> List[Dict[str, Any]]:
    """List all registered hardware sentinel devices."""
    devices = get_site_devices("")
    return [d.model_dump() for d in devices]


# -----------------------------------------------------------------------------
# Recovery Policy & Execution Framework
# -----------------------------------------------------------------------------
@app.post("/v1/tools/recovery/propose", dependencies=[Depends(require_bearer)], response_model=RecoveryProposalResponse, tags=["Recovery"])
def propose_recovery(request: RecoveryProposalRequest) -> RecoveryProposalResponse:
    """Propose an allowlisted recovery action and generate a single-use expiring approval token."""
    try:
        proposal = propose_recovery_action(
            incident_id=request.incident_id,
            action_type=request.action_type,
            parameters=request.parameters,
        )
        return RecoveryProposalResponse(**proposal)
    except RecoveryPolicyError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@app.post("/v1/tools/recovery/execute", dependencies=[Depends(require_bearer)], response_model=RecoveryExecuteResponse, tags=["Recovery"])
def execute_recovery(request: RecoveryExecuteRequest) -> RecoveryExecuteResponse:
    """Execute an authorized recovery action using the single-use approval token. Runs post-action verification."""
    try:
        result = execute_action(
            action_id=request.action_id,
            approval_token=request.approval_token,
            idempotency_key=request.idempotency_key,
        )
        return RecoveryExecuteResponse(**result)
    except ExecutionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


# Legacy recovery endpoint for backward compatibility with starter scripts
@app.post("/v1/tools/recover", dependencies=[Depends(require_bearer)], tags=["Recovery"])
def legacy_recover(request: RecoveryRequest) -> Dict[str, Any]:
    """Legacy recovery endpoint maintaining backward compatibility with starter runbook."""
    incident = storage.get_incident(request.incident_id)
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    if request.action != "clear_demo_dns_fault":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Action is not allowlisted")
    if not settings.demo_mode:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Demo recovery is disabled")
    if not request.user_confirmed:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Explicit user confirmation is required")

    proposal = propose_recovery_action(request.incident_id, "clear_demo_dns_fault", {})
    result = execute_action(proposal["action_id"], proposal["approval_token"])
    return {
        "ok": result["verification_passed"],
        "action": request.action,
        "message": result["message"],
        "verification": result["verification_details"],
        "verification_passed": result["verification_passed"],
        "warning": result["warning"],
    }


# -----------------------------------------------------------------------------
# Demo Fault Injection Controls (Guarded by DEMO_MODE)
# -----------------------------------------------------------------------------
@app.get("/v1/demo/status", dependencies=[Depends(require_bearer)], tags=["Demo Simulation"])
def demo_status() -> Dict[str, Any]:
    """Retrieve demo mode status and active simulated faults."""
    return {
        "demo_mode": settings.demo_mode,
        "active_faults": demo_fault_manager.get_all_faults(),
    }


@app.post("/v1/demo/faults/toggle", dependencies=[Depends(require_bearer)], tags=["Demo Simulation"])
def toggle_demo_fault(request: DemoFaultToggleRequest) -> Dict[str, Any]:
    """Toggle a specific demo fault scenario."""
    if not settings.demo_mode:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Demo mode is disabled on this server")
    try:
        demo_fault_manager.set_fault(request.fault_type, request.enabled)
        return {
            "ok": True,
            "fault_type": request.fault_type,
            "enabled": request.enabled,
            "active_faults": demo_fault_manager.get_all_faults(),
            "warning": "Simulated fault: no physical router or OS configuration was modified.",
        }
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


# Backward-compatible demo endpoints
@app.post("/v1/demo/faults/dns", dependencies=[Depends(require_bearer)], tags=["Demo Simulation"])
def inject_demo_dns_fault() -> Dict[str, Any]:
    if not settings.demo_mode:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Demo mode is disabled")
    demo_fault_manager.set_fault("dns_outage", True)
    return {
        "ok": True,
        "demo_dns_fault_active": True,
        "note": "Toggled simulated DNS outage. Does not modify router or OS DNS settings.",
    }


@app.post("/v1/demo/faults/clear", dependencies=[Depends(require_bearer)], tags=["Demo Simulation"])
def clear_all_demo_faults() -> Dict[str, Any]:
    if not settings.demo_mode:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Demo mode is disabled")
    demo_fault_manager.clear_all()
    return {"ok": True, "active_faults": demo_fault_manager.get_all_faults()}


# -----------------------------------------------------------------------------
# Bolna Voice Integration & Simulation
# -----------------------------------------------------------------------------
@app.get("/v1/bolna/schemas", dependencies=[Depends(require_bearer)], tags=["Bolna Voice"])
def bolna_schemas() -> Dict[str, Any]:
    """Retrieve pre-configured Bolna Custom Function schemas for agent setup."""
    return {"tools": get_bolna_tool_schemas()}


class VoiceSimulateRequest(BaseModel):
    user_message: str = Field(min_length=1, max_length=500)
    site_id: str = Field(default="jio-lab")
    incident_id: Optional[int] = None
    action_type: Optional[str] = None
    approval_token: Optional[str] = None


@app.post("/v1/bolna/voice-simulate", dependencies=[Depends(require_bearer)], tags=["Bolna Voice"])
def voice_simulate(request: VoiceSimulateRequest) -> Dict[str, Any]:
    """Local Voice Agent Simulator.
    Allows testing natural language conversational flows without live telephony or Bolna credentials.
    """
    msg = request.user_message.lower()

    # Intent 1: Execution approval
    if any(w in msg for w in ["yes", "approve", "confirm", "proceed", "fix it", "clear fault"]) and (
        request.action_type or request.incident_id
    ):
        # Find latest proposed action or propose one
        inc_id = request.incident_id
        if not inc_id:
            latest = storage.latest_incident(request.site_id)
            inc_id = latest["id"] if latest else 1

        action_type = request.action_type or "clear_demo_dns_fault"
        proposal = propose_recovery_action(inc_id, action_type, {})
        exec_res = execute_action(proposal["action_id"], proposal["approval_token"])
        voice_out = format_voice_recovery(exec_res)
        return {
            "intent": "EXECUTE_RECOVERY",
            "spoken_response": voice_out["spoken_response"],
            "tool_call": {
                "name": "execute_approved_recovery",
                "parameters": {"action_id": proposal["action_id"], "approval_token": proposal["approval_token"]},
                "result": exec_res,
            },
            "incident_id": inc_id,
        }

    # Intent 2: Diagnosis request
    checks = default_probe_engine.execute_all_probes()
    devices = get_site_devices(request.site_id)
    classification = classify_incident(checks, devices, request.user_message)
    report = DiagnosisReport(
        site_id=request.site_id,
        observed_at=datetime.now(timezone.utc).isoformat(),
        status=classification["status"],
        summary=classification["summary"],
        diagnosis=classification["diagnosis"],
        observations=classification["observations"],
        checks=checks,
        probable_causes=classification["probable_causes"],
        unresolved_questions=classification["unresolved_questions"],
        recommended_next_step=classification["recommended_next_step"],
        devices=devices,
        demo_dns_fault_active=demo_fault_manager.is_active("dns_outage"),
        demo_mode_active=settings.demo_mode,
    )
    incident = create_incident_from_diagnosis(request.site_id, request.user_message, report)
    voice_out = format_voice_diagnosis(report.model_dump(), incident["id"])

    return {
        "intent": "DIAGNOSE_NETWORK",
        "spoken_response": voice_out["spoken_response"],
        "tool_call": {
            "name": "diagnose_network",
            "parameters": {"site_id": request.site_id, "user_report": request.user_message},
            "result": report.model_dump(),
        },
        "incident_id": incident["id"],
        "voice_details": voice_out,
    }
