"""
Pydantic v2 DTO schemas for Member 4 (SLA, Audit Logs & Notifications).

Conventions enforced:
- Inherits from ``BaseDTO`` in ``app/api/v1/schemas.py`` for camelCase JSON serialization.
- Kept in a dedicated module to prevent merge conflicts with other team branches.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.api.v1.schemas import BaseDTO
from app.domain.sla.enums import (
    NotificationChannel,
    NotificationDeliveryStatus,
    NotificationType,
    SLAStatus,
)
from app.shared.enums import Priority


# ── SLA Policy Schemas ────────────────────────────────────────────────────────


class SLAPolicyCreateRequest(BaseDTO):
    """Payload to create a new SLA policy for a priority level."""

    priority: Priority = Field(examples=[Priority.P1])
    name: str = Field(min_length=1, max_length=100, examples=["P1 Critical SLA"])
    response_time_minutes: int = Field(gt=0, examples=[15])
    resolution_time_minutes: int = Field(gt=0, examples=[240])
    warning_threshold_percent: int = Field(default=80, ge=1, le=99, examples=[80])
    escalation_enabled: bool = Field(default=True)


class SLAPolicyUpdateRequest(BaseDTO):
    """Payload to update an existing SLA policy's target windows."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    response_time_minutes: int | None = Field(default=None, gt=0)
    resolution_time_minutes: int | None = Field(default=None, gt=0)
    warning_threshold_percent: int | None = Field(default=None, ge=1, le=99)
    escalation_enabled: bool | None = None


class SLAPolicyResponse(BaseDTO):
    """Read representation of an SLA policy."""

    id: UUID
    priority: Priority
    name: str
    response_time_minutes: int
    resolution_time_minutes: int
    warning_threshold_percent: int
    escalation_enabled: bool
    created_at: datetime
    updated_at: datetime


# ── SLA Tracking Schemas ──────────────────────────────────────────────────────


class SLATrackingStartRequest(BaseDTO):
    """Payload to initialize SLA tracking for an incident."""

    priority: Priority = Field(default=Priority.P3, examples=[Priority.P1])
    started_at: datetime | None = Field(default=None)


class IncidentSLAResponse(BaseDTO):
    """Read representation of an incident's SLA tracking status and deadlines."""

    id: UUID
    incident_id: UUID
    policy_id: UUID
    priority: Priority
    status: SLAStatus
    started_at: datetime
    response_due_at: datetime
    resolution_due_at: datetime
    first_responded_at: datetime | None = None
    resolved_at: datetime | None = None
    response_breached: bool
    resolution_breached: bool
    is_breached: bool
    warning_sent: bool
    remaining_response_seconds: int
    remaining_resolution_seconds: int
    created_at: datetime
    updated_at: datetime


class SLACheckSummaryResponse(BaseDTO):
    """Summary returned by an on-demand SLA evaluation sweep."""

    evaluated_count: int
    warnings_triggered: int
    breaches_triggered: int


# ── Audit Log Schemas ─────────────────────────────────────────────────────────


class AuditLogResponse(BaseDTO):
    """Read representation of an immutable incident audit trail entry."""

    id: UUID
    incident_id: UUID
    actor_id: UUID | None = None
    action: str
    event_type: str
    previous_value: str | None = None
    new_value: str | None = None
    details: str | None = None
    occurred_at: datetime
    created_at: datetime


# ── Notification Schemas ──────────────────────────────────────────────────────


class NotificationResponse(BaseDTO):
    """Read representation of a recipient notification."""

    id: UUID
    user_id: UUID
    incident_id: UUID | None = None
    channel: NotificationChannel
    notification_type: NotificationType
    title: str
    message: str
    is_read: bool
    read_at: datetime | None = None
    delivery_status: NotificationDeliveryStatus
    created_at: datetime
    updated_at: datetime


class NotificationsReadAllResponse(BaseDTO):
    """Response confirming bulk mark-as-read operation."""

    user_id: UUID
    marked_count: int
