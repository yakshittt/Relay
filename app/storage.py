"""SQLite event, incident, device telemetry, and audit store.
Keeps persistence clean, ACID-compliant, and strictly typed.
"""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from app.config import settings


def _connect() -> sqlite3.Connection:
    path = Path(settings.data_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    # Enable foreign keys
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """Initialize database tables, columns, and indexes."""
    with _connect() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            site_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            status TEXT NOT NULL,
            user_report TEXT NOT NULL,
            summary TEXT NOT NULL DEFAULT '',
            diagnosis TEXT NOT NULL,
            report_json TEXT NOT NULL
        )""")

        conn.execute("""CREATE TABLE IF NOT EXISTS incident_timeline (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            incident_id INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            description TEXT NOT NULL,
            metadata_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(incident_id) REFERENCES incidents(id) ON DELETE CASCADE
        )""")

        conn.execute("""CREATE TABLE IF NOT EXISTS recovery_actions (
            id TEXT PRIMARY KEY,
            incident_id INTEGER NOT NULL,
            action_type TEXT NOT NULL,
            parameters_json TEXT NOT NULL,
            impact_description TEXT NOT NULL,
            required_approval_level TEXT NOT NULL,
            status TEXT NOT NULL,
            idempotency_key TEXT,
            approval_token TEXT NOT NULL,
            token_expires_at TEXT NOT NULL,
            is_consumed INTEGER NOT NULL DEFAULT 0,
            outcome TEXT,
            verification_passed INTEGER,
            verification_json TEXT,
            created_at TEXT NOT NULL,
            executed_at TEXT,
            FOREIGN KEY(incident_id) REFERENCES incidents(id) ON DELETE CASCADE
        )""")

        conn.execute("""CREATE TABLE IF NOT EXISTS device_heartbeats (
            device_id TEXT PRIMARY KEY,
            site_id TEXT NOT NULL,
            received_at TEXT NOT NULL,
            wifi_rssi_dbm INTEGER,
            uptime_seconds INTEGER,
            firmware_version TEXT,
            free_heap INTEGER,
            cycle_count INTEGER
        )""")

        conn.execute("""CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            actor TEXT NOT NULL,
            details_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        )""")

        # Indexes for fast lookup
        conn.execute("CREATE INDEX IF NOT EXISTS idx_incidents_site ON incidents(site_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_incidents_status ON incidents(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_timeline_inc ON incident_timeline(incident_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_actions_inc ON recovery_actions(incident_id)")
        conn.commit()


def add_timeline_event(
    incident_id: int, event_type: str, description: str, metadata: Optional[Dict[str, Any]] = None
) -> None:
    now_iso = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        conn.execute(
            """INSERT INTO incident_timeline (incident_id, event_type, description, metadata_json, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (incident_id, event_type, description, json.dumps(metadata or {}), now_iso),
        )
        conn.commit()


