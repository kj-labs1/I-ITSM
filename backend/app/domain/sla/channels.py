"""
Multi-channel notification dispatchers — Strategy & Factory Patterns.

OOP Design:
- Abstraction: ``NotificationDispatcher`` ABC hides delivery channel details.
- Inheritance & Polymorphism: ``InAppNotificationDispatcher``,
  ``EmailNotificationDispatcher``, and ``WebhookNotificationDispatcher``
  implement ``dispatch(notification)`` interchangeably.
- Factory Pattern: ``NotificationDispatcherFactory`` resolves channel enum to
  the corresponding concrete dispatcher strategy (Open/Closed Principle).
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from app.domain.sla.enums import NotificationChannel
from app.domain.sla.notification import Notification

logger = logging.getLogger(__name__)


class NotificationDispatcher(ABC):
    """Abstract strategy for delivering a notification over a specific channel."""

    @property
    @abstractmethod
    def channel(self) -> NotificationChannel:
        """Return the channel handled by this dispatcher."""
        ...

    @abstractmethod
    async def dispatch(self, notification: Notification) -> bool:
        """Deliver the notification and return True on success."""
        ...


class InAppNotificationDispatcher(NotificationDispatcher):
    """Delivers in-app notifications (persisted in database for UI polling)."""

    @property
    def channel(self) -> NotificationChannel:
        return NotificationChannel.IN_APP

    async def dispatch(self, notification: Notification) -> bool:
        logger.info(
            "InAppNotificationDispatcher: Queued in-app notification '%s' for user %s",
            notification.title,
            notification.user_id,
        )
        notification.mark_sent()
        return True


class EmailNotificationDispatcher(NotificationDispatcher):
    """Adapter for outbound email notifications (structured log adapter in local dev)."""

    @property
    def channel(self) -> NotificationChannel:
        return NotificationChannel.EMAIL

    async def dispatch(self, notification: Notification) -> bool:
        logger.info(
            "EmailNotificationDispatcher: Dispatched email '%s' to user %s (incident=%s)",
            notification.title,
            notification.user_id,
            notification.incident_id,
        )
        notification.mark_sent()
        return True


class WebhookNotificationDispatcher(NotificationDispatcher):
    """Adapter for webhook/Slack/Teams escalation alerts (log adapter in local dev)."""

    @property
    def channel(self) -> NotificationChannel:
        return NotificationChannel.WEBHOOK

    async def dispatch(self, notification: Notification) -> bool:
        logger.info(
            "WebhookNotificationDispatcher: Dispatched webhook alert '%s' for user %s",
            notification.title,
            notification.user_id,
        )
        notification.mark_sent()
        return True


class NotificationDispatcherFactory:
    """Factory resolving NotificationChannel tokens to concrete dispatcher strategies."""

    _registry: dict[NotificationChannel, type[NotificationDispatcher]] = {
        NotificationChannel.IN_APP: InAppNotificationDispatcher,
        NotificationChannel.EMAIL: EmailNotificationDispatcher,
        NotificationChannel.WEBHOOK: WebhookNotificationDispatcher,
    }

    @classmethod
    def create(cls, channel: NotificationChannel) -> NotificationDispatcher:
        """Instantiate the dispatcher registered for ``channel``."""
        dispatcher_cls = cls._registry.get(channel, InAppNotificationDispatcher)
        return dispatcher_cls()

    @classmethod
    def register(
        cls,
        channel: NotificationChannel,
        dispatcher_cls: type[NotificationDispatcher],
    ) -> None:
        """Register or override a dispatcher strategy (Open/Closed Principle)."""
        cls._registry[channel] = dispatcher_cls
