"""
Integration tests for Member 4 services with async SQLite persistence.

Tests:
- SLAService policy seeding, tracking, violation queries, and evaluation sweeps
- AuditService recording and chronological retrieval
- NotificationService dispatch, unread filtering, and mark-all-read
- SLAMonitorTask single-sweep execution
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.application.sla.audit_service import AuditService
from app.application.sla.monitor import SLAMonitorTask
from app.application.sla.notification_service import NotificationService
from app.application.sla.sla_service import SLAService
from app.domain.sla.enums import NotificationChannel, NotificationType, SLAStatus
from app.shared.enums import Priority


@pytest.mark.asyncio
async def test_sla_service_lifecycle_and_violation_detection(
    sla_service: SLAService,
) -> None:
    policies = await sla_service.ensure_default_policies()
    assert len(policies) == 4

    incident_id = uuid4()
    past_start = datetime.now(UTC) - timedelta(minutes=30)

    # Start P1 tracking 30 minutes ago (P1 response target is 15m -> already breached!)
    tracking = await sla_service.start_tracking(
        incident_id=incident_id,
        priority=Priority.P1,
        started_at=past_start,
    )
    assert tracking.priority == Priority.P1

    # Run evaluation sweep
    results = await sla_service.evaluate_active_slas()
    assert len(results) == 1
    assert results[0].newly_breached is True
    assert results[0].new_status == SLAStatus.BREACHED

    violations = await sla_service.list_violations()
    assert len(violations) == 1
    assert violations[0].incident_id == incident_id
    assert violations[0].is_breached is True


@pytest.mark.asyncio
async def test_audit_and_notification_services(
    audit_service: AuditService,
    notification_service: NotificationService,
) -> None:
    incident_id = uuid4()
    user_id = uuid4()

    await audit_service.record(
        incident_id=incident_id,
        action="INCIDENT_ASSIGNED",
        event_type="IncidentAssignedEvent",
        actor_id=user_id,
        details="Assigned via SKILL_BASED",
    )
    trail = await audit_service.get_incident_audit_trail(incident_id)
    assert len(trail) == 1
    assert trail[0].action == "INCIDENT_ASSIGNED"

    n1 = await notification_service.send_notification(
        user_id=user_id,
        incident_id=incident_id,
        title="Assigned",
        message="Incident assigned to you.",
        notification_type=NotificationType.INCIDENT_ASSIGNED,
        channel=NotificationChannel.IN_APP,
    )
    n2 = await notification_service.send_notification(
        user_id=user_id,
        incident_id=incident_id,
        title="SLA Warning",
        message="Approaching SLA deadline.",
        notification_type=NotificationType.SLA_WARNING,
        channel=NotificationChannel.EMAIL,
    )

    unread = await notification_service.list_notifications(user_id=user_id, unread_only=True)
    assert len(unread) == 2

    read_n1 = await notification_service.mark_as_read(n1.id)
    assert read_n1.is_read is True

    marked = await notification_service.mark_all_read(user_id)
    assert marked == 1

    still_unread = await notification_service.list_notifications(user_id=user_id, unread_only=True)
    assert len(still_unread) == 0
    assert (await notification_service.get_notification(n2.id)).is_read is True


@pytest.mark.asyncio
async def test_sla_monitor_task_run_once(sla_service: SLAService) -> None:
    @asynccontextmanager
    async def factory():
        yield sla_service

    await sla_service.start_tracking(uuid4(), Priority.P2)
    monitor = SLAMonitorTask(factory, interval_seconds=60.0)
    checked = await monitor.run_once()
    assert checked == 1
