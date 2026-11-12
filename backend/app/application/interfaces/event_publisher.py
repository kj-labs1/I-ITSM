"""
Domain event publisher interfaces — Observer Pattern abstraction.

OOP Design:
- Observer Pattern: Decouples domain event producers (e.g. Assignment engine)
  from consumers (e.g. Audit logging, Notification dispatchers in M4).
- Dependency Inversion: Modules publish events to an abstract publisher interface
  without depending on specific message queues, brokers, or event bus implementations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.assignment.events import DomainEvent


class EventPublisher(ABC):
    """Abstract publisher for asynchronous or in-process domain events."""

    @abstractmethod
    async def publish(self, event: DomainEvent) -> None:
        """
        Publish a domain event to all subscribed listeners.

        Args:
            event: An immutable DomainEvent instance.
        """
        ...


class EventListener(ABC):
    """Abstract listener contract for components reacting to domain events."""

    @abstractmethod
    async def handle(self, event: DomainEvent) -> None:
        """
        Handle a dispatched domain event.

        Args:
            event: The dispatched DomainEvent instance.
        """
        ...
