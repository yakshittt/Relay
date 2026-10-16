"""SSRF Protection and target validation for diagnostic probes.
Prevents probes from targeting arbitrary internal services or non-allowlisted targets.
"""
import ipaddress
import re
from urllib.parse import urlparse
from app.config import settings


class SSRFValidationError(ValueError):
    """Raised when a probe target fails security validation."""
    pass


def is_ip_address(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


def validate_probe_host(host: str) -> str:
    """Validate a hostname or IP for probe execution against the allowlist."""
    clean_host = host.strip().lower()
    
    # Strip port if present
    if ":" in clean_host and not clean_host.startswith("["):
        clean_host = clean_host.split(":")[0]
    
    # Basic sanity regex for hostname
    if not re.match(r"^[a-zA-Z0-9.-]+$", clean_host):
        raise SSRFValidationError(f"Invalid characters in target hostname: {clean_host}")
    
    # Check allowlist
    allowlist = [h.lower() for h in settings.allowlisted_hosts]
    
    # Direct match in allowlist
    if clean_host in allowlist:
        return clean_host
        
    # Check if ends with allowlisted domain (e.g. sub.example.com in example.com)
    for allowed in allowlist:
        if clean_host.endswith("." + allowed):
            return clean_host
            
    # Allow the configured probe_host or business_host
    if clean_host == settings.probe_host.lower() or clean_host == settings.business_host.lower():
        return clean_host
        
    # Allow gateway_ip if configured
    if clean_host == settings.gateway_ip.lower():
        return clean_host

    raise SSRFValidationError(
        f"Host '{clean_host}' is not in the diagnostic target allowlist. Probes are restricted."
    )


def validate_probe_url(url: str) -> str:
    """Validate a full URL for HTTP probes."""
    clean_url = url.strip()
    try:
        parsed = urlparse(clean_url)
    except Exception as exc:
        raise SSRFValidationError(f"Malformed URL: {exc}")
        
    if parsed.scheme not in {"http", "https"}:
        raise SSRFValidationError(f"Invalid URL scheme '{parsed.scheme}'; only http and https are allowed")
        
    if not parsed.hostname:
        raise SSRFValidationError("URL lacks a valid hostname")
        
    validate_probe_host(parsed.hostname)
    return clean_url
