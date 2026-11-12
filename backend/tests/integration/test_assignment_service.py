"""
Integration tests for TechnicianAssignmentService.

Requirements:
- 12. Successful incident assignment.
- 13. Duplicate assignment prevention.
- 14. Concurrent assignment protection.
- 15. Incident integration boundary delegation (Member 2).
- 16. Assignment event publishing for Member 4 (Observer Pattern).
"""

import asyncio
from uuid import uuid4

import pytest

from app.application.assignment.service import TechnicianAssignmentService
from app.application.interfaces.event_publisher import EventListener
from app.core.exceptions import (
    CapacityExceededError,
    DuplicateAssignmentError,
    InvalidAssignmentError,
    SkillMismatchError,
    TechnicianUnavailableError,
)
from app.domain.assignment.events import DomainEvent, IncidentAssignedEvent
from app.domain.technician.technician import Technician
from app.infrastructure.events.event_bus import InProcessEventBus
from app.infrastructure.repositories.technician_repository import SQLAlchemyTechnicianRepository
from app.integrations.incidents.stub_incident_service import StubIncidentService
from app.shared.enums import AvailabilityStatus, IncidentCategory, IncidentStatus, Priority


class MockAuditEventListener(EventListener):
    """Test listener representing Member 4's SLA/Audit subscriber."""

    def __init__(self) -> None:
        self.received_events: list[IncidentAssignedEvent] = []

    async def handle(self, event: DomainEvent) -> None:
        if isinstance(event, IncidentAssignedEvent):
            self.received_events.append(event)


