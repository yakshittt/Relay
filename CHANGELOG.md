# Changelog

All notable changes to the RELAY project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned (Milestone 3: Multi-Site & Voice Telephony Bridge)
- Multi-turn conversational diagnostics with server-bounded tool execution.
- End-to-end multi-site evaluation and Bolna telephony tool bridge update.

---

## [0.3.0] - 2026-10-17 (Milestone 2: Operations Console Frontend Integration)

### Added
- **AI Interpretation UI Card** (`frontend/src/views/IncidentDetailView.tsx`):
  - Placed prominently between Caller Problem Statement and Confirmed Measured Facts.
  - Explicit **Generate interpretation** trigger preventing unwanted automatic API calls.
  - In-component state retention for interpreted incident explanations.
  - Error alert with interactive **Retry** action.
  - In-context **Ask AI** query form for operator clarifying questions.
  - Clear **Deterministic Fallback Engaged** banner when `fallback_used === true`.
  - Prominent visual demarcation of `unverified_model_claim` with an alert pill separate from server-verified probe citations (`probe:*`, `device:*`).
  - Active AI provider badge displaying provider identity (`mock`, `openai`, `mock:fallback`).
- **Follow-up Interaction & Decoupled Loading States** (`frontend/src/views/IncidentDetailView.tsx`):
  - Separated initial generation loading (`aiLoading`) from follow-up query execution (`aiQuerying`), keeping existing interpretation, citations, and probe evidence visible while follow-up questions are processed.
  - Added in-flight status indicator (`Processing follow-up query: "..."`) with inline loading spinner.
  - Input field automatically resets on successful response while retaining the active question badge (`Follow-up query: "..."` with `[Answered]` indicator).
  - Preserved operator input on query failure with retry support.
- **Typed Frontend Contracts** (`frontend/src/types.ts`): Added `GroundedFact`, `AIInterpretation`, and `AIInterpretationResponse` matching backend schemas.
- **Typed API Client Function** (`frontend/src/api.ts`): Added `interpretIncident(incidentId: number, userQuery?: string, signal?: AbortSignal)`.
- **Concurrency & Race Condition Guards** (`frontend/src/views/IncidentDetailView.tsx`):
  - `AbortController` signal forwarding to abort in-flight requests on incident switch.
  - Active incident ID tracking via `currentIncidentIdRef` to discard stale in-flight responses.
  - Synchronous guards in both `onSubmit` and `handleGenerateInterpretation` preventing duplicate simultaneous submissions.
- **Strict Boundary Preservation**: Deterministic RCA, probe matrix, single-use approval-token modal, and post-action verification remain authoritative and unchanged. The AI card contains zero action execution authority.

### Verified
- **TypeScript & Frontend Build**: Executed `npm run build` (`tsc -b && vite build`) producing clean production bundle in 413ms with 0 errors.
- **Linter**: Executed `npm run lint` (`oxlint`) with 0 errors across 14 frontend files (10 pre-existing framework warnings).
- **Backend Test Suite**: Full regression suite (60 tests) passed in 9.14s with pytest 8.4.2 (100% pass rate).

### Status & Remaining Limitations
- **Ask AI Follow-Up UI Verification**: The backend endpoint returns HTTP 200 responses to follow-up queries, and form submission logic is wired to both keyboard Enter and button click. However, the interactive response-to-UI update behavior has not been fully verified in a live operator browser session. Local debugging was intentionally deferred as local self-hosting is not planned.
- **No Component Test Framework**: The frontend repository does not include an automated component-testing library (e.g. Vitest, React Testing Library); verification is strictly based on TypeScript compilation (`tsc -b`), production Vite bundling, and Oxlint.
- **Live LLM Provider Unverified**: Live upstream connectivity has not been verified against a real OpenAI-compatible endpoint with valid API keys. All automated tests run offline against deterministic mock providers or mocked HTTP transports.
- **Preserved Baseline Workflows**: Physical ESP32 hardware telemetry, live Bolna voice telephony bridging, and live router recovery execution remain architecturally unchanged and tested by baseline unit tests, but were not re-validated in a live physical deployment during this AI feature pass.

---

## [0.2.0] - 2026-10-17 (Milestone 1: AI Incident Interpretation Service & Provider Abstraction)

### Added
- **Provider Abstraction** (`app/services/ai/providers.py`): Decoupled `LLMProvider` interface with offline, deterministic `MockLLMProvider` and configurable `OpenAICompatibleProvider`.
- **Grounded Interpretation Service** (`app/services/ai/interpreter.py`): Evidence-grounded incident interpretation service with source validation, targeted secret redaction, and automatic fallback to deterministic rule synthesis.
- **Typed Data Contracts** (`app/schemas.py`): Added `GroundedFact`, `AIInterpretation`, `AIInterpretationRequest`, and `AIInterpretationResponse` Pydantic models.
- **API Endpoint** (`POST /v1/ai/interpret` in `app/main.py`): Bearer-authenticated endpoint returning evidence-grounded incident explanations with fallback status.
- **Configuration** (`app/config.py`, `.env.example`): Added `AI_PROVIDER` (default `"mock"`), `AI_MODEL`, `AI_API_KEY`, `AI_API_BASE_URL`, and `AI_REQUEST_TIMEOUT_SECONDS`.
- **Automated Test Suite** (`tests/test_ai_agent.py`): 25 comprehensive unit and integration tests.

### Security Remediation (Findings F-01 through F-04)
- **F-01 (Provider HTTP Unit Tests)**: Added offline mocked HTTP unit tests for `OpenAICompatibleProvider` covering HTTP 200 payload parsing, HTTP 500 error mapping, timeouts, empty choices, and empty content.
- **F-02 (Malformed Evidence Resilience)**: Defensively handled stored incidents with missing, null, or corrupted probe checks/devices, preventing unhandled `TypeError` exceptions and safely returning deterministic fallbacks.
- **F-03 (Comprehensive Field Redaction)**: Applied secret and token redaction across all returned fields (`summary`, `diagnostic_hypothesis`, `recommended_action`, `uncertainty_caveats`, and `grounded_facts[].statement`).
- **F-04 (AI API Key Redaction)**: Extended `_sanitize_for_prompt` to include configured `ai_api_key`, preventing live LLM credential forwarding into prompts or responses.

### Verified
- **Full Test Suite**: All 60 tests passed in 10.00s on Python 3.11.9 with pytest 8.4.2 (35 existing regression tests + 25 AI tests, 100% pass rate).
- **Frontend Build**: Verified production build (`tsc -b && vite build`) finishes cleanly with 0 errors in 344ms.



## [0.1.0] - 2026-10-17 (Milestone 0: Baseline Verification)

### Added
- Created root `CHANGELOG.md` to track project evolution and auditable changes.
- Created `docs/ai/decisions.md` documenting architecture decisions (ADR-001 through ADR-003), verified baseline facts, AI development roadmap, and design constraints.
- Dedicated Python 3.11 virtual environment (`.venv`) configured with dependencies from `requirements.txt`.
- Frontend dependencies installed cleanly via `npm ci` from existing `frontend/package-lock.json`.

### Verified
- **Backend Tests**: Executed `pytest -v` within `.venv` (Python 3.11.9, pytest 8.4.2). 35 tests passed in 12.69s covering authentication, SSRF protection, Cases A through F, recovery approvals, and Bolna contracts.
- **Frontend Build**: Executed `npm run build` (`tsc -b && vite build`) in `frontend/`. Bundle produced cleanly (dist/index.html, dist/assets) in 1.58s with zero errors.
- **Git State**: Verified execution on feature branch `feat/ai-incident-agent`.
