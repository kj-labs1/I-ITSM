
"""
Unit tests for Member 2 IncidentLifecycle.

Tests:
- Allowed transitions.
- Invalid transitions.
- Terminal CLOSED state.
- Resolution details validation.
- Incident entity integration.
- Timestamp updates.
"""

from uuid import uuid4

import pytest

from app.core.exceptions import (
    InvalidStatusTransitionError,
    ValidationError,
)
from app.domain.incident.incident import Incident
from app.domain.incident.lifecycle import IncidentLifecycle
from app.shared.enums import (
    IncidentCategory,
    IncidentStatus,
    Priority,
)


def create_test_incident(
    status: IncidentStatus = IncidentStatus.NEW,
) -> Incident:
    """Create a valid incident for lifecycle tests."""

    return Incident(
        incident_code="INC-4001",
        reporter_id=uuid4(),
        service_id=uuid4(),
        category=IncidentCategory.NETWORK,
        required_skill="NETWORK",
        description="Campus network is unavailable",
        impact=4,
        urgency=5,
        business_criticality=5,
        priority=Priority.P1,
        status=status,
    )


# ============================================================
# VALID TRANSITION TESTS
# ============================================================


@pytest.mark.parametrize(
    "current_status, new_status",
    [
        (IncidentStatus.NEW, IncidentStatus.CLASSIFIED),
        (IncidentStatus.NEW, IncidentStatus.ASSIGNED),
        (IncidentStatus.CLASSIFIED, IncidentStatus.ASSIGNED),
        (IncidentStatus.ASSIGNED, IncidentStatus.ACKNOWLEDGED),
        (IncidentStatus.ACKNOWLEDGED, IncidentStatus.IN_PROGRESS),
        (IncidentStatus.IN_PROGRESS, IncidentStatus.RESOLVED),
        (IncidentStatus.RESOLVED, IncidentStatus.VERIFIED),
        (IncidentStatus.VERIFIED, IncidentStatus.CLOSED),
    ],
)
def test_valid_transitions(
    current_status,
    new_status,
):
    """All permitted transitions should return True."""

    assert IncidentLifecycle.can_transition(
        current_status,
        new_status,
    ) is True


# ============================================================
# INVALID TRANSITION TESTS
# ============================================================


@pytest.mark.parametrize(
    "current_status, new_status",
    [
        (IncidentStatus.NEW, IncidentStatus.CLOSED),
        (IncidentStatus.NEW, IncidentStatus.RESOLVED),
        (IncidentStatus.CLASSIFIED, IncidentStatus.CLOSED),
        (IncidentStatus.ASSIGNED, IncidentStatus.RESOLVED),
        (IncidentStatus.ACKNOWLEDGED, IncidentStatus.CLOSED),
        (IncidentStatus.IN_PROGRESS, IncidentStatus.VERIFIED),
        (IncidentStatus.RESOLVED, IncidentStatus.ASSIGNED),
        (IncidentStatus.VERIFIED, IncidentStatus.IN_PROGRESS),
        (IncidentStatus.CLOSED, IncidentStatus.IN_PROGRESS),
        (IncidentStatus.CLOSED, IncidentStatus.NEW),
        (IncidentStatus.NEW, IncidentStatus.NEW),
    ],
)
def test_invalid_transitions(
    current_status,
    new_status,
):
    """Forbidden transitions should return False."""

    assert IncidentLifecycle.can_transition(
        current_status,
        new_status,
    ) is False


def test_invalid_transition_raises_exception():

    with pytest.raises(InvalidStatusTransitionError) as exc_info:

        IncidentLifecycle.validate_transition(
            IncidentStatus.NEW,
            IncidentStatus.CLOSED,
            incident_code="INC-4001",
        )

    error = exc_info.value

    assert error.status_code == 409
    assert error.error_code == "INVALID_STATUS_TRANSITION"

    assert (
        "NEW to CLOSED"
        in error.message
    )


# ============================================================
# ALLOWED TRANSITIONS QUERY
# ============================================================


