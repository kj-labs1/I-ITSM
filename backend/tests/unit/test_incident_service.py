
"""
Unit/integration tests for IncidentApplicationService.

Uses the existing in-memory SQLite database fixture.
"""

from uuid import uuid4

import pytest

from app.application.incident.service import IncidentApplicationService
from app.core.exceptions import (
    DuplicateAssignmentError,
    InvalidStatusTransitionError,
    ValidationError,
)
from app.domain.incident.events import (
    IncidentCreatedEvent,
    IncidentStatusChangedEvent,
)
from app.infrastructure.repositories.incident_repository import (
    SQLAlchemyIncidentRepository,
)
from app.shared.enums import (
    IncidentCategory,
    IncidentStatus,
    Priority,
)


def make_service(db_session, event_bus):

    repository = SQLAlchemyIncidentRepository(db_session)

    return IncidentApplicationService(
        repository=repository,
        event_publisher=event_bus,
    )


@pytest.mark.asyncio
async def test_create_incident(db_session, event_bus):

    service = make_service(db_session, event_bus)

    reporter_id = uuid4()
    service_id = uuid4()

    incident = await service.create_incident(
        reporter_id=reporter_id,
        service_id=service_id,
        category=IncidentCategory.NETWORK,
        required_skill="NETWORK",
        description="Campus Wi-Fi is unavailable",
        impact=4,
        urgency=5,
        business_criticality=5,
    )

    assert incident.reporter_id == reporter_id
    assert incident.service_id == service_id

    assert incident.priority == Priority.P1
    assert incident.status == IncidentStatus.NEW

    assert incident.incident_code.startswith("INC-")


@pytest.mark.asyncio
async def test_create_publishes_event(db_session, event_bus):

    service = make_service(db_session, event_bus)

    captured_events = []

    class TestListener:
        async def handle(self, event):
            captured_events.append(event)

    event_bus.subscribe(IncidentCreatedEvent, TestListener())

    incident = await service.create_incident(
        reporter_id=uuid4(),
        service_id=uuid4(),
        category=IncidentCategory.SOFTWARE,
        required_skill="SOFTWARE",
        description="Application is not responding",
        impact=3,
        urgency=3,
        business_criticality=3,
    )

    assert len(captured_events) == 1
    assert isinstance(captured_events[0], IncidentCreatedEvent)
    assert captured_events[0].incident_id == incident.id


@pytest.mark.asyncio
async def test_get_incident(db_session, event_bus):

    service = make_service(db_session, event_bus)

    created = await service.create_incident(
        reporter_id=uuid4(),
        service_id=uuid4(),
        category=IncidentCategory.HARDWARE,
        required_skill="HARDWARE",
        description="Printer is not working",
        impact=2,
        urgency=2,
        business_criticality=2,
    )

    retrieved = await service.get_incident_entity(created.id)

    assert retrieved.id == created.id
    assert retrieved.incident_code == created.incident_code


@pytest.mark.asyncio
async def test_list_incidents_by_reporter(db_session, event_bus):

    service = make_service(db_session, event_bus)

    reporter_id = uuid4()

    await service.create_incident(
        reporter_id=reporter_id,
        service_id=uuid4(),
        category=IncidentCategory.NETWORK,
        required_skill="NETWORK",
        description="First incident",
        impact=2,
        urgency=2,
        business_criticality=2,
    )

    await service.create_incident(
        reporter_id=uuid4(),
        service_id=uuid4(),
        category=IncidentCategory.SOFTWARE,
        required_skill="SOFTWARE",
        description="Another employee's incident",
        impact=3,
        urgency=3,
        business_criticality=3,
    )

    results = await service.list_incidents(
        reporter_id=reporter_id
    )

    assert len(results) == 1
    assert results[0].reporter_id == reporter_id


@pytest.mark.asyncio
async def test_update_incident_recalculates_priority(
    db_session,
    event_bus,
):

    service = make_service(db_session, event_bus)

    incident = await service.create_incident(
        reporter_id=uuid4(),
        service_id=uuid4(),
        category=IncidentCategory.NETWORK,
        required_skill="NETWORK",
        description="Slow network connection",
        impact=2,
        urgency=2,
        business_criticality=2,
    )

    assert incident.priority == Priority.P4

    updated = await service.update_incident(
        incident_id=incident.id,
        changes={
            "impact": 5,
            "urgency": 5,
            "description": "Complete network failure",
        },
    )

    assert updated.priority == Priority.P2
    assert updated.description == "Complete network failure"


