# RELAY — voice-native incident resolution (starter)

This is a small, local-first prototype skeleton for a Bolna voice agent that calls a deterministic diagnostics API. The LLM must never directly execute shell commands or receive arbitrary router credentials.

## What works in this starter

- FastAPI service with bearer-token-protected endpoints.
- DNS and HTTPS probes from the machine running this API.
- A configurable business endpoint check.
- SQLite incident history.
- ESP32 HTTP heartbeat endpoint and Arduino sketch.
- Demo-only DNS fault injection and an allowlisted simulated recovery action.
- An explicit `user_confirmed` guard on the simulated recovery endpoint.

**The demo recovery does not touch Jio router settings, operating-system DNS, or any external service.** Do not expose demo controls publicly. This starter is a scaffold, not a production network management agent.

## 1. Run it locally

Use Python 3.11+.

```bash
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env
```

Set a fresh long token in `.env` for `RELAY_API_TOKEN` and `DEVICE_TOKEN`. The service loads `.env` automatically. You can also override values in your shell. For a quick local session:

```bash
# macOS/Linux shell example
export RELAY_API_TOKEN='replace-with-a-long-random-value'
export DEVICE_TOKEN='replace-with-another-long-random-value'
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Windows PowerShell:

```powershell
$env:RELAY_API_TOKEN = 'replace-with-a-long-random-value'
$env:DEVICE_TOKEN = 'replace-with-another-long-random-value'
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open `http://127.0.0.1:8000/docs`. Use the `Authorize` button and enter the API token as the bearer credential. `/health` is unauthenticated for local health checks.

## 2. Try diagnosis

```bash
curl -X POST http://127.0.0.1:8000/v1/tools/diagnose \
  -H 'Authorization: Bearer replace-with-a-long-random-value' \
  -H 'Content-Type: application/json' \
  -d '{"site_id":"jio-lab","user_report":"Billing app is not loading"}'
```

The returned JSON contains `incident_id`, `status`, `diagnosis`, `recommended_next_step`, evidence for each check, and ESP32 heartbeat state. Diagnostics run from the API host, so connect the laptop to the Jio router for the first lab test.

## 3. Run a deterministic fault demo

Use the interactive docs or `curl` to call `POST /v1/demo/faults/dns` with the bearer token. Then call `/v1/tools/diagnose` again. The business-service check will show an intentionally injected failure. This is deliberately an application-level demo fault, not a real router DNS mutation.

To clear it by invoking the controlled recovery endpoint, use the incident ID from the faulty diagnosis:

```bash
curl -X POST http://127.0.0.1:8000/v1/tools/recover \
  -H 'Authorization: Bearer replace-with-a-long-random-value' \
  -H 'Content-Type: application/json' \
  -d '{"incident_id":1,"action":"clear_demo_dns_fault","user_confirmed":true}'
```

Only the allowlisted simulated action is implemented. A true production design needs a separately authenticated action executor, short-lived approval tokens, audit records, per-site authorization, rollback, and exact verification checks.

## 4. ESP32 heartbeat

Install the `ArduinoJson` library in Arduino IDE. Open `firmware/relay_esp32.ino` and set Wi-Fi credentials, `API_BASE_URL` to the laptop's LAN IP, and `DEVICE_TOKEN` to match the backend. The laptop IP and router gateway vary; do not assume a particular Jio model/IP range. Make sure laptop firewall rules allow TCP 8000 only on your trusted test LAN. The sketch uses plain HTTP for LAN prototyping only; use TLS and unique per-device credentials in any deployed device.

Example heartbeat payload:

```json
{"device_id":"esp32-lab-01","site_id":"jio-lab","wifi_rssi_dbm":-58,"uptime_seconds":120}
```

## 5. Add Bolna

In the Bolna agent builder, add a **Custom Function** that calls your publicly reachable HTTPS backend. Bolna documents custom tools using an OpenAI-style JSON schema plus `key: "custom_task"`, an HTTP `method`, `url`, request `param`, bearer `api_token`, and headers. See:

- https://www.bolna.ai/docs/tool-calling/introduction
- https://www.bolna.ai/docs/tool-calling/custom-function-calls
- https://www.bolna.ai/docs/tool-calling/custom-function-examples

Do not expose your laptop directly to the internet without HTTPS, authentication and rate limiting. For a quick private demo use an HTTPS tunnel and keep the API token secret. Better: deploy the API to a small cloud instance and run site diagnostics in a local edge agent that reports measurements outbound.

### Suggested first tool schema

Set `name=diagnose_network`, `key=custom_task`, `method=POST`, and URL to `https://YOUR-HTTPS-HOST/v1/tools/diagnose`. Add this JSON schema in Bolna's Custom Function editor:

```json
{
  "name": "diagnose_network",
  "description": "Use when the caller reports slow internet, Wi-Fi trouble, a business application not loading, or asks what has failed at the jio-lab site. Runs real diagnostic checks and returns evidence. Do not claim an issue is fixed unless verification confirms it.",
  "pre_call_message": "I’ll run the connectivity checks and inspect the latest device heartbeat.",
  "parameters": {
    "type": "object",
    "properties": {
      "site_id": {"type": "string", "description": "Site identifier; use jio-lab for the prototype."},
      "user_report": {"type": "string", "description": "Short description of the reported issue."}
    },
    "required": ["site_id", "user_report"]
  },
  "key": "custom_task",
  "value": {
    "method": "POST",
    "param": {"site_id": "%(site_id)s", "user_report": "%(user_report)s"},
    "url": "https://YOUR-HTTPS-HOST/v1/tools/diagnose",
    "api_token": "Bearer YOUR_RELAY_API_TOKEN",
    "headers": {"Content-Type": "application/json"}
  }
}
```

Bolna's custom-function parameters are submitted to your endpoint. Test with curl first, then add the function to the agent. For an early demo, expose only diagnosis and incident lookup. Do not offer recovery as a voice tool until your confirmation/authorization flow is tested end-to-end.

## 6. Project shape

```text
app/
  main.py          HTTP API, auth boundaries, Bolna tool endpoints
  diagnostics.py   deterministic probes + diagnosis classification
  storage.py       SQLite incident/heartbeat persistence
  schemas.py       validated request contracts
  config.py        environment configuration
firmware/
  relay_esp32.ino  ESP32 Wi-Fi heartbeat
 tests/
  test_classification.py
```

## Recommended next steps

1. Make local diagnosis repeatable before adding any LLM.
2. Add an adapter for the exact Jio router model only if its admin/API interface supports it; don't assume a generic router API exists.
3. Move device polling to an edge agent if the cloud cannot reach the private LAN.
4. Add an event timeline and one end-to-end scripted incident.
5. Add one allowlisted recovery at a time, with human approval, audit logging, rollback, and automated post-action verification.
6. Interview real shop/office operators before widening the product scope.
