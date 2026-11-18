
"""
SQLAlchemy ORM models for Member 2 — Incident Management.

Database ownership:
- Member 2 owns incidents and incident_comments.
- reporter_id references M1's user identity.
- service_id references M1's service catalogue.
- assigned_technician_id references M3's technician user identity.

Cross-module UUID references are stored without physical foreign keys
in this initial migration to allow independent module development.
"""
from __future__ import annotations
from uuid import UUID


from datetime import UTC, datetime

from sqlalchemy import (
    CheckConstraint,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.infrastructure.database.base import (
    Base,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)
from app.shared.enums import IncidentCategory, IncidentStatus, Priority


class IncidentModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    ORM model for the incidents table.

    Maps the Incident domain entity to PostgreSQL.
    """

    __tablename__ = "incidents"

    __table_args__ = (
        UniqueConstraint(
            "incident_code",
            name="uq_incidents_incident_code",
        ),

        CheckConstraint(
            "impact BETWEEN 1 AND 5",
            name="ck_incidents_impact_range",
        ),

        CheckConstraint(
            "urgency BETWEEN 1 AND 5",
            name="ck_incidents_urgency_range",
        ),

        CheckConstraint(
            "business_criticality BETWEEN 1 AND 5",
            name="ck_incidents_business_criticality_range",
        ),

        Index("ix_incidents_reporter_id", "reporter_id"),
        Index("ix_incidents_service_id", "service_id"),
        Index("ix_incidents_category", "category"),
        Index("ix_incidents_priority", "priority"),
        Index("ix_incidents_status", "status"),
        Index("ix_incidents_created_at", "created_at"),
        Index(
            "ix_incidents_assigned_technician_id",
            "assigned_technician_id",
        ),
    )

    # Human-readable incident identifier, e.g. INC-1001.
    incident_code: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    # Shared Member 1 identity UUID.
    reporter_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        comment="Logical reference to users.id owned by Member 1",
    )

    # Shared Member 1 service UUID.
    service_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        comment="Logical reference to services.id owned by Member 1",
    )

    category: Mapped[IncidentCategory] = mapped_column(
        SAEnum(
            IncidentCategory,
            name="incident_category_enum",
            native_enum=False,
            values_callable=lambda enum_cls: [
                item.value for item in enum_cls
            ],
        ),
        nullable=False,
    )

    required_skill: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Required technician skill from category mapping",
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    impact: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    urgency: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    business_criticality: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Snapshot of affected service criticality",
    )

    priority: Mapped[Priority] = mapped_column(
        SAEnum(
            Priority,
            name="incident_priority_enum",
            native_enum=False,
            values_callable=lambda enum_cls: [
                item.value for item in enum_cls
            ],
        ),
        nullable=False,
    )

    status: Mapped[IncidentStatus] = mapped_column(
        SAEnum(
            IncidentStatus,
            name="incident_status_enum",
            native_enum=False,
            values_callable=lambda enum_cls: [
                item.value for item in enum_cls
            ],
        ),
        nullable=False,
        default=IncidentStatus.NEW,
        server_default=IncidentStatus.NEW.value,
    )

    # Shared Member 3 technician user UUID.
    assigned_technician_id: Mapped[UUID | None
    ] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
        comment="Logical reference to technicians.user_id",
    )

    resolution_details: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Composition: one Incident HAS multiple IncidentComments.
    comments: Mapped[list[IncidentCommentModel]] = relationship(
        "IncidentCommentModel",
        back_populates="incident",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="IncidentCommentModel.created_at",
    )

    def __repr__(self) -> str:
        return (
            f"<IncidentModel("
            f"id={self.id}, "
            f"code={self.incident_code}, "
            f"status={self.status}"
            f")>"
        )


class IncidentCommentModel(
    Base,
    UUIDPrimaryKeyMixin,
):
    """
    ORM model for incident_comments.

    Every comment belongs to exactly one incident.
    """

    __tablename__ = "incident_comments"

    __table_args__ = (
        CheckConstraint(
            "length(trim(content)) > 0",
            name="ck_incident_comments_content_not_empty",
        ),
        Index(
            "ix_incident_comments_incident_id",
            "incident_id",
        ),
    )

    incident_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Shared User UUID of the comment author.
    author_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        comment="Logical reference to users.id",
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )

    incident: Mapped[IncidentModel] = relationship(
        "IncidentModel",
        back_populates="comments",
    )

    def __repr__(self) -> str:
        return (
            f"<IncidentCommentModel("
            f"id={self.id}, "
            f"incident_id={self.incident_id}"
            f")>"
        )
