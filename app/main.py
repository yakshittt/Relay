"""RELAY local-first prototype API + Bolna custom-function endpoints."""
import secrets
from datetime import datetime, timezone
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from .config import settings
from .diagnostics import run_diagnostics, set_demo_dns_fault, demo_dns_fault_active
from .schemas import DiagnoseRequest, RecoveryRequest, HeartbeatRequest
from . import storage

app = FastAPI(title="RELAY API", version="0.1.0", description="Voice-native incident diagnosis prototype")
bearer = HTTPBearer(auto_error=False)


@app.on_event("startup")
def startup() -> None:
    storage.init_db()


def require_bearer(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> None:
    if credentials is None or not secrets.compare_digest(credentials.credentials, settings.api_token):
        raise HTTPException(status_code=401, detail="Missing or invalid bearer token")


def require_device_token(x_device_token: str | None = Header(default=None)) -> None:
    if x_device_token is None or not secrets.compare_digest(x_device_token, settings.device_token):
        raise HTTPException(status_code=401, detail="Missing or invalid device token")


@app.get("/health")
def health() -> dict:
    return {"ok": True, "service": "relay-api", "time": datetime.now(timezone.utc).isoformat()}


@app.post("/v1/tools/diagnose", dependencies=[Depends(require_bearer)])
def diagnose(request: DiagnoseRequest) -> dict:
    """Run real probes from the machine hosting this API and save an incident."""
    report = run_diagnostics(request.site_id, storage.get_heartbeats(request.site_id))
    incident = storage.create_incident(request.site_id, request.user_report, report)
    return {"incident_id": incident["id"], **report}


@app.get("/v1/tools/incidents/{incident_id}", dependencies=[Depends(require_bearer)])
def get_incident(incident_id: int) -> dict:
    incident = storage.get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


@app.get("/v1/sites/{site_id}/status", dependencies=[Depends(require_bearer)])
def site_status(site_id: str) -> dict:
    latest = storage.latest_incident(site_id)
    return {"site_id": site_id, "latest_incident": latest,
            "devices": run_diagnostics(site_id, storage.get_heartbeats(site_id))["devices"],
            "demo_dns_fault_active": demo_dns_fault_active()}


@app.post("/v1/devices/heartbeat", dependencies=[Depends(require_device_token)])
def device_heartbeat(request: HeartbeatRequest) -> dict:
    return {"ok": True, "device": storage.save_heartbeat(request.device_id, request.site_id,
                                                            request.wifi_rssi_dbm, request.uptime_seconds)}


@app.post("/v1/demo/faults/dns", dependencies=[Depends(require_bearer)])
def inject_demo_fault() -> dict:
    if not settings.demo_mode:
        raise HTTPException(status_code=403, detail="Demo mode is disabled")
    set_demo_dns_fault(True)
    return {"ok": True, "demo_dns_fault_active": True,
            "note": "This toggles an in-app test fault. It does not change the Jio router or OS DNS."}


@app.post("/v1/demo/faults/clear", dependencies=[Depends(require_bearer)])
def clear_demo_fault() -> dict:
    if not settings.demo_mode:
        raise HTTPException(status_code=403, detail="Demo mode is disabled")
    set_demo_dns_fault(False)
    return {"ok": True, "demo_dns_fault_active": False}


@app.post("/v1/tools/recover", dependencies=[Depends(require_bearer)])
def recover(request: RecoveryRequest) -> dict:
    """Only a safe, in-app demo operation is implemented. Never touches router config."""
    incident = storage.get_incident(request.incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    if request.action != "clear_demo_dns_fault":
        raise HTTPException(status_code=400, detail="Action is not allowlisted")
    if not settings.demo_mode:
        raise HTTPException(status_code=403, detail="Demo recovery is disabled")
    if not request.user_confirmed:
        raise HTTPException(status_code=409, detail="Explicit user confirmation is required")
    if not demo_dns_fault_active():
        return {"ok": True, "message": "No demo DNS fault is active; no action was needed."}
    set_demo_dns_fault(False)
    after = run_diagnostics(incident["site_id"], storage.get_heartbeats(incident["site_id"]))
    verification_passed = all(check["ok"] for check in after["checks"])
    return {"ok": verification_passed, "action": request.action,
            "message": "Demo fault cleared; diagnostics rerun.", "verification": after,
            "verification_passed": verification_passed,
            "warning": "This is a simulated recovery and does not modify router or operating-system settings."}
