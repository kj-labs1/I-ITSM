"""
Incident service integration boundary interface.

OOP Design:
- Interface Segregation: Defines only the incident lifecycle and query capabilities
  required by the assignment and technician engine (M3).
- Member 2 owns the Incident domain model, persistence, and state transitions.
- M3 interacts strictly through this interface rather than manipulating Incident records directly.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.incident.incident_ref import IncidentRef


class IncidentServiceBoundary(ABC):
    """
    Contract for cross-module integration with Member 2 (Incident Management).

    Responsibilities:
    - Provides read-only IncidentRef snapshots for recommendation scoring.
    - Coordinates technician assignment requests to enforce the ASSIGNED lifecycle transition.
    - Provides authoritative active incident counts per technician for workload derivation.
    """

    @abstractmethod
    async def get_incident(self, incident_id: UUID) -> IncidentRef | None:
        """
        Retrieve a read-only projection of an incident by its ID.

        Returns:
            IncidentRef if found, or None if no such incident exists.
        """
        ...

    @abstractmethod
    async def assign_technician(
        self,
        incident_id: UUID,
        technician_id: UUID,
        actor_id: UUID,
    ) -> bool:
        """
        Request Member 2 to assign a technician to the designated incident.

        Preconditions enforced by M2:
        - Incident exists and is in an assignable state (NEW or CLASSIFIED).
        - Incident does not already have an assigned technician.

        Postconditions enforced by M2:
        - Incident status transitions to ASSIGNED.
        - assignedTechnicianId is persisted.
        - Member 2 publishes IncidentStatusChangedEvent.

        Returns:
            True if assignment succeeded.

        Raises:
            IncidentNotFoundError: If incident does not exist.
            InvalidAssignmentError: If incident is not in an assignable state or already assigned.
        """
        ...

    @abstractmethod
    async def get_active_incident_count(self, technician_user_id: UUID) -> int:
        """
        Query the number of open/active incidents assigned to a technician.

        Active incidents are those not in RESOLVED, VERIFIED, or CLOSED states.
        This provides the single source of truth for technician workload calculations.
        """
        ...
