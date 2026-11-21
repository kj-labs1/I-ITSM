"""
Notification Application Service — Member 4.

OOP Design:
- Single Responsibility Principle: Dispatches notifications via pluggable
  ``NotificationDispatcher`` strategies and manages read/unread state.
- Dependency Inversion Principle: Depends on ``NotificationRepository`` and
  ``NotificationDispatcherFactory``.
"""

from __future__ import annotations

import logging
from uuid import UUID

from app.application.interfaces.sla_repositories import NotificationRepository
from app.core.exceptions import NotificationNotFoundError
from app.domain.sla.channels import NotificationDispatcherFactory
from app.domain.sla.enums import NotificationChannel, NotificationType
from app.domain.sla.notification import Notification

logger = logging.getLogger(__name__)


class NotificationService:
    """Application service for dispatching, listing, and reading notifications."""

    def __init__(self, notification_repo: NotificationRepository) -> None:
        self._notification_repo = notification_repo

    async def send_notification(
        self,
        user_id: UUID,
        title: str,
        message: str,
        notification_type: NotificationType = NotificationType.GENERAL,
        channel: NotificationChannel = NotificationChannel.IN_APP,
        incident_id: UUID | None = None,
    ) -> Notification:
        """Create, dispatch via the selected channel strategy, and persist a notification."""
        notification = Notification(
            user_id=user_id,
            incident_id=incident_id,
            channel=channel,
            notification_type=notification_type,
            title=title,
            message=message,
        )
        dispatcher = NotificationDispatcherFactory.create(channel)
        try:
            ok = await dispatcher.dispatch(notification)
            if not ok:
                notification.mark_failed()
        except Exception as exc:
            logger.exception("Notification dispatch failed via %s: %s", channel.value, exc)
            notification.mark_failed()

        return await self._notification_repo.create(notification)

    async def get_notification(self, notification_id: UUID) -> Notification:
        """Retrieve a single notification by ID."""
        notification = await self._notification_repo.get_by_id(notification_id)
        if notification is None:
            raise NotificationNotFoundError(resource_id=notification_id)
        return notification

    async def list_notifications(
        self,
        user_id: UUID | None = None,
        incident_id: UUID | None = None,
        unread_only: bool = False,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Notification]:
        """List notifications with optional user, incident, and unread filters."""
        return await self._notification_repo.list_for_user(
            user_id=user_id,
            incident_id=incident_id,
            unread_only=unread_only,
            skip=skip,
            limit=limit,
        )

    async def mark_as_read(self, notification_id: UUID) -> Notification:
        """Mark a single notification as read."""
        notification = await self.get_notification(notification_id)
        notification.mark_as_read()
        return await self._notification_repo.update(notification)

    async def mark_all_read(self, user_id: UUID) -> int:
        """Mark all unread notifications for ``user_id`` as read."""
        return await self._notification_repo.mark_all_read(user_id)

    async def count_unread(self, user_id: UUID) -> int:
        """Return the count of unread notifications for ``user_id``."""
        return await self._notification_repo.count_unread(user_id)
