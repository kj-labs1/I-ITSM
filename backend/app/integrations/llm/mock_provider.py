"""
Mock LLM Provider adapter for automated testing and offline development.

OOP Design:
- Polymorphism: Implements the exact same `LLMProvider` interface as real vendor adapters.
- Deterministic Behavior: Produces consistent, reproducible test recommendations
  without network calls or external API tokens.
- Fault Injection: Can be configured at runtime to simulate timeouts, malformed payloads,
  or upstream API outages to verify resilience and deterministic fallback paths.
"""

from __future__ import annotations

import asyncio
import logging

from app.core.exceptions import (
    LLMProviderError,
    LLMResponseValidationError,
    LLMTimeoutError,
)
from app.integrations.llm.provider import (
    LLMProvider,
    LLMRanking,
    LLMRecommendationRequest,
    LLMRecommendationResponse,
)

logger = logging.getLogger(__name__)


class MockLLMProvider(LLMProvider):
    """
    In-memory mock adapter conforming to LLMProvider.
    """

    def __init__(
        self,
        should_fail: bool = False,
        simulate_timeout: bool = False,
        malformed_response: bool = False,
        latency_seconds: float = 0.0,
    ) -> None:
        self.should_fail = should_fail
        self.simulate_timeout = simulate_timeout
        self.malformed_response = malformed_response
        self.latency_seconds = latency_seconds

    @property
    def provider_name(self) -> str:
        return "mock"

    async def get_recommendation(
        self,
        request: LLMRecommendationRequest,
    ) -> LLMRecommendationResponse:
        """Simulate LLM recommendation processing with optional fault injection."""
        if self.latency_seconds > 0:
            await asyncio.sleep(self.latency_seconds)

        if self.simulate_timeout:
            raise LLMTimeoutError("Mock LLM provider simulated timeout after deadline elapsed.")

        if self.should_fail:
            raise LLMProviderError("Mock LLM upstream service failure (simulated 503).")

        if self.malformed_response:
            raise LLMResponseValidationError(
                "Mock LLM returned malformed JSON payload missing required 'rankings' key."
            )

        # Deterministic scoring:
        # Score = (Proficiency * 15) + (Experience * 2) + ((MaxCapacity - Workload) * 3)
        scored: list[tuple[str, float, str]] = []
        for candidate in request.candidates:
            # Find relevant proficiency
            matched_prof = 1
            for sk in candidate.skills:
                if sk.get("name", "").upper() == request.required_skill.upper():
                    matched_prof = int(sk.get("proficiency", 1))
                    break

            exp = candidate.experience_years
            free_slots = max(0, candidate.max_capacity - candidate.active_incidents)

            raw_score = (matched_prof * 15.0) + (exp * 2.0) + (free_slots * 3.0)
            score = min(100.0, round(raw_score, 1))

            explanation = (
                f"[AI Evaluated] Candidate possesses '{request.required_skill}' proficiency {matched_prof}/5 "
                f"with {exp}y relevant experience. Active workload {candidate.active_incidents}/"
                f"{candidate.max_capacity} provides optimal bandwidth for {request.incident_priority} triage."
            )
            scored.append((candidate.id, score, explanation))

        # Sort descending by score, tie-break by candidate id
        scored.sort(key=lambda item: (-item[1], item[0]))

        rankings = [
            LLMRanking(
                technician_id=c_id,
                rank=idx + 1,
                relevance_score=c_score,
                explanation=c_exp,
            )
            for idx, (c_id, c_score, c_exp) in enumerate(scored)
        ]

        top_id = rankings[0].technician_id if rankings else "None"
        reasoning = (
            f"Evaluated {len(rankings)} eligible technician(s). Candidate {top_id} demonstrated "
            f"the optimal combination of domain skill depth and workload headroom."
        )

        return LLMRecommendationResponse(
            rankings=rankings,
            reasoning=reasoning,
            confidence=0.92,
        )

    async def health_check(self) -> bool:
        """Health check returns True unless configured to fail."""
        return not self.should_fail
