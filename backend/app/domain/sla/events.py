"""
SLA domain events — Observer Pattern.

OOP Design:
- Inherits from shared ``DomainEvent`` so Member 4's audit and notification
  listeners react to SLA warnings, breaches, and completions uniformly via
  the shared ``EventPublisher`` / ``InProcessEventBus``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from app.domain.assignment.events import DomainEvent
from app.shared.enums import Priority


@dataclass(frozen=True)
class SLAWarningEvent(DomainEvent):
    """Published when an active incident crosses its SLA warning threshold."""

    incident_id: UUID = field(default_factory=uuid4)
    priority: Priority = Priority.P3
    target_type: str = "RESOLUTION"  # "RESPONSE" or "RESOLUTION"
    due_at: datetime | None = None
    percent_elapsed: float = 0.0
    recipient_user_id: UUID | None = None


@dataclass(frozen=True)
class SLABreachedEvent(DomainEvent):
    """Published when an active incident exceeds its response or resolution SLA."""

    incident_id: UUID = field(default_factory=uuid4)
    priority: Priority = Priority.P3
    breach_type: str = "RESOLUTION"  # "RESPONSE", "RESOLUTION", or "BOTH"
    due_at: datetime | None = None
    overdue_minutes: float = 0.0
    escalation_enabled: bool = True
    recipient_user_id: UUID | None = None


@dataclass(frozen=True)
class SLAMetEvent(DomainEvent):
    """Published when an incident is resolved within its SLA targets."""

    incident_id: UUID = field(default_factory=uuid4)
    priority: Priority = Priority.P3
    resolved_at: datetime | None = None


@dataclass(frozen=True)
class SLAEscalationEvent(DomainEvent):
    """Published when an SLA breach triggers managerial escalation."""

    incident_id: UUID = field(default_factory=uuid4)
    priority: Priority = Priority.P3
    breach_type: str = "RESOLUTION"  # "RESPONSE", "RESOLUTION", or "BOTH"
    due_at: datetime | None = None
    overdue_minutes: float = 0.0
    escalation_level: int = 1
    recipient_user_id: UUID | None = None
