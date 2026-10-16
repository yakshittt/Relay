"""Tests for SSRF prevention and diagnostic probe engine."""
import pytest
from app.schemas import ProbeResult, ProbeStatus
from app.security.ssrf import validate_probe_host, validate_probe_url, SSRFValidationError
from app.services.probes import ProbeEngine


def test_ssrf_allows_allowlisted_host():
    """Allowlisted hosts must pass validation."""
    assert validate_probe_host("example.com") == "example.com"
    assert validate_probe_host("8.8.8.8") == "8.8.8.8"
    assert validate_probe_host("192.168.29.1") == "192.168.29.1"


def test_ssrf_blocks_unauthorized_external_host():
    """Non-allowlisted hosts must be blocked."""
    with pytest.raises(SSRFValidationError) as exc:
        validate_probe_host("malicious-internal-network.attacker.com")
    assert "not in the diagnostic target allowlist" in str(exc.value)


def test_ssrf_blocks_invalid_characters():
    """Hostnames with command injection or invalid characters must be blocked."""
    with pytest.raises(SSRFValidationError):
        validate_probe_host("example.com; rm -rf /")
    with pytest.raises(SSRFValidationError):
        validate_probe_host("example.com`curl attacker`")


def test_ssrf_blocks_invalid_scheme():
    """Only HTTP and HTTPS schemes must be permitted."""
    with pytest.raises(SSRFValidationError) as exc:
        validate_probe_url("ftp://example.com/file")
    assert "Invalid URL scheme" in str(exc.value)

    with pytest.raises(SSRFValidationError):
        validate_probe_url("file:///etc/passwd")


def test_probe_engine_dependency_injection():
    """Probe engine must support dependency injection for deterministic offline tests."""
    mock_dns = lambda host: ProbeResult(
        name="dns_resolution",
        target=host,
        status=ProbeStatus.HEALTHY,
        ok=True,
        latency_ms=12.4,
        detail=f"Resolved {host} to 93.184.216.34",
        evidence={"ips": ["93.184.216.34"]},
        timestamp="2026-10-16T12:00:00Z",
    )
    mock_https = lambda url: ProbeResult(
        name="https_egress",
        target=url,
        status=ProbeStatus.HEALTHY,
        ok=True,
        latency_ms=45.2,
        detail="HTTP status 200",
        evidence={"status_code": 200},
        timestamp="2026-10-16T12:00:00Z",
    )
    mock_gw = lambda ip: ProbeResult(
        name="gateway_reachability",
        target=ip,
        status=ProbeStatus.HEALTHY,
        ok=True,
        latency_ms=2.1,
        detail=f"Gateway {ip} is reachable",
        evidence={"gateway": ip},
        timestamp="2026-10-16T12:00:00Z",
    )

    engine = ProbeEngine(dns_fn=mock_dns, https_fn=mock_https, gateway_fn=mock_gw)
    probes = engine.execute_all_probes()

    assert len(probes) == 4
    assert all(p.ok for p in probes)
    assert probes[0].name == "gateway_reachability"
    assert probes[1].name == "dns_resolution"
    assert probes[2].name == "https_egress"
    assert probes[3].name == "business_service"
