# RELAY End-to-End Demo Runbook

This runbook guides an operator or evaluator through reproducing the full end-to-end incident resolution workflow on a local machine.

---

## 1. Prerequisites & Startup

### Start Backend
In terminal 1:
```powershell
# From project root
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
Verify: Open `http://127.0.0.1:8000/health` &rarr; Returns `{"ok": true, "service": "relay-api"}`.

### Start Frontend
In terminal 2:
```powershell
cd frontend
npm run dev
```
Verify: Open `http://localhost:5173` in your browser. The Operations Console will appear with a green **"API Connected"** badge.

---

## 2. Scenario 1: Baseline Healthy Check

1. In the console, navigate to the **Overview** tab.
2. In the "Trigger On-Demand Diagnostic Probe" card, keep the default report: *"Routine health verification"*.
3. Click **Run Diagnostic**.
4. Observe the results:
   - Overall Status: **HEALTHY**.
   - Probes: Gateway Reachability, DNS Resolution, HTTPS Egress, and Business Endpoint all show green **HEALTHY** status badges.
   - Classification: *"All automated diagnostic checks passed"*.

---

## 3. Scenario 2: Main Story (Voice Incident Report & Verified Resolution)

### Step 1: Inject the Simulated Service Fault
1. Navigate to the **Playground** tab (`http://localhost:5173`).
2. Under "1. Select Simulated Network Fault Scenarios", click **Inject Fault** next to **Business Hostname DNS Failure**.
3. Notice the purple **"DEMO MODE ACTIVE"** indicator and fault badge.

### Step 2: User Reports Issue via Voice AI
1. Click the **Voice Console** tab.
2. In the message box (or by clicking the quick prompt), enter:
   > *"The billing application is not loading."*
3. Click **Send**.

### Step 3: RELAY Diagnoses and Explains Evidence
1. Observe the visualizer waveform indicating agent processing.
2. The agent executes `diagnose_network` behind the scenes.
3. The agent responds in speech and text:
   > *"I ran site diagnostics for incident #... Overall health is degraded. A controlled simulation is actively injecting a service degradation... Gateway responded successfully, but DNS name resolution failed. Recommended action: Propose the allowlisted demo recovery action..."*
4. Notice how the agent distinguishes **confirmed facts** (Gateway responds, DNS failed) from **hypotheses** (resolver failure).

### Step 4: Authorize and Execute Recovery
1. The agent asks for approval. Reply in the Voice Console:
   > *"Yes, I approve the recovery action."*
2. The agent executes `execute_approved_recovery`:
   - Validates the single-use cryptographic approval token.
   - Atomically consumes the token to prevent replay attacks.
   - Executes the allowlisted adapter to clear the simulated fault.
   - **Immediately triggers post-action verification probes**.

### Step 5: Post-Action Verification Confirmed
1. The voice agent verifies that all 4 probes now pass and announces:
   > *"Recovery action ... was successfully executed. I reran the diagnostic probes, and verification confirmed: Verified recovery: All 4 probes passed. The issue has been verified as resolved."*
2. Navigate to **Site Lab** or **Overview** &rarr; Open the incident.
3. Inspect the **Incident Audit Timeline**:
   - `INCIDENT_CREATED`
   - `RECOVERY_PROPOSED`
   - `ACTION_EXECUTING`
   - `RECOVERY_VERIFIED`

---

## 4. Scenario 3: Case F — Verification Failure (Never Claiming False Success)

1. In the **Playground** tab, inject **Gateway Packet Loss**.
2. Click **Run Diagnostic Probes**.
3. Status becomes **FAILED** (Case B: Gateway Unreachable).
4. Click **Propose Authorized Recovery** &rarr; Authorize execution of `clear_demo_dns_fault`.
5. Notice that because the gateway fault is still active, post-action verification fails!
6. The modal displays:
   > **"Post-Action Verification Failed: Checks are still failing after execution. RELAY will not falsely report resolution."**
7. The incident remains **UNRESOLVED** in the database.

---

## 5. Automated Regression Test Run

To verify all 35 test cases programmatically at any time:
```powershell
pytest -v
```
All tests will complete with 100% pass rate in ~10 seconds.
