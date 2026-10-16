"""Small environment-based configuration for the RELAY prototype."""
from dataclasses import dataclass
import os
from dotenv import load_dotenv

load_dotenv()


def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    api_token: str = os.getenv("RELAY_API_TOKEN", "replace-me-with-a-long-random-secret")
    device_token: str = os.getenv("DEVICE_TOKEN", "replace-me-with-another-long-random-secret")
    demo_mode: bool = _bool("DEMO_MODE", True)
    data_path: str = os.getenv("DATA_PATH", "./relay.sqlite3")
    probe_host: str = os.getenv("RELAY_PROBE_HOST", "example.com")
    business_host: str = os.getenv("BUSINESS_HOST", "example.com")
    business_url: str = os.getenv("BUSINESS_URL", "https://example.com/")
    esp32_stale_seconds: int = int(os.getenv("ESP32_STALE_SECONDS", "45"))


settings = Settings()
