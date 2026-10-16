"""Deterministic network probes. Do not let an LLM invent or run probes."""
import socket
import time
from datetime import datetime, timezone
from typing import Any
import httpx
from .config import settings

# In-memory fault injection is deliberately limited to demo mode. It simulates a
# business endpoint failure without changing the Jio router or the host OS.
_demo_dns_fault_active = False


def set_demo_dns_fault(active: bool) -> None:
    global _demo_dns_fault_active
    if not settings.demo_mode:
        raise RuntimeError("Demo fault injection is disabled")
    _demo_dns_fault_active = active


def demo_dns_fault_active() -> bool:
    return _demo_dns_fault_active


def _dns_probe(host: str) -> dict[str, Any]:
    start = time.perf_counter()
    try:
        answers = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
        ips = sorted({answer[4][0] for answer in answers})
        return {"name": "dns", "target": host, "ok": True,
                "latency_ms": round((time.perf_counter() - start) * 1000, 1),
                "detail": f"Resolved {host} to {', '.join(ips[:3])}", "evidence": {"ips": ips[:3]}}
    except (socket.gaierror, OSError) as exc:
        return {"name": "dns", "target": host, "ok": False,
                "latency_ms": round((time.perf_counter() - start) * 1000, 1),
                "detail": f"Name resolution failed: {type(exc).__name__}", "evidence": {"error": str(exc)[:180]}}


def _http_probe(url: str) -> dict[str, Any]:
    start = time.perf_counter()
    try:
        with httpx.Client(timeout=3.0, follow_redirects=True) as client:
            response = client.get(url)
        elapsed = round((time.perf_counter() - start) * 1000, 1)
        ok = 200 <= response.status_code < 500
        return {"name": "https_egress", "target": url, "ok": ok, "latency_ms": elapsed,
                "detail": f"HTTP status {response.status_code}",
                "evidence": {"status_code": response.status_code}}
    except (httpx.HTTPError, OSError) as exc:
        return {"name": "https_egress", "target": url, "ok": False,
                "latency_ms": round((time.perf_counter() - start) * 1000, 1),
                "detail": f"HTTPS probe failed: {type(exc).__name__}", "evidence": {"error": str(exc)[:180]}}


def _business_service_probe() -> dict[str, Any]:
    if _demo_dns_fault_active:
        return {"name": "business_service", "target": settings.business_host, "ok": False,
                "latency_ms": 0, "detail": "Demo fault: business hostname resolution is intentionally failing",
                "evidence": {"injected_demo_fault": True}}
    dns = _dns_probe(settings.business_host)
    if not dns["ok"]:
        return {"name": "business_service", "target": settings.business_host, "ok": False,
                "latency_ms": dns["latency_ms"], "detail": "Business endpoint cannot be checked because DNS failed",
                "evidence": {"dependency": "dns"}}
    return _http_probe(settings.business_url) | {"name": "business_service", "target": settings.business_url}


def classify(checks: list[dict[str, Any]]) -> tuple[str, str, str]:
    by_name = {item["name"]: item for item in checks}
    business = by_name.get("business_service", {})
    dns = by_name.get("dns", {})
    egress = by_name.get("https_egress", {})
    if business.get("evidence", {}).get("injected_demo_fault"):
        return ("degraded", "Business hostname resolution is failing (demo fault injected)",
                "The general HTTPS probe is separate from the simulated business-endpoint failure. Clear the demo fault and rerun checks.")
    if not dns.get("ok") and not egress.get("ok"):
        return ("degraded", "DNS resolution and HTTPS egress both failed",
                "The evidence is consistent with a broader DNS or internet-connectivity issue. Check the router uplink and ISP before changing configuration.")
    if not dns.get("ok"):
        return ("degraded", "The DNS probe failed, but the overall connection needs further isolation",
                "Repeat the DNS check and compare against a second known-good resolver. Do not change router settings based on this result alone.")
    if not egress.get("ok"):
        return ("degraded", "DNS works, but the HTTPS egress probe failed",
                "Check for captive portal, firewall, TLS inspection, or upstream connectivity issues.")
    if not business.get("ok"):
        return ("degraded", "The business endpoint check failed while general connectivity probes passed",
                "Inspect the business endpoint, service status, access policy and target URL before blaming the router.")
    return ("healthy", "The tested DNS, HTTPS and business endpoint checks passed",
            "No fault was detected by this probe set. Ask the user which specific workflow still fails and add a targeted test.")


def run_diagnostics(site_id: str, heartbeats: list[dict[str, Any]]) -> dict[str, Any]:
    checks = [_dns_probe(settings.probe_host), _http_probe("https://example.com/"), _business_service_probe()]
    status, diagnosis, next_step = classify(checks)
    now = datetime.now(timezone.utc)
    heartbeat_views = []
    for item in heartbeats:
        try:
            seen = datetime.fromisoformat(item["received_at"])
            age = max(0, int((now - seen).total_seconds()))
            online = age <= settings.esp32_stale_seconds
        except (KeyError, TypeError, ValueError):
            age, online = None, False
        heartbeat_views.append({**item, "age_seconds": age, "online": online})
    return {"site_id": site_id, "observed_at": now.isoformat(), "status": status,
            "diagnosis": diagnosis, "recommended_next_step": next_step,
            "checks": checks, "devices": heartbeat_views,
            "demo_dns_fault_active": _demo_dns_fault_active}
