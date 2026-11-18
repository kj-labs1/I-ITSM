"""
Incident SLA Tracking aggregate root — Pure Python OOP model.

OOP Design:
- Encapsulation: All deadline, breach flag, and status transitions are controlled
  by explicit domain methods (``evaluate``, ``record_first_response``,
  ``record_resolution``, ``recalculate_for_policy``).
- Pure Python: Zero FastAPI or SQLAlchemy imports.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.domain.sla.enums import SLAStatus
from app.domain.sla.policy import SLAPolicy
from app.shared.enums import Priority


def _ensure_utc(dt: datetime) -> datetime:
    """Normalize naive datetimes (e.g. from SQLite) to UTC-aware datetimes."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


@dataclass(frozen=True)
class SLAEvaluationResult:
    """Immutable value object describing changes detected during an SLA check."""

    incident_id: UUID
    previous_status: SLAStatus
    new_status: SLAStatus
    newly_warned: bool = False
    newly_breached: bool = False
    breach_type: str | None = None  # "RESPONSE", "RESOLUTION", or "BOTH"
    warning_target_type: str | None = None  # "RESPONSE" or "RESOLUTION"
    percent_elapsed: float = 0.0
    overdue_minutes: float = 0.0


class IncidentSLATracking:
    """
    Aggregate root tracking SLA deadlines, warnings, and breaches for an incident.
    """

    def __init__(
        self,
        incident_id: UUID,
        policy_id: UUID,
        priority: Priority,
        started_at: datetime,
        response_due_at: datetime,
        resolution_due_at: datetime,
        first_responded_at: datetime | None = None,
        resolved_at: datetime | None = None,
        response_breached: bool = False,
        resolution_breached: bool = False,
        warning_sent: bool = False,
        breach_notified: bool = False,
        status: SLAStatus = SLAStatus.ON_TRACK,
        id: UUID | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        self._id: UUID = id or uuid4()
        self._incident_id: UUID = incident_id
        self._policy_id: UUID = policy_id
        self._priority: Priority = priority
        self._started_at: datetime = _ensure_utc(started_at)
        self._response_due_at: datetime = _ensure_utc(response_due_at)
        self._resolution_due_at: datetime = _ensure_utc(resolution_due_at)
        self._first_responded_at: datetime | None = (
            _ensure_utc(first_responded_at) if first_responded_at else None
        )
        self._resolved_at: datetime | None = (
            _ensure_utc(resolved_at) if resolved_at else None
        )
        self._response_breached: bool = response_breached
        self._resolution_breached: bool = resolution_breached
        self._warning_sent: bool = warning_sent
        self._breach_notified: bool = breach_notified
        self._status: SLAStatus = status
        now = datetime.now(UTC)
        self._created_at: datetime = _ensure_utc(created_at) if created_at else now
        self._updated_at: datetime = _ensure_utc(updated_at) if updated_at else now

    # ── Factory Method ────────────────────────────────────────────────────────

    @classmethod
    def start_for_incident(
        cls,
        incident_id: UUID,
        policy: SLAPolicy,
        started_at: datetime | None = None,
    ) -> IncidentSLATracking:
        """Create a new SLA tracking record computed from an SLAPolicy."""
        start = _ensure_utc(started_at) if started_at else datetime.now(UTC)
        return cls(
            incident_id=incident_id,
            policy_id=policy.id,
            priority=policy.priority,
            started_at=start,
            response_due_at=policy.compute_response_deadline(start),
            resolution_due_at=policy.compute_resolution_deadline(start),
            status=SLAStatus.ON_TRACK,
        )

    # ── Read-Only Properties ──────────────────────────────────────────────────

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def incident_id(self) -> UUID:
        return self._incident_id

    @property
    def policy_id(self) -> UUID:
        return self._policy_id

    @property
    def priority(self) -> Priority:
        return self._priority

    @property
    def started_at(self) -> datetime:
        return self._started_at

    @property
    def response_due_at(self) -> datetime:
        return self._response_due_at

    @property
    def resolution_due_at(self) -> datetime:
        return self._resolution_due_at

    @property
    def first_responded_at(self) -> datetime | None:
        return self._first_responded_at

    @property
    def resolved_at(self) -> datetime | None:
        return self._resolved_at

    @property
    def response_breached(self) -> bool:
        return self._response_breached

    @property
    def resolution_breached(self) -> bool:
        return self._resolution_breached

    @property
    def is_breached(self) -> bool:
        return self._response_breached or self._resolution_breached

    @property
    def warning_sent(self) -> bool:
        return self._warning_sent

    @property
    def breach_notified(self) -> bool:
        return self._breach_notified

    @property
    def status(self) -> SLAStatus:
        return self._status

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    # ── Computed Metrics ──────────────────────────────────────────────────────

    def remaining_response_seconds(self, now: datetime | None = None) -> int:
        """Seconds remaining until response deadline (0 if already responded or overdue)."""
        if self._first_responded_at is not None or self._resolved_at is not None:
            return 0
        current = _ensure_utc(now) if now else datetime.now(UTC)
        return max(0, int((self._response_due_at - current).total_seconds()))

    def remaining_resolution_seconds(self, now: datetime | None = None) -> int:
        """Seconds remaining until resolution deadline (0 if already resolved or overdue)."""
        if self._resolved_at is not None:
            return 0
        current = _ensure_utc(now) if now else datetime.now(UTC)
        return max(0, int((self._resolution_due_at - current).total_seconds()))

    # ── State Transitions ─────────────────────────────────────────────────────

    def record_first_response(self, responded_at: datetime | None = None) -> None:
        """Record the first technician acknowledgment/response timestamp."""
        if self._first_responded_at is not None:
            return
        ts = _ensure_utc(responded_at) if responded_at else datetime.now(UTC)
        self._first_responded_at = ts
        if ts > self._response_due_at:
            self._response_breached = True
            self._status = SLAStatus.BREACHED
        self._updated_at = datetime.now(UTC)

    def record_resolution(self, resolved_at: datetime | None = None) -> None:
        """Record incident resolution and finalize SLA status as MET or BREACHED."""
        if self._resolved_at is not None:
            return
        ts = _ensure_utc(resolved_at) if resolved_at else datetime.now(UTC)
        self._resolved_at = ts
        if self._first_responded_at is None:
            self._first_responded_at = ts
            if ts > self._response_due_at:
                self._response_breached = True
        if ts > self._resolution_due_at:
            self._resolution_breached = True

        self._status = SLAStatus.BREACHED if self.is_breached else SLAStatus.MET
        self._updated_at = datetime.now(UTC)

    def recalculate_for_policy(self, policy: SLAPolicy) -> None:
        """Recalculate deadlines when an incident's priority changes."""
        self._policy_id = policy.id
        self._priority = policy.priority
        self._response_due_at = policy.compute_response_deadline(self._started_at)
        self._resolution_due_at = policy.compute_resolution_deadline(self._started_at)
        self._updated_at = datetime.now(UTC)

    def evaluate(
        self,
        now: datetime | None = None,
        warning_threshold_percent: int = 80,
    ) -> SLAEvaluationResult:
        """
        Evaluate current time against response and resolution deadlines.

        Transitions status between ON_TRACK -> WARNING -> BREACHED and returns
        an ``SLAEvaluationResult`` indicating whether a new warning or breach
        notification should be emitted.
        """
        current = _ensure_utc(now) if now else datetime.now(UTC)
        previous_status = self._status

        if self._status in (SLAStatus.MET, SLAStatus.PAUSED) or self._resolved_at is not None:
            return SLAEvaluationResult(
                incident_id=self._incident_id,
                previous_status=previous_status,
                new_status=self._status,
            )

        # 1. Check response breach
        if self._first_responded_at is None and current > self._response_due_at:
            self._response_breached = True

        # 2. Check resolution breach
        if self._resolved_at is None and current > self._resolution_due_at:
            self._resolution_breached = True

        # 3. Determine breach notification
        if self.is_breached:
            self._status = SLAStatus.BREACHED
            newly_breached = not self._breach_notified
            if newly_breached:
                self._breach_notified = True

            if self._response_breached and self._resolution_breached:
                breach_type = "BOTH"
                overdue_min = max(
                    (current - self._response_due_at).total_seconds(),
                    (current - self._resolution_due_at).total_seconds(),
                ) / 60.0
            elif self._response_breached:
                breach_type = "RESPONSE"
                overdue_min = max(0.0, (current - self._response_due_at).total_seconds() / 60.0)
            else:
                breach_type = "RESOLUTION"
                overdue_min = max(0.0, (current - self._resolution_due_at).total_seconds() / 60.0)

            self._updated_at = datetime.now(UTC)
            return SLAEvaluationResult(
                incident_id=self._incident_id,
                previous_status=previous_status,
                new_status=self._status,
                newly_breached=newly_breached,
                breach_type=breach_type,
                overdue_minutes=round(overdue_min, 2),
            )

        # 4. Check warning threshold (response if unresponded, else resolution)
        resp_total = max(1.0, (self._response_due_at - self._started_at).total_seconds())
        res_total = max(1.0, (self._resolution_due_at - self._started_at).total_seconds())
        elapsed = max(0.0, (current - self._started_at).total_seconds())

        resp_pct = (elapsed / resp_total) * 100.0 if self._first_responded_at is None else 0.0
        res_pct = (elapsed / res_total) * 100.0

        max_pct = max(resp_pct, res_pct)
        warning_target = "RESPONSE" if resp_pct >= res_pct and resp_pct > 0 else "RESOLUTION"

        if max_pct >= warning_threshold_percent:
            self._status = SLAStatus.WARNING
            newly_warned = not self._warning_sent
            if newly_warned:
                self._warning_sent = True
            self._updated_at = datetime.now(UTC)
            return SLAEvaluationResult(
                incident_id=self._incident_id,
                previous_status=previous_status,
                new_status=self._status,
                newly_warned=newly_warned,
                warning_target_type=warning_target,
                percent_elapsed=round(min(max_pct, 100.0), 2),
            )

        self._status = SLAStatus.ON_TRACK
        return SLAEvaluationResult(
            incident_id=self._incident_id,
            previous_status=previous_status,
            new_status=self._status,
            percent_elapsed=round(max_pct, 2),
        )