def test_get_allowed_transitions():

    allowed = IncidentLifecycle.get_allowed_transitions(
        IncidentStatus.NEW
    )

    assert allowed == frozenset({
        IncidentStatus.CLASSIFIED,
        IncidentStatus.ASSIGNED,
    })


def test_closed_has_no_allowed_transitions():

    allowed = IncidentLifecycle.get_allowed_transitions(
        IncidentStatus.CLOSED
    )

    assert allowed == frozenset()


# ============================================================
# INCIDENT ENTITY INTEGRATION
# ============================================================


def test_incident_successful_transition():

    incident = create_test_incident()

    previous_updated_at = incident.updated_at

    result = incident.transition_to(
        IncidentStatus.CLASSIFIED
    )

    assert result == IncidentStatus.CLASSIFIED
    assert incident.status == IncidentStatus.CLASSIFIED
    assert incident.updated_at >= previous_updated_at


def test_incident_assignment_transition_from_new():

    incident = create_test_incident()

    incident.transition_to(
        IncidentStatus.ASSIGNED
    )

    assert incident.status == IncidentStatus.ASSIGNED


def test_incident_invalid_transition_does_not_change_status():

    incident = create_test_incident()

    original_status = incident.status
    original_updated_at = incident.updated_at

    with pytest.raises(InvalidStatusTransitionError):

        incident.transition_to(
            IncidentStatus.CLOSED
        )

    assert incident.status == original_status
    assert incident.updated_at == original_updated_at


# ============================================================
# RESOLUTION DETAILS VALIDATION
# ============================================================


def test_resolution_without_details_is_rejected():

    incident = create_test_incident(
        status=IncidentStatus.IN_PROGRESS
    )

    with pytest.raises(ValidationError) as exc_info:

        incident.transition_to(
            IncidentStatus.RESOLVED
        )

    assert exc_info.value.error_code == "RESOLUTION_DETAILS_REQUIRED"

    # Status must remain unchanged.
    assert incident.status == IncidentStatus.IN_PROGRESS


def test_resolution_with_details_succeeds():

    incident = create_test_incident(
        status=IncidentStatus.IN_PROGRESS
    )

    incident.transition_to(
        IncidentStatus.RESOLVED,
        resolution_details="Network configuration repaired.",
    )

    assert incident.status == IncidentStatus.RESOLVED

    assert (
        incident.resolution_details
        == "Network configuration repaired."
    )


def test_resolution_details_are_trimmed():

    incident = create_test_incident(
        status=IncidentStatus.IN_PROGRESS
    )

    incident.transition_to(
        IncidentStatus.RESOLVED,
        resolution_details="   Router restarted successfully.   ",
    )

    assert (
        incident.resolution_details
        == "Router restarted successfully."
    )


def test_blank_resolution_details_are_rejected():

    incident = create_test_incident(
        status=IncidentStatus.IN_PROGRESS
    )

    with pytest.raises(ValidationError):

        incident.transition_to(
            IncidentStatus.RESOLVED,
            resolution_details="   ",
        )

    assert incident.status == IncidentStatus.IN_PROGRESS


# ============================================================
# COMPLETE LIFECYCLE TEST
# ============================================================


def test_complete_incident_lifecycle():

    incident = create_test_incident()

    # Employee reports an incident.
    assert incident.status == IncidentStatus.NEW

    # Incident is classified.
    incident.transition_to(
        IncidentStatus.CLASSIFIED
    )

    # Technician is assigned.
    incident.transition_to(
        IncidentStatus.ASSIGNED
    )

    # Technician acknowledges.
    incident.transition_to(
        IncidentStatus.ACKNOWLEDGED
    )

    # Technician begins investigation.
    incident.transition_to(
        IncidentStatus.IN_PROGRESS
    )

    # Technician resolves the issue.
    incident.transition_to(
        IncidentStatus.RESOLVED,
        resolution_details="Network router configuration corrected.",
    )

    # Employee verifies the resolution.
    incident.transition_to(
        IncidentStatus.VERIFIED
    )

    # Employee closes the incident.
    incident.transition_to(
        IncidentStatus.CLOSED
    )

    assert incident.status == IncidentStatus.CLOSED
    assert incident.resolution_details == (
        "Network router configuration corrected."
    )
