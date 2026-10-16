"""Device and IoT probe telemetry service.
Manages ESP32 hardware monitors, online/stale status calculation, and heartbeat records.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from app.config import settings
from app.schemas import DeviceHeartbeatView, HeartbeatRequest
from app.services.demo import demo_fault_manager
from app import storage


def record_heartbeat(request: HeartbeatRequest) -> Dict[str, Any]:
    """Store device heartbeat and return updated state."""
    saved = storage.save_heartbeat(
        device_id=request.device_id,
        site_id=request.site_id,
        rssi=request.wifi_rssi_dbm,
        uptime=request.uptime_seconds,
        firmware_version=request.firmware_version,
        free_heap=request.free_heap,
        cycle_count=request.cycle_count,
    )
    storage.record_audit(
        action="DEVICE_HEARTBEAT_RECEIVED",
        actor=f"device:{request.device_id}",
        details={"site_id": request.site_id, "rssi": request.wifi_rssi_dbm, "uptime": request.uptime_seconds},
    )
    return saved


def get_site_devices(site_id: str) -> List[DeviceHeartbeatView]:
    """Retrieve all devices for a given site with calculated age and stale status."""
    raw_devices = storage.get_heartbeats(site_id)
    now = datetime.now(timezone.utc)
    views: List[DeviceHeartbeatView] = []

    force_stale = demo_fault_manager.is_active("stale_heartbeat")

    for d in raw_devices:
        try:
            seen = datetime.fromisoformat(d["received_at"])
            age = max(0, int((now - seen).total_seconds()))
            
            # If demo fault 'stale_heartbeat' is active, simulate aged-out device
            if force_stale:
                age = settings.esp32_stale_seconds + 120
                online = False
                status_str = "STALE"
            else:
                online = age <= settings.esp32_stale_seconds
                status_str = "ONLINE" if online else "STALE"
        except (KeyError, TypeError, ValueError):
            age = None
            online = False
            status_str = "UNKNOWN"

        views.append(
            DeviceHeartbeatView(
                device_id=d["device_id"],
                site_id=d["site_id"],
                received_at=d["received_at"],
                wifi_rssi_dbm=d.get("wifi_rssi_dbm"),
                uptime_seconds=d.get("uptime_seconds"),
                firmware_version=d.get("firmware_version"),
                free_heap=d.get("free_heap"),
                cycle_count=d.get("cycle_count"),
                age_seconds=age,
                online=online,
                status=status_str,
            )
        )

    return views
