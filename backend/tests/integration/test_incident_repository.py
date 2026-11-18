
"""
Integration tests for SQLAlchemyIncidentRepository.
"""

from uuid import uuid4

import pytest

from app.domain.incident.incident import Incident
from app.domain.incident.incident_comment import IncidentComment
from app.infrastructure.repositories.incident_repository import (
    SQLAlchemyIncidentRepository,
)
from app.shared.enums import IncidentCategory, Priority


def create_test_incident() -> Incident:

    return Incident(
        incident_code="INC-2001",
        reporter_id=uuid4(),
        service_id=uuid4(),
        category=IncidentCategory.NETWORK,
        required_skill="NETWORK",
        description="Wi-Fi unavailable in the library",
        impact=4,
        urgency=5,
        business_criticality=5,
        priority=Priority.P1,
    )


@pytest.mark.asyncio
async def test_save_and_retrieve_incident(db_session):

    repository = SQLAlchemyIncidentRepository(db_session)

    incident = create_test_incident()

    saved = await repository.save(incident)

    assert saved.id == incident.id
    assert saved.incident_code == "INC-2001"

    retrieved = await repository.get_by_id(saved.id)

    assert retrieved is not None
    assert retrieved.id == saved.id
    assert retrieved.category == IncidentCategory.NETWORK
    assert retrieved.priority == Priority.P1


@pytest.mark.asyncio
async def test_retrieve_incident_by_code(db_session):

    repository = SQLAlchemyIncidentRepository(db_session)

    incident = await repository.save(
        create_test_incident()
    )

    retrieved = await repository.get_by_code("INC-2001")

    assert retrieved is not None
    assert retrieved.id == incident.id


@pytest.mark.asyncio
async def test_update_incident(db_session):

    repository = SQLAlchemyIncidentRepository(db_session)

    incident = await repository.save(
        create_test_incident()
    )

    incident.description = "Updated network outage description"
    incident.touch()

    updated = await repository.update(incident)

    assert updated.description == "Updated network outage description"


@pytest.mark.asyncio
async def test_add_and_retrieve_comments(db_session):

    repository = SQLAlchemyIncidentRepository(db_session)

    incident = await repository.save(
        create_test_incident()
    )

    comment = IncidentComment(
        incident_id=incident.id,
        author_id=uuid4(),
        content="Technician is investigating the issue.",
    )

    saved_comment = await repository.save_comment(comment)

    assert saved_comment.incident_id == incident.id

    comments = await repository.list_comments(incident.id)

    assert len(comments) == 1

    assert (
        comments[0].content
        == "Technician is investigating the issue."
    )


@pytest.mark.asyncio
async def test_incident_without_comments_returns_empty_list(
    db_session,
):

    repository = SQLAlchemyIncidentRepository(db_session)

    incident = await repository.save(
        create_test_incident()
    )

    comments = await repository.list_comments(incident.id)

    assert comments == []
