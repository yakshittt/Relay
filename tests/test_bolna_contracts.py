"""Tests for Bolna voice agent tool contracts and voice simulation."""
import pytest
from app.services.bolna import (
    get_bolna_tool_schemas,
    format_voice_diagnosis,
    format_voice_recovery,
)


def test_bolna_tool_schemas_contract():
    """Verify generated schemas conform to Bolna custom function requirements."""
    tools = get_bolna_tool_schemas("https://relay.example.com", "test-token-123")
    assert len(tools) == 4
    tool_names = [t["name"] for t in tools]
    assert "diagnose_network" in tool_names
    assert "get_incident_status" in tool_names
    assert "propose_recovery" in tool_names
    assert "execute_approved_recovery" in tool_names

    for t in tools:
        assert t["key"] == "custom_task"
        assert "parameters" in t
        assert "value" in t
        assert "url" in t["value"]
        assert "method" in t["value"]
        assert "Bearer test-token-123" in t["value"]["api_token"]


def test_format_voice_diagnosis_facts_vs_hypothesis():
    """Voice output must distinguish observed probe facts from diagnostic hypotheses."""
    report = {
        "status": "degraded",
        "summary": "DNS resolver outage",
        "diagnosis": "Gateway responds, but DNS name resolution is failing.",
        "recommended_next_step": "Authorize DNS cache flush or failover.",
        "checks": [
            {"name": "gateway_reachability", "ok": True, "detail": "LAN ping ok"},
            {"name": "dns_resolution", "ok": False, "detail": "gaierror"},
        ],
        "devices": [{"device_id": "esp32-01", "status": "ONLINE", "wifi_rssi_dbm": -55, "uptime_seconds": 120}],
    }

    voice_out = format_voice_diagnosis(report, incident_id=42)
    assert "spoken_response" in voice_out
    assert "facts" in voice_out
    assert "hypothesis" in voice_out
    assert len(voice_out["facts"]) == 2
    assert "Gateway responds, but DNS" in voice_out["hypothesis"]
    assert "incident 42" in voice_out["spoken_response"]


def test_format_voice_recovery_speech():
    """Voice recovery formatter must clearly explain verified vs failed outcomes."""
    # Succeeded case
    success_res = {
        "action_id": "act_test1",
        "verification_passed": True,
        "verification_details": {"summary": "All 4 checks passed"},
    }
    voice_succ = format_voice_recovery(success_res)
    assert "verified as resolved" in voice_succ["spoken_response"]
    assert voice_succ["verified"] is True

    # Failed case
    fail_res = {
        "action_id": "act_test2",
        "verification_passed": False,
        "verification_details": {"summary": "Gateway remains unreachable"},
    }
    voice_fail = format_voice_recovery(fail_res)
    assert "post-action verification failed" in voice_fail["spoken_response"]
    assert "cannot claim the incident is resolved" in voice_fail["spoken_response"]
    assert voice_fail["verified"] is False
