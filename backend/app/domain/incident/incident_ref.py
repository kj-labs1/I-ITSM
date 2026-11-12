"""
Incident reference integration boundary.

OOP Design: IncidentRef is a value object containing only the incident
information that the assignment engine needs. Member 2 owns the full
Incident entity and lifecycle. Member 3 consumes this read-only reference
for recommendation and assignment operations.

This avoids creating a competing Incident class while providing
type-safe access to required fields.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.shared.enums import IncidentCategory, IncidentStatus, Priority


@dataclass(frozen=True)
class IncidentRef:
    """Read-only reference to an incident for assignment purposes."""

    id: UUID
    incident_code: str
    category: IncidentCategory
    required_skill: str
    priority: Priority
    status: IncidentStatus
    description: str
    service_id: UUID
    reporter_id: UUID
    assigned_technician_id: UUID | None = None
    created_at: datetime | None = None

    @property
    def is_assignable(self) -> bool:
        """Check if the incident is in a state that allows assignment."""
        return (
            self.status in (IncidentStatus.NEW, IncidentStatus.CLASSIFIED)
            and self.assigned_technician_id is None
        )

    @property
    def is_reassignable(self) -> bool:
        """Check if the incident can be reassigned."""
        return self.status in (
            IncidentStatus.NEW,
            IncidentStatus.CLASSIFIED,
            IncidentStatus.ASSIGNED,
        )
