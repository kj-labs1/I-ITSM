"""
SQLAlchemy ORM models for Member 3 (Technician & Skills).

Database Ownership Boundary:
- Module M3 owns:
  - `technicians` table: Technician profile & operational metadata.
  - `technician_skills` table: Skill catalog mapping for technicians.
- Module M1 owns `users`. The `technicians.user_id` column references M1's User UUID.
  In this initial phase, `user_id` is maintained as a UUID index/logical reference so
  that M3's schema can be migrated and tested independently before M1 merges.
- Module M2 owns `incidents`. Technicians do NOT store incident foreign keys directly;
  active workload is derived dynamically from open assigned incidents.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.infrastructure.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.shared.enums import AvailabilityStatus, IncidentCategory, UserRole

if TYPE_CHECKING:
    pass


class TechnicianModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Relational model for technician operational profiles.

    Shared Identity Agreement:
    - Uses the shared User UUID from M1 as `user_id`.
    - Does NOT duplicate user account information (email, password hash, full name).

    Proposed Fields (documented and subject to team contract approval):
    - `experience_years`: Integer >= 0 for ranking and tie-break resolution.
    - `max_capacity`: Integer >= 1 representing max concurrent assigned incidents.
    """

    __tablename__ = "technicians"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        unique=True,
        nullable=False,
        index=True,
        comment="References M1 users.id — shared User UUID",
    )
    availability: Mapped[AvailabilityStatus] = mapped_column(
        SAEnum(AvailabilityStatus, name="availability_status_enum", native_enum=False),
        default=AvailabilityStatus.AVAILABLE,
        nullable=False,
    )
    experience_years: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Proposed field: years of professional experience",
    )
    max_capacity: Mapped[int] = mapped_column(
        Integer,
        default=10,
        nullable=False,
        comment="Proposed field: maximum concurrent assigned incidents",
    )

    # Composition: Technician HAS skills
    skills: Mapped[list[TechnicianSkillModel]] = relationship(
        "TechnicianSkillModel",
        back_populates="technician",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # Reference to M1 User
    user: Mapped[UserModel | None] = relationship(
        "UserModel",
        primaryjoin="TechnicianModel.user_id == UserModel.id",
        foreign_keys=[user_id],
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<TechnicianModel(id={self.id}, user_id={self.user_id}, availability={self.availability})>"


class TechnicianSkillModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Relational model for technician skills.

    Each record maps a technician to an acquired skill with a 1-5 proficiency level.
    """

    __tablename__ = "technician_skills"
    __table_args__ = (
        UniqueConstraint("technician_id", "skill_name", name="uq_technician_skill"),
        Index("ix_technician_skills_skill_name", "skill_name"),
    )

    technician_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("technicians.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    skill_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Skill identifier or category name matching incident requirements",
    )
    proficiency_level: Mapped[int] = mapped_column(
        Integer,
        default=3,
        nullable=False,
        comment="Proficiency score from 1 (Novice) to 5 (Expert)",
    )

    # Relationship back to parent technician profile
    technician: Mapped[TechnicianModel] = relationship(
        "TechnicianModel",
        back_populates="skills",
    )

    def __repr__(self) -> str:
        return f"<TechnicianSkillModel(skill={self.skill_name}, proficiency={self.proficiency_level})>"


class UserModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Database model for system users (Member 1)."""

    __tablename__ = "users"

    username: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="user_role_enum", native_enum=False),
        default=UserRole.EMPLOYEE,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<UserModel(id={self.id}, username={self.username}, role={self.role})>"


class ServiceModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """IT service catalogue entry (Member 1)."""

    __tablename__ = "services"

    __table_args__ = (
        CheckConstraint(
            "business_criticality >= 1 AND business_criticality <= 5",
            name="ck_services_business_criticality",
        ),
    )

    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    business_criticality: Mapped[int] = mapped_column(
        Integer, default=3, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<ServiceModel(id={self.id}, name={self.name}, criticality={self.business_criticality})>"


class IncidentCategoryModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Configurable incident category and required technician skill (Member 1)."""

    __tablename__ = "incident_categories"

    category: Mapped[IncidentCategory] = mapped_column(
        SAEnum(
            IncidentCategory,
            name="incident_category_enum",
            native_enum=False,
        ),
        unique=True,
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    required_skill: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<IncidentCategoryModel(category={self.category}, required_skill={self.required_skill})>"


# Re-export Member 2 and Member 4 models for unified database metadata discovery
from app.infrastructure.database.incident_models import (  # noqa: E402, F401
    IncidentCommentModel,
    IncidentModel,
)
from app.infrastructure.database.sla_models import (  # noqa: E402, F401
    AuditLogModel,
    IncidentSLATrackingModel,
    NotificationModel,
    SLAPolicyModel,
)
