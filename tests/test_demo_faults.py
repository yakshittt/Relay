"""Tests for demo fault injection controls and guards."""
import pytest
from app.services.demo import demo_fault_manager
from app.services.probes import default_probe_engine
from app.config import settings


@pytest.fixture(autouse=True)
def cleanup():
    demo_fault_manager.clear_all()
    yield
    demo_fault_manager.clear_all()


def test_demo_fault_injection_dns_outage():
    """Toggling dns_outage must flag the business probe as simulated and failing."""
    demo_fault_manager.set_fault("dns_outage", True)
    assert demo_fault_manager.is_active("dns_outage") is True

    probe = default_probe_engine.probe_business_service()
    assert probe.ok is False
    assert probe.is_simulated is True
    assert probe.error_category == "SIMULATED_DNS_OUTAGE"


def test_demo_fault_injection_http_503():
    """Toggling business_http_503 must simulate a 503 outage on the business service."""
    demo_fault_manager.set_fault("business_http_503", True)
    assert demo_fault_manager.is_active("business_http_503") is True

    probe = default_probe_engine.probe_business_service()
    assert probe.ok is False
    assert probe.is_simulated is True
    assert probe.error_category == "SIMULATED_HTTP_503"


def test_demo_fault_injection_gateway_loss():
    """Toggling gateway_loss must simulate a router LAN unreachable state."""
    demo_fault_manager.set_fault("gateway_loss", True)
    assert demo_fault_manager.is_active("gateway_loss") is True

    probe = default_probe_engine.probe_gateway()
    assert probe.ok is False
    assert probe.is_simulated is True
    assert probe.error_category == "GATEWAY_UNREACHABLE"


def test_clear_all_demo_faults():
    """clear_all must reset all active demo faults."""
    demo_fault_manager.set_fault("dns_outage", True)
    demo_fault_manager.set_fault("gateway_loss", True)
    assert demo_fault_manager.is_active("dns_outage") is True

    demo_fault_manager.clear_all()
    assert demo_fault_manager.is_active("dns_outage") is False
    assert demo_fault_manager.is_active("gateway_loss") is False
