"""
SLA Policy domain entity — Pure Python OOP model.

OOP Design:
- Encapsulation: Protected attributes with invariant validation in ``__post_init__``
  and explicit mutation via ``update_targets()``.
- Zero external framework dependencies (no FastAPI or SQLAlchemy imports).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from app.core.exceptions import ValidationError
from app.shared.enums import Priority

# Standard ITIL-aligned default SLA targets (in minutes) per priority level
DEFAULT_SLA_POLICY_SPECS: dict[Priority, dict[str, object]] = {
    Priority.P1: {
        "name": "P1 Critical SLA",
        "response_time_minutes": 15,
        "resolution_time_minutes": 240,
        "warning_threshold_percent": 80,
        "escalation_enabled": True,
    },
    Priority.P2: {
        "name": "P2 High SLA",
        "response_time_minutes": 60,
        "resolution_time_minutes": 480,
        "warning_threshold_percent": 80,
        "escalation_enabled": True,
    },
    Priority.P3: {
        "name": "P3 Medium SLA",
        "response_time_minutes": 240,
        "resolution_time_minutes": 1440,
        "warning_threshold_percent": 80,
        "escalation_enabled": True,
    },
    Priority.P4: {
        "name": "P4 Low SLA",
        "response_time_minutes": 480,
        "resolution_time_minutes": 4320,
        "warning_threshold_percent": 85,
        "escalation_enabled": False,
    },
}


class SLAPolicy:
    """
    Domain entity defining response and resolution time targets for a Priority level.

    Invariants:
    - ``response_time_minutes`` must be a positive integer (> 0).
    - ``resolution_time_minutes`` must be >= ``response_time_minutes``.
    - ``warning_threshold_percent`` must be between 1 and 99 inclusive.
    """

    def __init__(
        self,
        priority: Priority,
        name: str,
        response_time_minutes: int,
        resolution_time_minutes: int,
        warning_threshold_percent: int = 80,
        escalation_enabled: bool = True,
        id: UUID | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        self._id: UUID = id or uuid4()
        self._priority: Priority = priority
        self._name: str = ""
        self._response_time_minutes: int = 0
        self._resolution_time_minutes: int = 0
        self._warning_threshold_percent: int = 80
        self._escalation_enabled: bool = escalation_enabled
        now = datetime.now(UTC)
        self._created_at: datetime = created_at or now
        self._updated_at: datetime = updated_at or now

        self._validate_and_set(
            name=name,
            response_time_minutes=response_time_minutes,
            resolution_time_minutes=resolution_time_minutes,
            warning_threshold_percent=warning_threshold_percent,
        )

    # ── Validation ────────────────────────────────────────────────────────────

    def _validate_and_set(
        self,
        name: str,
        response_time_minutes: int,
        resolution_time_minutes: int,
        warning_threshold_percent: int,
    ) -> None:
        cleaned_name = name.strip()
        if not cleaned_name:
            raise ValidationError("SLA policy name must not be empty.")
        if response_time_minutes <= 0:
            raise ValidationError("response_time_minutes must be greater than 0.")
        if resolution_time_minutes < response_time_minutes:
            raise ValidationError(
                "resolution_time_minutes must be greater than or equal to response_time_minutes."
            )
        if not (1 <= warning_threshold_percent <= 99):
            raise ValidationError("warning_threshold_percent must be between 1 and 99.")

        self._name = cleaned_name
        self._response_time_minutes = response_time_minutes
        self._resolution_time_minutes = resolution_time_minutes
        self._warning_threshold_percent = warning_threshold_percent

    # ── Read-Only Properties ──────────────────────────────────────────────────

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def priority(self) -> Priority:
        return self._priority

    @property
    def name(self) -> str:
        return self._name

    @property
    def response_time_minutes(self) -> int:
        return self._response_time_minutes

    @property
    def resolution_time_minutes(self) -> int:
        return self._resolution_time_minutes

    @property
    def warning_threshold_percent(self) -> int:
        return self._warning_threshold_percent

    @property
    def escalation_enabled(self) -> bool:
        return self._escalation_enabled

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    # ── Domain Behavior ───────────────────────────────────────────────────────

    def update_targets(
        self,
        name: str | None = None,
        response_time_minutes: int | None = None,
        resolution_time_minutes: int | None = None,
        warning_threshold_percent: int | None = None,
        escalation_enabled: bool | None = None,
    ) -> None:
        """Update policy targets while preserving all domain invariants."""
        self._validate_and_set(
            name=name if name is not None else self._name,
            response_time_minutes=(
                response_time_minutes
                if response_time_minutes is not None
                else self._response_time_minutes
            ),
            resolution_time_minutes=(
                resolution_time_minutes
                if resolution_time_minutes is not None
                else self._resolution_time_minutes
            ),
            warning_threshold_percent=(
                warning_threshold_percent
                if warning_threshold_percent is not None
                else self._warning_threshold_percent
            ),
        )
        if escalation_enabled is not None:
            self._escalation_enabled = escalation_enabled
        self._updated_at = datetime.now(UTC)

    def compute_response_deadline(self, started_at: datetime) -> datetime:
        """Return the UTC timestamp by which initial response is due."""
        return started_at + timedelta(minutes=self._response_time_minutes)

    def compute_resolution_deadline(self, started_at: datetime) -> datetime:
        """Return the UTC timestamp by which full resolution is due."""
        return started_at + timedelta(minutes=self._resolution_time_minutes)

    def __repr__(self) -> str:
        return (
            f"SLAPolicy(priority={self._priority.value}, "
            f"response={self._response_time_minutes}m, "
            f"resolution={self._resolution_time_minutes}m)"
        )
