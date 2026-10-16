"""Demo Fault State Management.
Guarded by settings.demo_mode. Explicitly flags simulated data to prevent misleading operators.
"""
from typing import Dict
from app.config import settings


class DemoFaultManager:
    def __init__(self) -> None:
        self._faults: Dict[str, bool] = {
            "dns_outage": False,
            "business_http_503": False,
            "stale_heartbeat": False,
            "gateway_loss": False,
        }

    def _ensure_demo_mode(self) -> None:
        if not settings.demo_mode:
            raise PermissionError("Demo fault injection is disabled when DEMO_MODE=False")

    def set_fault(self, fault_type: str, enabled: bool) -> None:
        self._ensure_demo_mode()
        if fault_type not in self._faults:
            raise ValueError(f"Unknown fault type: '{fault_type}'")
        self._faults[fault_type] = enabled

    def is_active(self, fault_type: str) -> bool:
        if not settings.demo_mode:
            return False
        return self._faults.get(fault_type, False)

    def get_all_faults(self) -> Dict[str, bool]:
        if not settings.demo_mode:
            return {k: False for k in self._faults}
        return dict(self._faults)

    def clear_all(self) -> None:
        self._ensure_demo_mode()
        for k in self._faults:
            self._faults[k] = False


# Global singleton instance
demo_fault_manager = DemoFaultManager()
