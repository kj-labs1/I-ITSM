
"""
Incident domain events — Member 2.

These events communicate incident lifecycle changes to other modules.

Consumers:
- Member 4: SLA tracking, audit history and notifications.
- Other modules: Incident lifecycle updates where required.

Uses the shared DomainEvent base class and EventPublisher infrastructure.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4

from app.domain.assignment.events import DomainEvent
from app.shared.enums import IncidentCategory, IncidentStatus, Priority


@dataclass(frozen=True)
class IncidentCreatedEvent(DomainEvent):
    """Published when a new incident is created."""

    incident_id: UUID = field(default_factory=uuid4)
    incident_code: str = ""
    reporter_id: UUID = field(default_factory=uuid4)
    service_id: UUID = field(default_factory=uuid4)
    category: IncidentCategory = IncidentCategory.NETWORK
    priority: Priority = Priority.P3


@dataclass(frozen=True)
class IncidentStatusChangedEvent(DomainEvent):
    """Published whenever an incident successfully changes status."""

    incident_id: UUID = field(default_factory=uuid4)
    incident_code: str = ""
    previous_status: IncidentStatus = IncidentStatus.NEW
    new_status: IncidentStatus = IncidentStatus.CLASSIFIED
    actor_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True)
class PriorityChangedEvent(DomainEvent):
    """Published whenever an incident priority changes."""

    incident_id: UUID = field(default_factory=uuid4)
    incident_code: str = ""
    previous_priority: Priority = Priority.P3
    new_priority: Priority = Priority.P2