class TestTechnicianAssignmentIntegration:
    """Integration test suite for incident assignment workflows."""

    @pytest.mark.asyncio
    async def test_successful_assignment_and_event_publishing(
        self,
        tech_repo: SQLAlchemyTechnicianRepository,
        stub_incidents: StubIncidentService,
        event_bus: InProcessEventBus,
        assign_service: TechnicianAssignmentService,
    ):
        """TC12, TC15, TC16: Successful assignment validates, delegates to M2, and publishes event for M4."""
        # 1. Register Member 4 test listener
        audit_listener = MockAuditEventListener()
        event_bus.subscribe(IncidentAssignedEvent, audit_listener)

        # 2. Seed available technician with required skill
        tech = Technician(user_id=uuid4(), experience_years=5, max_capacity=10)
        tech.add_skill("NETWORK", 4)
        saved_tech = await tech_repo.save(tech)

        # 3. Seed unassigned incident in M2 stub
        inc = stub_incidents.seed_incident(
            category=IncidentCategory.NETWORK,
            required_skill="NETWORK",
            priority=Priority.P1,
            status=IncidentStatus.CLASSIFIED,
        )

        actor_id = uuid4()

        # 4. Execute assignment
        result = await assign_service.assign_technician(
            incident_id=inc.id,
            technician_id=saved_tech.id,
            actor_id=actor_id,
            strategy_used="SKILL_BASED",
            reason="Top ranked candidate",
        )

        # Assert result DTO
        assert result["incidentId"] == inc.id
        assert result["technicianUserId"] == saved_tech.user_id
        assert result["status"] == "ASSIGNED"

        # TC15: Verify M2 integration boundary state
        updated_inc = await stub_incidents.get_incident(inc.id)
        assert updated_inc.status == IncidentStatus.ASSIGNED
        assert updated_inc.assigned_technician_id == saved_tech.user_id

        # TC16: Verify M4 Observer Pattern event publishing
        assert len(audit_listener.received_events) == 1
        event = audit_listener.received_events[0]
        assert event.incident_id == inc.id
        assert event.technician_id == saved_tech.user_id
        assert event.actor_id == actor_id
        assert event.strategy_used == "SKILL_BASED"

    @pytest.mark.asyncio
    async def test_duplicate_assignment_prevention(
        self,
        tech_repo: SQLAlchemyTechnicianRepository,
        stub_incidents: StubIncidentService,
        assign_service: TechnicianAssignmentService,
    ):
        """TC13: Prevent duplicate assignment when incident already has an assigned technician."""
        tech1 = Technician(user_id=uuid4())
        tech1.add_skill("NETWORK", 3)
        saved_tech1 = await tech_repo.save(tech1)

        tech2 = Technician(user_id=uuid4())
        tech2.add_skill("NETWORK", 4)
        saved_tech2 = await tech_repo.save(tech2)

        inc = stub_incidents.seed_incident(
            category=IncidentCategory.NETWORK,
            required_skill="NETWORK",
        )

        # First assignment succeeds
        await assign_service.assign_technician(
            incident_id=inc.id,
            technician_id=saved_tech1.id,
            actor_id=uuid4(),
        )

        # Attempting duplicate assignment must raise DuplicateAssignmentError
        with pytest.raises(DuplicateAssignmentError, match="already assigned"):
            await assign_service.assign_technician(
                incident_id=inc.id,
                technician_id=saved_tech2.id,
                actor_id=uuid4(),
            )

    @pytest.mark.asyncio
    async def test_concurrent_assignment_protection(
        self,
        tech_repo: SQLAlchemyTechnicianRepository,
        stub_incidents: StubIncidentService,
        assign_service: TechnicianAssignmentService,
    ):
        """TC14: Concurrency safety — two simultaneous assignment requests race, only one succeeds."""
        tech1 = Technician(user_id=uuid4())
        tech1.add_skill("NETWORK", 3)
        saved_tech1 = await tech_repo.save(tech1)

        tech2 = Technician(user_id=uuid4())
        tech2.add_skill("NETWORK", 4)
        saved_tech2 = await tech_repo.save(tech2)

        inc = stub_incidents.seed_incident(
            category=IncidentCategory.NETWORK,
            required_skill="NETWORK",
        )

        actor_id = uuid4()

        # Fire two concurrent assignment attempts
        task1 = assign_service.assign_technician(inc.id, saved_tech1.id, actor_id)
        task2 = assign_service.assign_technician(inc.id, saved_tech2.id, actor_id)

        results = await asyncio.gather(task1, task2, return_exceptions=True)

        successes = [r for r in results if isinstance(r, dict)]
        errors = [r for r in results if isinstance(r, Exception)]

        # Exactly one must succeed and one must be rejected with DuplicateAssignmentError or InvalidAssignmentError
        assert len(successes) == 1
        assert len(errors) == 1
        assert isinstance(errors[0], (DuplicateAssignmentError, InvalidAssignmentError))

    @pytest.mark.asyncio
    async def test_assignment_rejection_rules(
        self,
        tech_repo: SQLAlchemyTechnicianRepository,
        stub_incidents: StubIncidentService,
        assign_service: TechnicianAssignmentService,
    ):
        """Rejects assignment when technician is unavailable, lacks skill, or exceeds capacity."""
        # 1. Technician unavailable
        busy_tech = Technician(user_id=uuid4(), _availability=AvailabilityStatus.BUSY)
        busy_tech.add_skill("NETWORK", 4)
        saved_busy = await tech_repo.save(busy_tech)

        inc = stub_incidents.seed_incident(required_skill="NETWORK")

        with pytest.raises(TechnicianUnavailableError):
            await assign_service.assign_technician(inc.id, saved_busy.id, uuid4())

        # 2. Skill mismatch
        wrong_skill_tech = Technician(user_id=uuid4())
        wrong_skill_tech.add_skill("DATABASE", 5)
        saved_wrong = await tech_repo.save(wrong_skill_tech)

        with pytest.raises(SkillMismatchError):
            await assign_service.assign_technician(inc.id, saved_wrong.id, uuid4())

        # 3. Capacity exceeded
        full_tech = Technician(user_id=uuid4(), max_capacity=1)
        full_tech.add_skill("NETWORK", 4)
        saved_full = await tech_repo.save(full_tech)

        # Seed an existing incident assigned to full_tech
        stub_incidents.seed_incident(
            required_skill="NETWORK",
            assigned_technician_id=saved_full.user_id,
            status=IncidentStatus.ASSIGNED,
        )

        with pytest.raises(CapacityExceededError):
            await assign_service.assign_technician(inc.id, saved_full.id, uuid4())
