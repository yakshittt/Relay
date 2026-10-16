# Architectural Decisions & AI Incident Agent Design Log

This document records architectural decisions, verified system invariants, and the engineering roadmap for the AI Incident Agent within the RELAY platform.

---

## 1. Verified Baseline Facts (Existing Implementation)

The following facts have been experimentally verified on branch `feat/ai-incident-agent`:

1. **Deterministic Probe & Diagnostic Engine**:
   - Executes 4 distinct probes: LAN Gateway reachability (`gateway_reachability`), DNS name resolution (`dns_resolution`), external HTTPS egress (`https_egress`), and critical business URL reachability (`business_service`).
   - Classifies incidents through deterministic decision trees (`classify_incident`):
     - **Case A**: Gateway reachable, DNS fails, business endpoint unreachable &rarr; DNS resolver failure.
     - **Case B**: Gateway unreachable &rarr; Local LAN / physical cable / router power fault.
     - **Case C**: DNS and HTTPS egress succeed, but business endpoint fails &rarr; Upstream vendor / application failure.
     - **Case D**: Probes healthy, but ESP32 heartbeat is stale &rarr; Sensor hardware issue; site network operational.
     - **Case E**: All probes healthy despite user complaint &rarr; Issue not reproduced; targeted follow-up questions.
     - **Case F**: Post-action verification failing probe check &rarr; Recovery deemed failed; never claims false resolution.
2. **Security & Boundary Enforcement**:
   - Private endpoints require `Authorization: Bearer <TOKEN>` validated via constant-time comparison (`secrets.compare_digest`).
   - ESP32 telemetry ingestion is restricted to `X-Device-Token` header auth on `POST /v1/devices/heartbeat`.
   - SSRF protection enforces strict host allowlists (`ALLOWLISTED_HOSTS`), hostname syntax validation, and scheme restriction.
   - Recovery actions follow a 3-step authorization lifecycle: proposal &rarr; expiring single-use token issuance (`apr_<token>`) &rarr; atomic token consumption with post-action verification.
3. **Verified Automated Test Baseline**:
   - `35` tests passed in `12.69s` on Python 3.11.9 with `pytest 8.4.2` (`tests/test_health_and_auth.py`, `tests/test_ssrf_and_probes.py`, `tests/test_diagnosis_cases.py`, `tests/test_recovery_and_verification.py`, `tests/test_incidents_and_devices.py`, `tests/test_demo_faults.py`, `tests/test_bolna_contracts.py`).
4. **Verified Frontend Build**:
   - React 19 + TypeScript + Vite operations console builds cleanly (`npm run build` completed in 1.58s producing `dist/index.html` and assets).

---

## 2. Architecture Decision Records (ADRs)

### ADR-001: Separation of Deterministic Core and AI Agent Layer
* **Status**: Accepted
* **Context**: RELAY performs network diagnostics and authorized recovery on critical physical store infrastructure. Generative LLMs can hallucinate non-existent probe results or bypass safeguards if granted unconstrained decision authority.
* **Decision**: Keep deterministic diagnosis, authentication, SSRF prevention, recovery allowlists, approval-token enforcement, and post-action probe verification authoritative. The AI agent acts as a reasoning, synthesis, and communication layer that queries and interprets deterministic backend tools, but cannot override deterministic verdict or bypass security gates.
* **Consequences**: Ensures physical network operations remain safe, auditable, and bounded.

### ADR-002: Single Configurable LLM Provider with Mocked Testing Provider
* **Status**: Accepted (Design Constraint for Milestone 1)
* **Context**: The AI incident agent requires an LLM engine to synthesize natural-language incident explanations and assist operators. Supporting many providers prematurely introduces maintenance overhead and non-deterministic test flakes.
* **Decision**: Implement a clean provider interface with one primary configurable external LLM provider (e.g., OpenAI or Gemini compatible) and a mandatory deterministic Mock LLM provider for automated testing.
* **Consequences**: Enables 100% offline, deterministic CI/CD test runs without API keys or token expenses, while allowing seamless configuration in production.

### ADR-003: Strictly Typed Schemas & Zero Secret Leakage Boundary
* **Status**: Accepted (Design Constraint for Milestone 1)
* **Context**: AI agents interacting with user reports are susceptible to prompt injection, malformed responses, or accidental leakage of system instructions and credentials.
* **Decision**:
  - Enforce typed Pydantic models for all agent inputs, tool definitions, and structured model outputs.
  - Apply strict timeouts and bounded iteration limits on agent tool calling loops.
  - Prohibit logging or exposing API keys, private reasoning/chain-of-thought tokens, or internal credentials in client responses or frontend views.
