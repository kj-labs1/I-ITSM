
"""
Incident application service — Member 2.

Coordinates incident creation, retrieval, updates, lifecycle transitions,
comments and cross-module technician assignment integration.

Architecture:
- Depends on IncidentRepository abstraction.
- Depends on EventPublisher abstraction.
- Uses pure domain entities and business rules.
- Implements IncidentServiceBoundary for Member 3.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.application.interfaces.event_publisher import EventPublisher
from app.application.interfaces.incident_repository import IncidentRepository
from app.application.interfaces.incident_service import IncidentServiceBoundary
from app.core.exceptions import (
    DuplicateAssignmentError,
    IncidentNotFoundError,
    InvalidAssignmentError,
    ValidationError,
)
from app.domain.incident.duplicate_detector import (
    DuplicateDetector,
)
from app.domain.incident.duplicate_policy import (
    DEFAULT_DUPLICATE_POLICY,
)
from app.domain.incident.events import (
    IncidentArchivedEvent,
    IncidentCommentAddedEvent,
    IncidentCreatedEvent,
    IncidentMergedEvent,
    IncidentStatusChangedEvent,
    PriorityChangedEvent,
)
from app.domain.incident.incident import Incident
from app.domain.incident.incident_comment import IncidentComment
from app.domain.incident.incident_ref import IncidentRef
from app.domain.incident.priority_calculator import PriorityCalculator
from app.shared.enums import (
    IncidentCategory,
    IncidentStatus,
)

logger = logging.getLogger(__name__)


class IncidentApplicationService(IncidentServiceBoundary):
    """
    Application service for Member 2's Incident Management module.

    Responsibilities:
    1. Create incidents and calculate priority.
    2. Retrieve and list incidents.
    3. Update permitted incident information.
    4. Coordinate lifecycle transitions.
    5. Manage incident comments.
    6. Implement Member 3's IncidentServiceBoundary.
    7. Publish incident domain events for Member 4.
    """

    ACTIVE_STATUSES = (
        IncidentStatus.ASSIGNED,
        IncidentStatus.ACKNOWLEDGED,
        IncidentStatus.IN_PROGRESS,
    )

    def __init__(
        self,
        repository: IncidentRepository,
        event_publisher: EventPublisher,
    ) -> None:
        self.repository = repository
        self.event_publisher = event_publisher

    # ============================================================
    # INCIDENT CREATION
    # ============================================================

    @staticmethod
    def _normalize_search_datetime(
    value: datetime | None,
    field_name: str,
) -> datetime | None:
        """
    Validate a search datetime and normalize it to UTC.

    Naive datetimes are rejected because their timezone is ambiguous.
    """

        if value is None:
            return None

        if value.tzinfo is None or value.utcoffset() is None:
            raise ValidationError(
            f"{field_name} must include a timezone. "
            "Use an ISO-8601 datetime with Z or an explicit UTC offset.",
            error_code="TIMEZONE_REQUIRED",
        )

        return value.astimezone(UTC)
    async def create_incident(
        self,
        reporter_id: UUID,
        service_id: UUID,
        category: IncidentCategory,
        required_skill: str,
        description: str,
        impact: int,
        urgency: int,
        business_criticality: int,
    ) -> Incident:
        """
        Create and persist a new incident.

        Priority is always calculated on the backend.

        Initial status:
            NEW
        """

        priority = PriorityCalculator.calculate(
            impact=impact,
            urgency=urgency,
            business_criticality=business_criticality,
        )

        incident = Incident(
            incident_code=f"INC-{uuid4().hex[:8].upper()}",
            reporter_id=reporter_id,
            service_id=service_id,
            category=category,
            required_skill=required_skill,
            description=description,
            impact=impact,
            urgency=urgency,
            business_criticality=business_criticality,
            priority=priority,
            status=IncidentStatus.NEW,
        )

        saved = await self.repository.save(incident)

        await self.event_publisher.publish(
            IncidentCreatedEvent(
                incident_id=saved.id,
                incident_code=saved.incident_code,
                reporter_id=saved.reporter_id,
                service_id=saved.service_id,
                category=saved.category,
                priority=saved.priority,
            )
        )

        logger.info(
            "Created incident %s with priority %s",
            saved.incident_code,
            saved.priority.value,
        )

        return saved

    # ============================================================
    # INCIDENT RETRIEVAL
    # ============================================================

    async def list_incidents(
        self,
        skip: int = 0,
        limit: int = 50,
        reporter_id: UUID | None = None,
        incident_id: UUID | None = None,
        incident_code: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        status=None,
        priority=None,
        category=None,
        service_id: UUID | None = None,
        assigned_technician_id: UUID | None = None,
        is_archived: bool | None = False,
    ) -> list[Incident]:
        """List incidents after validating all search criteria."""

    # Validate pagination even if this method is called outside FastAPI.
        if skip < 0:
            raise ValidationError(
            "skip cannot be negative.",
            error_code="INVALID_PAGINATION",
        )

        if not 1 <= limit <= 100:
            raise ValidationError(
            "limit must be between 1 and 100.",
            error_code="INVALID_PAGINATION",
        )

    # Normalize incident-code input.
        # Normalize incident-code input.
        if incident_code is not None:
            incident_code = incident_code.strip()

            if not incident_code:
                raise ValidationError(
                    "Incident code cannot contain only whitespace.",
                    error_code="INVALID_INCIDENT_CODE",
                )

            if len(incident_code) > 50:
                raise ValidationError(
                    "Incident code cannot exceed 50 characters.",
                    error_code="INVALID_INCIDENT_CODE",
                )

    # Validate and normalize date filters.
        date_from = self._normalize_search_datetime(
        date_from,
        "dateFrom",
    )

        date_to = self._normalize_search_datetime(
        date_to,
        "dateTo",
    )

        if (
        date_from is not None
        and date_to is not None
        and date_from > date_to
    ):
            raise ValidationError(
            "dateFrom must be earlier than or equal to dateTo.",
            error_code="INVALID_DATE_RANGE",
        )

        return await self.repository.list_all(
            skip=skip,
            limit=limit,
            reporter_id=reporter_id,
            incident_id=incident_id,
            incident_code=incident_code,
            date_from=date_from,
            date_to=date_to,
            status=status,
            priority=priority,
            category=category,
            service_id=service_id,
            assigned_technician_id=assigned_technician_id,
            is_archived=is_archived,
        )

    async def find_potential_duplicates(
    self,
    incident_id: UUID,
) -> list:
        """
    Find potential duplicates using the shared duplicate policy.

    Conditions:
    - Same affected service.
    - Same incident category.
    - Created during the preceding 24 hours.
    - Jaccard similarity >= 0.50.
    """

        incident = await self.get_incident_entity(incident_id)

        policy = DEFAULT_DUPLICATE_POLICY

    # SQLite may return naive datetimes even when timezone=True is used.
    # The application contract stores timestamps in UTC, so interpret
    # such values as UTC before computing the candidate window.
        reference_time = incident.created_at

        if reference_time.tzinfo is None:
            reference_time = reference_time.replace(tzinfo=UTC)
        else:
            reference_time = reference_time.astimezone(UTC)

        since = reference_time - policy.lookback_window

        candidates = (
        await self.repository.find_recent_by_service_and_category(
            service_id=incident.service_id,
            category=incident.category,
            since=since,
            until=reference_time,
        )
    )

        detector = DuplicateDetector(
        threshold=policy.similarity_threshold,
    )

        return detector.find_duplicates(
        incident=incident,
        candidates=candidates,
    )
    async def get_incident_entity(
        self,
        incident_id: UUID,
    ) -> Incident:
        """Retrieve the full Incident domain entity."""

        incident = await self.repository.get_by_id(incident_id)

        if incident is None:
            raise IncidentNotFoundError(resource_id=str(incident_id))

        return incident

    async def get_incident_details(
        self,
        incident_id: UUID,
    ) -> tuple[Incident, list[IncidentComment]]:
        """Retrieve an incident together with its comments."""

        incident = await self.get_incident_entity(incident_id)

        comments = await self.repository.list_comments(incident_id)

        return incident, comments

    # ============================================================
    # INCIDENT UPDATE
    # ============================================================

    async def update_incident(
        self,
        incident_id: UUID,
        changes: dict[str, object],
    ) -> Incident:
        """
        Update permitted incident fields.

        Editable fields:
        - description
        - impact
        - urgency

        Priority is recalculated whenever scoring information changes.
        """

        allowed_fields = {
            "description",
            "impact",
            "urgency",
        }

        invalid_fields = set(changes) - allowed_fields

        if invalid_fields:
            raise ValidationError(
                message=(
                    "The following incident fields cannot be updated: "
                    + ", ".join(sorted(invalid_fields))
                )
            )

        if not changes:
            raise ValidationError("At least one field must be provided.")

        incident = await self.get_incident_entity(incident_id)

        new_description = changes.get(
            "description",
            incident.description,
        )

        new_impact = changes.get("impact", incident.impact)
        new_urgency = changes.get("urgency", incident.urgency)

        if (
            not isinstance(new_description, str)
            or not new_description.strip()
        ):
            raise ValidationError(
                "Incident description cannot be empty."
            )

        # Validate all factors before mutating the domain entity.
        try:
            PriorityCalculator.calculate(
                impact=new_impact,
                urgency=new_urgency,
                business_criticality=incident.business_criticality,
            )
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc

        previous_priority = incident.priority

        incident.description = new_description.strip()
        incident.impact = new_impact
        incident.urgency = new_urgency

        # Recalculate priority through the domain entity.
        incident.recalculate_priority()

        updated = await self.repository.update(incident)

        if updated.priority != previous_priority:
            await self.event_publisher.publish(
                PriorityChangedEvent(
                    incident_id=updated.id,
                    incident_code=updated.incident_code,
                    previous_priority=previous_priority,
                    new_priority=updated.priority,
                    reporter_id=updated.reporter_id,
                    assigned_technician_id=updated.assigned_technician_id,
                )
            )

        logger.info(
            "Updated incident %s",
            updated.incident_code,
        )

        return updated

    # ============================================================
    # INCIDENT STATUS TRANSITION
    # ============================================================

    async def update_incident_status(
        self,
        incident_id: UUID,
        new_status: IncidentStatus,
        actor_id: UUID,
        resolution_details: str | None = None,
    ) -> Incident:
        """
        Change incident status through the domain state machine.

        Invalid transitions are rejected by Incident.transition_to().
        """

        incident = await self.get_incident_entity(incident_id)

        previous_status = incident.status

        incident.transition_to(
            new_status=new_status,
            resolution_details=resolution_details,
        )

        updated = await self.repository.update(incident)

        await self.event_publisher.publish(
            IncidentStatusChangedEvent(
                incident_id=updated.id,
                incident_code=updated.incident_code,
                previous_status=previous_status,
                new_status=updated.status,
                actor_id=actor_id,
                reporter_id=updated.reporter_id,
                assigned_technician_id=updated.assigned_technician_id,
            )
        )

        logger.info(
            "Incident %s transitioned from %s to %s",
            updated.incident_code,
            previous_status.value,
            updated.status.value,
        )

        return updated

    # ============================================================
    # INCIDENT COMMENTS
    # ============================================================

    async def add_comment(
        self,
        incident_id: UUID,
        author_id: UUID,
        content: str,
    ) -> IncidentComment:
        """Add a comment to an existing incident."""

        # Ensure that the parent incident exists.
        parent = await self.get_incident_entity(incident_id)

        try:
            comment = IncidentComment(
                incident_id=incident_id,
                author_id=author_id,
                content=content,
            )
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc

        saved_comment = await self.repository.save_comment(comment)

        await self.event_publisher.publish(
            IncidentCommentAddedEvent(
                incident_id=parent.id,
                incident_code=parent.incident_code,
                author_id=author_id,
                reporter_id=parent.reporter_id,
                assigned_technician_id=parent.assigned_technician_id,
                content_snippet=content[:100],
            )
        )

        return saved_comment

    # ============================================================
    # MEMBER 3 INTEGRATION — INCIDENT SERVICE BOUNDARY
    # ============================================================

    async def get_incident(
        self,
        incident_id: UUID,
    ) -> IncidentRef | None:
        """
        Return a read-only incident projection for Member 3.

        Implements IncidentServiceBoundary.get_incident().
        """

        incident = await self.repository.get_by_id(incident_id)

        if incident is None:
            return None

        return IncidentRef(
            id=incident.id,
            incident_code=incident.incident_code,
            category=incident.category,
            required_skill=incident.required_skill,
            priority=incident.priority,
            status=incident.status,
            description=incident.description,
            service_id=incident.service_id,
            reporter_id=incident.reporter_id,
            assigned_technician_id=incident.assigned_technician_id,
            created_at=incident.created_at,
        )

    async def assign_technician(
        self,
        incident_id: UUID,
        technician_id: UUID,
        actor_id: UUID,
    ) -> bool:
        """
        Persist a technician assignment requested by Member 3.

        Member 3 selects and validates the technician.
        Member 2 owns the incident status transition and persistence.
        """

        incident = await self.get_incident_entity(incident_id)

        if incident.assigned_technician_id is not None:
            raise DuplicateAssignmentError(
                f"Incident {incident.incident_code} is already assigned."
            )

        if incident.status not in (
            IncidentStatus.NEW,
            IncidentStatus.CLASSIFIED,
        ):
            raise InvalidAssignmentError(
                f"Incident {incident.incident_code} cannot be assigned "
                f"while in status {incident.status.value}."
            )

        previous_status = incident.status

        incident.transition_to(
            IncidentStatus.ASSIGNED
        )

        incident.assigned_technician_id = technician_id

        await self.repository.update(incident)

        await self.event_publisher.publish(
            IncidentStatusChangedEvent(
                incident_id=incident.id,
                incident_code=incident.incident_code,
                previous_status=previous_status,
                new_status=IncidentStatus.ASSIGNED,
                actor_id=actor_id,
                reporter_id=incident.reporter_id,
                assigned_technician_id=technician_id,
            )
        )

        logger.info(
            "Technician %s assigned to incident %s",
            technician_id,
            incident.incident_code,
        )

        return True

    async def get_active_incident_count(
        self,
        technician_user_id: UUID,
    ) -> int:
        """
        Return authoritative active workload for Member 3.

        Completed incidents are excluded.
        """

        return await self.repository.count_active_by_technician(
            technician_user_id
        )

    # ============================================================
    # ARCHIVING & MERGING OPERATIONS (Tasks 3 & 4)
    # ============================================================

    async def archive_incident(
        self,
        incident_id: UUID,
        actor_id: UUID,
    ) -> Incident:
        """Soft-archive a CLOSED incident (admin only)."""
        incident = await self.repository.get_by_id(incident_id)
        if incident is None:
            raise IncidentNotFoundError(resource_id=str(incident_id))

        incident.archive(actor_id=actor_id)
        updated = await self.repository.update(incident)

        await self.event_publisher.publish(
            IncidentArchivedEvent(
                incident_id=updated.id,
                incident_code=updated.incident_code,
                actor_id=actor_id,
            )
        )

        logger.info(
            "Incident %s (%s) soft-archived by actor %s",
            updated.incident_code,
            updated.id,
            actor_id,
        )
        return updated

    async def list_archived_incidents(
        self,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Incident]:
        """Retrieve soft-archived incidents (admin only)."""
        if skip < 0 or not 1 <= limit <= 100:
            raise ValidationError(
                "Invalid pagination parameters.",
                error_code="INVALID_PAGINATION",
            )
        return await self.repository.list_all(
            skip=skip,
            limit=limit,
            is_archived=True,
        )

    async def merge_incidents(
        self,
        primary_incident_id: UUID,
        duplicate_incident_ids: list[UUID],
        actor_id: UUID,
    ) -> dict:
        """Merge one or more duplicate incidents into a primary incident (admin only)."""
        if not duplicate_incident_ids:
            raise ValidationError(
                "At least one duplicate incident ID must be specified for merge.",
                error_code="EMPTY_MERGE_LIST",
            )

        if primary_incident_id in duplicate_incident_ids:
            raise ValidationError(
                "Primary incident cannot be in the list of duplicate incidents to merge.",
                error_code="SELF_MERGE_DISALLOWED",
            )

        primary = await self.repository.get_by_id(primary_incident_id)
        if primary is None:
            raise IncidentNotFoundError(resource_id=str(primary_incident_id))

        if primary.is_archived:
            raise ValidationError(
                f"Primary incident {primary.incident_code} is archived and cannot receive merged incidents.",
                error_code="ARCHIVED_MERGE_DISALLOWED",
            )

        if primary.merged_into_incident_id is not None:
            raise ValidationError(
                f"Primary incident {primary.incident_code} has already been merged into another incident.",
                error_code="PRIMARY_ALREADY_MERGED",
            )

        merged_duplicates = []
        for dup_id in duplicate_incident_ids:
            dup = await self.repository.get_by_id(dup_id)
            if dup is None:
                raise IncidentNotFoundError(resource_id=str(dup_id))

            if dup.is_archived:
                raise ValidationError(
                    f"Duplicate incident {dup.incident_code} is archived and cannot be merged.",
                    error_code="ARCHIVED_MERGE_DISALLOWED",
                )

            if dup.merged_into_incident_id is not None:
                raise ValidationError(
                    f"Incident {dup.incident_code} has already been merged into {dup.merged_into_incident_id}.",
                    error_code="ALREADY_MERGED",
                )

            dup.merge_into(primary_id=primary.id, actor_id=actor_id)
            dup.status = IncidentStatus.CLOSED
            dup.resolution_details = (
                f"Merged into primary incident {primary.incident_code} ({primary.id})"
            )
            saved_dup = await self.repository.update(dup)
            merged_duplicates.append(saved_dup)

            # Preserve history: add comment to primary referencing duplicate
            await self.add_comment(
                incident_id=primary.id,
                author_id=actor_id,
                content=(
                    f"[Duplicate Merged] Incident {dup.incident_code} (ID: {dup.id}) "
                    f"was merged into this incident. Original description: '{dup.description}'"
                ),
            )

            # Publish event for audit logs
            await self.event_publisher.publish(
                IncidentMergedEvent(
                    incident_id=dup.id,
                    incident_code=dup.incident_code,
                    primary_incident_id=primary.id,
                    primary_incident_code=primary.incident_code,
                    actor_id=actor_id,
                    duplicate_incident_ids=[dup.id],
                )
            )

        logger.info(
            "Successfully merged %d incidents into primary incident %s (%s)",
            len(merged_duplicates),
            primary.incident_code,
            primary.id,
        )

        return {
            "primary_incident_id": primary.id,
            "primary_incident_code": primary.incident_code,
            "merged_incident_ids": [d.id for d in merged_duplicates],
            "merged_count": len(merged_duplicates),
            "merged_at": datetime.now(UTC),
        }
