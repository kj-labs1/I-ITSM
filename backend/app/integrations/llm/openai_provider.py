"""
OpenAI-compatible LLM Provider adapter using asynchronous HTTPX.

OOP Design:
- Adapter Pattern: Adapts the standard OpenAI Chat Completion HTTP REST protocol
  to our domain's `LLMProvider` interface.
- Encapsulates HTTP transport, header management, JSON extraction, and retry semantics.
- Secure by Design: API tokens are injected from environment variables and never written to logs.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.exceptions import (
    LLMProviderError,
    LLMResponseValidationError,
    LLMTimeoutError,
)
from app.integrations.llm.prompts import build_recommendation_prompt
from app.integrations.llm.provider import (
    LLMProvider,
    LLMRecommendationRequest,
    LLMRecommendationResponse,
)

logger = logging.getLogger(__name__)


class OpenAICompatibleProvider(LLMProvider):
    """
    Adapter communicating with OpenAI or any OpenAI-compatible completions endpoint
    (e.g. Azure OpenAI, Groq, Ollama, vLLM).
    """

    def __init__(self) -> None:
        self.settings = get_settings()

    @property
    def provider_name(self) -> str:
        return "openai_compatible"

    async def get_recommendation(
        self,
        request: LLMRecommendationRequest,
    ) -> LLMRecommendationResponse:
        """
        Dispatches prompt to OpenAI chat completions API with response_format=json_object.
        """
        if not self.settings.LLM_API_KEY:
            raise LLMProviderError("LLM API key is not configured. Set LLM_API_KEY in environment or .env.")

        prompts = build_recommendation_prompt(request)
        base_url = self.settings.LLM_BASE_URL or "https://api.openai.com/v1"
        url = f"{base_url.rstrip('/')}/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.settings.LLM_API_KEY}",
            "Content-Type": "application/json",
        }

        payload: dict[str, Any] = {
            "model": self.settings.LLM_MODEL or "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": prompts["system"]},
                {"role": "user", "content": prompts["user"]},
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }

        timeout = float(self.settings.LLM_TIMEOUT_SECONDS)
        max_retries = max(0, self.settings.LLM_MAX_RETRIES)

        for attempt in range(max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.post(url, headers=headers, json=payload)

                if response.status_code == 429 or response.status_code >= 500:
                    if attempt < max_retries:
                        backoff = 2**attempt
                        logger.warning(
                            "LLM HTTP %d received. Retrying in %ds (attempt %d/%d)...",
                            response.status_code,
                            backoff,
                            attempt + 1,
                            max_retries,
                        )
                        await asyncio.sleep(backoff)
                        continue
                    raise LLMProviderError(
                        f"LLM API failed with status {response.status_code}: {response.text}"
                    )

                if response.status_code != 200:
                    raise LLMProviderError(
                        f"LLM API returned unexpected status {response.status_code}: {response.text}"
                    )

                data = response.json()
                content = data["choices"][0]["message"]["content"]

                try:
                    parsed_json = json.loads(content)
                    return LLMRecommendationResponse.model_validate(parsed_json)
                except (json.JSONDecodeError, KeyError, Exception) as parse_err:
                    raise LLMResponseValidationError(
                        f"Failed to validate LLM JSON structure: {parse_err}"
                    ) from parse_err

            except httpx.TimeoutException as exc:
                if attempt < max_retries:
                    logger.warning("LLM request timed out, retrying attempt %d...", attempt + 1)
                    await asyncio.sleep(1)
                    continue
                raise LLMTimeoutError(f"LLM request timed out after {timeout} seconds.") from exc
            except httpx.RequestError as exc:
                if attempt < max_retries:
                    await asyncio.sleep(1)
                    continue
                raise LLMProviderError(f"HTTP transport error contacting LLM: {exc}") from exc

        raise LLMProviderError("Exhausted all retry attempts contacting LLM provider.")

    async def health_check(self) -> bool:
        """Perform basic credential presence check."""
        return bool(self.settings.LLM_API_KEY)