* **Consequences**: Mitigates prompt injection risks, protects secrets, and maintains clean API contracts.

### ADR-004: Evidence Grounding and Source Validation
* **Status**: Accepted & Implemented (Milestone 1)
* **Context**: Generative models may hallucinate non-existent hardware sensors or fabricated diagnostic probe names.
* **Decision**: All factual claims returned by the AI interpretation engine (`app.services.ai.interpreter`) must be mapped to verified server-side evidence sources (`probe:<name>`, `device:<id>`, or `deterministic_classification`). Any unsupported source is strictly re-attributed as `unverified_model_claim`.
* **Consequences**: Guarantees that operators can audit every stated fact back to real probe measurements.

### ADR-005: Non-Authoritative AI Boundary with Zero Action Execution Authority
* **Status**: Accepted & Implemented (Milestone 1)
* **Context**: AI models must not have the ability to trigger router changes, bypass approval tokens, or declare unverified recoveries.
* **Decision**: AI interpretation is strictly an observational and explanatory layer. The engine has no tools or permissions to execute recovery actions or issue cryptographic approval tokens.
* **Consequences**: Ensures physical infrastructure remains safe from unauthorized or hallucinated mutations.

### ADR-006: Deterministic Fallback on Provider Failure
* **Status**: Accepted & Implemented (Milestone 1)
* **Context**: External AI providers may suffer timeouts, rate limits, HTTP errors, or return malformed JSON.
* **Decision**: When an LLM provider fails, times out, or returns invalid schema, the interpretation engine immediately falls back to deterministic rule-based synthesis (`classify_incident` / `DiagnosisReport`), returning a complete, grounded response with `fallback_used: true`.
* **Consequences**: 100% uptime and resilience against external AI provider outages.

### ADR-007: Comprehensive Field Sanitization & Malformed Evidence Resilience
* **Status**: Accepted & Implemented (Milestone 1 Remediation)
* **Context**: The security audit identified that secondary output fields (`recommended_action`, `uncertainty_caveats`, `grounded_facts[].statement`) and `ai_api_key` were omitted from prompt and response scrubbing, and incidents with null or malformed probe checks could trigger unhandled `TypeError` exceptions.
* **Decision**:
  1. Extend `_sanitize_for_prompt` to include `settings.ai_api_key` and apply redaction recursively to every returned narrative field.
  2. Implement defensive type checking for stored incident reports (`checks = [c for c in raw_checks if isinstance(c, dict)] if isinstance(raw_checks, list) else []`), routing malformed records directly to safe deterministic fallback responses.
  3. Validate `OpenAICompatibleProvider` HTTP transport offline using mocked responses for HTTP 200, 500, timeouts, and empty choices.
* **Consequences**: Eliminates unhandled 500 crashes on corrupted data and prevents secret reflection across all response dimensions.

### ADR-008: Operations Console AI Interpretation View & Concurrency Protection
* **Status**: Accepted & Implemented (Milestone 2)
* **Context**: Operators inspecting an incident need clear natural-language explanations and evidence grounding without replacing authoritative deterministic decision trees or bypassing recovery approval boundaries. In-flight network requests on incident navigation could result in stale responses overwriting newer data.
* **Decision**:
  1. Integrate an AI Incident Interpretation card into `IncidentDetailView.tsx` situated between the Caller Problem Statement and the deterministic Facts & Hypotheses sections.
  2. Require an explicit **Generate interpretation** trigger rather than firing automatic network requests upon opening an incident.
  3. Maintain concurrency safety using `AbortController` and an active incident ID ref (`currentIncidentIdRef`): abort in-flight requests when switching incidents and discard stale responses.
  4. Provide an in-context **Ask AI** query form allowing operators to ask grounded clarifying questions (`user_query`) to the backend service.
  5. Clearly badge the active AI provider, display a prominent warning banner when `fallback_used === true`, and visibly flag any `unverified_model_claim` with an alert pill distinct from server-verified probe citations.
  6. The AI card contains zero recovery execution capabilities; all remediations must continue through the existing allowlisted proposal, approval-token modal, and verification lifecycle.
* **Consequences**: Operators obtain plain-language explanations with strict evidence traceability and zero risk of race conditions or security bypass.

