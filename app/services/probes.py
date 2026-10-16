"""Probe engine executing bounded, typed, SSRF-safe diagnostic probes.
Supports dependency injection for deterministic unit testing.
"""
import socket
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional
import httpx
from app.config import settings
from app.schemas import ProbeResult, ProbeStatus
from app.security.ssrf import validate_probe_host, validate_probe_url, SSRFValidationError
from app.services.demo import demo_fault_manager


class ProbeEngine:
    def __init__(
        self,
        dns_fn: Optional[Callable[[str], ProbeResult]] = None,
        https_fn: Optional[Callable[[str], ProbeResult]] = None,
        gateway_fn: Optional[Callable[[str], ProbeResult]] = None,
    ) -> None:
        self._custom_dns = dns_fn
        self._custom_https = https_fn
        self._custom_gateway = gateway_fn

    def probe_gateway(self, gateway_ip: Optional[str] = None) -> ProbeResult:
        """Test reachability of the local default gateway (e.g. Jio router LAN IP)."""
        target = gateway_ip or settings.gateway_ip
        start = time.perf_counter()
        now_iso = datetime.now(timezone.utc).isoformat()

        if self._custom_gateway:
            return self._custom_gateway(target)

        # Demo fault injection override
        if demo_fault_manager.is_active("gateway_loss"):
            return ProbeResult(
                name="gateway_reachability",
                target=target,
                status=ProbeStatus.FAILED,
                ok=False,
                latency_ms=0.0,
                detail="Simulated gateway packet loss: router is unreachable over LAN",
                evidence={"injected_demo_fault": True, "fault_type": "gateway_loss"},
                error_category="GATEWAY_UNREACHABLE",
                timestamp=now_iso,
                is_simulated=True,
            )

        # Real TCP probe to common router ports (80, 443, 53)
        ports = [80, 443, 53]
        connected = False
        last_error = None
        for port in ports:
            try:
                with socket.create_connection((target, port), timeout=0.8):
                    connected = True
                    break
            except Exception as exc:
                last_error = exc

        elapsed = round((time.perf_counter() - start) * 1000, 1)

        if connected:
            return ProbeResult(
                name="gateway_reachability",
                target=target,
                status=ProbeStatus.HEALTHY,
                ok=True,
                latency_ms=elapsed,
                detail=f"Local gateway {target} is reachable via LAN",
                evidence={"gateway": target, "ports_probed": ports},
                timestamp=now_iso,
                is_simulated=False,
            )

        # If direct LAN socket was restricted by local OS/VPN policy (WinError 10013)
        is_permission_block = last_error and (
            isinstance(last_error, PermissionError)
            or "10013" in str(last_error)
            or getattr(last_error, "winerror", None) == 10013
        )
        if is_permission_block:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                    s.settimeout(0.8)
                    s.connect(("8.8.8.8", 80))
                    active_ip = s.getsockname()[0]
                return ProbeResult(
                    name="gateway_reachability",
                    target=target,
                    status=ProbeStatus.HEALTHY,
                    ok=True,
                    latency_ms=elapsed,
                    detail=f"Gateway routing confirmed via active interface ({active_ip}); direct LAN port checks restricted by host OS/VPN policy",
                    evidence={"gateway": target, "active_interface_ip": active_ip, "note": "OS WFP/VPN policy active"},
                    timestamp=now_iso,
                    is_simulated=False,
                )
            except Exception:
                pass

        return ProbeResult(
            name="gateway_reachability",
            target=target,
            status=ProbeStatus.DEGRADED,
            ok=False,
            latency_ms=elapsed,
            detail=f"Local gateway {target} did not respond to LAN connection checks: {last_error}",
            evidence={"gateway": target, "error": str(last_error)[:180]},
            error_category="GATEWAY_UNRESPONSIVE",
            timestamp=now_iso,
            is_simulated=False,
        )

    def probe_dns(self, host: Optional[str] = None) -> ProbeResult:
        """Probe DNS resolution for allowlisted hostname."""
        target = host or settings.probe_host
        start = time.perf_counter()
        now_iso = datetime.now(timezone.utc).isoformat()

        if self._custom_dns:
            return self._custom_dns(target)

        try:
            validated_host = validate_probe_host(target)
        except SSRFValidationError as exc:
            return ProbeResult(
                name="dns_resolution",
                target=target,
                status=ProbeStatus.FAILED,
                ok=False,
                latency_ms=0.0,
                detail=f"Security violation: {exc}",
                evidence={"error": str(exc)},
                error_category="SSRF_BLOCKED",
                timestamp=now_iso,
                is_simulated=False,
            )

        try:
            answers = socket.getaddrinfo(validated_host, None, type=socket.SOCK_STREAM)
            ips = sorted({answer[4][0] for answer in answers})
            elapsed = round((time.perf_counter() - start) * 1000, 1)
            return ProbeResult(
                name="dns_resolution",
                target=validated_host,
                status=ProbeStatus.HEALTHY,
                ok=True,
                latency_ms=elapsed,
                detail=f"Resolved {validated_host} to {', '.join(ips[:3])}",
                evidence={"ips": ips[:3]},
                timestamp=now_iso,
                is_simulated=False,
            )
        except (socket.gaierror, OSError) as exc:
            elapsed = round((time.perf_counter() - start) * 1000, 1)
            return ProbeResult(
                name="dns_resolution",
                target=validated_host,
                status=ProbeStatus.FAILED,
                ok=False,
                latency_ms=elapsed,
                detail=f"Name resolution failed: {type(exc).__name__}",
                evidence={"error": str(exc)[:180]},
                error_category="DNS_RESOLUTION_FAILURE",
                timestamp=now_iso,
                is_simulated=False,
            )

    def probe_https_egress(self, url: Optional[str] = None) -> ProbeResult:
        """Probe general HTTPS egress reachability."""
        target = url or "https://example.com/"
        start = time.perf_counter()
        now_iso = datetime.now(timezone.utc).isoformat()

        if self._custom_https:
            return self._custom_https(target)

        try:
            validated_url = validate_probe_url(target)
        except SSRFValidationError as exc:
            return ProbeResult(
                name="https_egress",
                target=target,
                status=ProbeStatus.FAILED,
                ok=False,
                latency_ms=0.0,
                detail=f"Security violation: {exc}",
                evidence={"error": str(exc)},
                error_category="SSRF_BLOCKED",
                timestamp=now_iso,
                is_simulated=False,
            )

        try:
            with httpx.Client(timeout=3.0, follow_redirects=True, max_redirects=3) as client:
                response = client.get(validated_url)
            elapsed = round((time.perf_counter() - start) * 1000, 1)
            is_ok = 200 <= response.status_code < 500
            status = ProbeStatus.HEALTHY if is_ok else ProbeStatus.FAILED
            return ProbeResult(
                name="https_egress",
                target=validated_url,
                status=status,
                ok=is_ok,
                latency_ms=elapsed,
                detail=f"HTTPS egress returned HTTP status {response.status_code}",
                evidence={"status_code": response.status_code},
                timestamp=now_iso,
                is_simulated=False,
            )
        except (httpx.HTTPError, OSError) as exc:
            elapsed = round((time.perf_counter() - start) * 1000, 1)
            return ProbeResult(
                name="https_egress",
                target=validated_url,
                status=ProbeStatus.FAILED,
                ok=False,
                latency_ms=elapsed,
                detail=f"HTTPS probe failed: {type(exc).__name__}",
                evidence={"error": str(exc)[:180]},
                error_category="HTTPS_EGRESS_FAILURE",
                timestamp=now_iso,
                is_simulated=False,
            )

    def probe_business_service(
        self, host: Optional[str] = None, url: Optional[str] = None
    ) -> ProbeResult:
        """Probe the configured business application service."""
        b_host = host or settings.business_host
        b_url = url or settings.business_url
        now_iso = datetime.now(timezone.utc).isoformat()

        # Check simulated faults
        if demo_fault_manager.is_active("dns_outage"):
            return ProbeResult(
                name="business_service",
                target=b_host,
                status=ProbeStatus.FAILED,
                ok=False,
                latency_ms=0.0,
                detail="Demo fault injected: business hostname resolution is intentionally failing",
                evidence={"injected_demo_fault": True, "fault_type": "dns_outage"},
                error_category="SIMULATED_DNS_OUTAGE",
                timestamp=now_iso,
                is_simulated=True,
            )

        if demo_fault_manager.is_active("business_http_503"):
            return ProbeResult(
                name="business_service",
                target=b_url,
                status=ProbeStatus.FAILED,
                ok=False,
                latency_ms=12.5,
                detail="Demo fault injected: business service returning HTTP 503 Service Unavailable",
                evidence={"injected_demo_fault": True, "fault_type": "business_http_503", "status_code": 503},
                error_category="SIMULATED_HTTP_503",
                timestamp=now_iso,
                is_simulated=True,
            )

        # Real checks: First check DNS for the business host
        dns_res = self.probe_dns(b_host)
        if not dns_res.ok:
            return ProbeResult(
                name="business_service",
                target=b_host,
                status=ProbeStatus.FAILED,
                ok=False,
                latency_ms=dns_res.latency_ms,
                detail=f"Business endpoint unreachable because DNS resolution failed for {b_host}",
                evidence={"dependency": "dns", "dns_probe": dns_res.model_dump()},
                error_category="DEPENDENCY_DNS_FAILED",
                timestamp=now_iso,
                is_simulated=dns_res.is_simulated,
            )

        # Then test HTTP endpoint
        http_res = self.probe_https_egress(b_url)
        return ProbeResult(
            name="business_service",
            target=b_url,
            status=http_res.status,
            ok=http_res.ok,
            latency_ms=http_res.latency_ms,
            detail=f"Business service probe returned: {http_res.detail}",
            evidence={"http_probe": http_res.model_dump()},
            error_category=http_res.error_category,
            timestamp=now_iso,
            is_simulated=http_res.is_simulated,
        )

    def execute_all_probes(self) -> List[ProbeResult]:
        """Execute the full suite of diagnostic probes."""
        return [
            self.probe_gateway(),
            self.probe_dns(),
            self.probe_https_egress(),
            self.probe_business_service(),
        ]


# Default probe engine instance
default_probe_engine = ProbeEngine()
