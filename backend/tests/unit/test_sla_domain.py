"""
Unit tests for Member 4 pure Python domain entities.

Tests:
- SLAPolicy invariants, updates, and deadline computation
- IncidentSLATracking evaluation (ON_TRACK -> WARNING -> BREACHED -> MET)
- Notification encapsulation and state transitions
- Multi-channel NotificationDispatcher Strategy & Factory patterns
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.core.exceptions import ValidationError
from app.domain.sla.audit import AuditLogEntry
from app.domain.sla.channels import (
    EmailNotificationDispatcher,
    InAppNotificationDispatcher,
    NotificationDispatcherFactory,
    WebhookNotificationDispatcher,
)
from app.domain.sla.enums import (
    NotificationChannel,
    NotificationDeliveryStatus,
    NotificationType,
    SLAStatus,
)
from app.domain.sla.notification import Notification
from app.domain.sla.policy import SLAPolicy
from app.domain.sla.tracking import IncidentSLATracking
from app.shared.enums import Priority


class TestSLAPolicy:
    """Tests for SLAPolicy encapsulation and validation invariants."""

    def test_valid_policy_creation_and_deadlines(self) -> None:
        policy = SLAPolicy(
            priority=Priority.P1,
            name="P1 Critical",
            response_time_minutes=15,
            resolution_time_minutes=240,
            warning_threshold_percent=80,
        )
        start = datetime(2026, 11, 18, 10, 0, 0, tzinfo=UTC)
        assert policy.compute_response_deadline(start) == start + timedelta(minutes=15)
        assert policy.compute_resolution_deadline(start) == start + timedelta(minutes=240)

    def test_invalid_response_time_raises(self) -> None:
        with pytest.raises(ValidationError):
            SLAPolicy(
                priority=Priority.P1,
                name="Invalid",
                response_time_minutes=0,
                resolution_time_minutes=60,
            )

    def test_resolution_less_than_response_raises(self) -> None:
        with pytest.raises(ValidationError):
            SLAPolicy(
                priority=Priority.P2,
                name="Invalid",
                response_time_minutes=120,
                resolution_time_minutes=60,
            )

    def test_invalid_warning_threshold_raises(self) -> None:
        with pytest.raises(ValidationError):
            SLAPolicy(
                priority=Priority.P3,
                name="Invalid",
                response_time_minutes=30,
                resolution_time_minutes=120,
                warning_threshold_percent=100,
            )

    def test_update_targets(self) -> None:
        policy = SLAPolicy(
            priority=Priority.P2,
            name="P2 High",
            response_time_minutes=60,
            resolution_time_minutes=480,
        )
        policy.update_targets(response_time_minutes=30, resolution_time_minutes=360)
        assert policy.response_time_minutes == 30
        assert policy.resolution_time_minutes == 360


class TestIncidentSLATracking:
    """Tests for SLA deadline evaluation, warnings, breaches, and resolution."""

    def _make_p1_policy(self) -> SLAPolicy:
        return SLAPolicy(
            priority=Priority.P1,
            name="P1 Critical",
            response_time_minutes=20,
            resolution_time_minutes=100,
            warning_threshold_percent=80,
        )

    def test_on_track_then_warning_then_breach(self) -> None:
        policy = self._make_p1_policy()
        start = datetime(2026, 11, 18, 10, 0, 0, tzinfo=UTC)
        tracking = IncidentSLATracking.start_for_incident(uuid4(), policy, started_at=start)

        # 5 minutes elapsed (25% of 20m response) -> ON_TRACK
        r1 = tracking.evaluate(now=start + timedelta(minutes=5), warning_threshold_percent=80)
        assert r1.new_status == SLAStatus.ON_TRACK
        assert not r1.newly_warned
        assert not r1.newly_breached

        # 17 minutes elapsed (85% of 20m response) -> WARNING (newly_warned=True)
        r2 = tracking.evaluate(now=start + timedelta(minutes=17), warning_threshold_percent=80)
        assert r2.new_status == SLAStatus.WARNING
        assert r2.newly_warned is True
        assert r2.warning_target_type == "RESPONSE"

        # 18 minutes elapsed -> still WARNING, but newly_warned=False (idempotent)
        r3 = tracking.evaluate(now=start + timedelta(minutes=18), warning_threshold_percent=80)
        assert r3.new_status == SLAStatus.WARNING
        assert r3.newly_warned is False

        # 25 minutes elapsed -> RESPONSE BREACHED
        r4 = tracking.evaluate(now=start + timedelta(minutes=25), warning_threshold_percent=80)
        assert r4.new_status == SLAStatus.BREACHED
        assert r4.newly_breached is True
        assert r4.breach_type == "RESPONSE"
        assert tracking.response_breached is True
        assert tracking.is_breached is True

    def test_resolved_within_sla_marks_met(self) -> None:
        policy = self._make_p1_policy()
        start = datetime(2026, 11, 18, 10, 0, 0, tzinfo=UTC)
        tracking = IncidentSLATracking.start_for_incident(uuid4(), policy, started_at=start)

        tracking.record_first_response(start + timedelta(minutes=10))
        tracking.record_resolution(start + timedelta(minutes=60))

        assert tracking.status == SLAStatus.MET
        assert not tracking.is_breached
        assert tracking.remaining_response_seconds(start + timedelta(minutes=70)) == 0
        assert tracking.remaining_resolution_seconds(start + timedelta(minutes=70)) == 0

    def test_resolved_after_deadline_marks_breached(self) -> None:
        policy = self._make_p1_policy()
        start = datetime(2026, 11, 18, 10, 0, 0, tzinfo=UTC)
        tracking = IncidentSLATracking.start_for_incident(uuid4(), policy, started_at=start)

        tracking.record_first_response(start + timedelta(minutes=10))
        tracking.record_resolution(start + timedelta(minutes=120))

        assert tracking.status == SLAStatus.BREACHED
        assert tracking.response_breached is False
        assert tracking.resolution_breached is True


class TestNotificationAndDispatchers:
    """Tests for Notification entity and multi-channel Strategy/Factory patterns."""

    def test_notification_mark_as_read_is_idempotent(self) -> None:
        notif = Notification(
            user_id=uuid4(),
            title="Incident Assigned",
            message="Incident INC-1001 assigned to you.",
            notification_type=NotificationType.INCIDENT_ASSIGNED,
        )
        assert notif.is_read is False
        assert notif.read_at is None

        notif.mark_as_read()
        first_read_at = notif.read_at
        assert notif.is_read is True
        assert first_read_at is not None

        notif.mark_as_read()
        assert notif.read_at == first_read_at

    def test_empty_title_raises_validation_error(self) -> None:
        with pytest.raises(ValidationError):
            Notification(user_id=uuid4(), title="   ", message="Hello")

    @pytest.mark.asyncio
    async def test_dispatcher_factory_and_dispatch(self) -> None:
        in_app = NotificationDispatcherFactory.create(NotificationChannel.IN_APP)
        email = NotificationDispatcherFactory.create(NotificationChannel.EMAIL)
        webhook = NotificationDispatcherFactory.create(NotificationChannel.WEBHOOK)

        assert isinstance(in_app, InAppNotificationDispatcher)
        assert isinstance(email, EmailNotificationDispatcher)
        assert isinstance(webhook, WebhookNotificationDispatcher)

        notif = Notification(
            user_id=uuid4(),
            title="SLA Breach",
            message="Incident exceeded resolution SLA.",
            channel=NotificationChannel.EMAIL,
        )
        ok = await email.dispatch(notif)
        assert ok is True
        assert notif.delivery_status == NotificationDeliveryStatus.SENT

    def test_audit_log_entry_is_immutable(self) -> None:
        entry = AuditLogEntry(
            incident_id=uuid4(),
            action="INCIDENT_ASSIGNED",
            event_type="IncidentAssignedEvent",
        )
        with pytest.raises(FrozenInstanceError):
            entry.action = "MODIFIED"  # type: ignore[misc]
