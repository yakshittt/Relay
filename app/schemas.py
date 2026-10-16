from typing import Literal, Optional
from pydantic import BaseModel, Field


class DiagnoseRequest(BaseModel):
    site_id: str = Field(default="jio-lab", min_length=1, max_length=80)
    user_report: str = Field(default="Run a routine connectivity check", max_length=1000)


class RecoveryRequest(BaseModel):
    incident_id: int
    action: Literal["clear_demo_dns_fault"]
    user_confirmed: bool = False


class HeartbeatRequest(BaseModel):
    device_id: str = Field(min_length=1, max_length=80)
    site_id: str = Field(default="jio-lab", min_length=1, max_length=80)
    wifi_rssi_dbm: Optional[int] = Field(default=None, ge=-127, le=0)
    uptime_seconds: Optional[int] = Field(default=None, ge=0)
