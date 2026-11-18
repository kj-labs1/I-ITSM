"""
Unit tests for Member 4 Observer Pattern event listeners with InProcessEventBus.

Uses lightweight in-memory repository doubles so Observer Pattern behavior is
verified without touching any database.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from uuid import UUID, uuid4

import pytest

from app.application.interfaces.sla_repositories import (
    AuditLogRepository,
    NotificationRepository,
    SLAPolicyRepository,
    SLATrackingRepository,
)
from app.application.sla.audit_service import AuditService
from app.application.sla.listeners import (
    AuditEventListener,
    NotificationEventListener,
    SLALifecycleEventListener,
)
from app.application.sla.notification_service import NotificationService
from app.application.sla.sla_service import SLAService
from app.domain.assignment.events import DomainEvent, IncidentAssignedEvent
from app.domain.sla.audit import AuditLogEntry
from app.domain.sla.enums import AuditAction, NotificationType, SLAStatus
from app.domain.sla.events import SLABreachedEvent, SLAWarningEvent
from app.domain.sla.notification import Notification
from app.domain.sla.policy import SLAPolicy
from app.domain.sla.tracking import IncidentSLATracking
from app.infrastructure.events.event_bus import InProcessEventBus
from app.shared.enums import IncidentStatus, Priority

# ── In-Memory Repository Doubles ──────────────────────────────────────────────


class InMemoryPolicyRepo(SLAPolicyRepository):
    def __init__(self) -> None:
        self.items: dict[Priority, SLAPolicy] = {}

    async def get_by_priority(self, priority: Priority) -> SLAPolicy | None:
        return self.items.get(priority)

    async def get_by_id(self, policy_id: UUID) -> SLAPolicy | None:
        return next((p for p in self.items.values() if p.id == policy_id), None)

    async def list_all(self) -> list[SLAPolicy]:
        return list(self.items.values())

    async def create(self, policy: SLAPolicy) -> SLAPolicy:
        self.items[policy.priority] = policy
        return policy

    async def update(self, policy: SLAPolicy) -> SLAPolicy:
        self.items[policy.priority] = policy
        return policy


class InMemoryTrackingRepo(SLATrackingRepository):
    def __init__(self) -> None:
        self.items: dict[UUID, IncidentSLATracking] = {}

    async def get_by_incident_id(self, incident_id: UUID) -> IncidentSLATracking | None:
        return self.items.get(incident_id)

    async def create(self, tracking: IncidentSLATracking) -> IncidentSLATracking:
        self.items[tracking.incident_id] = tracking
        return tracking

    async def update(self, tracking: IncidentSLATracking) -> IncidentSLATracking:
        self.items[tracking.incident_id] = tracking
        return tracking

    async def list_active(self) -> list[IncidentSLATracking]:
        return [t for t in self.items.values() if t.resolved_at is None]

    async def list_violations(
        self,
        include_warnings: bool = False,
        priority: Priority | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[IncidentSLATracking]:
        out = []
        for t in self.items.values():
            if (t.is_breached or (include_warnings and t.status == SLAStatus.WARNING)) and (
                priority is None or t.priority == priority
            ):
                out.append(t)
        return out[skip : skip + limit]


class InMemoryAuditRepo(AuditLogRepository):
    def __init__(self) -> None:
        self.entries: list[AuditLogEntry] = []

    async def create(self, entry: AuditLogEntry) -> AuditLogEntry:
        self.entries.append(entry)
        return entry

    async def list_by_incident(
        self, incident_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[AuditLogEntry]:
        matched = [e for e in self.entries if e.incident_id == incident_id]
        return matched[skip : skip + limit]

    async def list_all(
        self,
        incident_id: UUID | None = None,
        actor_id: UUID | None = None,
        action: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[AuditLogEntry]:
        matched = self.entries
        if incident_id:
            matched = [e for e in matched if e.incident_id == incident_id]
        if actor_id:
            matched = [e for e in matched if e.actor_id == actor_id]
        if action:
            matched = [e for e in matched if e.action == action]
        return matched[skip : skip + limit]


class InMemoryNotificationRepo(NotificationRepository):
    def __init__(self) -> None:
        self.items: dict[UUID, Notification] = {}

    async def create(self, notification: Notification) -> Notification:
        self.items[notification.id] = notification
        return notification

    async def get_by_id(self, notification_id: UUID) -> Notification | None:
        return self.items.get(notification_id)

    async def list_for_user(
        self,
        user_id: UUID | None = None,
        incident_id: UUID | None = None,
        unread_only: bool = False,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Notification]:
        matched = list(self.items.values())
        if user_id:
            matched = [n for n in matched if n.user_id == user_id]
        if incident_id:
            matched = [n for n in matched if n.incident_id == incident_id]
        if unread_only:
            matched = [n for n in matched if not n.is_read]
        return matched[skip : skip + limit]

    async def update(self, notification: Notification) -> Notification:
        self.items[notification.id] = notification
        return notification

    async def mark_all_read(self, user_id: UUID) -> int:
        count = 0
        for n in self.items.values():
            if n.user_id == user_id and not n.is_read:
                n.mark_as_read()
                count += 1
        return count


@dataclass(frozen=True)
class IncidentStatusChangedEvent(DomainEvent):
    """Test double matching Member 2's IncidentStatusChangedEvent contract."""

    incident_id: UUID = field(default_factory=uuid4)
    incident_code: str = "INC-1001"
    previous_status: IncidentStatus = IncidentStatus.ASSIGNED
    new_status: IncidentStatus = IncidentStatus.RESOLVED
    actor_id: UUID = field(default_factory=uuid4)


