"""
Audit Trail Application Service — Member 4.

OOP Design:
- Single Responsibility Principle: Records and retrieves immutable audit entries.
- Dependency Inversion Principle: Depends solely on ``AuditLogRepository``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.application.interfaces.sla_repositories import AuditLogRepository
from app.domain.sla.audit import AuditLogEntry


class AuditService:
    """Application service for recording and querying incident audit trails."""

    def __init__(self, audit_repo: AuditLogRepository) -> None:
        self._audit_repo = audit_repo

    async def record(
        self,
        incident_id: UUID,
        action: str,
        event_type: str,
        actor_id: UUID | None = None,
        previous_value: str | None = None,
        new_value: str | None = None,
        details: str | None = None,
        occurred_at: datetime | None = None,
    ) -> AuditLogEntry:
        """Persist a new immutable audit log entry."""
        entry = AuditLogEntry(
            incident_id=incident_id,
            action=action,
            event_type=event_type,
            actor_id=actor_id,
            previous_value=previous_value,
            new_value=new_value,
            details=details,
            occurred_at=occurred_at or datetime.now(UTC),
        )
        return await self._audit_repo.create(entry)

    async def get_incident_audit_trail(
        self,
        incident_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> list[AuditLogEntry]:
        """Return chronological audit trail for a specific incident."""
        return await self._audit_repo.list_by_incident(
            incident_id=incident_id,
            skip=skip,
            limit=limit,
        )

    async def query_audit_logs(
        self,
        incident_id: UUID | None = None,
        actor_id: UUID | None = None,
        action: str | None = None,
        event_type: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[AuditLogEntry]:
        """Query audit log records with optional filtering."""
        return await self._audit_repo.list_all(
            incident_id=incident_id,
            actor_id=actor_id,
            action=action,
            event_type=event_type,
            date_from=date_from,
            date_to=date_to,
            skip=skip,
            limit=limit,
        )
