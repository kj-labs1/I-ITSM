"""
Unit and integration tests for LLM Integration (Adapter Pattern).

Requirements:
- 18. Valid LLM response handling and schema validation.
- 19. Malformed LLM response handling.
- 20. LLM timeout and deterministic fallback.
"""

from uuid import uuid4

import pytest

from app.application.assignment.service import SmartTechnicianRecommendationService
from app.core.exceptions import (
    LLMProviderError,
    LLMResponseValidationError,
    LLMTimeoutError,
)
from app.domain.technician.technician import Technician
from app.infrastructure.repositories.technician_repository import SQLAlchemyTechnicianRepository
from app.integrations.incidents.stub_incident_service import StubIncidentService
from app.integrations.llm.mock_provider import MockLLMProvider
from app.integrations.llm.provider import (
    LLMCandidateData,
    LLMRecommendationRequest,
    LLMRecommendationResponse,
)
from app.shared.enums import AssignmentStrategyType, IncidentCategory, Priority


class TestLLMProviderAdapter:
    """Tests for LLMProvider adapter and MockLLMProvider."""

    @pytest.mark.asyncio
    async def test_llm_valid_response(self):
        """TC18: LLM provider generates valid structured output conforming to schema."""
        provider = MockLLMProvider()
        tech_id = str(uuid4())

        request = LLMRecommendationRequest(
            incidentCategory="NETWORK",
            incidentPriority="P1",
            incidentDescription="Datacenter core router crashed",
            requiredSkill="NETWORK",
            candidates=[
                LLMCandidateData(
                    id=tech_id,
                    skills=[{"name": "NETWORK", "proficiency": 5}],
                    experienceYears=6,
                    activeIncidents=1,
                    maxCapacity=10,
                )
            ],
        )

        response = await provider.get_recommendation(request)
        assert isinstance(response, LLMRecommendationResponse)
        assert len(response.rankings) == 1
        assert response.rankings[0].technician_id == tech_id
        assert response.rankings[0].rank == 1
        assert response.rankings[0].relevance_score > 0
        assert len(response.rankings[0].explanation) > 0
        assert response.confidence > 0

    @pytest.mark.asyncio
    async def test_llm_malformed_response_handling(self):
        """TC19: Malformed LLM response raises LLMResponseValidationError."""
        provider = MockLLMProvider(malformed_response=True)
        request = LLMRecommendationRequest(
            incidentCategory="NETWORK",
            incidentPriority="P2",
            incidentDescription="Slow switch port",
            requiredSkill="NETWORK",
            candidates=[],
        )

        with pytest.raises(LLMResponseValidationError):
            await provider.get_recommendation(request)

    @pytest.mark.asyncio
    async def test_llm_timeout_handling(self):
        """TC20: Simulated timeout raises LLMTimeoutError."""
        provider = MockLLMProvider(simulate_timeout=True)
        request = LLMRecommendationRequest(
            incidentCategory="NETWORK",
            incidentPriority="P2",
            incidentDescription="Slow switch port",
            requiredSkill="NETWORK",
            candidates=[],
        )

        with pytest.raises(LLMTimeoutError):
            await provider.get_recommendation(request)

    @pytest.mark.asyncio
    async def test_llm_upstream_failure_handling(self):
        """Simulated 503 provider error raises LLMProviderError."""
        provider = MockLLMProvider(should_fail=True)
        request = LLMRecommendationRequest(
            incidentCategory="NETWORK",
            incidentPriority="P2",
            incidentDescription="Test",
            requiredSkill="NETWORK",
            candidates=[],
        )

        with pytest.raises(LLMProviderError):
            await provider.get_recommendation(request)


class TestRecommendationServiceFallback:
    """Verifies that SmartTechnicianRecommendationService falls back seamlessly on LLM failures."""

    @pytest.mark.asyncio
    async def test_deterministic_fallback_on_llm_timeout(
        self,
        tech_repo: SQLAlchemyTechnicianRepository,
        stub_incidents: StubIncidentService,
    ):
        """TC20 (Service level): LLM timeout falls back to deterministic recommendations without crashing."""
        failing_llm = MockLLMProvider(simulate_timeout=True)
        service = SmartTechnicianRecommendationService(
            technician_repo=tech_repo,
            incident_service=stub_incidents,
            llm_provider=failing_llm,
        )

        # Seed technician
        tech = Technician(user_id=uuid4(), experience_years=4)
        tech.add_skill("NETWORK", 4)
        saved_tech = await tech_repo.save(tech)

        # Seed incident
        inc = stub_incidents.seed_incident(
            category=IncidentCategory.NETWORK,
            required_skill="NETWORK",
            priority=Priority.P2,
        )

        # Request with use_llm=True
        result = await service.get_recommendations(
            incident_id=inc.id,
            strategy_type=AssignmentStrategyType.SKILL_BASED,
            use_llm=True,
        )

        # Must succeed and return deterministic results with fallback annotation
        assert result.has_recommendations is True
        assert len(result.recommendations) == 1
        rec = result.recommendations[0]
        assert rec.technician_user_id == saved_tech.user_id
        assert rec.is_llm_enhanced is False
        assert "LLM fallback applied" in rec.explanation
        assert "LLMTimeoutError" in rec.explanation

    @pytest.mark.asyncio
    async def test_deterministic_fallback_on_llm_malformed(
        self,
        tech_repo: SQLAlchemyTechnicianRepository,
        stub_incidents: StubIncidentService,
    ):
        """TC19 (Service level): Malformed LLM output falls back to deterministic rankings."""
        failing_llm = MockLLMProvider(malformed_response=True)
        service = SmartTechnicianRecommendationService(
            technician_repo=tech_repo,
            incident_service=stub_incidents,
            llm_provider=failing_llm,
        )

        tech = Technician(user_id=uuid4(), experience_years=3)
        tech.add_skill("NETWORK", 3)
        await tech_repo.save(tech)

        inc = stub_incidents.seed_incident(
            category=IncidentCategory.NETWORK,
            required_skill="NETWORK",
        )

        result = await service.get_recommendations(
            incident_id=inc.id,
            strategy_type=AssignmentStrategyType.SKILL_BASED,
            use_llm=True,
        )

        assert result.has_recommendations is True
        assert "LLM fallback applied" in result.recommendations[0].explanation
