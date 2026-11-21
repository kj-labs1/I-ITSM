
"""
Incident repository interface — Member 2.

Repository Pattern:
Defines persistence operations independently of SQLAlchemy.

The application layer depends on this abstraction rather than
directly interacting with the database.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from app.domain.incident.incident import Incident
from app.domain.incident.incident_comment import IncidentComment
from app.shared.enums import IncidentCategory


class IncidentRepository(ABC):
    """Abstract repository for Incident and IncidentComment entities."""

    @abstractmethod
    async def save(self, incident: Incident) -> Incident:
        """Persist a new incident."""
        ...


    @abstractmethod
    async def find_recent_by_service_and_category(
    self,
    service_id: UUID,
    category: IncidentCategory,
    since: datetime,
    until: datetime,
) -> list[Incident]:
        """
    Retrieve incidents from the same service and category
    within the supplied time interval.
    """
    ...
    @abstractmethod
    async def get_by_id(self, incident_id: UUID) -> Incident | None:
        """Retrieve an incident using its UUID."""
        ...

    @abstractmethod
    async def get_by_code(self, incident_code: str) -> Incident | None:
        """Retrieve an incident using its human-readable code."""
        ...

    @abstractmethod
    async def update(self, incident: Incident) -> Incident:
        """Update an existing incident."""
        ...

    @abstractmethod
    async def list_all(
    self,
    skip: int = 0,
    limit: int = 50,
    reporter_id: UUID | None = None,
    incident_id: UUID | None = None,
    incident_code: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    status=None,
    priority=None,
    category: IncidentCategory | None = None,
    service_id: UUID | None = None,
    assigned_technician_id: UUID | None = None,
    is_archived: bool | None = False,
) -> list[Incident]:
        """Retrieve incidents matching the supplied search criteria."""
    ...
    @abstractmethod
    async def count_active_by_technician(
        self,
        technician_user_id: UUID,
    ) -> int:
        """
    Count active incidents assigned to a technician.

    Active statuses:
    - ASSIGNED
    - ACKNOWLEDGED
    - IN_PROGRESS
    """
    ...
    @abstractmethod
    async def save_comment(
        self,
        comment: IncidentComment,
    ) -> IncidentComment:
        """Persist a new incident comment."""
        ...

    @abstractmethod
    async def list_comments(
        self,
        incident_id: UUID,
    ) -> list[IncidentComment]:
        """Retrieve all comments associated with an incident."""
        ...

