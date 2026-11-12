"""
In-process event bus — Observer Pattern implementation.

Replaces Spring ApplicationEventPublisher for the Python/FastAPI backend.
Provides a thread-safe / async publish-subscribe mechanism for domain events.
M4 registers audit and notification listeners; M2 and M3 publish events.
"""

from __future__ import annotations

import logging
from collections import defaultdict

from app.application.interfaces.event_publisher import EventListener, EventPublisher
from app.domain.assignment.events import DomainEvent

logger = logging.getLogger(__name__)


class InProcessEventBus(EventPublisher):
    """
    In-memory asynchronous event bus implementing the Observer Pattern.

    OOP Design:
    - Implements EventPublisher interface (Dependency Inversion Principle).
    - Maintains subscribers partitioned by DomainEvent type.
    - Fault Isolation: Exception in one subscriber does not break publisher
      or other subscribers.
    """

    def __init__(self) -> None:
        self._listeners: dict[type[DomainEvent], list[EventListener]] = defaultdict(list)

    def subscribe(self, event_type: type[DomainEvent], listener: EventListener) -> None:
        """Register a listener for a specific domain event type."""
        if listener not in self._listeners[event_type]:
            self._listeners[event_type].append(listener)
            logger.info(
                "Subscribed %s to %s events",
                type(listener).__name__,
                event_type.__name__,
            )

    def unsubscribe(self, event_type: type[DomainEvent], listener: EventListener) -> None:
        """Remove a listener from a specific domain event type."""
        if listener in self._listeners[event_type]:
            self._listeners[event_type].remove(listener)
            logger.info(
                "Unsubscribed %s from %s events",
                type(listener).__name__,
                event_type.__name__,
            )

    async def publish(self, event: DomainEvent) -> None:
        """
        Dispatches a domain event to all registered listeners.

        Logs execution and suppresses individual listener errors to ensure
        isolation between independent event subscribers.
        """
        event_type = type(event)
        subscribers = list(self._listeners.get(event_type, []))

        # Also dispatch to subscribers of parent DomainEvent if any
        if event_type is not DomainEvent:
            subscribers.extend(self._listeners.get(DomainEvent, []))

        logger.info(
            "EventBus: Publishing %s (event_id=%s) to %d listener(s)",
            event_type.__name__,
            event.event_id,
            len(subscribers),
        )

        for listener in subscribers:
            try:
                await listener.handle(event)
            except Exception as exc:
                logger.exception(
                    "Error executing listener %s for event %s: %s",
                    type(listener).__name__,
                    event_type.__name__,
                    exc,
                )

    def clear(self) -> None:
        """Clear all registered listeners (primarily for testing)."""
        self._listeners.clear()


# Global singleton instance for application lifespan
_event_bus: InProcessEventBus | None = None


def get_event_bus() -> InProcessEventBus:
    """Return the global InProcessEventBus singleton."""
    global _event_bus
    if _event_bus is None:
        _event_bus = InProcessEventBus()
    return _event_bus
