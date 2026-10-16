"""LLM Provider abstractions and implementations for RELAY.
Provides an abstract base interface, a deterministic offline MockLLMProvider for tests,
and an OpenAICompatibleProvider for live production integration.
"""
from abc import ABC, abstractmethod
import json
import logging
from typing import Any, Callable, Dict, Optional
import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class LLMProviderError(RuntimeError):
    """Raised when an LLM provider encounters an upstream error or HTTP failure."""
    pass


class LLMProviderTimeoutError(LLMProviderError):
    """Raised when an LLM provider request exceeds the configured timeout."""
    pass


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Return the unique provider identifier (e.g., 'mock', 'openai')."""
        pass

    @abstractmethod
    def generate_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
    ) -> str:
        """Generate a raw text completion from system and user prompt strings.

        Args:
            system_prompt: The grounding system instructions.
            user_prompt: The user input and server-side evidence payload.
            temperature: Sampling temperature (default 0.0 for deterministic output).

        Returns:
            The raw text string returned by the provider.

        Raises:
            LLMProviderTimeoutError: If the request times out.
            LLMProviderError: If the provider fails.
        """
        pass


class MockLLMProvider(LLMProvider):
    """Deterministic, offline mock provider for automated tests and local development.
    Requires zero network access, credentials, or API keys.
    """

    def __init__(
        self,
        fixed_response: Optional[str] = None,
        should_timeout: bool = False,
        should_fail: bool = False,
        error_message: str = "Simulated upstream provider error",
        custom_handler: Optional[Callable[[str, str], str]] = None,
    ) -> None:
        self.fixed_response = fixed_response
        self.should_timeout = should_timeout
        self.should_fail = should_fail
        self.error_message = error_message
        self.custom_handler = custom_handler

    @property
    def provider_id(self) -> str:
        return "mock"

    def generate_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
    ) -> str:
        if self.should_timeout:
            raise LLMProviderTimeoutError("Mock provider simulated timeout after 10.0s")

        if self.should_fail:
            raise LLMProviderError(self.error_message)

        if self.custom_handler:
            return self.custom_handler(system_prompt, user_prompt)

        if self.fixed_response is not None:
            return self.fixed_response

        # Default deterministic behavior: synthesize structured response from user_prompt
        # Inspect user prompt for common incident contexts to return faithful grounded mock JSON
        user_lower = user_prompt.lower()

        if "gateway is unreachable" in user_lower or "gateway unresponsive" in user_lower:
            return json.dumps({
                "summary": "Local network gateway is unreachable over the LAN.",
                "grounded_facts": [
                    {
                        "source": "probe:gateway_reachability",
                        "statement": "TCP connection to gateway target timed out or failed.",
                    }
                ],
                "diagnostic_hypothesis": "Local LAN disconnection, cable failure, or router power loss.",
                "confidence": "HIGH",
                "recommended_action": "Verify the physical Ethernet cable, Wi-Fi connection, and Jio router power.",
                "uncertainty_caveats": [
                    "Cannot verify external internet status until local gateway connectivity is restored."
                ],
            })

        if "dns resolution failure" in user_lower or "name resolution failed" in user_lower or "dns outage" in user_lower:
            return json.dumps({
                "summary": "Local gateway is healthy, but DNS domain name resolution is failing.",
                "grounded_facts": [
                    {
                        "source": "probe:gateway_reachability",
                        "statement": "Gateway reached successfully over local LAN.",
                    },
                    {
                        "source": "probe:dns_resolution",
                        "statement": "Domain name resolution failed for target host.",
                    },
                ],
                "diagnostic_hypothesis": "Probable DNS resolver outage or upstream DNS misconfiguration.",
                "confidence": "HIGH",
                "recommended_action": "Verify router DNS settings or request authorization to flush DNS cache.",
                "uncertainty_caveats": [
                    "Direct IP reachability to public resolvers (e.g. 1.1.1.1) requires further probe verification."
                ],
            })

        if "isolated business service" in user_lower or "503" in user_lower:
            return json.dumps({
                "summary": "General internet egress is operating normally, but the business application endpoint is returning errors.",
                "grounded_facts": [
                    {
                        "source": "probe:https_egress",
                        "statement": "General internet HTTPS egress probe succeeded.",
                    },
                    {
                        "source": "probe:business_service",
                        "statement": "Business endpoint responded with HTTP service failure or timeout.",
                    },
                ],
                "diagnostic_hypothesis": "Isolated upstream application or vendor cloud outage.",
                "confidence": "HIGH",
                "recommended_action": "Inspect vendor cloud status page and application backend logs.",
                "uncertainty_caveats": [
                    "Verify if other physical locations are experiencing the same application outage."
                ],
            })

        if "monitoring sensor offline" in user_lower or "stale" in user_lower:
            return json.dumps({
                "summary": "Site network probes are healthy, but the ESP32 hardware monitor has stopped reporting telemetry.",
                "grounded_facts": [
                    {
                        "source": "probe:gateway_reachability",
                        "statement": "All site network probes passed.",
                    },
                    {
                        "source": "device:telemetry",
                        "statement": "ESP32 hardware heartbeat is past the stale threshold.",
                    },
                ],
                "diagnostic_hypothesis": "Hardware sensor is unplugged or powered down; site network is operational.",
                "confidence": "HIGH",
                "recommended_action": "Inspect physical power connection and status LEDs on the ESP32 board.",
                "uncertainty_caveats": [
                    "Network health is operational despite sensor absence."
                ],
            })

        # Generic healthy / all passing fallback
        return json.dumps({
            "summary": "All diagnostic probes passed. The reported issue was not reproduced by automated probes.",
            "grounded_facts": [
                {
                    "source": "probe:gateway_reachability",
                    "statement": "Gateway reachability probe passed.",
                },
                {
                    "source": "probe:dns_resolution",
                    "statement": "DNS resolution probe passed.",
                },
                {
                    "source": "probe:https_egress",
                    "statement": "External HTTPS egress probe passed.",
                },
                {
                    "source": "probe:business_service",
                    "statement": "Business endpoint probe passed.",
                },
            ],
            "diagnostic_hypothesis": "Potential client-side caching, transient error, or local application issue.",
            "confidence": "LOW",
            "recommended_action": "Verify client workstation configuration and ask user for specific error screenshots.",
            "uncertainty_caveats": [
                "Issue may be intermittent or isolated to a single client workstation."
            ],
        })


class OpenAICompatibleProvider(LLMProvider):
    """Real HTTP LLM provider using OpenAI-compatible chat completions API.
    Compatible with OpenAI, Gemini (via OpenAI compatibility endpoints), or local vLLM.
    Strictly reads credentials from environment settings.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: float = 10.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds

    @property
    def provider_id(self) -> str:
        return "openai"

    def generate_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
    ) -> str:
        if not self.api_key:
            raise LLMProviderError(
                "AI_API_KEY is not configured for OpenAICompatibleProvider. Set AI_API_KEY in environment."
            )

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }

        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                choices = data.get("choices", [])
                if not choices:
                    raise LLMProviderError("Empty choices returned from LLM provider")
                content = choices[0].get("message", {}).get("content", "")
                if not content:
                    raise LLMProviderError("Empty content in LLM completion choice")
                return content
        except httpx.TimeoutException as exc:
            raise LLMProviderTimeoutError(
                f"LLM provider request timed out after {self.timeout_seconds}s"
            ) from exc
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            raise LLMProviderError(
                f"LLM provider HTTP error: status {status_code}"
            ) from exc
        except httpx.RequestError as exc:
            raise LLMProviderError(
                f"LLM provider connection error: {exc}"
            ) from exc


def get_ai_provider(provider_type: Optional[str] = None) -> LLMProvider:
    """Factory to retrieve the configured LLM provider instance."""
    chosen = (provider_type or settings.ai_provider).lower().strip()
    if chosen in ("openai", "openai_compatible", "live"):
        return OpenAICompatibleProvider(
            base_url=settings.ai_api_base_url,
            api_key=settings.ai_api_key,
            model=settings.ai_model,
            timeout_seconds=settings.ai_request_timeout_seconds,
        )
    return MockLLMProvider()
