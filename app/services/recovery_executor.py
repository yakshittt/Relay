"""Recovery action executor.
Consumes single-use approval tokens, executes restricted adapters, and runs verification.
"""
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from app.config import settings
from app.schemas import ActionStatus
from app.services.demo import demo_fault_manager
from app.services.verification import run_post_action_verification
from app import storage


class ExecutionError(RuntimeError):
    """Raised during recovery execution failure."""
    pass


def execute_action(
    action_id: str,
    approval_token: str,
    idempotency_key: Optional[str] = None,
    operator: str = "operator:console",
) -> Dict[str, Any]:
    """Execute an approved action after strictly verifying the single-use token."""
    action = storage.get_recovery_action(action_id)
    if not action:
        raise ExecutionError(f"Action '{action_id}' not found")

    if action["status"] in ("SUCCEEDED", "FAILED", "EXECUTING"):
        return {
            "ok": action["verification_passed"] or False,
            "action_id": action_id,
            "status": action["status"],
            "message": f"Action was already executed (status: {action['status']}).",
            "verification_passed": action["verification_passed"] or False,
            "verification_details": action["verification_details"] or {},
            "executed_at": action["executed_at"] or datetime.now(timezone.utc).isoformat(),
            "warning": "Simulated recovery action; did not alter router firmware.",
        }

    # Consume token
    token_valid = storage.consume_approval_token(action_id, approval_token)
    if not token_valid:
        storage.record_audit(
            action="UNAUTHORIZED_RECOVERY_ATTEMPT",
            actor=operator,
            details={"action_id": action_id, "reason": "Invalid, expired, or already-consumed approval token"},
        )
        raise ExecutionError(
            "Authorization failed: Approval token is invalid, expired, or was already consumed."
        )

    incident_id = action["incident_id"]
    incident = storage.get_incident(incident_id)
    if not incident:
        raise ExecutionError(f"Associated incident #{incident_id} not found")

    # Record execution start
    storage.add_timeline_event(
        incident_id,
        "ACTION_EXECUTING",
        f"Executing recovery action '{action['action_type']}' by {operator}",
        {"action_id": action_id, "action_type": action["action_type"]},
    )

    action_type = action["action_type"]
    executed_at = datetime.now(timezone.utc).isoformat()

    # Restricted adapter execution
    outcome_message = ""
    try:
        if action_type == "clear_demo_dns_fault":
            demo_fault_manager.set_fault("dns_outage", False)
            demo_fault_manager.set_fault("business_http_503", False)
            outcome_message = "Cleared active demo fault injection."
        elif action_type == "flush_dns_cache_simulated":
            outcome_message = "Simulated local resolver cache eviction executed successfully."
        elif action_type == "switch_failover_dns_simulated":
            outcome_message = "Simulated secondary DNS failover configuration applied."
        else:
            raise ExecutionError(f"Unsupported action type: {action_type}")
    except Exception as exc:
        storage.update_recovery_action_execution(
            action_id=action_id,
            status=ActionStatus.FAILED.value,
            outcome=f"Execution error: {exc}",
            verification_passed=False,
            verification_details={"error": str(exc)},
            idempotency_key=idempotency_key,
        )
        storage.update_incident_status(incident_id, "unresolved", f"Action failed: {exc}")
        raise ExecutionError(f"Adapter execution failed: {exc}")

    # Immediately run post-action verification
    verification = run_post_action_verification(incident["site_id"], incident["report"])
    verification_passed = verification["verification_passed"]

    final_status = ActionStatus.SUCCEEDED.value if verification_passed else ActionStatus.FAILED.value
    storage.update_recovery_action_execution(
        action_id=action_id,
        status=final_status,
        outcome=outcome_message,
        verification_passed=verification_passed,
        verification_details=verification,
        idempotency_key=idempotency_key,
    )

    if verification_passed:
        storage.update_incident_status(
            incident_id, "healthy", f"Recovery verified: {verification['summary']}"
        )
        storage.add_timeline_event(
            incident_id,
            "RECOVERY_VERIFIED",
            f"Action '{action_type}' succeeded. Post-action verification confirmed all probes passing.",
            verification,
        )
    else:
        storage.update_incident_status(
            incident_id, "unresolved", f"Verification failed: {verification['summary']}"
        )
        storage.add_timeline_event(
            incident_id,
            "VERIFICATION_FAILED",
            f"Action '{action_type}' executed but verification failed. Probes still failing.",
            verification,
        )

    storage.record_audit(
        action="RECOVERY_ACTION_COMPLETED",
        actor=operator,
        details={
            "action_id": action_id,
            "action_type": action_type,
            "verification_passed": verification_passed,
            "final_status": final_status,
        },
    )

    return {
        "ok": verification_passed,
        "action_id": action_id,
        "status": final_status,
        "message": outcome_message,
        "verification_passed": verification_passed,
        "verification_details": verification,
        "executed_at": executed_at,
        "warning": "Simulated recovery action; did not alter router firmware.",
    }
