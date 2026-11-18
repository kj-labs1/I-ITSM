
"""
Incident lifecycle state machine — Member 2.

Controls valid incident status transitions.

Lifecycle:
    NEW -> CLASSIFIED -> ASSIGNED
    -> ACKNOWLEDGED -> IN_PROGRESS
    -> RESOLVED -> VERIFIED -> CLOSED

Integration:
    NEW -> ASSIGNED is also supported because Member 3's
    assignment contract permits assignment from NEW or CLASSIFIED.

Invalid transitions raise InvalidStatusTransitionError.
"""

from __future__ import annotations

from app.core.exceptions import InvalidStatusTransitionError
from app.shared.enums import IncidentStatus


class IncidentLifecycle:
    """
    Encapsulates the valid state transitions of an incident.

    OOP principles:
    - Encapsulation: All transition rules are maintained in one class.
    - Abstraction: Other components use can_transition() and
      validate_transition() without knowing the internal mapping.
    - Single Responsibility: Only manages lifecycle transition rules.
    """

    ALLOWED_TRANSITIONS: dict[
        IncidentStatus,
        frozenset[IncidentStatus],
    ] = {
        IncidentStatus.NEW: frozenset({
            IncidentStatus.CLASSIFIED,
            IncidentStatus.ASSIGNED,
        }),

        IncidentStatus.CLASSIFIED: frozenset({
            IncidentStatus.ASSIGNED,
        }),

        IncidentStatus.ASSIGNED: frozenset({
            IncidentStatus.ACKNOWLEDGED,
        }),

        IncidentStatus.ACKNOWLEDGED: frozenset({
            IncidentStatus.IN_PROGRESS,
        }),

        IncidentStatus.IN_PROGRESS: frozenset({
            IncidentStatus.RESOLVED,
        }),

        IncidentStatus.RESOLVED: frozenset({
            IncidentStatus.VERIFIED,
        }),

        IncidentStatus.VERIFIED: frozenset({
            IncidentStatus.CLOSED,
        }),

        # CLOSED is a terminal state.
        IncidentStatus.CLOSED: frozenset(),
    }

    @classmethod
    def can_transition(
        cls,
        current_status: IncidentStatus,
        new_status: IncidentStatus,
    ) -> bool:
        """
        Check whether a particular status transition is permitted.

        Returns:
            True if the transition is allowed, False otherwise.
        """

        if (
            not isinstance(current_status, IncidentStatus)
            or not isinstance(new_status, IncidentStatus)
        ):
            return False

        allowed = cls.ALLOWED_TRANSITIONS.get(
            current_status,
            frozenset(),
        )

        return new_status in allowed

    @classmethod
    def get_allowed_transitions(
        cls,
        current_status: IncidentStatus,
    ) -> frozenset[IncidentStatus]:
        """
        Return all statuses that can follow the current status.
        """

        if not isinstance(current_status, IncidentStatus):
            return frozenset()

        return cls.ALLOWED_TRANSITIONS.get(
            current_status,
            frozenset(),
        )

    @classmethod
    def validate_transition(
        cls,
        current_status: IncidentStatus,
        new_status: IncidentStatus,
        incident_code: str | None = None,
    ) -> None:
        """
        Validate a transition.

        Raises:
            InvalidStatusTransitionError if the transition is invalid.
        """

        if cls.can_transition(current_status, new_status):
            return

        current = (
            current_status.value
            if isinstance(current_status, IncidentStatus)
            else str(current_status)
        )

        requested = (
            new_status.value
            if isinstance(new_status, IncidentStatus)
            else str(new_status)
        )

        

        raise InvalidStatusTransitionError(
            current_status=current,
            requested_status=requested,
            incident_code=incident_code,
        )
