"""SQLite event/incident store. Keep persistence separate from diagnosis logic."""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from .config import settings


def _connect() -> sqlite3.Connection:
    path = Path(settings.data_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            site_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            status TEXT NOT NULL,
            user_report TEXT NOT NULL,
            diagnosis TEXT NOT NULL,
            report_json TEXT NOT NULL
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS device_heartbeats (
            device_id TEXT PRIMARY KEY,
            site_id TEXT NOT NULL,
            received_at TEXT NOT NULL,
            wifi_rssi_dbm INTEGER,
            uptime_seconds INTEGER
        )""")
        conn.commit()


def create_incident(site_id: str, user_report: str, report: dict[str, Any]) -> dict[str, Any]:
    created_at = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        cursor = conn.execute(
            "INSERT INTO incidents(site_id, created_at, status, user_report, diagnosis, report_json) VALUES(?,?,?,?,?,?)",
            (site_id, created_at, report["status"], user_report, report["diagnosis"], json.dumps(report)),
        )
        incident_id = int(cursor.lastrowid)
        conn.commit()
    return {"id": incident_id, "site_id": site_id, "created_at": created_at,
            "status": report["status"], "user_report": user_report,
            "diagnosis": report["diagnosis"], "report": report}


def get_incident(incident_id: int) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM incidents WHERE id=?", (incident_id,)).fetchone()
    if row is None:
        return None
    return {"id": row["id"], "site_id": row["site_id"], "created_at": row["created_at"],
            "status": row["status"], "user_report": row["user_report"],
            "diagnosis": row["diagnosis"], "report": json.loads(row["report_json"])}


def latest_incident(site_id: str) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute("SELECT id FROM incidents WHERE site_id=? ORDER BY id DESC LIMIT 1", (site_id,)).fetchone()
    return get_incident(int(row["id"])) if row else None


def save_heartbeat(device_id: str, site_id: str, rssi: int | None, uptime: int | None) -> dict[str, Any]:
    received_at = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        conn.execute("""INSERT INTO device_heartbeats(device_id, site_id, received_at, wifi_rssi_dbm, uptime_seconds)
            VALUES(?,?,?,?,?) ON CONFLICT(device_id) DO UPDATE SET
            site_id=excluded.site_id, received_at=excluded.received_at,
            wifi_rssi_dbm=excluded.wifi_rssi_dbm, uptime_seconds=excluded.uptime_seconds""",
            (device_id, site_id, received_at, rssi, uptime))
        conn.commit()
    return {"device_id": device_id, "site_id": site_id, "received_at": received_at,
            "wifi_rssi_dbm": rssi, "uptime_seconds": uptime}


def get_heartbeats(site_id: str) -> list[dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM device_heartbeats WHERE site_id=? ORDER BY device_id", (site_id,)).fetchall()
    return [dict(row) for row in rows]
