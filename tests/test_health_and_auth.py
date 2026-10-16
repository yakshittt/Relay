"""Tests for health endpoint and authentication boundaries."""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings
from app import storage

client = TestClient(app)


@pytest.fixture(autouse=True)
def ensure_db():
    storage.init_db()



def test_health_endpoint_unauthenticated():
    """Health endpoint must respond without authentication and avoid leaking secrets."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["service"] == "relay-api"
    assert "version" in data
    assert "timestamp" in data
    # Verify no secrets leaked
    assert settings.api_token not in str(data)
    assert settings.device_token not in str(data)


def test_bearer_auth_missing_fails():
    """Private endpoints must reject requests with missing credentials."""
    response = client.post("/v1/tools/diagnose", json={"site_id": "jio-lab", "user_report": "test"})
    assert response.status_code == 401
    assert "Missing Bearer" in response.json()["detail"]


def test_bearer_auth_invalid_fails():
    """Private endpoints must reject requests with wrong bearer credentials."""
    response = client.post(
        "/v1/tools/diagnose",
        headers={"Authorization": "Bearer totally-invalid-token-1234"},
        json={"site_id": "jio-lab", "user_report": "test"},
    )
    assert response.status_code == 401
    assert "Invalid Bearer token" in response.json()["detail"]


def test_bearer_auth_valid_succeeds():
    """Private endpoints must succeed with valid bearer credentials."""
    response = client.get(
        "/v1/overview/stats",
        headers={"Authorization": f"Bearer {settings.api_token}"},
    )
    assert response.status_code == 200
    assert "total_sites" in response.json()


def test_device_auth_missing_header_fails():
    """Heartbeat endpoint must require X-Device-Token."""
    response = client.post(
        "/v1/devices/heartbeat",
        json={"device_id": "esp32-01", "site_id": "jio-lab"},
    )
    assert response.status_code == 401
    assert "Missing X-Device-Token" in response.json()["detail"]


def test_device_auth_invalid_token_fails():
    """Heartbeat endpoint must reject invalid X-Device-Token."""
    response = client.post(
        "/v1/devices/heartbeat",
        headers={"X-Device-Token": "wrong-token"},
        json={"device_id": "esp32-01", "site_id": "jio-lab"},
    )
    assert response.status_code == 401
    assert "Invalid device credentials" in response.json()["detail"]


def test_device_auth_valid_token_succeeds():
    """Heartbeat endpoint must accept valid X-Device-Token."""
    response = client.post(
        "/v1/devices/heartbeat",
        headers={"X-Device-Token": settings.device_token},
        json={
            "device_id": "esp32-test-01",
            "site_id": "jio-lab",
            "wifi_rssi_dbm": -55,
            "uptime_seconds": 360,
        },
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert response.json()["device"]["device_id"] == "esp32-test-01"
