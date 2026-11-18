"""
Audit Log Entry domain entity — Pure Python OOP model.

OOP Design:
- Immutable audit record capturing every significant incident and SLA event.
- Zero external framework dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass(frozen=True)
class AuditLogEntry:
    """Immutable domain entity representing one entry in an incident's audit trail."""

    incident_id: UUID
    action: str
    event_type: str
    actor_id: UUID | None = None
    previous_value: str | None = None
    new_value: str | None = None
    details: str | None = None
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