@pytest.mark.asyncio
async def test_invalid_incident_update_is_rejected(
    db_session,
    event_bus,
):

    service = make_service(db_session, event_bus)

    incident = await service.create_incident(
        reporter_id=uuid4(),
        service_id=uuid4(),
        category=IncidentCategory.NETWORK,
        required_skill="NETWORK",
        description="Network problem",
        impact=2,
        urgency=2,
        business_criticality=2,
    )

    from app.core.exceptions import ValidationError

    with pytest.raises(ValidationError):

        await service.update_incident(
            incident_id=incident.id,
            changes={
                "impact": 10,
            },
        )


@pytest.mark.asyncio
async def test_status_update_publishes_event(
    db_session,
    event_bus,
):

    service = make_service(db_session, event_bus)

    captured_events = []

    class TestListener:
        async def handle(self, event):
            captured_events.append(event)

    event_bus.subscribe(
        IncidentStatusChangedEvent,
        TestListener(),
    )

    incident = await service.create_incident(
        reporter_id=uuid4(),
        service_id=uuid4(),
        category=IncidentCategory.DATABASE,
        required_skill="DATABASE",
        description="Database is unavailable",
        impact=5,
        urgency=5,
        business_criticality=5,
    )

    updated = await service.update_incident_status(
        incident_id=incident.id,
        new_status=IncidentStatus.CLASSIFIED,
        actor_id=incident.reporter_id,
    )

    assert updated.status == IncidentStatus.CLASSIFIED

    assert len(captured_events) == 1
    assert isinstance(
        captured_events[0],
        IncidentStatusChangedEvent,
    )


@pytest.mark.asyncio
async def test_invalid_status_update_is_rejected(
    db_session,
    event_bus,
):

    service = make_service(db_session, event_bus)

    incident = await service.create_incident(
        reporter_id=uuid4(),
        service_id=uuid4(),
        category=IncidentCategory.DATABASE,
        required_skill="DATABASE",
        description="Database problem",
        impact=3,
        urgency=3,
        business_criticality=3,
    )

    with pytest.raises(InvalidStatusTransitionError):

        await service.update_incident_status(
            incident_id=incident.id,
            new_status=IncidentStatus.CLOSED,
            actor_id=incident.reporter_id,
        )


@pytest.mark.asyncio
async def test_add_comment(db_session, event_bus):

    service = make_service(db_session, event_bus)

    incident = await service.create_incident(
        reporter_id=uuid4(),
        service_id=uuid4(),
        category=IncidentCategory.HARDWARE,
        required_skill="HARDWARE",
        description="System is not booting",
        impact=3,
        urgency=4,
        business_criticality=3,
    )

    author_id = uuid4()

    comment = await service.add_comment(
        incident_id=incident.id,
        author_id=author_id,
        content="Investigating the hardware issue.",
    )

    assert comment.incident_id == incident.id
    assert comment.author_id == author_id


@pytest.mark.asyncio
async def test_member3_assignment_boundary(
    db_session,
    event_bus,
):

    service = make_service(db_session, event_bus)

    incident = await service.create_incident(
        reporter_id=uuid4(),
        service_id=uuid4(),
        category=IncidentCategory.NETWORK,
        required_skill="NETWORK",
        description="Network is down",
        impact=4,
        urgency=5,
        business_criticality=5,
    )

    technician_user_id = uuid4()

    result = await service.assign_technician(
        incident_id=incident.id,
        technician_id=technician_user_id,
        actor_id=uuid4(),
    )

    assert result is True

    updated = await service.get_incident_entity(incident.id)

    assert updated.status == IncidentStatus.ASSIGNED
    assert updated.assigned_technician_id == technician_user_id

    active_count = await service.get_active_incident_count(
        technician_user_id
    )

    assert active_count == 1


@pytest.mark.asyncio
async def test_duplicate_assignment_rejected(
    db_session,
    event_bus,
):

    service = make_service(db_session, event_bus)

    incident = await service.create_incident(
        reporter_id=uuid4(),
        service_id=uuid4(),
        category=IncidentCategory.NETWORK,
        required_skill="NETWORK",
        description="Network failure",
        impact=4,
        urgency=4,
        business_criticality=4,
    )

    technician_id = uuid4()

    await service.assign_technician(
        incident_id=incident.id,
        technician_id=technician_id,
        actor_id=uuid4(),
    )

    from app.core.exceptions import DuplicateAssignmentError

    with pytest.raises(DuplicateAssignmentError):

        await service.assign_technician(
            incident_id=incident.id,
            technician_id=technician_id,
            actor_id=uuid4(),
        )
