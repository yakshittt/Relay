"""Post-action verification engine.
Executes fresh diagnostic probes to mathematically verify whether recovery succeeded.
NEVER asserts recovery without confirmed passing probe evidence.
"""
from typing import Any, Dict, List
from app.schemas import ProbeResult
from app.services.probes import default_probe_engine
from app.services.devices import get_site_devices
from app.services.diagnosis import classify_incident


def run_post_action_verification(
    site_id: str,
    pre_recovery_report: Dict[str, Any],
) -> Dict[str, Any]:
    """Execute fresh probes and compare against baseline to verify recovery."""
    # Run fresh probes
    post_probes: List[ProbeResult] = default_probe_engine.execute_all_probes()
    devices = get_site_devices(site_id)
    post_diagnosis = classify_incident(post_probes, devices)

    pre_checks = pre_recovery_report.get("checks", [])
    pre_failing_names = {c.get("name") for c in pre_checks if not c.get("ok")}

    post_failing_names = {p.name for p in post_probes if not p.ok}

    recovered_checks = list(pre_failing_names - post_failing_names)
    remaining_failures = list(post_failing_names)
    new_failures = list(post_failing_names - pre_failing_names)

    # Verification passes ONLY if all pre-failing probes recovered and no new failures occurred
    all_passing = len(post_failing_names) == 0
    verification_passed = (len(remaining_failures) == 0) and (len(new_failures) == 0) and all_passing

    summary = (
        f"Verified recovery: All {len(post_probes)} probes passed."
        if verification_passed
        else f"Recovery failed: {len(remaining_failures)} check(s) remain in failing state: {', '.join(remaining_failures)}."
    )

    return {
        "verification_passed": verification_passed,
        "summary": summary,
        "recovered_checks": recovered_checks,
        "remaining_failures": remaining_failures,
        "new_failures": new_failures,
        "post_status": post_diagnosis["status"],
        "post_diagnosis": post_diagnosis["diagnosis"],
        "checks": [p.model_dump() for p in post_probes],
        "devices": [d.model_dump() for d in devices],
    }
