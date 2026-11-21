"""
SQLAlchemy 2.x repository implementations for Member 4 (SLA, Audit, Notifications).

OOP Design:
- Repository Pattern: Implements abstract repository contracts from
  ``app/application/interfaces/sla_repositories.py`` and translates cleanly
  between SQLAlchemy ORM models and pure Python domain entities.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.interfaces.sla_repositories import (
    AuditLogRepository,
    NotificationRepository,
    SLAPolicyRepository,
    SLATrackingRepository,
)
from app.domain.sla.audit import AuditLogEntry
from app.domain.sla.enums import SLAStatus
from app.domain.sla.notification import Notification
from app.domain.sla.policy import SLAPolicy
from app.domain.sla.tracking import IncidentSLATracking
from app.infrastructure.database.sla_models import (
    AuditLogModel,
    IncidentSLATrackingModel,
    NotificationModel,
    SLAPolicyModel,
)
from app.shared.enums import Priority


def _to_domain_policy(model: SLAPolicyModel) -> SLAPolicy:
    return SLAPolicy(
        id=model.id,
        priority=model.priority,
        name=model.name,
        response_time_minutes=model.response_time_minutes,
        resolution_time_minutes=model.resolution_time_minutes,
        warning_threshold_percent=model.warning_threshold_percent,
        escalation_enabled=model.escalation_enabled,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _to_domain_tracking(model: IncidentSLATrackingModel) -> IncidentSLATracking:
    return IncidentSLATracking(
        id=model.id,
        incident_id=model.incident_id,
        policy_id=model.policy_id,
        priority=model.priority,
        started_at=model.started_at,
        response_due_at=model.response_due_at,
        resolution_due_at=model.resolution_due_at,
        first_responded_at=model.first_responded_at,
        resolved_at=model.resolved_at,
        response_breached=model.response_breached,
        resolution_breached=model.resolution_breached,
        warning_sent=model.warning_sent,
        breach_notified=model.breach_notified,
        status=model.status,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _to_domain_audit(model: AuditLogModel) -> AuditLogEntry:
    return AuditLogEntry(
        id=model.id,
        incident_id=model.incident_id,
        actor_id=model.actor_id,
        action=model.action,
        event_type=model.event_type,
        previous_value=model.previous_value,
        new_value=model.new_value,
        details=model.details,
        occurred_at=model.occurred_at,
        created_at=model.created_at,
    )


def _to_domain_notification(model: NotificationModel) -> Notification:
    return Notification(
        id=model.id,
        user_id=model.user_id,
        incident_id=model.incident_id,
        channel=model.channel,
        notification_type=model.notification_type,
        title=model.title,
        message=model.message,
        is_read=model.is_read,
        read_at=model.read_at,
        delivery_status=model.delivery_status,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


class SQLAlchemySLAPolicyRepository(SLAPolicyRepository):
    """Async SQLAlchemy implementation of SLAPolicyRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_priority(self, priority: Priority) -> SLAPolicy | None:
        result = await self._session.execute(
            select(SLAPolicyModel).where(SLAPolicyModel.priority == priority)
        )
        model = result.scalar_one_or_none()
        return _to_domain_policy(model) if model else None

    async def get_by_id(self, policy_id: UUID) -> SLAPolicy | None:
        result = await self._session.execute(
            select(SLAPolicyModel).where(SLAPolicyModel.id == policy_id)
        )
        model = result.scalar_one_or_none()
        return _to_domain_policy(model) if model else None

    async def list_all(self) -> list[SLAPolicy]:
        result = await self._session.execute(
            select(SLAPolicyModel).order_by(SLAPolicyModel.priority.asc())
        )
        return [_to_domain_policy(m) for m in result.scalars().all()]

    async def create(self, policy: SLAPolicy) -> SLAPolicy:
        model = SLAPolicyModel(
            id=policy.id,
            priority=policy.priority,
            name=policy.name,
            response_time_minutes=policy.response_time_minutes,
            resolution_time_minutes=policy.resolution_time_minutes,
            warning_threshold_percent=policy.warning_threshold_percent,
            escalation_enabled=policy.escalation_enabled,
            created_at=policy.created_at,
            updated_at=policy.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _to_domain_policy(model)

    async def update(self, policy: SLAPolicy) -> SLAPolicy:
        result = await self._session.execute(
            select(SLAPolicyModel).where(SLAPolicyModel.id == policy.id)
        )
        model = result.scalar_one()
        model.name = policy.name
        model.response_time_minutes = policy.response_time_minutes
        model.resolution_time_minutes = policy.resolution_time_minutes
        model.warning_threshold_percent = policy.warning_threshold_percent
        model.escalation_enabled = policy.escalation_enabled
        model.updated_at = policy.updated_at
        await self._session.flush()
        await self._session.refresh(model)
        return _to_domain_policy(model)


class SQLAlchemySLATrackingRepository(SLATrackingRepository):
    """Async SQLAlchemy implementation of SLATrackingRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_incident_id(self, incident_id: UUID) -> IncidentSLATracking | None:
        result = await self._session.execute(
            select(IncidentSLATrackingModel).where(
                IncidentSLATrackingModel.incident_id == incident_id
            )
        )
        model = result.scalar_one_or_none()
        return _to_domain_tracking(model) if model else None

    async def create(self, tracking: IncidentSLATracking) -> IncidentSLATracking:
        model = IncidentSLATrackingModel(
            id=tracking.id,
            incident_id=tracking.incident_id,
            policy_id=tracking.policy_id,
            priority=tracking.priority,
            started_at=tracking.started_at,
            response_due_at=tracking.response_due_at,
            resolution_due_at=tracking.resolution_due_at,
            first_responded_at=tracking.first_responded_at,
            resolved_at=tracking.resolved_at,
            response_breached=tracking.response_breached,
            resolution_breached=tracking.resolution_breached,
            warning_sent=tracking.warning_sent,
            breach_notified=tracking.breach_notified,
            status=tracking.status,
            created_at=tracking.created_at,
            updated_at=tracking.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _to_domain_tracking(model)

    async def update(self, tracking: IncidentSLATracking) -> IncidentSLATracking:
        result = await self._session.execute(
            select(IncidentSLATrackingModel).where(
                IncidentSLATrackingModel.id == tracking.id
            )
        )
        model = result.scalar_one()
        model.policy_id = tracking.policy_id
        model.priority = tracking.priority
        model.response_due_at = tracking.response_due_at
        model.resolution_due_at = tracking.resolution_due_at
        model.first_responded_at = tracking.first_responded_at
        model.resolved_at = tracking.resolved_at
        model.response_breached = tracking.response_breached
        model.resolution_breached = tracking.resolution_breached
        model.warning_sent = tracking.warning_sent
        model.breach_notified = tracking.breach_notified
        model.status = tracking.status
        model.updated_at = tracking.updated_at
        await self._session.flush()
        await self._session.refresh(model)
        return _to_domain_tracking(model)

    async def list_active(self) -> list[IncidentSLATracking]:
        result = await self._session.execute(
            select(IncidentSLATrackingModel).where(
                IncidentSLATrackingModel.resolved_at.is_(None),
                IncidentSLATrackingModel.status != SLAStatus.PAUSED,
            )
        )
        return [_to_domain_tracking(m) for m in result.scalars().all()]

    async def list_all(self) -> list[IncidentSLATracking]:
        result = await self._session.execute(
            select(IncidentSLATrackingModel).order_by(IncidentSLATrackingModel.created_at.desc())
        )
        return [_to_domain_tracking(m) for m in result.scalars().all()]

    async def list_violations(
        self,
        include_warnings: bool = False,
        priority: Priority | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[IncidentSLATracking]:
        stmt = select(IncidentSLATrackingModel)
        if include_warnings:
            stmt = stmt.where(
                or_(
                    IncidentSLATrackingModel.status == SLAStatus.BREACHED,
                    IncidentSLATrackingModel.status == SLAStatus.WARNING,
                    IncidentSLATrackingModel.response_breached.is_(True),
                    IncidentSLATrackingModel.resolution_breached.is_(True),
                )
            )
        else:
            stmt = stmt.where(
                or_(
                    IncidentSLATrackingModel.status == SLAStatus.BREACHED,
                    IncidentSLATrackingModel.response_breached.is_(True),
                    IncidentSLATrackingModel.resolution_breached.is_(True),
                )
            )

        if priority is not None:
            stmt = stmt.where(IncidentSLATrackingModel.priority == priority)

        stmt = (
            stmt.order_by(IncidentSLATrackingModel.resolution_due_at.asc())
            .offset(skip)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [_to_domain_tracking(m) for m in result.scalars().all()]


class SQLAlchemyAuditLogRepository(AuditLogRepository):
    """Async SQLAlchemy implementation of AuditLogRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, entry: AuditLogEntry) -> AuditLogEntry:
        model = AuditLogModel(
            id=entry.id,
            incident_id=entry.incident_id,
            actor_id=entry.actor_id,
            action=entry.action,
            event_type=entry.event_type,
            previous_value=entry.previous_value,
            new_value=entry.new_value,
            details=entry.details,
            occurred_at=entry.occurred_at,
            created_at=entry.created_at,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _to_domain_audit(model)

    async def list_by_incident(
        self,
        incident_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> list[AuditLogEntry]:
        result = await self._session.execute(
            select(AuditLogModel)
            .where(AuditLogModel.incident_id == incident_id)
            .order_by(AuditLogModel.occurred_at.asc())
            .offset(skip)
            .limit(limit)
        )
        return [_to_domain_audit(m) for m in result.scalars().all()]

    async def list_all(
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
        stmt = select(AuditLogModel)
        if incident_id is not None:
            stmt = stmt.where(AuditLogModel.incident_id == incident_id)
        if actor_id is not None:
            stmt = stmt.where(AuditLogModel.actor_id == actor_id)
        if action is not None:
            stmt = stmt.where(AuditLogModel.action == action)
        if event_type is not None:
            stmt = stmt.where(AuditLogModel.event_type == event_type)
        if date_from is not None:
            stmt = stmt.where(AuditLogModel.occurred_at >= date_from)
        if date_to is not None:
            stmt = stmt.where(AuditLogModel.occurred_at <= date_to)

        stmt = stmt.order_by(AuditLogModel.occurred_at.desc()).offset(skip).limit(limit)
        result = await self._session.execute(stmt)
        return [_to_domain_audit(m) for m in result.scalars().all()]


class SQLAlchemyNotificationRepository(NotificationRepository):
    """Async SQLAlchemy implementation of NotificationRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, notification: Notification) -> Notification:
        model = NotificationModel(
            id=notification.id,
            user_id=notification.user_id,
            incident_id=notification.incident_id,
            channel=notification.channel,
            notification_type=notification.notification_type,
            title=notification.title,
            message=notification.message,
            is_read=notification.is_read,
            read_at=notification.read_at,
            delivery_status=notification.delivery_status,
            created_at=notification.created_at,
            updated_at=notification.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _to_domain_notification(model)

    async def get_by_id(self, notification_id: UUID) -> Notification | None:
        result = await self._session.execute(
            select(NotificationModel).where(NotificationModel.id == notification_id)
        )
        model = result.scalar_one_or_none()
        return _to_domain_notification(model) if model else None

    async def list_for_user(
        self,
        user_id: UUID | None = None,
        incident_id: UUID | None = None,
        unread_only: bool = False,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Notification]:
        stmt = select(NotificationModel)
        if user_id is not None:
            stmt = stmt.where(NotificationModel.user_id == user_id)
        if incident_id is not None:
            stmt = stmt.where(NotificationModel.incident_id == incident_id)
        if unread_only:
            stmt = stmt.where(NotificationModel.is_read.is_(False))

        stmt = stmt.order_by(NotificationModel.created_at.desc()).offset(skip).limit(limit)
        result = await self._session.execute(stmt)
        return [_to_domain_notification(m) for m in result.scalars().all()]

    async def update(self, notification: Notification) -> Notification:
        result = await self._session.execute(
            select(NotificationModel).where(NotificationModel.id == notification.id)
        )
        model = result.scalar_one()
        model.is_read = notification.is_read
        model.read_at = notification.read_at
        model.delivery_status = notification.delivery_status
        model.updated_at = notification.updated_at
        await self._session.flush()
        await self._session.refresh(model)
        return _to_domain_notification(model)

    async def mark_all_read(self, user_id: UUID) -> int:
        now = datetime.now(UTC)
        result = await self._session.execute(
            update(NotificationModel)
            .where(
                NotificationModel.user_id == user_id,
                NotificationModel.is_read.is_(False),
            )
            .values(is_read=True, read_at=now, updated_at=now)
        )
        await self._session.flush()
        return int(result.rowcount or 0)

    async def count_unread(self, user_id: UUID) -> int:
        result = await self._session.execute(
            select(func.count()).select_from(NotificationModel).where(
                NotificationModel.user_id == user_id,
                NotificationModel.is_read.is_(False),
            )
        )
        return int(result.scalar_one() or 0)
