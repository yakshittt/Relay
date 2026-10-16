# RELAY — Voice-Native Incident Resolution Engine

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![React 19](https://img.shields.io/badge/React-19.2-61dafb.svg)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-6.0-blue.svg)](https://www.typescriptlang.org/)
[![Vite](https://img.shields.io/badge/Vite-8.3-646cff.svg)](https://vitejs.dev/)
[![Arduino ESP32](https://img.shields.io/badge/ESP32-Arduino%203.3.5-brightgreen.svg)](https://github.com/espressif/arduino-esp32)
[![Pytest Tests](https://img.shields.io/badge/tests-60%20passed-success.svg)](tests/)

> *"When a business location has a technology problem, RELAY investigates the issue, explains the evidence, recommends a safe fix, executes authorized actions, and verifies whether the problem was resolved."*

RELAY is a production-grade incident resolution platform designed for physical business locations (retail chains, cafes, clinics) operating on standard consumer or small business broadband (such as Jio Home Gateway).

---

## The Core Product Workflow

```
VOICE REPORT → EVIDENCE COLLECTION → DETERMINISTIC DIAGNOSIS → AUTHORIZED ACTION → POST-ACTION VERIFICATION → AUDITABLE TIMELINE
```

1. **Non-Technical User Reports Issue**: Store manager speaks naturally ("The billing application is not loading").
2. **Probes Collect Live Evidence**: RELAY executes real, SSRF-safe diagnostic probes (Gateway reachability, DNS resolution, HTTPS egress, business endpoint).
3. **Hardware Sentinel Telemetry**: Collects physical Wi-Fi RSSI, uptime, and memory counters from an ESP32 hardware monitor.
4. **Deterministic Rule Classification**: Distinguishes confirmed facts from hypotheses across decision trees (Cases A–F) with explicit confidence scores.
5. **Safe Action Formulation**: Issues an allowlisted recovery action with impact disclosure and single-use cryptographic approval token (`apr_<token>`).
6. **Authorized Execution**: Consumes the token atomically to prevent replay attacks and runs restricted adapters.
7. **Mathematical Post-Action Verification**: Automatically reruns diagnostic probes. Success is announced **only** if all failing probes pass.
8. **Auditable Incident Trail**: Persists an immutable timeline with timestamps in SQLite.

---

## Architecture & Repository Structure

```
relay_starter/
├── app/                           # FastAPI Backend
│   ├── main.py                    # API Routes, CORS, Bolna endpoints, voice simulation, AI endpoint
│   ├── config.py                  # Environment settings, allowlists, and credentials
│   ├── storage.py                 # SQLite persistence (incidents, timeline, actions, telemetry)
│   ├── schemas.py                 # Pydantic data models & contracts
│   ├── security/                  # Security boundaries
│   │   ├── auth.py                # Bearer tokens, device tokens, approval tokens
│   │   └── ssrf.py                # Target allowlist validator & SSRF prevention
│   └── services/                  # Clean domain service modules
│       ├── probes.py              # Typed probe engine with dependency injection
│       ├── diagnosis.py           # Transparent rule-based classification (Cases A–F)
│       ├── devices.py             # ESP32 heartbeat management & stale detection
│       ├── incidents.py           # Incident lifecycle and audit trails
│       ├── recovery_policy.py     # Allowlisted action registry & approval tokens
│       ├── recovery_executor.py   # Secure execution & replay protection
│       ├── verification.py        # Post-action probe verification
│       ├── demo.py                # Demo fault simulation manager (guarded by DEMO_MODE)
│       ├── bolna.py               # Bolna custom function schemas & voice formatter
│       └── ai/                    # Evidence-grounded AI interpreter & LLM providers
├── frontend/                      # React 19 + TypeScript + Vite Operations Console
│   ├── src/
│   │   ├── api.ts                 # Typed API client
│   │   ├── types.ts               # TypeScript data interfaces
│   │   ├── index.css              # Dark-mode B2B operations design system
│   │   ├── components/            # Reusable UI components
│   │   │   ├── Navbar.tsx         # Navigation bar & API settings modal
│   │   │   ├── StatusBadge.tsx    # Health & status indicators
│   │   │   ├── ProbeMatrix.tsx    # Detailed probe results matrix
│   │   │   └── RecoveryModal.tsx  # Authorization dialog with single-use tokens
│   │   ├── views/                 # Operations Console Views
│   │   │   ├── OverviewView.tsx   # Fleet overview, metrics, active incidents
│   │   │   ├── SiteDetailView.tsx # Site inspection, probe matrix, ESP32 telemetry
│   │   │   ├── IncidentDetailView.tsx # RCA view, evidence, timeline, recovery, AI Interpretation
│   │   │   ├── VoiceConsoleView.tsx   # Voice AI assistant simulation & Bolna schemas
│   │   │   └── PlaygroundView.tsx     # 6-step testing & fault injection lab
│   │   └── App.tsx                # Main router & state manager
├── firmware/                      # ESP32 Sentinel Firmware
│   ├── relay_esp32.ino            # Main Arduino sketch
│   └── relay_esp32/
│       └── relay_esp32.ino        # Arduino CLI-compatible sketch (compiled & verified)
├── tests/                         # Comprehensive Pytest Suite (60 tests, 100% pass)
│   ├── test_health_and_auth.py
│   ├── test_ssrf_and_probes.py
│   ├── test_diagnosis_cases.py    # Validates Cases A, B, C, D, E
│   ├── test_recovery_and_verification.py # Validates Case F, tokens, verification
│   ├── test_incidents_and_devices.py
│   ├── test_demo_faults.py
│   ├── test_bolna_contracts.py
│   └── test_ai_agent.py          # Provider abstraction, evidence grounding, fallback, security
└── docs/                          # Detailed Technical Documentation
    ├── architecture.md            # Architecture diagrams & component boundaries
    ├── bolna-integration.md       # Bolna tool schemas, curl examples, voice guide
    ├── hardware-setup.md          # ESP32 setup, Arduino CLI compilation report
    ├── security.md                # Threat model, token lifecycle, SSRF protection
    ├── demo-runbook.md            # Step-by-step reproduction instructions
    ├── IMPLEMENTATION_CHECKLIST.md# Engineering milestone tracking
    └── ai/
        └── decisions.md           # AI architecture decision records (ADR-001 - ADR-009) & limitations
```

---

## Getting Started

### 1. Prerequisites
- **Python 3.11+**
- **Node.js 18+ & npm**
- **Arduino CLI / Arduino IDE** (Optional: for flashing physical ESP32 boards)

### 2. Backend Setup
```powershell
# Clone or navigate to the directory
cd relay_starter

# Install Python dependencies
pip install -r requirements.txt

# Copy example environment configuration
cp .env.example .env

# Start the FastAPI backend server
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

The interactive API documentation is accessible at `http://127.0.0.1:8000/docs`.  
The unauthenticated health check is at `http://127.0.0.1:8000/health`.

### 3. Frontend Setup
In a new terminal:
```powershell
cd relay_starter/frontend

# Install dependencies (already completed)
npm install

# Start the Vite development server
npm run dev
```

Open `http://localhost:5173` in your browser. The Operations Console connects automatically to the backend at `http://127.0.0.1:8000`.

---

## Automated Test Suite

To run the complete automated test suite:
```powershell
pytest -v
```

**Results**: All 60 tests pass deterministically (covering authentication boundaries, SSRF prevention, decision trees Cases A–E, recovery verification Case F, token replay prevention, device telemetry, Bolna contracts, and AI interpretation core).

---

## Hardware Sentinel (ESP32) Setup

The firmware in `firmware/relay_esp32/relay_esp32.ino` connects to your local Jio Router Wi-Fi access point and sends periodic heartbeats containing Wi-Fi RSSI, uptime, and memory statistics.

### Verified Compilation
The firmware has been compiled and validated using `arduino-cli` with the official Espressif ESP32 core:
```powershell
arduino-cli compile --fqbn esp32:esp32:esp32 firmware/relay_esp32
```
*Result: 941,403 bytes (71% flash), 46,608 bytes dynamic memory, 0 compilation errors.*

To flash your physical board:
```powershell
arduino-cli upload -p COM3 --fqbn esp32:esp32:esp32 firmware/relay_esp32
```

See [docs/hardware-setup.md](docs/hardware-setup.md) for full circuit and TLS configuration details.

---

## Bolna Voice AI Integration

RELAY exposes 4 custom function tools compatible with Bolna's tool calling specifications:
- `diagnose_network(site_id, user_report)`
- `get_incident_status(incident_id)`
- `propose_recovery(incident_id, action_type)`
- `execute_approved_recovery(action_id, approval_token)`

Ready-to-copy JSON definitions and webhook instructions are documented in [docs/bolna-integration.md](docs/bolna-integration.md).

You can also test the full conversational experience without live telephony using the **Voice Console** tab in the web dashboard.

---

## Reproducing the Demo

Follow the step-by-step instructions in [docs/demo-runbook.md](docs/demo-runbook.md) to reproduce:
1. Baseline healthy diagnostic run.
2. Injected simulated DNS fault.
3. Voice AI complaint reporting: *"The billing application is not loading"*.
4. Deterministic diagnosis distinguishing facts from hypotheses.
5. Authorized recovery using single-use approval token.
6. Post-action verification confirming resolution.
7. Verification failure handling (Case F: never reporting false success).

---

## Security Model Summary

- **Secrets**: Kept in environment variables, never committed to source.
- **SSRF**: Strictly allowlisted targets with hostname and scheme validation.
- **Approvals**: Cryptographically signed tokens with expiring TTL and atomic single-use consumption.
- **No Arbitrary Execution**: Zero user-controlled shell or command execution.
- **Safe Recoveries**: Router configuration is never altered; recovery actions run through vetted adapters.

See [docs/security.md](docs/security.md) for the complete threat model.