def create_incident(site_id: str, user_report: str, report: Dict[str, Any]) -> Dict[str, Any]:
    now_iso = datetime.now(timezone.utc).isoformat()
    status_str = report.get("status", "unknown")
    if hasattr(status_str, "value"):
        status_str = status_str.value
    summary_str = report.get("summary", "Network connectivity diagnostic run")
    diagnosis_str = report.get("diagnosis", "")

    with _connect() as conn:
        cursor = conn.execute(
            """INSERT INTO incidents (site_id, created_at, updated_at, status, user_report, summary, diagnosis, report_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                site_id,
                now_iso,
                now_iso,
                str(status_str),
                user_report,
                summary_str,
                diagnosis_str,
                json.dumps(report, default=str),
            ),
        )
        incident_id = int(cursor.lastrowid)
        conn.commit()

    add_timeline_event(
        incident_id,
        "INCIDENT_CREATED",
        f"Incident opened with report: '{user_report}'",
        {"initial_status": str(status_str), "summary": summary_str},
    )

    return {
        "id": incident_id,
        "site_id": site_id,
        "created_at": now_iso,
        "updated_at": now_iso,
        "status": str(status_str),
        "user_report": user_report,
        "summary": summary_str,
        "diagnosis": diagnosis_str,
        "report": report,
    }


def update_incident_status(incident_id: int, status: str, note: Optional[str] = None) -> None:
    now_iso = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        conn.execute(
            "UPDATE incidents SET status=?, updated_at=? WHERE id=?",
            (status, now_iso, incident_id),
        )
        conn.commit()

    add_timeline_event(
        incident_id,
        "STATUS_UPDATED",
        f"Incident status changed to {status}. {note or ''}".strip(),
        {"new_status": status, "note": note},
    )


def get_incident(incident_id: int) -> Optional[Dict[str, Any]]:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM incidents WHERE id=?", (incident_id,)).fetchone()
        if not row:
            return None

        # Fetch timeline
        timeline_rows = conn.execute(
            "SELECT * FROM incident_timeline WHERE incident_id=? ORDER BY id ASC",
            (incident_id,),
        ).fetchall()

        # Fetch recovery actions
        action_rows = conn.execute(
            "SELECT * FROM recovery_actions WHERE incident_id=? ORDER BY created_at ASC",
            (incident_id,),
        ).fetchall()

    timeline = [
        {
            "id": r["id"],
            "incident_id": r["incident_id"],
            "event_type": r["event_type"],
            "description": r["description"],
            "metadata": json.loads(r["metadata_json"]),
            "created_at": r["created_at"],
        }
        for r in timeline_rows
    ]

    actions = [
        {
            "id": r["id"],
            "action_id": r["id"],
            "incident_id": r["incident_id"],
            "action_type": r["action_type"],
            "parameters": json.loads(r["parameters_json"]),
            "impact_description": r["impact_description"],
            "required_approval_level": r["required_approval_level"],
            "status": r["status"],
            "idempotency_key": r["idempotency_key"],
            "approval_token": r["approval_token"],
            "token_expires_at": r["token_expires_at"],
            "is_consumed": bool(r["is_consumed"]),
            "outcome": r["outcome"],
            "verification_passed": None if r["verification_passed"] is None else bool(r["verification_passed"]),
            "verification_details": json.loads(r["verification_json"]) if r["verification_json"] else None,
            "created_at": r["created_at"],
            "executed_at": r["executed_at"],
        }
        for r in action_rows
    ]

    return {
        "id": row["id"],
        "site_id": row["site_id"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "status": row["status"],
        "user_report": row["user_report"],
        "summary": row["summary"] if "summary" in row.keys() else "",
        "diagnosis": row["diagnosis"],
        "report": json.loads(row["report_json"]),
        "timeline": timeline,
        "recovery_actions": actions,
    }


def list_incidents(
    site_id: Optional[str] = None, status: Optional[str] = None, limit: int = 50
) -> List[Dict[str, Any]]:
    query = "SELECT * FROM incidents"
    params: List[Any] = []
    conditions = []

    if site_id:
        conditions.append("site_id = ?")
        params.append(site_id)
    if status:
        conditions.append("status = ?")
        params.append(status)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)

    with _connect() as conn:
        rows = conn.execute(query, params).fetchall()

    return [
        {
            "id": r["id"],
            "site_id": r["site_id"],
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
            "status": r["status"],
            "user_report": r["user_report"],
            "summary": r["summary"] if "summary" in r.keys() else "",
            "diagnosis": r["diagnosis"],
            "report": json.loads(r["report_json"]),
        }
        for r in rows
    ]


def latest_incident(site_id: str) -> Optional[Dict[str, Any]]:
    with _connect() as conn:
        row = conn.execute(
            "SELECT id FROM incidents WHERE site_id=? ORDER BY id DESC LIMIT 1", (site_id,)
        ).fetchone()
    return get_incident(int(row["id"])) if row else None


def create_recovery_action(
    action_id: str,
    incident_id: int,
    action_type: str,
    parameters: Dict[str, Any],
    impact_description: str,
    required_approval_level: str,
    approval_token: str,
    token_expires_at: str,
) -> Dict[str, Any]:
    now_iso = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        conn.execute(
            """INSERT INTO recovery_actions
               (id, incident_id, action_type, parameters_json, impact_description,
                required_approval_level, status, approval_token, token_expires_at, is_consumed, created_at)
               VALUES (?, ?, ?, ?, ?, ?, 'PROPOSED', ?, ?, 0, ?)""",
            (
                action_id,
                incident_id,
                action_type,
                json.dumps(parameters),
                impact_description,
                required_approval_level,
                approval_token,
                token_expires_at,
                now_iso,
            ),
        )
        conn.commit()

    add_timeline_event(
        incident_id,
        "RECOVERY_PROPOSED",
        f"Proposed recovery action '{action_type}'. Approval required ({required_approval_level}).",
        {"action_id": action_id, "action_type": action_type, "impact": impact_description},
    )

    return {
        "action_id": action_id,
        "incident_id": incident_id,
        "action_type": action_type,
        "parameters": parameters,
        "impact_description": impact_description,
        "required_approval_level": required_approval_level,
        "status": "PROPOSED",
        "approval_token": approval_token,
        "token_expires_at": token_expires_at,
        "created_at": now_iso,
    }


def get_recovery_action(action_id: str) -> Optional[Dict[str, Any]]:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM recovery_actions WHERE id=?", (action_id,)).fetchone()
    if not row:
        return None
    return {
        "id": row["id"],
        "action_id": row["id"],
        "incident_id": row["incident_id"],
        "action_type": row["action_type"],
        "parameters": json.loads(row["parameters_json"]),
        "impact_description": row["impact_description"],
        "required_approval_level": row["required_approval_level"],
        "status": row["status"],
        "idempotency_key": row["idempotency_key"],
        "approval_token": row["approval_token"],
        "token_expires_at": row["token_expires_at"],
        "is_consumed": bool(row["is_consumed"]),
        "outcome": row["outcome"],
        "verification_passed": None if row["verification_passed"] is None else bool(row["verification_passed"]),
        "verification_details": json.loads(row["verification_json"]) if row["verification_json"] else None,
        "created_at": row["created_at"],
        "executed_at": row["executed_at"],
    }


def update_recovery_action_execution(
    action_id: str,
    status: str,
    outcome: str,
    verification_passed: bool,
    verification_details: Dict[str, Any],
    idempotency_key: Optional[str] = None,
) -> None:
    now_iso = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        conn.execute(
            """UPDATE recovery_actions SET
               status=?, outcome=?, verification_passed=?, verification_json=?,
               idempotency_key=?, executed_at=?
               WHERE id=?""",
            (
                status,
                outcome,
                1 if verification_passed else 0,
                json.dumps(verification_details, default=str),
                idempotency_key,
                now_iso,
                action_id,
            ),
        )
        conn.commit()


def consume_approval_token(action_id: str, token_str: str) -> bool:
    """Validate and consume single-use approval token. Returns True if successfully consumed."""
    now_iso = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM recovery_actions WHERE id=? AND approval_token=? AND is_consumed=0",
            (action_id, token_str),
        ).fetchone()

        if not row:
            return False

        # Check expiry
        if row["token_expires_at"] < now_iso:
            return False

        # Mark consumed atomically
        conn.execute("UPDATE recovery_actions SET is_consumed=1 WHERE id=?", (action_id,))
        conn.commit()
    return True


def save_heartbeat(
    device_id: str,
    site_id: str,
    rssi: Optional[int],
    uptime: Optional[int],
    firmware_version: Optional[str] = None,
    free_heap: Optional[int] = None,
    cycle_count: Optional[int] = None,
) -> Dict[str, Any]:
    received_at = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        conn.execute(
            """INSERT INTO device_heartbeats
               (device_id, site_id, received_at, wifi_rssi_dbm, uptime_seconds, firmware_version, free_heap, cycle_count)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(device_id) DO UPDATE SET
               site_id=excluded.site_id,
               received_at=excluded.received_at,
               wifi_rssi_dbm=excluded.wifi_rssi_dbm,
               uptime_seconds=excluded.uptime_seconds,
               firmware_version=COALESCE(excluded.firmware_version, device_heartbeats.firmware_version),
               free_heap=excluded.free_heap,
               cycle_count=excluded.cycle_count""",
            (device_id, site_id, received_at, rssi, uptime, firmware_version, free_heap, cycle_count),
        )
        conn.commit()

    return {
        "device_id": device_id,
        "site_id": site_id,
        "received_at": received_at,
        "wifi_rssi_dbm": rssi,
        "uptime_seconds": uptime,
        "firmware_version": firmware_version,
        "free_heap": free_heap,
        "cycle_count": cycle_count,
    }


def get_heartbeats(site_id: Optional[str] = None) -> List[Dict[str, Any]]:
    query = "SELECT * FROM device_heartbeats"
    params: List[Any] = []
    if site_id:
        query += " WHERE site_id=?"
        params.append(site_id)
    query += " ORDER BY device_id ASC"

    with _connect() as conn:
        rows = conn.execute(query, params).fetchall()

    return [dict(r) for r in rows]


def record_audit(action: str, actor: str, details: Dict[str, Any]) -> None:
    now_iso = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        conn.execute(
            "INSERT INTO audit_logs (action, actor, details_json, created_at) VALUES (?, ?, ?, ?)",
            (action, actor, json.dumps(details), now_iso),
        )
        conn.commit()


def get_all_sites() -> List[str]:
    with _connect() as conn:
        inc_sites = [r[0] for r in conn.execute("SELECT DISTINCT site_id FROM incidents").fetchall()]
        dev_sites = [r[0] for r in conn.execute("SELECT DISTINCT site_id FROM device_heartbeats").fetchall()]
    all_sites = sorted(set(inc_sites + dev_sites + ["jio-lab"]))
    return all_sites


def get_overview_stats() -> Dict[str, Any]:
    """Calculate live production statistics for the operations console."""
    all_sites = get_all_sites()
    with _connect() as conn:
        open_incidents_count = conn.execute(
            "SELECT COUNT(*) FROM incidents WHERE status IN ('degraded', 'failed', 'open', 'action_required')"
        ).fetchone()[0]

        total_incidents_count = conn.execute("SELECT COUNT(*) FROM incidents").fetchone()[0]

        actions_succeeded = conn.execute(
            "SELECT COUNT(*) FROM recovery_actions WHERE status='SUCCEEDED' AND verification_passed=1"
        ).fetchone()[0]

        total_actions = conn.execute(
            "SELECT COUNT(*) FROM recovery_actions WHERE status IN ('SUCCEEDED', 'FAILED')"
        ).fetchone()[0]

    recovery_rate = (
        round((actions_succeeded / total_actions) * 100, 1) if total_actions > 0 else 100.0
    )

    devices = get_heartbeats()
    now = datetime.now(timezone.utc)
    online_devices = 0
    stale_devices = 0
    for d in devices:
        try:
            seen = datetime.fromisoformat(d["received_at"])
            age = (now - seen).total_seconds()
            if age <= settings.esp32_stale_seconds:
                online_devices += 1
            else:
                stale_devices += 1
        except Exception:
            stale_devices += 1

    return {
        "total_sites": len(all_sites),
        "open_incidents": open_incidents_count,
        "total_incidents": total_incidents_count,
        "online_devices": online_devices,
        "stale_devices": stale_devices,
        "recovery_success_rate": recovery_rate,
        "total_recovery_actions": total_actions,
    }
