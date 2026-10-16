"""Bolna voice agent integration service.
Provides tool configuration schemas, voice-friendly response summarization,
and a deterministic local voice interaction simulator.
"""
from typing import Any, Dict, List, Optional
from app.config import settings
from app.schemas import DiagnosisReport


def get_bolna_tool_schemas(base_url: Optional[str] = None, token: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return official Bolna Custom Function schemas for all RELAY incident resolution tools."""
    url_base = base_url or "https://YOUR-PUBLIC-TUNNEL.ngrok-free.app"
    api_token = token or settings.api_token

    return [
        {
            "name": "diagnose_network",
            "description": (
                "Run real network diagnostic probes on a physical business site. "
                "Use when the caller reports connectivity issues, slow Wi-Fi, application errors, "
                "or asks what is wrong with the network. Returns measured facts and probable causes."
            ),
            "pre_call_message": "Checking connectivity, running probes, and inspecting hardware sentinel...",
            "parameters": {
                "type": "object",
                "properties": {
                    "site_id": {
                        "type": "string",
                        "description": "Identifier of the site (default: jio-lab)",
                        "default": "jio-lab",
                    },
                    "user_report": {
                        "type": "string",
                        "description": "Exact problem reported by the caller in natural language",
                    },
                },
                "required": ["site_id", "user_report"],
            },
            "key": "custom_task",
            "value": {
                "method": "POST",
                "url": f"{url_base}/v1/tools/diagnose",
                "param": {"site_id": "%(site_id)s", "user_report": "%(user_report)s"},
                "api_token": f"Bearer {api_token}",
                "headers": {"Content-Type": "application/json"},
            },
        },
        {
            "name": "get_incident_status",
            "description": "Retrieve current status, timeline, and probe evidence for an existing incident by ID.",
            "pre_call_message": "Looking up incident records...",
            "parameters": {
                "type": "object",
                "properties": {
                    "incident_id": {
                        "type": "integer",
                        "description": "The unique numerical incident ID",
                    }
                },
                "required": ["incident_id"],
            },
            "key": "custom_task",
            "value": {
                "method": "GET",
                "url": f"{url_base}/v1/tools/incidents/%(incident_id)s",
                "param": {},
                "api_token": f"Bearer {api_token}",
                "headers": {"Content-Type": "application/json"},
            },
        },
        {
            "name": "propose_recovery",
            "description": (
                "Propose an allowlisted recovery action for an active incident. "
                "Returns the impact description, approval token, and requirements. "
                "Always explain the impact to the user and ask for explicit confirmation."
            ),
            "pre_call_message": "Formulating recovery plan and requesting authorization token...",
            "parameters": {
                "type": "object",
                "properties": {
                    "incident_id": {
                        "type": "integer",
                        "description": "ID of the incident requiring recovery",
                    },
                    "action_type": {
                        "type": "string",
                        "description": "Allowlisted action type, e.g. clear_demo_dns_fault, flush_dns_cache_simulated",
                        "enum": ["clear_demo_dns_fault", "flush_dns_cache_simulated", "switch_failover_dns_simulated"],
                    },
                },
                "required": ["incident_id", "action_type"],
            },
            "key": "custom_task",
            "value": {
                "method": "POST",
                "url": f"{url_base}/v1/tools/recovery/propose",
                "param": {"incident_id": "%(incident_id)s", "action_type": "%(action_type)s"},
                "api_token": f"Bearer {api_token}",
                "headers": {"Content-Type": "application/json"},
            },
        },
        {
            "name": "execute_approved_recovery",
            "description": (
                "Execute an authorized recovery action using the single-use approval token. "
                "Triggers automatic post-action verification. Returns whether recovery actually passed."
            ),
            "pre_call_message": "Executing authorized recovery and running verification checks...",
            "parameters": {
                "type": "object",
                "properties": {
                    "action_id": {
                        "type": "string",
                        "description": "The action ID to execute",
                    },
                    "approval_token": {
                        "type": "string",
                        "description": "The single-use cryptographically verified approval token",
                    },
                },
                "required": ["action_id", "approval_token"],
            },
            "key": "custom_task",
            "value": {
                "method": "POST",
                "url": f"{url_base}/v1/tools/recovery/execute",
                "param": {"action_id": "%(action_id)s", "approval_token": "%(approval_token)s"},
                "api_token": f"Bearer {api_token}",
                "headers": {"Content-Type": "application/json"},
            },
        },
    ]


def format_voice_diagnosis(report: Dict[str, Any], incident_id: int) -> Dict[str, Any]:
    """Format diagnosis output into concise, voice-agent optimized speech phrases."""
    status = report.get("status")
    if hasattr(status, "value"):
        status = status.value
    summary = report.get("summary", "")
    diagnosis = report.get("diagnosis", "")
    next_step = report.get("recommended_next_step", "")

    checks = report.get("checks", [])
    passing_count = sum(1 for c in checks if c.get("ok"))
    total_count = len(checks)

    # Distinguish facts from hypotheses
    facts = []
    for c in checks:
        name = c.get("name")
        ok = c.get("ok")
        detail = c.get("detail")
        facts.append(f"{name}: {'Passed' if ok else 'Failed'} ({detail})")

    devices = report.get("devices", [])
    device_summary = "No hardware probes installed"
    if devices:
        dev = devices[0]
        device_summary = (
            f"ESP32 monitor {dev.get('device_id')} is {dev.get('status')} "
            f"(RSSI {dev.get('wifi_rssi_dbm', 'N/A')} dBm, uptime {dev.get('uptime_seconds', 'N/A')}s)"
        )

    speech = (
        f"I ran site diagnostics for incident {incident_id}. "
        f"Overall health is {status}. {diagnosis} "
        f"{device_summary}. {next_step}"
    )

    return {
        "spoken_response": speech,
        "incident_id": incident_id,
        "status": status,
        "summary": summary,
        "facts": facts,
        "hypothesis": diagnosis,
        "recommended_action": next_step,
        "checks_passing": f"{passing_count}/{total_count}",
        "devices": devices,
    }


def format_voice_recovery(result: Dict[str, Any]) -> Dict[str, Any]:
    """Format recovery outcome for voice readout."""
    verified = result.get("verification_passed", False)
    action_id = result.get("action_id", "")
    message = result.get("message", "")
    verification = result.get("verification_details", {})
    summary = verification.get("summary", "")

    if verified:
        speech = (
            f"Recovery action {action_id} was successfully executed. "
            f"I reran the diagnostic probes, and verification confirmed: {summary}. "
            f"The issue has been verified as resolved."
        )
    else:
        speech = (
            f"Recovery action {action_id} was executed, but post-action verification failed. "
            f"{summary}. I cannot claim the incident is resolved. Please check router hardware."
        )

    return {
        "spoken_response": speech,
        "verified": verified,
        "action_id": action_id,
        "summary": summary,
        "raw_result": result,
    }