@pytest.mark.asyncio
async def test_observer_listeners_react_to_assignment_and_sla_events() -> None:
    bus = InProcessEventBus()
    policy_repo = InMemoryPolicyRepo()
    tracking_repo = InMemoryTrackingRepo()
    audit_repo = InMemoryAuditRepo()
    notif_repo = InMemoryNotificationRepo()

    sla_service = SLAService(policy_repo, tracking_repo, bus)
    audit_service = AuditService(audit_repo)
    notif_service = NotificationService(notif_repo)

    @asynccontextmanager
    async def sla_ctx():
        yield sla_service

    @asynccontextmanager
    async def audit_ctx():
        yield audit_service

    @asynccontextmanager
    async def notif_ctx():
        yield notif_service

    bus.subscribe(DomainEvent, AuditEventListener(audit_ctx))
    bus.subscribe(DomainEvent, NotificationEventListener(notif_ctx))
    bus.subscribe(DomainEvent, SLALifecycleEventListener(sla_ctx))

    incident_id = uuid4()
    tech_user_id = uuid4()
    actor_id = uuid4()

    # 1. Publish Member 3 IncidentAssignedEvent
    await bus.publish(
        IncidentAssignedEvent(
            incident_id=incident_id,
            technician_id=tech_user_id,
            actor_id=actor_id,
            strategy_used="SKILL_BASED",
            explanation="Best skill match",
        )
    )

    assert len(audit_repo.entries) == 1
    assert audit_repo.entries[0].action == AuditAction.INCIDENT_ASSIGNED.value
    assert tracking_repo.items[incident_id].status == SLAStatus.ON_TRACK

    tech_notifs = await notif_repo.list_for_user(user_id=tech_user_id)
    assert len(tech_notifs) == 1
    assert tech_notifs[0].notification_type == NotificationType.INCIDENT_ASSIGNED

    # 2. Publish SLAWarningEvent & SLABreachedEvent
    await bus.publish(
        SLAWarningEvent(
            incident_id=incident_id,
            priority=Priority.P1,
            target_type="RESPONSE",
            percent_elapsed=85.0,
            recipient_user_id=tech_user_id,
        )
    )
    await bus.publish(
        SLABreachedEvent(
            incident_id=incident_id,
            priority=Priority.P1,
            breach_type="RESPONSE",
            overdue_minutes=12.5,
            escalation_enabled=True,
            recipient_user_id=tech_user_id,
        )
    )

    # Audit trail should now have assignment + warning + breach
    actions = [e.action for e in audit_repo.entries]
    assert AuditAction.SLA_WARNING_TRIGGERED.value in actions
    assert AuditAction.SLA_BREACHED.value in actions

    # Breach with escalation_enabled=True generates both IN_APP breach + EMAIL escalation
    all_notifs = await notif_repo.list_for_user()
    notif_types = {n.notification_type for n in all_notifs}
    assert NotificationType.SLA_WARNING in notif_types
    assert NotificationType.SLA_BREACHED in notif_types
    assert NotificationType.ESCALATION in notif_types

    # 3. Publish Member 2 IncidentStatusChangedEvent -> RESOLVED
    await bus.publish(
        IncidentStatusChangedEvent(
            incident_id=incident_id,
            previous_status=IncidentStatus.IN_PROGRESS,
            new_status=IncidentStatus.RESOLVED,
            actor_id=tech_user_id,
        )
    )
    assert tracking_repo.items[incident_id].resolved_at is not None
