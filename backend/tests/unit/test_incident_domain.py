
"""
Unit tests for Member 2 incident domain entities.
"""

from uuid import uuid4

import pytest

from app.domain.incident.incident import Incident
from app.domain.incident.incident_comment import IncidentComment
from app.shared.enums import IncidentCategory, IncidentStatus, Priority


def create_valid_incident(**overrides) -> Incident:
    """Build an incident with valid default test data."""

    data = {
        "incident_code": "INC-1001",
        "reporter_id": uuid4(),
        "service_id": uuid4(),
        "category": IncidentCategory.NETWORK,
        "required_skill": "NETWORK",
        "description": "Campus Wi-Fi is unavailable",
        "impact": 4,
        "urgency": 5,
        "business_criticality": 5,
        "priority": Priority.P1,
    }

    data.update(overrides)

    return Incident(**data)


def test_incident_creation():

    incident = create_valid_incident()

    assert incident.incident_code == "INC-1001"
    assert incident.category == IncidentCategory.NETWORK
    assert incident.priority == Priority.P1
    assert incident.status == IncidentStatus.NEW

    assert incident.id is not None
    assert incident.created_at is not None


def test_incident_has_unique_uuid():

    incident1 = create_valid_incident()
    incident2 = create_valid_incident(
        incident_code="INC-1002"
    )

    assert incident1.id != incident2.id


def test_incident_rejects_empty_description():

    with pytest.raises(ValueError):
        create_valid_incident(description="   ")


@pytest.mark.parametrize(
    "field_name",
    [
        "impact",
        "urgency",
        "business_criticality",
    ],
)
@pytest.mark.parametrize(
    "invalid_value",
    [0, 6, -1, True],
)
def test_incident_rejects_invalid_scores(
    field_name,
    invalid_value,
):

    with pytest.raises(ValueError):
        create_valid_incident(
            **{field_name: invalid_value}
        )


def test_incident_rejects_invalid_category():

    with pytest.raises(ValueError):
        create_valid_incident(category="INVALID")


def test_incident_comment_creation():

    incident_id = uuid4()
    author_id = uuid4()

    comment = IncidentComment(
        incident_id=incident_id,
        author_id=author_id,
        content="Please investigate the network issue.",
    )

    assert comment.incident_id == incident_id
    assert comment.author_id == author_id
    assert comment.content == "Please investigate the network issue."


def test_incident_comment_strips_whitespace():

    comment = IncidentComment(
        incident_id=uuid4(),
        author_id=uuid4(),
        content="   Network connection restored.   ",
    )

    assert comment.content == "Network connection restored."


def test_incident_comment_rejects_empty_content():

    with pytest.raises(ValueError):
        IncidentComment(
            incident_id=uuid4(),
            author_id=uuid4(),
            content="   ",
        )
