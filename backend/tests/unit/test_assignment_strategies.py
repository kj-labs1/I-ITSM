"""
Unit tests for Assignment Strategies (Strategy Pattern).

OOP Verification:
- Strategy Pattern: Verifies SkillBasedAssignmentStrategy and LeastLoadedAssignmentStrategy
  implement the same AssignmentStrategy interface and are polymorphically interchangeable.
- Business Rules:
  - Skill-based ranking by proficiency and experience.
  - Least-loaded ranking by lowest active incidents with deterministic tie-breaking.
  - Hard exclusions: Unavailable, over-capacity, and skill-mismatched candidates.
  - No eligible technician raises domain-specific NoEligibleTechnicianError.
"""

from uuid import uuid4

import pytest

from app.application.assignment.factory import AssignmentStrategyFactory
from app.core.exceptions import NoEligibleTechnicianError
from app.domain.assignment.strategies import (
    EXPERIENCE_WEIGHT,
    PROFICIENCY_WEIGHT,
    LeastLoadedAssignmentStrategy,
    SkillBasedAssignmentStrategy,
)
from app.domain.assignment.strategy import AssignmentContext, AssignmentStrategy
from app.domain.incident.incident_ref import IncidentRef
from app.domain.technician.technician import Technician
from app.shared.enums import (
    AssignmentStrategyType,
    AvailabilityStatus,
    IncidentCategory,
    IncidentStatus,
    Priority,
)


@pytest.fixture
def sample_incident() -> IncidentRef:
    """Fixture creating a standard test incident reference."""
    return IncidentRef(
        id=uuid4(),
        incident_code="INC-2001",
        category=IncidentCategory.NETWORK,
        required_skill="NETWORK",
        priority=Priority.P2,
        status=IncidentStatus.CLASSIFIED,
        description="Core switch flapping in Datacenter Rack 4.",
        service_id=uuid4(),
        reporter_id=uuid4(),
    )


def _build_technician(
    skill_name: str = "NETWORK",
    proficiency: int = 3,
    experience_years: int = 2,
    active_incidents: int = 0,
    max_capacity: int = 10,
    availability: AvailabilityStatus = AvailabilityStatus.AVAILABLE,
) -> Technician:
    """Helper creating a technician entity for strategy testing."""
    tech = Technician(
        user_id=uuid4(),
        _availability=availability,
        experience_years=experience_years,
        max_capacity=max_capacity,
    )
    if skill_name:
        tech.add_skill(skill_name, proficiency)
    tech.update_active_incident_count(active_incidents)
    return tech


class TestSkillBasedAssignmentStrategy:
    """Tests for Strategy A: SkillBasedAssignmentStrategy."""

    def test_skill_based_ranking_and_explanation(self, sample_incident: IncidentRef):
        """TC5: Ranks technicians primarily by skill proficiency and secondarily by experience."""
        strategy = SkillBasedAssignmentStrategy()

        tech_senior = _build_technician(proficiency=5, experience_years=8)
        tech_junior = _build_technician(proficiency=3, experience_years=2)
        tech_mid = _build_technician(proficiency=4, experience_years=4)

        context = AssignmentContext(
            incident=sample_incident,
            available_technicians=[tech_junior, tech_senior, tech_mid],
            strategy_type=strategy.strategy_name,
        )

        result = strategy.evaluate(context)

        assert result.strategy_used == "SKILL_BASED"
        assert result.eligible_candidates == 3
        assert len(result.recommendations) == 3

        # Expected order: senior (5*20 + 8*2 = 116), mid (4*20 + 4*2 = 88), junior (3*20 + 2*2 = 64)
        top = result.recommendations[0]
        assert top.technician_user_id == tech_senior.user_id
        assert top.rank == 1
        assert top.score == (5 * PROFICIENCY_WEIGHT) + (8 * EXPERIENCE_WEIGHT)
        assert "proficiency: 5/5" in top.explanation
        assert "experience: 8 years" in top.explanation

        second = result.recommendations[1]
        assert second.technician_user_id == tech_mid.user_id
        assert second.rank == 2

        third = result.recommendations[2]
        assert third.technician_user_id == tech_junior.user_id
        assert third.rank == 3

    def test_skill_mismatch_exclusion(self, sample_incident: IncidentRef):
        """TC6: Technicians lacking the required skill are excluded from recommendations."""
        strategy = SkillBasedAssignmentStrategy()

        tech_db = _build_technician(skill_name="DATABASE", proficiency=5)
        tech_net = _build_technician(skill_name="NETWORK", proficiency=3)

        context = AssignmentContext(
            incident=sample_incident,
            available_technicians=[tech_db, tech_net],
            strategy_type=strategy.strategy_name,
        )

        result = strategy.evaluate(context)
        assert result.eligible_candidates == 1
        assert len(result.recommendations) == 1
        assert result.recommendations[0].technician_user_id == tech_net.user_id

    def test_unavailable_technician_rejection(self, sample_incident: IncidentRef):
        """TC9: Unavailable or busy technicians are strictly excluded."""
        strategy = SkillBasedAssignmentStrategy()

        tech_busy = _build_technician(availability=AvailabilityStatus.BUSY)
        tech_offline = _build_technician(availability=AvailabilityStatus.OFFLINE)
        tech_leave = _build_technician(availability=AvailabilityStatus.ON_LEAVE)
        tech_available = _build_technician(availability=AvailabilityStatus.AVAILABLE)

        context = AssignmentContext(
            incident=sample_incident,
            available_technicians=[tech_busy, tech_offline, tech_leave, tech_available],
            strategy_type=strategy.strategy_name,
        )

        result = strategy.evaluate(context)
        assert len(result.recommendations) == 1
        assert result.recommendations[0].technician_user_id == tech_available.user_id

    def test_maximum_workload_capacity_rejection(self, sample_incident: IncidentRef):
        """TC10: Technicians that have reached max capacity are excluded."""
        strategy = SkillBasedAssignmentStrategy()

        tech_full = _build_technician(active_incidents=5, max_capacity=5)
        tech_open = _build_technician(active_incidents=4, max_capacity=5)

        context = AssignmentContext(
            incident=sample_incident,
            available_technicians=[tech_full, tech_open],
            strategy_type=strategy.strategy_name,
        )

        result = strategy.evaluate(context)
        assert len(result.recommendations) == 1
        assert result.recommendations[0].technician_user_id == tech_open.user_id

    def test_no_eligible_technician_raises_error(self, sample_incident: IncidentRef):
        """TC11: Raises NoEligibleTechnicianError when no technician satisfies criteria."""
        strategy = SkillBasedAssignmentStrategy()

        # Technicians with wrong skill and full workload
        tech1 = _build_technician(skill_name="DATABASE")
        tech2 = _build_technician(availability=AvailabilityStatus.BUSY)

        context = AssignmentContext(
            incident=sample_incident,
            available_technicians=[tech1, tech2],
            strategy_type=strategy.strategy_name,
        )

        with pytest.raises(NoEligibleTechnicianError, match="No eligible technician found"):
            strategy.evaluate(context)


