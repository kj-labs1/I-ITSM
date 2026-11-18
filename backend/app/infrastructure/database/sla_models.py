"""
SQLAlchemy 2.x ORM models for Member 4 (SLA, Audit Logs & Notifications).

Database Ownership Boundary:
- Module M4 owns:
  - ``sla_policies``: P1–P4 response and resolution duration targets.
  - ``incident_sla_tracking``: Per-incident SLA deadlines, warning, and breach flags.
  - ``audit_logs``: Immutable chronological event timeline per incident.
  - ``notifications``: Recipient delivery queue and read state.
- ``incident_id`` and ``user_id``/``actor_id`` are maintained as indexed UUID
  logical references so M4 can migrate and test independently before M1 and M2 merge
  (matching M3's ``technicians.user_id`` convention).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.domain.sla.enums import (
    NotificationChannel,
    NotificationDeliveryStatus,
    NotificationType,
    SLAStatus,
)
from app.infrastructure.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.shared.enums import Priority


class SLAPolicyModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Relational model for SLA target policies (P1–P4)."""

    __tablename__ = "sla_policies"

    priority: Mapped[Priority] = mapped_column(
        SAEnum(Priority, name="sla_priority_enum", native_enum=False),
        unique=True,
        nullable=False,
        index=True,
        comment="Shared Priority enum (P1, P2, P3, P4)",
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    response_time_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    resolution_time_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    warning_threshold_percent: Mapped[int] = mapped_column(
        Integer,
        default=80,
        nullable=False,
    )
    escalation_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    trackings: Mapped[list[IncidentSLATrackingModel]] = relationship(
        "IncidentSLATrackingModel",
        back_populates="policy",
    )

    def __repr__(self) -> str:
        return (
            f"<SLAPolicyModel(priority={self.priority}, "
            f"response={self.response_time_minutes}m, resolution={self.resolution_time_minutes}m)>"
        )


class IncidentSLATrackingModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Relational model tracking SLA deadlines and breach state for an incident."""

    __tablename__ = "incident_sla_tracking"
    __table_args__ = (
        Index("ix_incident_sla_tracking_status", "status"),
        Index("ix_incident_sla_tracking_priority", "priority"),
    )

    incident_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        unique=True,
        nullable=False,
        index=True,
        comment="Logical FK to M2 incidents.id",
    )
    policy_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("sla_policies.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    priority: Mapped[Priority] = mapped_column(
        SAEnum(Priority, name="tracking_priority_enum", native_enum=False),
        nullable=False,
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    response_due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolution_due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    first_responded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    response_breached: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    resolution_breached: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    warning_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    breach_notified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[SLAStatus] = mapped_column(
        SAEnum(SLAStatus, name="sla_status_enum", native_enum=False),
        default=SLAStatus.ON_TRACK,
        nullable=False,
    )

    policy: Mapped[SLAPolicyModel] = relationship(
        "SLAPolicyModel",
        back_populates="trackings",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<IncidentSLATrackingModel(incident_id={self.incident_id}, "
            f"status={self.status}, breached={self.response_breached or self.resolution_breached})>"
        )


class AuditLogModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Relational model storing immutable audit trail records."""

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_incident_occurred", "incident_id", "occurred_at"),
        Index("ix_audit_logs_action", "action"),
    )

    incident_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        index=True,
        comment="Logical FK to M2 incidents.id",
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
        index=True,
        comment="Logical FK to M1 users.id",
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    previous_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )

    def __repr__(self) -> str:
        return f"<AuditLogModel(incident_id={self.incident_id}, action={self.action})>"


class NotificationModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Relational model storing recipient notifications and read status."""

    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_user_read", "user_id", "is_read"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        index=True,
        comment="Logical FK to M1 users.id",
    )
    incident_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
        index=True,
        comment="Logical FK to M2 incidents.id",
    )
    channel: Mapped[NotificationChannel] = mapped_column(
        SAEnum(NotificationChannel, name="notification_channel_enum", native_enum=False),
        default=NotificationChannel.IN_APP,
        nullable=False,
    )
    notification_type: Mapped[NotificationType] = mapped_column(
        SAEnum(NotificationType, name="notification_type_enum", native_enum=False),
        default=NotificationType.GENERAL,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivery_status: Mapped[NotificationDeliveryStatus] = mapped_column(
        SAEnum(
            NotificationDeliveryStatus,
            name="notification_delivery_status_enum",
            native_enum=False,
        ),
        default=NotificationDeliveryStatus.PENDING,
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<NotificationModel(id={self.id}, user_id={self.user_id}, is_read={self.is_read})>"
