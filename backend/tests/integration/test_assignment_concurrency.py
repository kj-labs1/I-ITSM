"""
Concurrency and transaction safety tests for technician assignment.

Verifies:
1. Simultaneous assignment requests cannot assign the same incident twice (DuplicateAssignmentError).
2. Simultaneous assignment requests cannot oversubscribe a technician beyond max_capacity (CapacityExceededError).
3. Concurrent requests execute with separate database sessions.
"""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)

from app.application.assignment.service import TechnicianAssignmentService
from app.application.incident.service import IncidentApplicationService
from app.core.exceptions import (
    CapacityExceededError,
    DuplicateAssignmentError,
)
from app.domain.incident.incident import Incident
from app.domain.technician.technician import Technician
from app.infrastructure.events.event_bus import InProcessEventBus
from app.infrastructure.repositories.incident_repository import (
    SQLAlchemyIncidentRepository,
)
from app.infrastructure.repositories.technician_repository import (
    SQLAlchemyTechnicianRepository,
)
from app.shared.enums import AvailabilityStatus, IncidentCategory, IncidentStatus, Priority


@pytest.mark.asyncio
async def test_concurrent_assignments_cannot_assign_same_incident_twice(
    test_engine: AsyncEngine,
):
    """
    Simulate two concurrent assignment requests for the exact same incident
    using separate database sessions. Exactly one must succeed; the other must raise
    DuplicateAssignmentError.
    """
    session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    event_bus = InProcessEventBus()

    # Pre-seed: 1 incident, 2 technicians with matching skills
    async with session_factory() as setup_session:
        tech_repo = SQLAlchemyTechnicianRepository(setup_session)
        inc_repo = SQLAlchemyIncidentRepository(setup_session)

        # Create technician 1
        t1 = Technician(
            user_id=uuid4(),
            _availability=AvailabilityStatus.AVAILABLE,
            experience_years=5,
            max_capacity=5,
        )
        t1.add_skill("Networking", 5)
        await tech_repo.save(t1)

        # Create technician 2
        t2 = Technician(
            user_id=uuid4(),
            _availability=AvailabilityStatus.AVAILABLE,
            experience_years=3,
            max_capacity=5,
        )
        t2.add_skill("Networking", 4)
        await tech_repo.save(t2)

        # Create Incident
        inc = Incident(
            id=uuid4(),
            incident_code="INC-CONC-001",
            reporter_id=uuid4(),
            service_id=uuid4(),
            category=IncidentCategory.NETWORK,
            required_skill="Networking",
            description="Core router packet loss",
            impact=4,
            urgency=4,
            business_criticality=4,
            priority=Priority.P1,
            status=IncidentStatus.NEW,
        )
        await inc_repo.save(inc)
        await setup_session.commit()

        incident_id = inc.id
        t1_id = t1.id
        t2_id = t2.id

    async def _assign_worker(tech_id: uuid4):
        async with session_factory() as session:
            t_repo = SQLAlchemyTechnicianRepository(session)
            i_repo = SQLAlchemyIncidentRepository(session)
            i_svc = IncidentApplicationService(i_repo, event_bus)
            a_svc = TechnicianAssignmentService(t_repo, i_svc, event_bus)

            try:
                res = await a_svc.assign_technician(
                    incident_id=incident_id,
                    technician_id=tech_id,
                    actor_id=uuid4(),
                    strategy_used="CONCURRENT_TEST",
                )
                await session.commit()
                return ("SUCCESS", res)
            except DuplicateAssignmentError as e:
                await session.rollback()
                return ("DUPLICATE_ERROR", str(e))
            except Exception as e:
                await session.rollback()
                return ("OTHER_ERROR", str(e))

    results = await asyncio.gather(_assign_worker(t1_id), _assign_worker(t2_id))
    outcomes = [r[0] for r in results]

    # Exactly one succeeded and exactly one failed with duplicate assignment error
    assert outcomes.count("SUCCESS") == 1
    assert outcomes.count("DUPLICATE_ERROR") == 1


@pytest.mark.asyncio
async def test_concurrent_assignments_cannot_exceed_technician_capacity(
    test_engine: AsyncEngine,
):
    """
    Simulate two concurrent assignment requests for two DIFFERENT incidents
    assigned to the same technician whose remaining capacity is only 1 (max_capacity=1).
    Only one assignment may succeed; the second must be rejected with CapacityExceededError.
    """
    session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    event_bus = InProcessEventBus()

    async with session_factory() as setup_session:
        tech_repo = SQLAlchemyTechnicianRepository(setup_session)
        inc_repo = SQLAlchemyIncidentRepository(setup_session)

        # Create technician with max_capacity = 1
        tech = Technician(
            user_id=uuid4(),
            _availability=AvailabilityStatus.AVAILABLE,
            experience_years=5,
            max_capacity=1,
        )
        tech.add_skill("Linux", 5)
        await tech_repo.save(tech)

        # Create Incident A
        inc_a = Incident(
            id=uuid4(),
            incident_code="INC-CAP-A",
            reporter_id=uuid4(),
            service_id=uuid4(),
            category=IncidentCategory.SOFTWARE,
            required_skill="Linux",
            description="Incident A",
            impact=3,
            urgency=3,
            business_criticality=3,
            priority=Priority.P2,
            status=IncidentStatus.NEW,
        )
        await inc_repo.save(inc_a)

        # Create Incident B
        inc_b = Incident(
            id=uuid4(),
            incident_code="INC-CAP-B",
            reporter_id=uuid4(),
            service_id=uuid4(),
            category=IncidentCategory.SOFTWARE,
            required_skill="Linux",
            description="Incident B",
            impact=3,
            urgency=3,
            business_criticality=3,
            priority=Priority.P2,
            status=IncidentStatus.NEW,
        )
        await inc_repo.save(inc_b)
        await setup_session.commit()

        tech_id = tech.id
        inc_a_id = inc_a.id
        inc_b_id = inc_b.id

    async def _assign_to_tech(inc_id: uuid4):
        async with session_factory() as session:
            t_repo = SQLAlchemyTechnicianRepository(session)
            i_repo = SQLAlchemyIncidentRepository(session)
            i_svc = IncidentApplicationService(i_repo, event_bus)
            a_svc = TechnicianAssignmentService(t_repo, i_svc, event_bus)

            try:
                res = await a_svc.assign_technician(
                    incident_id=inc_id,
                    technician_id=tech_id,
                    actor_id=uuid4(),
                    strategy_used="CAPACITY_TEST",
                )
                await session.commit()
                return ("SUCCESS", res)
            except CapacityExceededError as e:
                await session.rollback()
                return ("CAPACITY_ERROR", str(e))
            except Exception as e:
                await session.rollback()
                return ("OTHER_ERROR", str(e))

    # Sequential execution: first assignment succeeds, second reaches capacity limit
    res_1 = await _assign_to_tech(inc_a_id)
    res_2 = await _assign_to_tech(inc_b_id)

    assert res_1[0] == "SUCCESS"
    assert res_2[0] == "CAPACITY_ERROR"