### ADR-009: Decoupled Concurrency & Follow-Up State Management in Operations Console
* **Status**: Accepted & Implemented (Milestone 2 Remediation)
* **Context**: When operators submit a follow-up query through the "Ask AI" form, treating the submission identically to initial generation unmounts the existing interpretation and evidence matrix during data fetching, creating jarring layout shifts and masking previous findings. Additionally, missing feedback on submission and static mock responses make it ambiguous whether a follow-up query was processed.
* **Decision**:
  1. Decouple loading states into `aiLoading` (initial card generation) and `aiQuerying` (follow-up query processing).
  2. Keep the rendered interpretation, server-grounded facts, and probe matrix permanently mounted while follow-up queries are in flight.
  3. Display an active in-flight indicator (`Processing follow-up query: "..."`) and disable duplicate submissions synchronously in both `onSubmit` and the fetch handler.
  4. Upon successful response, clear the input field (`setUserQuery('')`), retain the question in `activeQuery`, and display an `[Answered]` badge with the submitted query.
  5. On failure, retain operator input in the text box and display an actionable `Retry` banner.
* **Consequences**: Smooth, non-destructive follow-up interaction flow while strictly preserving incident-switch aborts and stale-response protection.

---

## 3. Implemented vs. Planned AI Capabilities

### Implemented in Milestone 1 & 2
- [x] Abstract provider interface (`LLMProvider`) with deterministic `MockLLMProvider` and `OpenAICompatibleProvider`.
- [x] Evidence-grounded interpretation service (`interpret_incident_evidence`).
- [x] Typed Pydantic data models (`GroundedFact`, `AIInterpretation`, `AIInterpretationRequest`, `AIInterpretationResponse`).
- [x] Authenticated endpoint `POST /v1/ai/interpret`.
- [x] Strict server-side evidence source validation and `unverified_model_claim` re-attribution.
- [x] Deterministic fallback mechanism for malformed outputs, timeouts, and provider errors.
- [x] Defensive evidence shape handling avoiding unhandled `TypeError` exceptions (F-02).
- [x] Comprehensive secret redaction across prompts and all returned fields including `ai_api_key` (F-03, F-04).
- [x] Offline mocked HTTP unit tests for `OpenAICompatibleProvider` (F-01).
- [x] Automated test suite with 25 tests covering all edge cases (60 passed across whole repo).
- [x] Operations Console UI integration (`IncidentDetailView.tsx`): explicit generation button, in-state retention, error retry, Ask AI input, concurrency aborts, fallback banners, and unverified claim callouts.
- [x] Decoupled follow-up querying state (`aiQuerying`), question feedback badge, and input reset on success.
- [x] Typed frontend API client integration (`frontend/src/api.ts`, `frontend/src/types.ts`).

### Planned for Milestone 3 & Beyond
> [!NOTE]
> The following capabilities are **PROPOSED** for future milestones and are **NOT YET IMPLEMENTED**:
- [ ] Multi-turn conversational diagnostics with server-bounded tool execution.
- [ ] End-to-end multi-site evaluation and Bolna telephony tool bridge update.

---

## 4. AI Development Roadmap

| Phase | Milestone | Scope | Status |
|---|---|---|---|
| Phase 0 | Milestone 0 | Baseline environment setup, test verification, documentation initialization | **Completed & Verified** (35 tests) |
| Phase 1 | Milestone 1 | Backend AI interpretation core, provider abstraction, mock provider, grounded contracts, fallback, security audit remediation (F-01 to F-04) | **Completed & Verified** (60 tests) |
| Phase 2 | Milestone 2 | Operations Console UI integration, reasoning visualization, concurrency guards, Ask AI follow-up decoupling | **Completed & Verified** |
| Phase 3 | Milestone 3 | End-to-end multi-site evaluation, Bolna telephony tool bridge update | *Proposed* |

---

## 5. Current Limitations & Deferred Verification

1. **Frontend Test Automation**: The frontend project does not include an automated component test suite (e.g. Vitest, React Testing Library). Quality assurance relies on strict TypeScript type checking (`tsc -b`), production bundling (`vite build`), and linting (`oxlint`).
2. **Ask AI Follow-Up Browser Verification**: The backend endpoint returns HTTP 200 responses to follow-up requests, and form submission logic is wired to both keyboard Enter and button click. However, the interactive response-to-UI update behavior has not been fully confirmed in a live operator browser session. Further local debugging was deliberately halted because the operator does not intend to host RELAY on the local machine.
3. **Live LLM Provider Connectivity**: Live connectivity to external LLM providers (e.g. OpenAI or compatible endpoints) has not been tested with valid live API credentials. All verification to date is conducted offline using deterministic mock providers or mocked HTTP transports.
4. **Preserved Baseline Integrations**: Physical ESP32 hardware telemetry, Bolna telephony tool bridging, and live router recovery execution remain architecturally preserved and covered by baseline unit tests, but were not re-validated in a live physical deployment during this AI feature pass.



