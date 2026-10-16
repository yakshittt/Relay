"""Tests for incident persistence, timeline events, and device sentinels."""
from datetime import datetime, timezone, timedelta
import pytest
from app import storage
from app.schemas import HeartbeatRequest, DiagnosisReport, HealthStatus
from app.services.devices import record_heartbeat, get_site_devices
from app.services.incidents import create_incident_from_diagnosis, get_incident_details
from app.config import settings


@pytest.fixture(autouse=True)
def init_database():
    storage.init_db()


def test_heartbeat_ingestion_and_stale_detection():
    """Device heartbeats must persist and calculate stale status properly."""
    req = HeartbeatRequest(
        device_id="esp32-unit-01",
        site_id="jio-lab",
        wifi_rssi_dbm=-52,
        uptime_seconds=750,
        firmware_version="1.2.0",
        free_heap=184000,
        cycle_count=50,
    )
    saved = record_heartbeat(req)
    assert saved["device_id"] == "esp32-unit-01"

    # Should be ONLINE immediately
    devices = get_site_devices("jio-lab")
    matching = [d for d in devices if d.device_id == "esp32-unit-01"]
    assert len(matching) == 1
    assert matching[0].status == "ONLINE"
    assert matching[0].online is True
    assert matching[0].wifi_rssi_dbm == -52

    # If timestamp is aged out past threshold, status becomes STALE
    old_time = (datetime.now(timezone.utc) - timedelta(seconds=settings.esp32_stale_seconds + 30)).isoformat()
    storage.save_heartbeat("esp32-unit-01", "jio-lab", -60, 1000)
    with storage._connect() as conn:
        conn.execute("UPDATE device_heartbeats SET received_at=? WHERE device_id=?", (old_time, "esp32-unit-01"))
        conn.commit()

    devices_aged = get_site_devices("jio-lab")
    matching_aged = [d for d in devices_aged if d.device_id == "esp32-unit-01"]
    assert matching_aged[0].status == "STALE"
    assert matching_aged[0].online is False


def test_incident_timeline_persistence():
    """Incidents must record structured timeline events across their lifecycle."""
    report = DiagnosisReport(
        site_id="jio-lab",
        observed_at=datetime.now(timezone.utc).isoformat(),
        status=HealthStatus.DEGRADED,
        summary="Payment app unreachable",
        diagnosis="Isolated endpoint outage",
        observations=["Observation 1"],
        checks=[],
        probable_causes=[],
        unresolved_questions=[],
        recommended_next_step="Inspect vendor status",
        devices=[],
    )
    created = create_incident_from_diagnosis("jio-lab", "Payment terminal reports offline", report)
    inc_id = created["id"]

    # Check incident detail
    detail = get_incident_details(inc_id)
    assert detail is not None
    assert detail["id"] == inc_id
    assert detail["user_report"] == "Payment terminal reports offline"
    assert len(detail["timeline"]) >= 1
    assert detail["timeline"][0]["event_type"] == "INCIDENT_CREATED"

    # Update status and verify timeline entry
    storage.update_incident_status(inc_id, "investigating", "Operator looking into logs")
    updated = get_incident_details(inc_id)
    assert updated["status"] == "investigating"
    assert len(updated["timeline"]) >= 2
    assert updated["timeline"][1]["event_type"] == "STATUS_UPDATED"
