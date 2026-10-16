"""Deterministic Rule-Based Diagnosis Engine Tests.
Explicitly validates Cases A through F.
"""
import pytest
from app.schemas import ProbeResult, ProbeStatus, DeviceHeartbeatView, HealthStatus
from app.services.diagnosis import classify_incident


def make_probe(name: str, target: str, ok: bool, detail: str = "", evidence: dict = None, is_simulated: bool = False):
    return ProbeResult(
        name=name,
        target=target,
        status=ProbeStatus.HEALTHY if ok else ProbeStatus.FAILED,
        ok=ok,
        latency_ms=15.0 if ok else 0.0,
        detail=detail or (f"{name} ok" if ok else f"{name} failed"),
        evidence=evidence or {},
        timestamp="2026-10-16T12:00:00Z",
        is_simulated=is_simulated,
    )


def test_case_a_gateway_reachable_dns_fails_business_fails():
    """CASE A: Gateway reachable, DNS resolution fails, business endpoint unreachable -> probable DNS issue."""
    checks = [
        make_probe("gateway_reachability", "192.168.29.1", ok=True, detail="Gateway ping ok"),
        make_probe("dns_resolution", "example.com", ok=False, detail="Name resolution failed: gaierror"),
        make_probe("https_egress", "https://example.com/", ok=True, detail="HTTPS ok"),
        make_probe("business_service", "https://example.com/", ok=False, detail="DNS failed"),
    ]
    devices = [DeviceHeartbeatView(device_id="esp32-01", site_id="jio-lab", received_at="2026-10-16T12:00:00Z", status="ONLINE", online=True)]
    
    result = classify_incident(checks, devices, "Billing app is not loading")

    assert result["status"] == HealthStatus.DEGRADED
    assert "DNS" in result["summary"]
    assert any("DNS server outage" in c.cause for c in result["probable_causes"])
    assert result["probable_causes"][0].confidence == "HIGH"


def test_case_b_gateway_unreachable():
    """CASE B: Gateway unreachable -> local connectivity issue; avoid asserting ISP fault."""
    checks = [
        make_probe("gateway_reachability", "192.168.29.1", ok=False, detail="Gateway unresponsive"),
        make_probe("dns_resolution", "example.com", ok=False, detail="Name resolution failed"),
        make_probe("https_egress", "https://example.com/", ok=False, detail="HTTPS failed"),
        make_probe("business_service", "https://example.com/", ok=False, detail="Connection refused"),
    ]
    devices = []
    
    result = classify_incident(checks, devices, "Internet is completely down")

    assert result["status"] == HealthStatus.FAILED
    assert "gateway" in result["summary"].lower()
    assert any("LAN disconnection" in c.cause for c in result["probable_causes"])
    assert "Jio router" in result["recommended_next_step"]


def test_case_c_general_egress_succeeds_business_endpoint_fails():
    """CASE C: DNS & egress succeed, but one business endpoint fails -> isolated application/upstream problem."""
    checks = [
        make_probe("gateway_reachability", "192.168.29.1", ok=True),
        make_probe("dns_resolution", "example.com", ok=True),
        make_probe("https_egress", "https://example.com/", ok=True),
        make_probe("business_service", "https://pos-app.internal/", ok=False, detail="HTTP 503 Service Unavailable"),
    ]
    devices = []

    result = classify_incident(checks, devices, "Billing application is crashing")

    assert result["status"] == HealthStatus.DEGRADED
    assert "Isolated business service failure" in result["summary"]
    assert any("Upstream application outage" in c.cause for c in result["probable_causes"])


def test_case_d_network_probes_healthy_esp32_stale():
    """CASE D: Network probes healthy, but ESP32 heartbeat is stale -> monitoring sensor offline, not whole network."""
    checks = [
        make_probe("gateway_reachability", "192.168.29.1", ok=True),
        make_probe("dns_resolution", "example.com", ok=True),
        make_probe("https_egress", "https://example.com/", ok=True),
        make_probe("business_service", "https://example.com/", ok=True),
    ]
    # Stale device
    devices = [DeviceHeartbeatView(device_id="esp32-01", site_id="jio-lab", received_at="2026-10-16T10:00:00Z", status="STALE", online=False, age_seconds=7200)]

    result = classify_incident(checks, devices, "Routine status check")

    assert result["status"] == HealthStatus.DEGRADED
    assert "Monitoring sensor offline" in result["summary"]
    assert any("ESP32 hardware unplugged" in c.cause for c in result["probable_causes"])
    assert "Site network is operational" in result["recommended_next_step"]


def test_case_e_all_probes_pass_despite_user_report():
    """CASE E: All available probes pass despite user report -> incident not reproduced; follow-up questions."""
    checks = [
        make_probe("gateway_reachability", "192.168.29.1", ok=True),
        make_probe("dns_resolution", "example.com", ok=True),
        make_probe("https_egress", "https://example.com/", ok=True),
        make_probe("business_service", "https://example.com/", ok=True),
    ]
    devices = [DeviceHeartbeatView(device_id="esp32-01", site_id="jio-lab", received_at="2026-10-16T12:00:00Z", status="ONLINE", online=True, age_seconds=5)]

    result = classify_incident(checks, devices, "I cannot submit orders")

    assert result["status"] == HealthStatus.HEALTHY
    assert "All automated diagnostic checks passed" in result["summary"]
    assert "not reproduced" in result["diagnosis"]
    assert len(result["unresolved_questions"]) > 0
    assert any("specific error message" in q for q in result["unresolved_questions"])


def test_injected_demo_fault_classification():
    """Demo fault injection must be clearly marked as simulated in diagnosis."""
    checks = [
        make_probe("gateway_reachability", "192.168.29.1", ok=True),
        make_probe("dns_resolution", "example.com", ok=True),
        make_probe("https_egress", "https://example.com/", ok=True),
        make_probe(
            "business_service",
            "https://example.com/",
            ok=False,
            detail="Injected demo fault",
            evidence={"injected_demo_fault": True, "fault_type": "dns_outage"},
            is_simulated=True,
        ),
    ]
    result = classify_incident(checks, [], "App is failing")

    assert result["status"] == HealthStatus.DEGRADED
    assert "Simulated fault active" in result["summary"]
    assert any("Injected demo fault" in c.cause for c in result["probable_causes"])
