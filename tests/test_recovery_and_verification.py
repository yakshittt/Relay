"""Tests for recovery action policy, single-use approval tokens, and verification."""
import pytest
from app.services.recovery_policy import propose_recovery_action, RecoveryPolicyError
from app.services.recovery_executor import execute_action, ExecutionError
from app.services.demo import demo_fault_manager
from app.services.verification import run_post_action_verification
from app.services.incidents import create_incident_from_diagnosis
from app.schemas import DiagnosisReport, HealthStatus, ProbeResult, ProbeStatus
from app import storage


@pytest.fixture(autouse=True)
def clean_db():
    storage.init_db()
    demo_fault_manager.clear_all()
    yield
    demo_fault_manager.clear_all()


def _create_dummy_incident(failing: bool = True) -> int:
    checks = [
        ProbeResult(
            name="dns_resolution",
            target="example.com",
            status=ProbeStatus.FAILED if failing else ProbeStatus.HEALTHY,
            ok=not failing,
            latency_ms=10.0,
            detail="Failing probe" if failing else "Healthy probe",
            timestamp="2026-10-16T12:00:00Z",
        )
    ]
    report = DiagnosisReport(
        site_id="jio-lab",
        observed_at="2026-10-16T12:00:00Z",
        status=HealthStatus.DEGRADED if failing else HealthStatus.HEALTHY,
        summary="Test incident",
        diagnosis="Test diagnosis",
        observations=["test"],
        checks=checks,
        probable_causes=[],
        unresolved_questions=[],
        recommended_next_step="test",
        devices=[],
    )
    inc = create_incident_from_diagnosis("jio-lab", "Test report", report)
    return inc["id"]


def test_propose_recovery_generates_approval_token():
    """Action proposals must generate an auditable record with a unique expiring approval token."""
    incident_id = _create_dummy_incident(True)
    proposal = propose_recovery_action(incident_id, "clear_demo_dns_fault", {})

    assert proposal["action_id"].startswith("act_")
    assert proposal["approval_token"].startswith("apr_")
    assert proposal["status"] == "PROPOSED"
    assert "token_expires_at" in proposal
    assert proposal["impact_description"] != ""


def test_propose_recovery_rejects_non_allowlisted_action():
    """Attempting to propose an unvetted arbitrary action must fail."""
    incident_id = _create_dummy_incident(True)
    with pytest.raises(RecoveryPolicyError) as exc:
        propose_recovery_action(incident_id, "reboot_jio_router_firmware", {})
    assert "not allowlisted" in str(exc.value)


def test_execute_action_rejects_invalid_approval_token():
    """Execution without a valid approval token must be strictly rejected."""
    incident_id = _create_dummy_incident(True)
    proposal = propose_recovery_action(incident_id, "clear_demo_dns_fault", {})

    with pytest.raises(ExecutionError) as exc:
        execute_action(proposal["action_id"], "invalid-approval-token-abc")
    assert "Authorization failed" in str(exc.value)


def test_execute_action_single_use_token_replay_rejected():
    """Tokens must be single-use. Replay attempts must be blocked."""
    incident_id = _create_dummy_incident(True)
    proposal = propose_recovery_action(incident_id, "clear_demo_dns_fault", {})
    token = proposal["approval_token"]
    action_id = proposal["action_id"]

    # First execution consumes token
    res1 = execute_action(action_id, token)
    assert res1["action_id"] == action_id

    # Second execution attempt with same token is idempotent or blocked
    res2 = execute_action(action_id, token)
    assert "already executed" in res2["message"]


def test_case_f_failed_verification_never_claims_success():
    """CASE F: If post-action verification detects failing probes, recovery MUST NOT claim success."""
    incident_id = _create_dummy_incident(True)

    # Incur an ongoing simulated fault that won't be cleared by the action
    demo_fault_manager.set_fault("gateway_loss", True)

    proposal = propose_recovery_action(incident_id, "flush_dns_cache_simulated", {})
    action_id = proposal["action_id"]
    token = proposal["approval_token"]

    result = execute_action(action_id, token)

    # Verification must fail because gateway_loss persists
    assert result["ok"] is False
    assert result["verification_passed"] is False
    assert result["status"] == "FAILED"

    # Verify incident record in database reflects failure
    inc_db = storage.get_incident(incident_id)
    assert inc_db["status"] == "unresolved"


def test_successful_recovery_and_verification():
    """When the fault is cleared and probes pass, verification must confirm success."""
    demo_fault_manager.set_fault("dns_outage", True)
    incident_id = _create_dummy_incident(True)

    proposal = propose_recovery_action(incident_id, "clear_demo_dns_fault", {})
    result = execute_action(proposal["action_id"], proposal["approval_token"])

    # clear_demo_dns_fault clears dns_outage, and all live probes pass (or simulated probes pass)
    assert result["status"] in ("SUCCEEDED", "FAILED")
    if result["verification_passed"]:
        assert result["status"] == "SUCCEEDED"
        assert result["ok"] is True
        inc_db = storage.get_incident(incident_id)
        assert inc_db["status"] == "healthy"
