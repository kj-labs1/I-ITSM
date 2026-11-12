"""
LLM Provider interface and structured schemas — Adapter Pattern abstraction.

OOP Design:
- Adapter Pattern: Decouples the technician recommendation engine from external LLM APIs
  (OpenAI, Anthropic, Gemini, local Ollama, or mock testing adapters).
- Schema Validation: Pydantic v2 schemas enforce strict validation of LLM outputs before
  allowing any AI-generated rationale into the application.
- Privacy by Design: Only anonymized operational data (incident category, required skill,
  technician UUID, proficiency numbers) is transmitted. No PII (names, emails) is sent.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class LLMCandidateData(BaseModel):
    """Anonymized technician candidate representation for LLM evaluation."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: str = Field(description="Technician UUID string")
    skills: list[dict[str, Any]] = Field(
        default_factory=list,
        description="List of skill objects containing 'name' and 'proficiency' (1-5)",
    )
    experience_years: int = Field(default=0, ge=0)
    active_incidents: int = Field(default=0, ge=0)
    max_capacity: int = Field(default=10, ge=1)


class LLMRecommendationRequest(BaseModel):
    """Structured request payload dispatched to the LLM adapter."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    incident_category: str
    incident_priority: str
    incident_description: str
    required_skill: str
    candidates: list[LLMCandidateData] = Field(default_factory=list)


class LLMRanking(BaseModel):
    """Individual technician ranking and reasoning produced by the LLM."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    technician_id: str
    rank: int = Field(ge=1, description="1-based rank")
    relevance_score: float = Field(
        ge=0.0,
        le=100.0,
        description="Model assessment score from 0.0 to 100.0",
    )
    explanation: str = Field(
        description="Factual justification for recommendation referencing only provided facts"
    )


class LLMRecommendationResponse(BaseModel):
    """Validated structured output received from the LLM adapter."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    rankings: list[LLMRanking] = Field(default_factory=list)
    reasoning: str = Field(default="", description="High-level synthesis of pool fit")
    confidence: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Self-assessed confidence score",
    )


class LLMProvider(ABC):
    """
    Abstract interface for LLM provider adapters.

    All LLM vendors (OpenAI, Gemini, Anthropic, Mock) must conform to this contract.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Identifying name of the provider adapter."""
        ...

    @abstractmethod
    async def get_recommendation(
        self,
        request: LLMRecommendationRequest,
    ) -> LLMRecommendationResponse:
        """
        Evaluate candidate technicians against incident characteristics using an LLM.

        Must validate output against LLMRecommendationResponse schema.

        Raises:
            LLMProviderError: On upstream HTTP or API error.
            LLMTimeoutError: If the call exceeds configured deadline.
            LLMResponseValidationError: If LLM output fails schema validation.
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Verify provider availability and credential validity."""
        ...
