from app.diagnostics import classify


def test_full_failure_is_broad_connectivity_issue():
    checks = [
        {"name": "dns", "ok": False},
        {"name": "https_egress", "ok": False},
        {"name": "business_service", "ok": False, "evidence": {}},
    ]
    status, diagnosis, _ = classify(checks)
    assert status == "degraded"
    assert "DNS" in diagnosis


def test_all_checks_passing_is_healthy():
    checks = [
        {"name": "dns", "ok": True},
        {"name": "https_egress", "ok": True},
        {"name": "business_service", "ok": True, "evidence": {}},
    ]
    status, _, _ = classify(checks)
    assert status == "healthy"
