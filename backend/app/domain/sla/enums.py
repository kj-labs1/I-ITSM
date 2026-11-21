"""
Member 4 domain enumerations for SLA tracking, audit logging, and notifications.

OOP Design:
- Uses ``str, Enum`` for type-safe JSON serialization consistent with ``app/shared/enums.py``.
- Kept inside ``app/domain/sla/`` to avoid merge conflicts in shared files.
"""

from __future__ import annotations

from enum import Enum


class SLAStatus(str, Enum):
    """Lifecycle status of an incident's SLA tracking record."""

    ON_TRACK = "ON_TRACK"
    WARNING = "WARNING"
    BREACHED = "BREACHED"
    MET = "MET"
    PAUSED = "PAUSED"


class NotificationChannel(str, Enum):
    """Supported delivery channels for outbound notifications."""

    IN_APP = "IN_APP"
    EMAIL = "EMAIL"
    WEBHOOK = "WEBHOOK"


class NotificationType(str, Enum):
    """Semantic categories of system notifications."""

    INCIDENT_CREATED = "INCIDENT_CREATED"
    INCIDENT_ASSIGNED = "INCIDENT_ASSIGNED"
    STATUS_CHANGED = "STATUS_CHANGED"
    SLA_WARNING = "SLA_WARNING"
    SLA_BREACHED = "SLA_BREACHED"
    ESCALATION = "ESCALATION"
    WORKLOAD_WARNING = "WORKLOAD_WARNING"
    INCIDENT_UPDATED = "INCIDENT_UPDATED"
    COMMENT_ADDED = "COMMENT_ADDED"
    AVAILABILITY_CHANGED = "AVAILABILITY_CHANGED"
    GENERAL = "GENERAL"


class NotificationDeliveryStatus(str, Enum):
    """Delivery state of a persisted notification record."""

    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"


class AuditAction(str, Enum):
    """Standardized audit action tokens for incident timelines."""

    INCIDENT_CREATED = "INCIDENT_CREATED"
    INCIDENT_ASSIGNED = "INCIDENT_ASSIGNED"
    STATUS_CHANGED = "STATUS_CHANGED"
    PRIORITY_CHANGED = "PRIORITY_CHANGED"
    SLA_TRACKING_STARTED = "SLA_TRACKING_STARTED"
    SLA_FIRST_RESPONSE_RECORDED = "SLA_FIRST_RESPONSE_RECORDED"
    SLA_WARNING_TRIGGERED = "SLA_WARNING_TRIGGERED"
    SLA_BREACHED = "SLA_BREACHED"
    SLA_MET = "SLA_MET"
    SLA_POLICY_UPDATED = "SLA_POLICY_UPDATED"
    AVAILABILITY_CHANGED = "AVAILABILITY_CHANGED"
    COMMENT_ADDED = "COMMENT_ADDED"
    INCIDENT_ARCHIVED = "INCIDENT_ARCHIVED"
    INCIDENT_MERGED = "INCIDENT_MERGED"
    DOMAIN_EVENT = "DOMAIN_EVENT"
