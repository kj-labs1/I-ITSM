"""
Domain Event Listeners — Observer Pattern (Member 4).

OOP Design:
- Observer Pattern: Implements ``EventListener`` from
  ``app/application/interfaces/event_publisher.py`` and subscribes to
  ``InProcessEventBus`` during application startup.
- Loose Coupling: Handles Member 3's ``IncidentAssignedEvent``, Member 4's
  SLA events (``SLAWarningEvent``, ``SLABreachedEvent``, ``SLAMetEvent``),
  and Member 2's incident lifecycle events (``IncidentCreatedEvent``,
  ``IncidentStatusChangedEvent``, ``PriorityChangedEvent``) via duck-typed
  attribute inspection so Member 4 works cleanly both standalone and after
  all branches merge.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from uuid import UUID

from app.application.interfaces.event_publisher import EventListener
from app.application.sla.audit_service import AuditService
from app.application.sla.notification_service import NotificationService
from app.application.sla.sla_service import SLAService
from app.domain.assignment.events import DomainEvent, IncidentAssignedEvent
from app.domain.sla.enums import AuditAction, NotificationChannel, NotificationType
from app.domain.sla.events import SLABreachedEvent, SLAMetEvent, SLAWarningEvent
from app.shared.enums import IncidentStatus, Priority

logger = logging.getLogger(__name__)

# Fallback system escalation user UUID used when an incident has no assignee yet
DEFAULT_ESCALATION_USER_ID = UUID("00000000-0000-0000-0000-000000000001")

AuditServiceFactory = Callable[[], AbstractAsyncContextManager[AuditService]]
NotificationServiceFactory = Callable[[], AbstractAsyncContextManager[NotificationService]]
SLAServiceFactory = Callable[[], AbstractAsyncContextManager[SLAService]]


class AuditEventListener(EventListener):
    """
    Observer subscribing to domain events and persisting immutable audit entries.
    """

    def __init__(self, audit_service_factory: AuditServiceFactory) -> None:
        self._audit_service_factory = audit_service_factory

    async def handle(self, event: DomainEvent) -> None:
        incident_id: UUID | None = getattr(event, "incident_id", None)
        if incident_id is None:
            return

        event_name = type(event).__name__
        actor_id: UUID | None = getattr(event, "actor_id", None) or getattr(
            event, "reporter_id", None
        )
        previous_value: str | None = None
        new_value: str | None = None
        details: str | None = None
        action: str = AuditAction.DOMAIN_EVENT.value

        if isinstance(event, IncidentAssignedEvent):
            action = AuditAction.INCIDENT_ASSIGNED.value
            new_value = str(event.technician_id)
            details = (
                f"Assigned to technician {event.technician_id} using "
                f"{event.strategy_used or 'MANUAL'}. {event.explanation}".strip()
            )
        elif isinstance(event, SLAWarningEvent):
            action = AuditAction.SLA_WARNING_TRIGGERED.value
            new_value = f"{event.percent_elapsed:.1f}% elapsed ({event.target_type})"
            details = (
                f"SLA warning for {event.priority.value} incident "
                f"(target={event.target_type}, due={event.due_at.isoformat() if event.due_at else 'N/A'})."
            )
        elif isinstance(event, SLABreachedEvent):
            action = AuditAction.SLA_BREACHED.value
            new_value = f"BREACHED ({event.breach_type})"
            details = (
                f"SLA breached for {event.priority.value} incident "
                f"by {event.overdue_minutes:.1f} min (type={event.breach_type})."
            )
        elif isinstance(event, SLAMetEvent):
            action = AuditAction.SLA_MET.value
            new_value = "MET"
            details = f"Incident resolved within {event.priority.value} SLA targets."
        elif event_name == "IncidentCreatedEvent":
            action = AuditAction.INCIDENT_CREATED.value
            priority = getattr(event, "priority", Priority.P3)
            category = getattr(event, "category", "")
            code = getattr(event, "incident_code", "")
            new_value = f"{getattr(priority, 'value', priority)}"
            details = f"Incident {code} created (category={getattr(category, 'value', category)})."
        elif event_name == "IncidentStatusChangedEvent":
            action = AuditAction.STATUS_CHANGED.value
            prev_s = getattr(event, "previous_status", None)
            new_s = getattr(event, "new_status", None)
            previous_value = getattr(prev_s, "value", str(prev_s)) if prev_s else None
            new_value = getattr(new_s, "value", str(new_s)) if new_s else None
            code = getattr(event, "incident_code", str(incident_id))
            details = f"Incident {code} status changed from {previous_value} to {new_value}."
        elif event_name == "PriorityChangedEvent":
            action = AuditAction.PRIORITY_CHANGED.value
            prev_p = getattr(event, "previous_priority", None)
            new_p = getattr(event, "new_priority", None)
            previous_value = getattr(prev_p, "value", str(prev_p)) if prev_p else None
            new_value = getattr(new_p, "value", str(new_p)) if new_p else None
            details = f"Incident priority changed from {previous_value} to {new_value}."

        async with self._audit_service_factory() as audit_service:
            await audit_service.record(
                incident_id=incident_id,
                action=action,
                event_type=event_name,
                actor_id=actor_id,
                previous_value=previous_value,
                new_value=new_value,
                details=details,
                occurred_at=event.occurred_at,
            )


class NotificationEventListener(EventListener):
    """
    Observer subscribing to domain events and dispatching recipient notifications.
    """

    def __init__(self, notification_service_factory: NotificationServiceFactory) -> None:
        self._notification_service_factory = notification_service_factory

    async def handle(self, event: DomainEvent) -> None:
        event_name = type(event).__name__

        async with self._notification_service_factory() as notif_service:
            if isinstance(event, IncidentAssignedEvent):
                await notif_service.send_notification(
                    user_id=event.technician_id,
                    incident_id=event.incident_id,
                    notification_type=NotificationType.INCIDENT_ASSIGNED,
                    channel=NotificationChannel.IN_APP,
                    title="New Incident Assigned",
                    message=(
                        f"You have been assigned incident {event.incident_id} "
                        f"via {event.strategy_used or 'MANUAL'}."
                    ),
                )
            elif isinstance(event, SLAWarningEvent):
                recipient = event.recipient_user_id or DEFAULT_ESCALATION_USER_ID
                await notif_service.send_notification(
                    user_id=recipient,
                    incident_id=event.incident_id,
                    notification_type=NotificationType.SLA_WARNING,
                    channel=NotificationChannel.IN_APP,
                    title=f"SLA Warning ({event.priority.value})",
                    message=(
                        f"Incident {event.incident_id} has consumed "
                        f"{event.percent_elapsed:.1f}% of its {event.target_type} SLA window."
                    ),
                )
            elif isinstance(event, SLABreachedEvent):
                recipient = event.recipient_user_id or DEFAULT_ESCALATION_USER_ID
                await notif_service.send_notification(
                    user_id=recipient,
                    incident_id=event.incident_id,
                    notification_type=NotificationType.SLA_BREACHED,
                    channel=NotificationChannel.IN_APP,
                    title=f"SLA Breached ({event.priority.value})",
                    message=(
                        f"Incident {event.incident_id} breached its {event.breach_type} SLA "
                        f"by {event.overdue_minutes:.1f} minutes."
                    ),
                )
                if event.escalation_enabled:
                    await notif_service.send_notification(
                        user_id=DEFAULT_ESCALATION_USER_ID,
                        incident_id=event.incident_id,
                        notification_type=NotificationType.ESCALATION,
                        channel=NotificationChannel.EMAIL,
                        title=f"SLA Escalation Alert ({event.priority.value})",
                        message=(
                            f"Escalation triggered for breached incident {event.incident_id} "
                            f"({event.breach_type} SLA overdue by {event.overdue_minutes:.1f} min)."
                        ),
                    )
            elif event_name == "IncidentStatusChangedEvent":
                incident_id: UUID | None = getattr(event, "incident_id", None)
                actor_id: UUID | None = getattr(event, "actor_id", None)
                new_status = getattr(event, "new_status", "")
                if incident_id and actor_id:
                    await notif_service.send_notification(
                        user_id=actor_id,
                        incident_id=incident_id,
                        notification_type=NotificationType.STATUS_CHANGED,
                        channel=NotificationChannel.IN_APP,
                        title="Incident Status Updated",
                        message=(
                            f"Incident {getattr(event, 'incident_code', incident_id)} "
                            f"moved to {getattr(new_status, 'value', new_status)}."
                        ),
                    )


class SLALifecycleEventListener(EventListener):
    """
    Observer synchronizing incident lifecycle events with SLA tracking records.
    """

    def __init__(self, sla_service_factory: SLAServiceFactory) -> None:
        self._sla_service_factory = sla_service_factory

    async def handle(self, event: DomainEvent) -> None:
        event_name = type(event).__name__
        incident_id: UUID | None = getattr(event, "incident_id", None)
        if incident_id is None:
            return

        async with self._sla_service_factory() as sla_service:
            if event_name == "IncidentCreatedEvent":
                priority = getattr(event, "priority", Priority.P3)
                await sla_service.start_tracking(
                    incident_id=incident_id,
                    priority=priority,
                    started_at=event.occurred_at,
                )
            elif isinstance(event, IncidentAssignedEvent):
                # Ensure SLA tracking exists even if incident was seeded/created outside M2
                await sla_service.start_tracking(
                    incident_id=incident_id,
                    priority=Priority.P3,
                    started_at=event.occurred_at,
                )
            elif event_name == "IncidentStatusChangedEvent":
                new_status = getattr(event, "new_status", None)
                status_val = getattr(new_status, "value", str(new_status))
                if status_val in (
                    IncidentStatus.ACKNOWLEDGED.value,
                    IncidentStatus.IN_PROGRESS.value,
                ):
                    await sla_service.record_first_response(
                        incident_id=incident_id,
                        responded_at=event.occurred_at,
                    )
                elif status_val in (
                    IncidentStatus.RESOLVED.value,
                    IncidentStatus.VERIFIED.value,
                    IncidentStatus.CLOSED.value,
                ):
                    await sla_service.record_resolution(
                        incident_id=incident_id,
                        resolved_at=event.occurred_at,
                    )
            elif event_name == "PriorityChangedEvent":
                new_priority = getattr(event, "new_priority", None)
                if isinstance(new_priority, Priority):
                    await sla_service.recalculate_priority(
                        incident_id=incident_id,
                        new_priority=new_priority,
                    )
