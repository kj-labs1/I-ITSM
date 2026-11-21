
"""
Incident domain entity — Member 2.

Represents the core incident in the I-ITSM domain.

Architecture:
- Pure Python dataclass; no SQLAlchemy or FastAPI dependencies.
- Uses shared enums from app.shared.enums.
- Encapsulates basic incident data validation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.core.exceptions import ValidationError
from app.domain.incident.lifecycle import IncidentLifecycle
from app.domain.incident.priority_calculator import PriorityCalculator
from app.shared.enums import IncidentCategory, IncidentStatus, Priority


@dataclass
class Incident:
    """
    Domain entity representing an IT incident.

    Identity:
        id: Internal UUID.
        incident_code: Human-readable incident reference.

    Ownership:
        reporter_id: UUID of the employee who reported the issue.
        service_id: UUID of the affected IT service.

    Classification:
        category: Incident category.
        required_skill: Skill required to investigate the incident.
        description: Problem description.
        impact: Impact score (1-5).
        urgency: Urgency score (1-5).
        business_criticality: Affected service criticality (1-5).
        priority: Calculated priority.

    Lifecycle:
        status: Current incident state.
        assigned_technician_id: Shared technician user UUID.
        resolution_details: Resolution entered by technician.
    """

    incident_code: str
    reporter_id: UUID
    service_id: UUID

    category: IncidentCategory
    required_skill: str
    description: str

    impact: int
    urgency: int
    business_criticality: int
    priority: Priority

    status: IncidentStatus = IncidentStatus.NEW

    assigned_technician_id: UUID | None = None
    resolution_details: str | None = None

    is_archived: bool = False
    archived_at: datetime | None = None
    archived_by: UUID | None = None

    merged_into_incident_id: UUID | None = None
    merged_at: datetime | None = None
    merged_by: UUID | None = None

    id: UUID = field(default_factory=uuid4)

    created_at: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )

    updated_at: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )

    def __post_init__(self) -> None:
        """Validate basic domain invariants after construction."""

        if not self.incident_code or not self.incident_code.strip():
            raise ValueError("Incident code cannot be empty.")

        if not self.required_skill or not self.required_skill.strip():
            raise ValueError("Required skill cannot be empty.")

        if not self.description or not self.description.strip():
            raise ValueError("Incident description cannot be empty.")

        self.incident_code = self.incident_code.strip()
        self.required_skill = self.required_skill.strip()
        self.description = self.description.strip()

        self._validate_score("impact", self.impact)
        self._validate_score("urgency", self.urgency)
        self._validate_score(
            "business_criticality",
            self.business_criticality,
        )

        if not isinstance(self.category, IncidentCategory):
            raise ValueError("Invalid incident category.")

        if not isinstance(self.priority, Priority):
            raise ValueError("Invalid incident priority.")

        if not isinstance(self.status, IncidentStatus):
            raise ValueError("Invalid incident status.")

    @staticmethod
    def _validate_score(field_name: str, value: int) -> None:
        """Ensure incident scoring factors are between 1 and 5."""

        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or not 1 <= value <= 5
        ):
            raise ValueError(
                f"{field_name} must be an integer between 1 and 5."
            )

    def transition_to(
        self,
        new_status: IncidentStatus,
        resolution_details: str | None = None,
    ) -> IncidentStatus:
        """
    Transition the incident to a new lifecycle state.

    This method ensures:
    1. The requested transition is valid.
    2. Resolution details are supplied before RESOLVED.
    3. The incident status is updated only after validation.
    4. The updated timestamp is refreshed.

    Args:
        new_status:
            The requested new incident status.

        resolution_details:
            Required when transitioning to RESOLVED.

    Returns:
        The newly assigned IncidentStatus.

    Raises:
        InvalidStatusTransitionError:
            If the lifecycle transition is not permitted.

        ValidationError:
            If required resolution details are missing.
    """

        # Step 1: Validate the lifecycle transition.
        IncidentLifecycle.validate_transition(
            current_status=self.status,
            new_status=new_status,
            incident_code=self.incident_code,
        )

        # Step 2: Require resolution details before resolving.
        if new_status == IncidentStatus.RESOLVED:

            if (
            not isinstance(resolution_details, str)
            or not resolution_details.strip()
            ):
                raise ValidationError(
                    message=(
                        "Resolution details must be provided "
                        "before marking an incident as RESOLVED."
                    ),
                    error_code="RESOLUTION_DETAILS_REQUIRED",
                )

            self.resolution_details = resolution_details.strip()

        # Step 3: Update the status only after all validations pass.
        self.status = new_status

        # Step 4: Update the modification timestamp.
        self.touch()

        return self.status
    def recalculate_priority(self) -> Priority:
        """Recalculate incident priority using the current scoring factors.
        This method must be called whenever impact, urgency or
        business criticality changes.

        Returns:
            The newly calculated Priority enum.
        """

        self.priority = PriorityCalculator.calculate(
            impact=self.impact,
            urgency=self.urgency,
            business_criticality=self.business_criticality,
        )

        self.touch()

        return self.priority

    def archive(self, actor_id: UUID) -> None:
        """Soft-archive a CLOSED incident."""
        if self.is_archived:
            raise ValidationError(
                f"Incident {self.incident_code} is already archived.",
                error_code="ALREADY_ARCHIVED",
            )

        if self.status != IncidentStatus.CLOSED:
            raise ValidationError(
                f"Only CLOSED incidents can be archived. Current status: '{self.status.value}'.",
                error_code="INVALID_STATUS_FOR_ARCHIVE",
            )

        self.is_archived = True
        self.archived_at = datetime.now(UTC)
        self.archived_by = actor_id
        self.touch()

    def merge_into(self, primary_id: UUID, actor_id: UUID) -> None:
        """Mark this incident as a duplicate merged into a primary incident."""
        if self.id == primary_id:
            raise ValidationError(
                "An incident cannot be merged into itself.",
                error_code="SELF_MERGE_DISALLOWED",
            )

        if self.merged_into_incident_id is not None:
            raise ValidationError(
                f"Incident {self.incident_code} has already been merged into {self.merged_into_incident_id}.",
                error_code="ALREADY_MERGED",
            )

        self.merged_into_incident_id = primary_id
        self.merged_at = datetime.now(UTC)
        self.merged_by = actor_id
        self.touch()

    def touch(self) -> None:
        """Update the modification timestamp."""

        self.updated_at = datetime.now(UTC)

    def __repr__(self) -> str:
        return (
            f"Incident("
            f"code={self.incident_code}, "
            f"priority={self.priority.value}, "
            f"status={self.status.value}"
            f")"
        )
