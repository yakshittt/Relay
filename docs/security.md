# RELAY Security & Threat Model

## 1. Security Architecture Principles

RELAY enforces zero-trust boundaries between:
1. **The Voice LLM Layer**: The LLM is an untrusted natural language parser. It cannot directly execute shell commands, run arbitrary HTTP queries, or provide a simple boolean flag to bypass approval.
2. **The IoT Device Tier**: ESP32 probes possess only telemetry ingestion authority via dedicated device tokens; they cannot query incidents or trigger recoveries.
3. **The Operator / Management Tier**: Protected by Bearer authentication, audit logging, and single-use cryptographic tokens.
4. **Physical Network Hardware (Jio Router)**: Probed strictly as an external black-box target over LAN. No firmware modification or unauthenticated admin commands are ever executed.

---

## 2. Authentication & Authorization Boundaries

### Bearer Token Authentication
- Private endpoints (`/v1/tools/*`, `/v1/sites/*`, `/v1/overview/*`, `/v1/demo/*`) require an `Authorization: Bearer <TOKEN>` header.
- Validated using constant-time string comparison (`secrets.compare_digest`) to prevent timing side-channel attacks.

### Device Telemetry Authentication
- IoT devices submit heartbeats via `POST /v1/devices/heartbeat` authenticated with an `X-Device-Token` header.
- Devices are restricted strictly to telemetry writes. They cannot access diagnostic probe outputs, read incident records, or trigger recovery actions.

### Multi-Step Action Authorization Flow
To prevent accidental or LLM-induced disruptions, recovery follows a 3-step authorization lifecycle:
1. **Proposal**: `/v1/tools/recovery/propose` validates that the action type is on the strict server-side allowlist.
2. **Token Issuance**: The server generates a high-entropy URL-safe token (`apr_<token>`) with a strictly enforced TTL (default 300 seconds) and records it in SQLite.
3. **Atomic Consumption**: When `/v1/tools/recovery/execute` is invoked, the token is validated and marked consumed in a database transaction (`is_consumed=1`). Replayed or duplicate requests are rejected.

---

## 3. SSRF & Target Allowlist Enforcement

To prevent Server-Side Request Forgery (SSRF) and intranet port scanning:
- Every diagnostic probe target is validated through `app/security/ssrf.py`.
- Targets must match the configured target allowlist (`ALLOWLISTED_HOSTS`).
- Malformed hostnames, embedded command characters (`;`, `|`, `` ` ``), and unsafe URL schemes (`file://`, `ftp://`, `gopher://`) are rejected with `SSRFValidationError`.
- Request timeouts are strictly bounded (e.g., 3.0s for HTTPS egress, 800ms for gateway checks) to prevent resource exhaustion attacks.

---

## 4. No Arbitrary Shell Execution

- RELAY does **not** invoke `subprocess.Popen` or `os.system` with parameters derived from user queries or LLM outputs.
- Probes use native Python sockets (`socket.getaddrinfo`, `socket.create_connection`) and `httpx`.
- Recovery adapters are hardcoded Python handlers registered in `ALLOWLISTED_ACTIONS`.

---

## 5. Audit Logging

Every security-sensitive operation is logged to the `audit_logs` SQLite table with UTC timestamp, actor identity, action type, and structured metadata:
- `INCIDENT_OPENED`
- `DEVICE_HEARTBEAT_RECEIVED`
- `RECOVERY_ACTION_PROPOSED`
- `RECOVERY_ACTION_COMPLETED`
- `UNAUTHORIZED_RECOVERY_ATTEMPT`
