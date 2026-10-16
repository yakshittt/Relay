"""Configuration system for RELAY.
Loads environment variables safely with typed defaults.
"""
from dataclasses import dataclass, field
import os
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv

# Load .env file if available
load_dotenv()


def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _list(name: str, default: List[str]) -> List[str]:
    value = os.getenv(name)
    if value is None:
        return default
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    # Security Credentials
    api_token: str = os.getenv("RELAY_API_TOKEN", "relay-dev-token-secret-2026")
    device_token: str = os.getenv("DEVICE_TOKEN", "relay-esp32-token-secret-2026")
    approval_token_ttl_seconds: int = int(os.getenv("APPROVAL_TOKEN_TTL_SECONDS", "300"))
    
    # Operational flags
    demo_mode: bool = _bool("DEMO_MODE", True)
    data_path: str = os.getenv("DATA_PATH", "./relay.sqlite3")
    
    # Network Diagnostics Targets
    probe_host: str = os.getenv("RELAY_PROBE_HOST", "example.com")
    business_host: str = os.getenv("BUSINESS_HOST", "example.com")
    business_url: str = os.getenv("BUSINESS_URL", "https://example.com/")
    gateway_ip: str = os.getenv("GATEWAY_IP", "192.168.29.1")  # Standard Jio Fiber gateway IP
    
    # Device monitoring
    esp32_stale_seconds: int = int(os.getenv("ESP32_STALE_SECONDS", "45"))
    
    # SSRF Allowlist for probes (hostnames and IPs permitted to be targeted by probes)
    allowlisted_hosts: List[str] = field(
        default_factory=lambda: _list(
            "ALLOWLISTED_HOSTS",
            ["example.com", "google.com", "8.8.8.8", "1.1.1.1", "192.168.29.1", "192.168.1.1", "127.0.0.1", "localhost"]
        )
    )
    
    # CORS Configuration
    cors_origins: List[str] = field(
        default_factory=lambda: _list(
            "CORS_ORIGINS",
            ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000", "http://127.0.0.1:3000", "*"]
        )
    )
    
    # Optional Bolna integration
    bolna_api_key: Optional[str] = os.getenv("BOLNA_API_KEY")
    bolna_agent_id: Optional[str] = os.getenv("BOLNA_AGENT_ID")
    bolna_api_url: str = os.getenv("BOLNA_API_URL", "https://api.bolna.dev")


settings = Settings()
