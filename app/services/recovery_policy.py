"""Recovery policy engine and allowlisted action registry.
Enforces strict parameter schemas, impact disclosures, and expiring approval tokens.
"""
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional
from app.config import settings
from app.schemas import ActionStatus
from app.security.auth import generate_approval_token
from app import storage


# Allowlisted Action Definitions
ALLOWLISTED_ACTIONS: Dict[str, Dict[str, Any]] = {
    "clear_demo_dns_fault": {
        "impact_description": "Clears the active simulated DNS/HTTP fault. Resumes normal simulated routing without changing host or router settings.",
        "required_approval_level": "OPERATOR",
        "allowed_parameters": {},
        "is_safe_simulation": True,
    },
    "flush_dns_cache_simulated": {
        "impact_description": "Simulates flushing client and local resolver DNS cache to evict stale negative TTL records.",
        "required_approval_level": "OPERATOR",
        "allowed_parameters": {"scope": ["local", "all"]},
        "is_safe_simulation": True,
    },
    "switch_failover_dns_simulated": {
        "impact_description": "Simulates switching the secondary upstream resolver to 1.1.1.1 / 8.8.8.8 failover.",
        "required_approval_level": "ADMIN",
        "allowed_parameters": {"provider": ["cloudflare", "google"]},
        "is_safe_simulation": True,
    },
}


class RecoveryPolicyError(ValueError):
    """Raised when an action violates recovery safety policy."""
    pass


def validate_action_proposal(action_type: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Validate action type against allowlist and verify parameter constraints."""
    if action_type not in ALLOWLISTED_ACTIONS:
        raise RecoveryPolicyError(
            f"Action '{action_type}' is not allowlisted. Only vetted actions may be proposed."
        )

    action_def = ALLOWLISTED_ACTIONS[action_type]
    allowed_params = action_def["allowed_parameters"]

    # Parameter schema validation
    for key, val in parameters.items():
        if key not in allowed_params:
            raise RecoveryPolicyError(f"Unexpected parameter '{key}' for action '{action_type}'")
        allowed_values = allowed_params[key]
        if isinstance(allowed_values, list) and val not in allowed_values:
            raise RecoveryPolicyError(
                f"Invalid value '{val}' for parameter '{key}'. Expected one of {allowed_values}"
            )

    return action_def


def propose_recovery_action(
    incident_id: int, action_type: str, parameters: Dict[str, Any]
) -> Dict[str, Any]:
    """Create and persist an auditable recovery action proposal with single-use approval token."""
    incident = storage.get_incident(incident_id)
    if not incident:
        raise RecoveryPolicyError(f"Incident #{incident_id} not found")

    action_def = validate_action_proposal(action_type, parameters)
    action_id = f"act_{uuid.uuid4().hex[:12]}"
    approval_token = generate_approval_token()

    now = datetime.now(timezone.utc)
    token_expires_at = (now + timedelta(seconds=settings.approval_token_ttl_seconds)).isoformat()

    action_record = storage.create_recovery_action(
        action_id=action_id,
        incident_id=incident_id,
        action_type=action_type,
        parameters=parameters,
        impact_description=action_def["impact_description"],
        required_approval_level=action_def["required_approval_level"],
        approval_token=approval_token,
        token_expires_at=token_expires_at,
    )

    storage.record_audit(
        action="RECOVERY_ACTION_PROPOSED",
        actor="system:recovery_policy",
        details={
            "action_id": action_id,
            "incident_id": incident_id,
            "action_type": action_type,
            "token_expires_at": token_expires_at,
        },
    )

    return action_record
