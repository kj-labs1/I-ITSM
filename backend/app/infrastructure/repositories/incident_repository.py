
"""
SQLAlchemy implementation of IncidentRepository — Member 2.

Repository Pattern:
Implements incident persistence using SQLAlchemy 2.x Async.

The repository translates between pure domain entities and
database ORM models.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.interfaces.incident_repository import (
    IncidentRepository,
)
from app.core.exceptions import (
    DuplicateAssignmentError,
    InvalidAssignmentError,
)
from app.domain.incident.incident import Incident
from app.domain.incident.incident_comment import IncidentComment
from app.infrastructure.database.incident_models import (
    IncidentCommentModel,
    IncidentModel,
)
from app.shared.enums import (
    IncidentCategory,
    IncidentStatus,
    Priority,
)


class SQLAlchemyIncidentRepository(IncidentRepository):
    """
    PostgreSQL/SQLAlchemy implementation of IncidentRepository.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        """Normalise database timestamps to timezone-aware UTC."""

        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)

        return value.astimezone(UTC)

    def _to_domain(self, model: IncidentModel) -> Incident:
        """Convert IncidentModel into a domain Incident."""

        category = (
            model.category
            if isinstance(model.category, IncidentCategory)
            else IncidentCategory(model.category)
        )

        priority = (
            model.priority
            if isinstance(model.priority, Priority)
            else Priority(model.priority)
        )

        status = (
            model.status
            if isinstance(model.status, IncidentStatus)
            else IncidentStatus(model.status)
        )

        return Incident(
            id=model.id,
            incident_code=model.incident_code,
            reporter_id=model.reporter_id,
            service_id=model.service_id,
            category=category,
            required_skill=model.required_skill,
            description=model.description,
            impact=model.impact,
            urgency=model.urgency,
            business_criticality=model.business_criticality,
            priority=priority,
            status=status,
            assigned_technician_id=model.assigned_technician_id,
            resolution_details=model.resolution_details,
            created_at=self._as_utc(model.created_at),
            updated_at=self._as_utc(model.updated_at),
        )

    def _to_comment_domain(
        self,
        model: IncidentCommentModel,
    ) -> IncidentComment:
        """Convert IncidentCommentModel into a domain IncidentComment."""

        return IncidentComment(
            id=model.id,
            incident_id=model.incident_id,
            author_id=model.author_id,
            content=model.content,
            created_at=self._as_utc(model.created_at),
        )

    async def save(self, incident: Incident) -> Incident:
        """Persist a new incident."""

        model = IncidentModel(
            id=incident.id,
            incident_code=incident.incident_code,
            reporter_id=incident.reporter_id,
            service_id=incident.service_id,
            category=incident.category,
            required_skill=incident.required_skill,
            description=incident.description,
            impact=incident.impact,
            urgency=incident.urgency,
            business_criticality=incident.business_criticality,
            priority=incident.priority,
            status=incident.status,
            assigned_technician_id=incident.assigned_technician_id,
            resolution_details=incident.resolution_details,
            created_at=incident.created_at,
            updated_at=incident.updated_at,
        )

        self._session.add(model)

        await self._session.flush()

        return self._to_domain(model)


    async def find_recent_by_service_and_category(
        self,
        service_id: UUID,
        category: IncidentCategory,
        since: datetime,
        until: datetime,
    ) -> list[Incident]:
        """
    Find incidents with the same service and category
    created within the specified time interval.
    """

        stmt = (
            select(IncidentModel)
            .where(
                IncidentModel.service_id == service_id,
                IncidentModel.category == category,
                IncidentModel.created_at >= since,
                IncidentModel.created_at <= until,
            )
            .order_by(
                IncidentModel.created_at.desc(),
                IncidentModel.id.asc(),
            )
        )

        result = await self._session.execute(stmt)

        models = result.scalars().all()

        return [self._to_domain(model) for model in models]
    async def list_all(
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
        category: IncidentCategory | None = None,
        service_id: UUID | None = None,
        assigned_technician_id: UUID | None = None,
    ) -> list[Incident]:
        """Retrieve incidents using optional search and filter criteria."""

        stmt = select(IncidentModel)

        if reporter_id is not None:
            stmt = stmt.where(
            IncidentModel.reporter_id == reporter_id
        )

        if incident_id is not None:
            stmt = stmt.where(
            IncidentModel.id == incident_id
        )

        if incident_code:
            stmt = stmt.where(
            IncidentModel.incident_code.ilike(
                f"%{incident_code.strip()}%"
            )
        )

        if date_from is not None:
            stmt = stmt.where(
            IncidentModel.created_at >= date_from
        )

        if date_to is not None:
            stmt = stmt.where(
            IncidentModel.created_at <= date_to
        )

        if status is not None:
            stmt = stmt.where(
            IncidentModel.status == status
        )

        if priority is not None:
            stmt = stmt.where(
            IncidentModel.priority == priority
        )

        if category is not None:
            stmt = stmt.where(
            IncidentModel.category == category
        )

        if service_id is not None:
            stmt = stmt.where(
            IncidentModel.service_id == service_id
        )

        if assigned_technician_id is not None:
            stmt = stmt.where(
            IncidentModel.assigned_technician_id
            == assigned_technician_id
        )

    # Stable ordering makes pagination predictable.
        stmt = (
            stmt
            .order_by(
                IncidentModel.created_at.desc(),
                IncidentModel.id.asc(),
            )
            .offset(skip)
            .limit(limit)
        )

        result = await self._session.execute(stmt)

        models = result.scalars().all()

        return [self._to_domain(model) for model in models]
    async def count_active_by_technician(
        self,
        technician_user_id: UUID,
    ) -> int:
        """
        Count active incidents assigned to a technician.

        Completed incidents are excluded from the workload.
        """

        active_statuses = [
            IncidentStatus.ASSIGNED,
            IncidentStatus.ACKNOWLEDGED,
            IncidentStatus.IN_PROGRESS,
        ]

        stmt = (
            select(func.count())
            .select_from(IncidentModel)
            .where(
                IncidentModel.assigned_technician_id
                == technician_user_id
            )
            .where(
                IncidentModel.status.in_(active_statuses)
            )
        )

        result = await self._session.execute(stmt)

        return int(result.scalar_one() or 0)
    async def get_by_id(
        self,
        incident_id: UUID,
    ) -> Incident | None:
        """Retrieve incident by primary key."""

        stmt = select(IncidentModel).where(
            IncidentModel.id == incident_id
        )

        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        return self._to_domain(model) if model else None

    async def get_by_code(
        self,
        incident_code: str,
    ) -> Incident | None:
        """Retrieve incident by human-readable code."""

        stmt = select(IncidentModel).where(
            IncidentModel.incident_code == incident_code
        )

        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        return self._to_domain(model) if model else None

    async def update(self, incident: Incident) -> Incident:
        """Update an existing incident with atomic concurrency protection."""

        if (
            incident.status == IncidentStatus.ASSIGNED
            and incident.assigned_technician_id is not None
        ):
            # Atomic Compare-And-Swap (CAS) guard against concurrent duplicate assignments
            cas_stmt = (
                update(IncidentModel)
                .where(IncidentModel.id == incident.id)
                .where(
                    or_(
                        IncidentModel.assigned_technician_id.is_(None),
                        IncidentModel.assigned_technician_id == incident.assigned_technician_id,
                    )
                )
                .where(
                    IncidentModel.status.in_(
                        [
                            IncidentStatus.NEW,
                            IncidentStatus.CLASSIFIED,
                            IncidentStatus.ASSIGNED,
                        ]
                    )
                )
                .values(
                    incident_code=incident.incident_code,
                    reporter_id=incident.reporter_id,
                    service_id=incident.service_id,
                    category=incident.category,
                    required_skill=incident.required_skill,
                    description=incident.description,
                    impact=incident.impact,
                    urgency=incident.urgency,
                    business_criticality=incident.business_criticality,
                    priority=incident.priority,
                    status=IncidentStatus.ASSIGNED,
                    assigned_technician_id=incident.assigned_technician_id,
                    resolution_details=incident.resolution_details,
                    updated_at=datetime.now(UTC),
                )
            )
            result = await self._session.execute(cas_stmt)
            if result.rowcount == 0:
                self._session.expire_all()
                check_stmt = select(IncidentModel).where(IncidentModel.id == incident.id)
                current = (await self._session.execute(check_stmt)).scalar_one_or_none()
                if current and current.assigned_technician_id is not None:
                    raise DuplicateAssignmentError(
                        f"Incident {current.incident_code} is already assigned."
                    )
                raise InvalidAssignmentError(
                    f"Incident {incident.incident_code} cannot be assigned."
                )

            self._session.expire_all()
            fresh_stmt = select(IncidentModel).where(IncidentModel.id == incident.id)
            fresh_model = (await self._session.execute(fresh_stmt)).scalar_one()
            return self._to_domain(fresh_model)

        stmt = select(IncidentModel).where(
            IncidentModel.id == incident.id
        )

        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing is None:
            raise ValueError(
                f"Incident with ID {incident.id} does not exist."
            )

        existing.incident_code = incident.incident_code
        existing.reporter_id = incident.reporter_id
        existing.service_id = incident.service_id
        existing.category = incident.category
        existing.required_skill = incident.required_skill
        existing.description = incident.description
        existing.impact = incident.impact
        existing.urgency = incident.urgency
        existing.business_criticality = incident.business_criticality
        existing.priority = incident.priority
        existing.status = incident.status
        existing.assigned_technician_id = (
            incident.assigned_technician_id
        )
        existing.resolution_details = incident.resolution_details

        existing.updated_at = datetime.now(UTC)

        await self._session.flush()

        return self._to_domain(existing)

    async def save_comment(
        self,
        comment: IncidentComment,
    ) -> IncidentComment:
        """Persist an incident comment."""

        model = IncidentCommentModel(
            id=comment.id,
            incident_id=comment.incident_id,
            author_id=comment.author_id,
            content=comment.content,
            created_at=comment.created_at,
        )

        self._session.add(model)

        await self._session.flush()

        return self._to_comment_domain(model)

    async def list_comments(
        self,
        incident_id: UUID,
    ) -> list[IncidentComment]:
        """Retrieve incident comments in chronological order."""

        stmt = (
            select(IncidentCommentModel)
            .where(
                IncidentCommentModel.incident_id == incident_id
            )
            .order_by(
                IncidentCommentModel.created_at.asc(),
                IncidentCommentModel.id.asc(),
            )
        )

        result = await self._session.execute(stmt)

        models = result.scalars().all()

        return [
            self._to_comment_domain(model)
            for model in models
        ]