class TestLeastLoadedAssignmentStrategy:
    """Tests for Strategy B: LeastLoadedAssignmentStrategy."""

    def test_least_loaded_selection(self, sample_incident: IncidentRef):
        """TC7: Prioritizes technician with lowest current workload."""
        strategy = LeastLoadedAssignmentStrategy()

        tech_busy = _build_technician(active_incidents=7, max_capacity=10)
        tech_free = _build_technician(active_incidents=1, max_capacity=10)
        tech_mid = _build_technician(active_incidents=4, max_capacity=10)

        context = AssignmentContext(
            incident=sample_incident,
            available_technicians=[tech_busy, tech_free, tech_mid],
            strategy_type=strategy.strategy_name,
        )

        result = strategy.evaluate(context)
        assert result.strategy_used == "LEAST_LOADED"
        assert result.recommendations[0].technician_user_id == tech_free.user_id
        assert result.recommendations[1].technician_user_id == tech_mid.user_id
        assert result.recommendations[2].technician_user_id == tech_busy.user_id
        assert "lowest workload" in result.recommendations[0].explanation

    def test_deterministic_tie_breaking(self, sample_incident: IncidentRef):
        """TC8: Breaks workload ties first by experience, then by stable UUID."""
        strategy = LeastLoadedAssignmentStrategy()

        # Both have 2 active incidents; tech_experienced has 10y, tech_junior has 2y
        tech_experienced = _build_technician(active_incidents=2, experience_years=10)
        tech_junior = _build_technician(active_incidents=2, experience_years=2)

        context = AssignmentContext(
            incident=sample_incident,
            available_technicians=[tech_junior, tech_experienced],
            strategy_type=strategy.strategy_name,
        )

        result = strategy.evaluate(context)
        assert result.recommendations[0].technician_user_id == tech_experienced.user_id
        assert result.recommendations[1].technician_user_id == tech_junior.user_id


class TestStrategyPolymorphismAndFactory:
    """Verifies Strategy Pattern polymorphism and Factory Pattern."""

    def test_factory_creates_both_strategies(self):
        """Factory Pattern returns correct strategy conforming to AssignmentStrategy ABC."""
        strat_skill = AssignmentStrategyFactory.get_strategy(AssignmentStrategyType.SKILL_BASED)
        assert isinstance(strat_skill, AssignmentStrategy)
        assert strat_skill.strategy_name == "SKILL_BASED"

        strat_load = AssignmentStrategyFactory.get_strategy(AssignmentStrategyType.LEAST_LOADED)
        assert isinstance(strat_load, AssignmentStrategy)
        assert strat_load.strategy_name == "LEAST_LOADED"

    def test_polymorphic_execution(self, sample_incident: IncidentRef):
        """Both strategies can be executed interchangeably through common interface."""
        tech = _build_technician(proficiency=4, experience_years=3, active_incidents=1)
        strategies: list[AssignmentStrategy] = [
            SkillBasedAssignmentStrategy(),
            LeastLoadedAssignmentStrategy(),
        ]

        for s in strategies:
            context = AssignmentContext(
                incident=sample_incident,
                available_technicians=[tech],
                strategy_type=s.strategy_name,
            )
            res = s.evaluate(context)
            assert res.has_recommendations is True
            assert res.top_recommendation is not None
            assert res.top_recommendation.technician_user_id == tech.user_id
