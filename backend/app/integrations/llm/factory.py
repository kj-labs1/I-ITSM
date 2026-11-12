"""
LLM Provider Factory — Factory Pattern.

OOP Design:
- Factory Pattern: Encapsulates the instantiation logic for LLM provider adapters.
- Open/Closed Principle: New LLM providers can be registered dynamically without modifying
  existing client services.
"""

from __future__ import annotations

import logging

from app.core.config import get_settings
from app.integrations.llm.mock_provider import MockLLMProvider
from app.integrations.llm.provider import LLMProvider

logger = logging.getLogger(__name__)


class LLMProviderFactory:
    """
    Factory creating configured LLMProvider instances.
    """

    _registry: dict[str, type[LLMProvider]] = {
        "mock": MockLLMProvider,
    }

    @classmethod
    def register(cls, name: str, provider_cls: type[LLMProvider]) -> None:
        """Register a new LLM provider adapter class."""
        cls._registry[name.lower()] = provider_cls
        logger.info("Registered LLM provider adapter: '%s'", name)

    @classmethod
    def create(cls, provider_name: str | None = None) -> LLMProvider:
        """
        Instantiate and return the appropriate LLM provider adapter.

        Falls back gracefully to MockLLMProvider if provider is unknown or 'mock'.
        """
        settings = get_settings()
        target = (provider_name or settings.LLM_PROVIDER or "mock").lower()

        if target in ("openai", "openai_compatible"):
            from app.integrations.llm.openai_provider import OpenAICompatibleProvider

            return OpenAICompatibleProvider()

        if target in cls._registry:
            provider_cls = cls._registry[target]
            return provider_cls()

        logger.warning(
            "Requested LLM provider '%s' not recognized. Falling back to MockLLMProvider.",
            target,
        )
        return MockLLMProvider()
