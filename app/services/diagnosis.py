"""Deterministic rule-based diagnosis engine for RELAY.
Implements transparent diagnostic decision trees (Cases A through F) with confidence scoring.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from app.config import settings
from app.schemas import (
    DiagnosisReport,
    HealthStatus,
    ProbeResult,
    ProbeStatus,
    ProbableCause,
    DeviceHeartbeatView,
)
from app.services.demo import demo_fault_manager


def classify_incident(
    checks: List[ProbeResult],
    devices: List[DeviceHeartbeatView],
    user_report: str = "",
) -> Dict[str, Any]:
    """Analyze probe results and device telemetry through deterministic decision trees."""
    by_name: Dict[str, ProbeResult] = {p.name: p for p in checks}
    gateway = by_name.get("gateway_reachability")
    dns = by_name.get("dns_resolution") or by_name.get("dns")
    egress = by_name.get("https_egress")
    business = by_name.get("business_service")

    observations: List[str] = []
    probable_causes: List[ProbableCause] = []
    unresolved_questions: List[str] = []
    overall_status = HealthStatus.HEALTHY
    summary = ""
    diagnosis = ""
    recommended_next_step = ""

    # Check for active hardware monitoring devices
    any_device_stale = any(d.status == "STALE" for d in devices) if devices else False
    all_devices_stale = all(d.status == "STALE" for d in devices) if devices else False
    has_devices = len(devices) > 0

    # 1. DEMO FAULT INJECTION CHECK
    is_demo_fault = any(p.is_simulated for p in checks) or (
        business and business.evidence.get("injected_demo_fault")
    )
    if is_demo_fault:
        overall_status = HealthStatus.DEGRADED
        fault_name = (
            business.evidence.get("fault_type")
            if business and business.evidence.get("injected_demo_fault")
            else "simulated_probe_fault"
        )
        summary = f"Simulated fault active: {fault_name}"
        diagnosis = "A controlled simulation is actively injecting a service degradation into the diagnostic probes."
        observations.append("Simulated demo fault is active; actual Jio router settings remain untouched.")
        probable_causes.append(
            ProbableCause(
                cause=f"Injected demo fault: {fault_name}",
                confidence="HIGH",
                evidence_summary="Probe tagged as is_simulated=True in demo environment",
            )
        )
        recommended_next_step = (
            "Propose the allowlisted demo recovery action, review the impact, and authorize clearance."
        )
        unresolved_questions.append("Is this test being run as part of operator training or system verification?")
        return {
            "status": overall_status,
            "summary": summary,
            "diagnosis": diagnosis,
            "observations": observations,
            "probable_causes": probable_causes,
            "unresolved_questions": unresolved_questions,
            "recommended_next_step": recommended_next_step,
        }

    # 2. CASE B: GATEWAY UNREACHABLE
    if gateway and not gateway.ok:
        overall_status = HealthStatus.FAILED
        summary = "Local gateway is unreachable over the LAN"
        diagnosis = (
            "The diagnostic host cannot communicate with the local router gateway. "
            "This suggests a local Wi-Fi disconnection, Ethernet cabling issue, or router power loss."
        )
        observations.append(f"Gateway probe failed targeting {gateway.target}: {gateway.detail}")
        probable_causes.append(
            ProbableCause(
                cause="Local LAN disconnection or router power/hardware failure",
                confidence="HIGH",
                evidence_summary=f"TCP connection to gateway {gateway.target} failed",
            )
        )
        unresolved_questions.append("Are physical LEDs on the Jio router illuminated green or blinking red?")
        unresolved_questions.append("Is the laptop connected to the correct Wi-Fi SSID?")
        recommended_next_step = (
            "Verify the device's local Wi-Fi or Ethernet connection to the Jio router before testing the internet."
        )
        return {
            "status": overall_status,
            "summary": summary,
            "diagnosis": diagnosis,
            "observations": observations,
            "probable_causes": probable_causes,
            "unresolved_questions": unresolved_questions,
            "recommended_next_step": recommended_next_step,
        }

    # 3. CASE A: GATEWAY REACHABLE, DNS FAILS, BUSINESS ENDPOINT UNREACHABLE
    if dns and not dns.ok and business and not business.ok:
        overall_status = HealthStatus.DEGRADED
        summary = "DNS resolution failure with reachable local gateway"
        diagnosis = (
            "Local gateway responds, but domain name resolution is failing. "
            "The configured DNS resolver or upstream WAN link is failing to resolve names."
        )
        observations.append(f"Gateway ({gateway.target if gateway else 'LAN'}) responded successfully.")
        observations.append(f"DNS query for '{dns.target}' failed: {dns.detail}")
        observations.append(f"Business service '{business.target}' unreachable due to name resolution failure.")
        probable_causes.append(
            ProbableCause(
                cause="DNS server outage or upstream WAN DNS misconfiguration",
                confidence="HIGH",
                evidence_summary="DNS resolution failed while gateway is reachable",
            )
        )
        unresolved_questions.append("Is the router obtaining valid DNS servers via DHCP/PPPoE from the ISP?")
        unresolved_questions.append("Can public IP addresses (e.g. 8.8.8.8) be reached directly?")
        recommended_next_step = (
            "Test fallback DNS resolution using a known public resolver (e.g. 1.1.1.1, 8.8.8.8) and check WAN uplink."
        )
        return {
            "status": overall_status,
            "summary": summary,
            "diagnosis": diagnosis,
            "observations": observations,
            "probable_causes": probable_causes,
            "unresolved_questions": unresolved_questions,
            "recommended_next_step": recommended_next_step,
        }

    # 4. BROADER WAN / EGRESS FAILURE (DNS and HTTPS both fail)
    if dns and not dns.ok and egress and not egress.ok:
        overall_status = HealthStatus.FAILED
        summary = "Broad internet egress failure"
        diagnosis = (
            "Both DNS resolution and external HTTPS reachability failed. "
            "The site has lost external internet connectivity."
        )
        observations.append("External HTTPS reachability failed.")
        observations.append("DNS resolution failed.")
        probable_causes.append(
            ProbableCause(
                cause="ISP WAN link outage or optical fiber signal loss",
                confidence="HIGH",
                evidence_summary="All external WAN probes failed while LAN is active",
            )
        )
        unresolved_questions.append("Is the optical fiber LED on the Jio router solid green?")
        recommended_next_step = "Check the physical fiber connection and contact ISP support if optical link is down."
        return {
            "status": overall_status,
            "summary": summary,
            "diagnosis": diagnosis,
            "observations": observations,
            "probable_causes": probable_causes,
            "unresolved_questions": unresolved_questions,
            "recommended_next_step": recommended_next_step,
        }

    # 5. CASE C: GENERAL EGRESS SUCCEEDS, BUT SPECIFIC BUSINESS ENDPOINT FAILS
    if egress and egress.ok and business and not business.ok:
        overall_status = HealthStatus.DEGRADED
        summary = "Isolated business service failure (general internet operational)"
        diagnosis = (
            "General internet connectivity and DNS resolution are healthy, "
            "but the specific business application endpoint is not responding."
        )
        observations.append(f"General internet HTTPS probe succeeded ({egress.target}).")
        observations.append(f"Business endpoint probe failed ({business.target}): {business.detail}")
        probable_causes.append(
            ProbableCause(
                cause="Upstream application outage, cloud downtime, or vendor service disruption",
                confidence="HIGH",
                evidence_summary="Egress is healthy; only business application endpoint failed",
            )
        )
        unresolved_questions.append("Is there an announced maintenance window or outage on the business vendor's status page?")
        unresolved_questions.append("Are other workstations at the site experiencing the exact same error?")
        recommended_next_step = (
            "Check the vendor status page and inspect application server logs before assuming a local network failure."
        )
        return {
            "status": overall_status,
            "summary": summary,
            "diagnosis": diagnosis,
            "observations": observations,
            "probable_causes": probable_causes,
            "unresolved_questions": unresolved_questions,
            "recommended_next_step": recommended_next_step,
        }

    # 6. CASE D: NETWORK PROBES HEALTHY, BUT ESP32 HEARTBEAT IS STALE
    if (
        (not egress or egress.ok)
        and (not dns or dns.ok)
        and (not business or business.ok)
        and has_devices
        and any_device_stale
    ):
        overall_status = HealthStatus.DEGRADED
        stale_devices = [d.device_id for d in devices if d.status == "STALE"]
        summary = f"Monitoring sensor offline: {', '.join(stale_devices)}"
        diagnosis = (
            "The site network probes are all healthy, but the dedicated ESP32 hardware monitor "
            "has stopped sending heartbeats. Do not conclude that the entire site is down."
        )
        observations.append("All network probes (Gateway, DNS, Egress, Business App) passed.")
        observations.append(f"Device(s) {', '.join(stale_devices)} are past the stale heartbeat threshold.")
        probable_causes.append(
            ProbableCause(
                cause="ESP32 hardware unplugged, unpowered, or out of Wi-Fi range",
                confidence="HIGH",
                evidence_summary="Heartbeat age exceeds threshold while network probes succeed",
            )
        )
        unresolved_questions.append("Is the ESP32 board plugged into USB power?")
        unresolved_questions.append("Is the ESP32 power LED lit up?")
        recommended_next_step = (
            "Check physical power and placement of the ESP32 hardware probe. Site network is operational."
        )
        return {
            "status": overall_status,
            "summary": summary,
            "diagnosis": diagnosis,
            "observations": observations,
            "probable_causes": probable_causes,
            "unresolved_questions": unresolved_questions,
            "recommended_next_step": recommended_next_step,
        }

    # 7. CASE E: ALL PROBES PASS DESPITE USER REPORT
    all_probes_pass = all(p.ok for p in checks)
    if all_probes_pass:
        overall_status = HealthStatus.HEALTHY
        summary = "All automated diagnostic checks passed"
        diagnosis = (
            "The tested gateway, DNS, external HTTPS, and business endpoints are operating normally. "
            "The reported issue was not reproduced by automated probes."
        )
        observations.append("Gateway reachability confirmed.")
        observations.append("DNS resolution confirmed.")
        observations.append("External HTTPS egress confirmed.")
        observations.append("Business endpoint reached successfully.")
        if has_devices and not any_device_stale:
            observations.append("ESP32 hardware monitor is reporting fresh heartbeats.")

        probable_causes.append(
            ProbableCause(
                cause="Transient glitch, client-side caching, local workstation issue, or authentication session expiry",
                confidence="LOW",
                evidence_summary="Automated probe matrix detected zero anomalies across all tiers",
            )
        )
        unresolved_questions.append("What specific error message or HTTP code appears on the user's screen?")
        unresolved_questions.append("Does refreshing the browser or testing in Incognito mode resolve the issue?")
        recommended_next_step = (
            "Ask the user for the specific URL or error message and test the client browser cache."
        )
        return {
            "status": overall_status,
            "summary": summary,
            "diagnosis": diagnosis,
            "observations": observations,
            "probable_causes": probable_causes,
            "unresolved_questions": unresolved_questions,
            "recommended_next_step": recommended_next_step,
        }

    # Fallback degraded classification
    overall_status = HealthStatus.DEGRADED
    summary = "Degraded connectivity detected"
    diagnosis = "One or more secondary diagnostic checks reported degraded performance or timeouts."
    observations.extend([f"Check '{c.name}' status: {c.detail}" for c in checks if not c.ok])
    probable_causes.append(
        ProbableCause(
            cause="Unclassified intermittent network degradation",
            confidence="LOW",
            evidence_summary="Mixed probe outcomes observed",
        )
    )
    recommended_next_step = "Rerun diagnostics and isolate whether the failure persists on subsequent runs."

    return {
        "status": overall_status,
        "summary": summary,
        "diagnosis": diagnosis,
        "observations": observations,
        "probable_causes": probable_causes,
        "unresolved_questions": unresolved_questions,
        "recommended_next_step": recommended_next_step,
    }
