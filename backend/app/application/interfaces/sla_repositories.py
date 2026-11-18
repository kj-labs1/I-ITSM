"""
Abstract repository interfaces for Member 4 (SLA, Audit, Notifications).

OOP Design:
- Repository Pattern & Dependency Inversion Principle: Application services
  depend only on these ABCs, decoupling domain workflows from SQLAlchemy.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.sla.audit import AuditLogEntry
from app.domain.sla.enums import SLAStatus
from app.domain.sla.notification import Notification
from app.domain.sla.policy import SLAPolicy
from app.domain.sla.tracking import IncidentSLATracking
from app.shared.enums import Priority


class SLAPolicyRepository(ABC):
    """Persistence contract for SLA policy definitions (P1–P4)."""

    @abstractmethod
    async def get_by_priority(self, priority: Priority) -> SLAPolicy | None:
        ...

    @abstractmethod
    async def get_by_id(self, policy_id: UUID) -> SLAPolicy | None:
        ...

    @abstractmethod
    async def list_all(self) -> list[SLAPolicy]:
        ...

    @abstractmethod
    async def create(self, policy: SLAPolicy) -> SLAPolicy:
        ...

    @abstractmethod
    async def update(self, policy: SLAPolicy) -> SLAPolicy:
        ...


class SLATrackingRepository(ABC):
    """Persistence contract for per-incident SLA tracking records."""

    @abstractmethod
    async def get_by_incident_id(self, incident_id: UUID) -> IncidentSLATracking | None:
        ...

    @abstractmethod
    async def create(self, tracking: IncidentSLATracking) -> IncidentSLATracking:
        ...

    @abstractmethod
    async def update(self, tracking: IncidentSLATracking) -> IncidentSLATracking:
        ...

    @abstractmethod
    async def list_active(self) -> list[IncidentSLATracking]:
        """Return all SLA tracking records that have not yet been resolved."""
        ...

    @abstractmethod
    async def list_violations(
        self,
        include_warnings: bool = False,
        priority: Priority | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[IncidentSLATracking]:
        """Return breached (and optionally warning) SLA tracking records."""
        ...


class AuditLogRepository(ABC):
    """Persistence contract for immutable incident audit log entries."""

    @abstractmethod
    async def create(self, entry: AuditLogEntry) -> AuditLogEntry:
        ...

    @abstractmethod
    async def list_by_incident(
        self,
        incident_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> list[AuditLogEntry]:
        ...

    @abstractmethod
    async def list_all(
        self,
        incident_id: UUID | None = None,
        actor_id: UUID | None = None,
        action: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[AuditLogEntry]:
        ...


class NotificationRepository(ABC):
    """Persistence contract for recipient notification delivery records."""

    @abstractmethod
    async def create(self, notification: Notification) -> Notification:
        ...

    @abstractmethod
    async def get_by_id(self, notification_id: UUID) -> Notification | None:
        ...

    @abstractmethod
    async def list_for_user(
        self,
        user_id: UUID | None = None,
        incident_id: UUID | None = None,
        unread_only: bool = False,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Notification]:
        ...

    @abstractmethod
    async def update(self, notification: Notification) -> Notification:
        ...

    @abstractmethod
    async def mark_all_read(self, user_id: UUID) -> int:
        """Mark all unread notifications for ``user_id`` as read; return count updated."""
        ...
