"""
Assignment domain events — Observer Pattern.

OOP Design: Events decouple the assignment module from audit and notification
concerns. When an assignment occurs, an IncidentAssignedEvent is published.
Member 4 subscribes to these events without the assignment code knowing
about notification or audit implementations.

This demonstrates the Observer Pattern and Dependency Inversion Principle.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass(frozen=True)
class DomainEvent:
    """Base class for domain events. Immutable value objects."""

    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class IncidentAssignedEvent(DomainEvent):
    """
    Published when a technician is assigned to an incident.

    Consumers (owned by M4):
    - AuditListener: creates an audit log entry
    - NotificationListener: notifies technician and reporter

    Event payload agreed with M4:
    - event_id: UUID
    - incident_id: UUID
    - technician_id: UUID (user_id of the assigned technician)
    - actor_id: UUID (user_id of the person who confirmed the assignment)
    - strategy_used: str
    - occurred_at: datetime (UTC)
    """

    incident_id: UUID = field(default_factory=uuid4)
    technician_id: UUID = field(default_factory=uuid4)
    actor_id: UUID = field(default_factory=uuid4)
    strategy_used: str = ""
    explanation: str = ""
    incident_code: str = ""
    reporter_id: UUID | None = None


@dataclass(frozen=True)
class TechnicianAvailabilityChangedEvent(DomainEvent):
    """Published when a technician's availability changes."""

    technician_id: UUID = field(default_factory=uuid4)
    previous_status: str = ""
    new_status: str = ""
