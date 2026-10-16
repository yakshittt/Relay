# Bolna Voice AI Agent Integration Guide

## Overview

RELAY integrates with [Bolna](https://www.bolna.ai/) through Bolna's official Custom Function Tool Calling mechanism. The voice model acts as a natural-language conversational interface that queries the deterministic diagnostic backend, explains evidence to non-technical users, requests explicit approval for recovery, and announces verified recovery.

The voice agent is strictly prohibited from inventing arbitrary shell commands or router mutations.

---

## 1. Exposing the Backend over Public HTTPS

Bolna cloud telephony requires an HTTPS endpoint accessible from the internet.

### Option A: Using ngrok (Development / private testing)
```bash
# In a separate terminal
ngrok http 8000
```
Note the assigned URL, e.g., `https://abc-123.ngrok-free.app`.

### Option B: Cloudflare Tunnel (Free & stable)
```bash
cloudflared tunnel --url http://localhost:8000
```

---

## 2. Bolna Custom Function Schemas

In the **Bolna Agent Builder** &rarr; **Tools** &rarr; **Add Custom Tool**, add the following 4 tools. Replace `YOUR_HTTPS_HOST` with your tunnel host and `YOUR_RELAY_API_TOKEN` with your configured token.

### Tool 1: `diagnose_network`
```json
{
  "name": "diagnose_network",
  "description": "Run real network diagnostic probes on a physical business location. Use when the caller reports connectivity issues, slow Wi-Fi, or application failures.",
  "pre_call_message": "Checking local gateway reachability, DNS resolution, and hardware sentinel status...",
  "parameters": {
    "type": "object",
    "properties": {
      "site_id": {
        "type": "string",
        "description": "Site identifier (default: jio-lab)",
        "default": "jio-lab"
      },
      "user_report": {
        "type": "string",
        "description": "Exact problem reported by the caller in natural language"
      }
    },
    "required": ["site_id", "user_report"]
  },
  "key": "custom_task",
  "value": {
    "method": "POST",
    "url": "https://YOUR_HTTPS_HOST/v1/tools/diagnose",
    "param": {
      "site_id": "%(site_id)s",
      "user_report": "%(user_report)s"
    },
    "api_token": "Bearer YOUR_RELAY_API_TOKEN",
    "headers": {
      "Content-Type": "application/json"
    }
  }
}
```

### Tool 2: `get_incident_status`
```json
{
  "name": "get_incident_status",
  "description": "Retrieve current status, timeline, and probe evidence for an existing incident by ID.",
  "pre_call_message": "Looking up incident records...",
  "parameters": {
    "type": "object",
    "properties": {
      "incident_id": {
        "type": "integer",
        "description": "The unique numerical incident ID"
      }
    },
    "required": ["incident_id"]
  },
  "key": "custom_task",
  "value": {
    "method": "GET",
    "url": "https://YOUR_HTTPS_HOST/v1/tools/incidents/%(incident_id)s",
    "param": {},
    "api_token": "Bearer YOUR_RELAY_API_TOKEN",
    "headers": {
      "Content-Type": "application/json"
    }
  }
}
```

### Tool 3: `propose_recovery`
```json
{
  "name": "propose_recovery",
  "description": "Propose an allowlisted recovery action for an active incident. Returns impact description and approval token. Always explain impact to the caller before asking for confirmation.",
  "pre_call_message": "Formulating safe recovery plan and requesting approval token...",
  "parameters": {
    "type": "object",
    "properties": {
      "incident_id": {
        "type": "integer",
        "description": "ID of the incident requiring recovery"
      },
      "action_type": {
        "type": "string",
        "description": "Allowlisted action type",
        "enum": ["clear_demo_dns_fault", "flush_dns_cache_simulated", "switch_failover_dns_simulated"]
      }
    },
    "required": ["incident_id", "action_type"]
  },
  "key": "custom_task",
  "value": {
    "method": "POST",
    "url": "https://YOUR_HTTPS_HOST/v1/tools/recovery/propose",
    "param": {
      "incident_id": "%(incident_id)s",
      "action_type": "%(action_type)s"
    },
    "api_token": "Bearer YOUR_RELAY_API_TOKEN",
    "headers": {
      "Content-Type": "application/json"
    }
  }
}
```

### Tool 4: `execute_approved_recovery`
```json
{
  "name": "execute_approved_recovery",
  "description": "Execute an authorized recovery action using the single-use approval token. Automatically runs post-action verification to verify if the issue was actually resolved.",
  "pre_call_message": "Executing authorized recovery and running verification probes...",
  "parameters": {
    "type": "object",
    "properties": {
      "action_id": {
        "type": "string",
        "description": "The action ID to execute"
      },
      "approval_token": {
        "type": "string",
        "description": "The single-use cryptographically verified approval token"
      }
    },
    "required": ["action_id", "approval_token"]
  },
  "key": "custom_task",
  "value": {
    "method": "POST",
    "url": "https://YOUR_HTTPS_HOST/v1/tools/recovery/execute",
    "param": {
      "action_id": "%(action_id)s",
      "approval_token": "%(approval_token)s"
    },
    "api_token": "Bearer YOUR_RELAY_API_TOKEN",
    "headers": {
      "Content-Type": "application/json"
    }
  }
}
```

---

## 3. Testing with curl

### A. Test Diagnostic Trigger
```bash
curl -X POST http://127.0.0.1:8000/v1/tools/diagnose \
  -H "Authorization: Bearer relay-dev-token-secret-2026" \
  -H "Content-Type: application/json" \
  -d '{"site_id":"jio-lab","user_report":"The billing application is not loading"}'
```

### B. Propose Recovery
```bash
curl -X POST http://127.0.0.1:8000/v1/tools/recovery/propose \
  -H "Authorization: Bearer relay-dev-token-secret-2026" \
  -H "Content-Type: application/json" \
  -d '{"incident_id": 1, "action_type": "clear_demo_dns_fault"}'
```

### C. Execute with Single-Use Approval Token
```bash
curl -X POST http://127.0.0.1:8000/v1/tools/recovery/execute \
  -H "Authorization: Bearer relay-dev-token-secret-2026" \
  -H "Content-Type: application/json" \
  -d '{"action_id": "act_YOUR_ACTION_ID", "approval_token": "apr_YOUR_APPROVAL_TOKEN"}'
```

---

## 4. Deterministic Local Voice Simulator (No Bolna Account Required)

If you do not have active Bolna credits or telephony phone numbers, RELAY includes a complete local voice simulator:

1. Open the **Voice Console** tab in the operations dashboard (`http://localhost:5173`).
2. Type or speak queries like:
   - *"The billing application is not loading."*
   - *"Is the local gateway reachable?"*
   - *"Yes, please proceed with the fix."*
3. The simulator invokes the real backend tools (`/v1/bolna/voice-simulate`), traces the executed tool calls, formats voice responses distinguishing facts from hypotheses, and synthesizes speech using the browser's native Web Speech API.
