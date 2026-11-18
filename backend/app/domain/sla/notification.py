"""
Notification domain entity — Pure Python OOP model.

OOP Design:
- Encapsulation: Protected attributes with explicit state transitions
  (``mark_as_read``, ``mark_sent``, ``mark_failed``).
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.core.exceptions import ValidationError
from app.domain.sla.enums import (
    NotificationChannel,
    NotificationDeliveryStatus,
    NotificationType,
)


class Notification:
    """Domain entity representing a user notification in the delivery queue."""

    def __init__(
        self,
        user_id: UUID,
        title: str,
        message: str,
        notification_type: NotificationType = NotificationType.GENERAL,
        channel: NotificationChannel = NotificationChannel.IN_APP,
        incident_id: UUID | None = None,
        is_read: bool = False,
        read_at: datetime | None = None,
        delivery_status: NotificationDeliveryStatus = NotificationDeliveryStatus.PENDING,
        id: UUID | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        if not title.strip():
            raise ValidationError("Notification title must not be empty.")
        if not message.strip():
            raise ValidationError("Notification message must not be empty.")

        self._id: UUID = id or uuid4()
        self._user_id: UUID = user_id
        self._incident_id: UUID | None = incident_id
        self._channel: NotificationChannel = channel
        self._notification_type: NotificationType = notification_type
        self._title: str = title.strip()
        self._message: str = message.strip()
        self._is_read: bool = is_read
        self._read_at: datetime | None = read_at
        self._delivery_status: NotificationDeliveryStatus = delivery_status
        now = datetime.now(UTC)
        self._created_at: datetime = created_at or now
        self._updated_at: datetime = updated_at or now

    # ── Read-Only Properties ──────────────────────────────────────────────────

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def user_id(self) -> UUID:
        return self._user_id

    @property
    def incident_id(self) -> UUID | None:
        return self._incident_id

    @property
    def channel(self) -> NotificationChannel:
        return self._channel

    @property
    def notification_type(self) -> NotificationType:
        return self._notification_type

    @property
    def title(self) -> str:
        return self._title

    @property
    def message(self) -> str:
        return self._message

    @property
    def is_read(self) -> bool:
        return self._is_read

    @property
    def read_at(self) -> datetime | None:
        return self._read_at

    @property
    def delivery_status(self) -> NotificationDeliveryStatus:
        return self._delivery_status

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    # ── State Transitions ─────────────────────────────────────────────────────

    def mark_as_read(self, read_at: datetime | None = None) -> None:
        """Mark the notification as read (idempotent)."""
        if self._is_read:
            return
        now = read_at or datetime.now(UTC)
        self._is_read = True
        self._read_at = now
        self._updated_at = now

    def mark_sent(self) -> None:
        """Mark the notification as successfully dispatched."""
        self._delivery_status = NotificationDeliveryStatus.SENT
        self._updated_at = datetime.now(UTC)

    def mark_failed(self) -> None:
        """Mark the notification delivery attempt as failed."""
        self._delivery_status = NotificationDeliveryStatus.FAILED
        self._updated_at = datetime.now(UTC)
