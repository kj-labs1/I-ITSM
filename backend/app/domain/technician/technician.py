"""
Technician domain entity — the core domain model for Member 3.

OOP Design Decisions:
- Encapsulation: Availability, skills, operational parameters, and workload are managed through
  controlled methods and private state backing. Direct state mutation is prevented.
- Aggregate Root: Technician acts as the aggregate root for TechnicianSkill child entities.
  External callers cannot mutate internal skill objects directly; all skill modifications
  flow through controlled aggregate methods.
- Composition: Technician HAS skills (list of TechnicianSkill).
- Domain Methods: Business logic lives in the entity, not in controllers.
- Integration: Uses the shared User UUID as identity (does not duplicate M1's User).
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.domain.technician.skill import TechnicianSkill
from app.shared.enums import AvailabilityStatus


class Technician:
    """
    Technician domain entity (Aggregate Root).

    Uses the shared User UUID from M1's identity module as its primary identity.
    Technician-specific attributes are maintained separately from user account data.

    OOP: Demonstrates strict encapsulation through private backing attributes,
    read-only property accessors, domain invariant validation, and detached clone
    protection for aggregate composition.
    """

    def __init__(
        self,
        user_id: UUID,
        _availability: AvailabilityStatus = AvailabilityStatus.AVAILABLE,
        _skills: list[TechnicianSkill] | None = None,
        experience_years: int = 0,
        max_capacity: int = 10,
        _active_incident_count: int = 0,
        id: UUID | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        """Initialize a technician entity and enforce domain invariants."""
        if experience_years < 0:
            raise ValueError("Experience years cannot be negative")
        if max_capacity < 1:
            raise ValueError("Max capacity must be at least 1")

        self.user_id = user_id
        self._availability = _availability
        self._skills: list[TechnicianSkill] = [s.clone() for s in _skills] if _skills else []
        self._experience_years = experience_years
        self._max_capacity = max_capacity
        self._active_incident_count = _active_incident_count
        self.id = id if id is not None else uuid4()
        now = datetime.now(UTC)
        self.created_at = created_at if created_at is not None else now
        self.updated_at = updated_at if updated_at is not None else now

    # --- Operational Parameters Management (Encapsulation - R1) ---

    @property
    def experience_years(self) -> int:
        """Years of professional experience (read-only property)."""
        return self._experience_years

    @property
    def max_capacity(self) -> int:
        """Maximum concurrent incident capacity (read-only property)."""
        return self._max_capacity

    def update_operational_parameters(
        self,
        experience_years: int | None = None,
        max_capacity: int | None = None,
    ) -> None:
        """
        Update technician operational parameters with domain invariant validation.

        Validates:
        - experience_years >= 0 (if supplied)
        - max_capacity >= 1 (if supplied)
        Updates updated_at on successful changes.
        """
        if experience_years is not None and experience_years < 0:
            raise ValueError("Experience years cannot be negative")
        if max_capacity is not None and max_capacity < 1:
            raise ValueError("Max capacity must be at least 1")

        changed = False
        if experience_years is not None:
            self._experience_years = experience_years
            changed = True
        if max_capacity is not None:
            self._max_capacity = max_capacity
            changed = True

        if changed:
            self.updated_at = datetime.now(UTC)

    # --- Availability Management (Encapsulation) ---

    @property
    def availability(self) -> AvailabilityStatus:
        """Current availability status of the technician."""
        return self._availability

    @property
    def is_available(self) -> bool:
        """Check if technician is available for assignment."""
        return self._availability == AvailabilityStatus.AVAILABLE

    def set_available(self) -> None:
        """Mark technician as available."""
        self._availability = AvailabilityStatus.AVAILABLE
        self.updated_at = datetime.now(UTC)

    def set_busy(self) -> None:
        """Mark technician as busy."""
        self._availability = AvailabilityStatus.BUSY
        self.updated_at = datetime.now(UTC)

    def set_offline(self) -> None:
        """Mark technician as offline."""
        self._availability = AvailabilityStatus.OFFLINE
        self.updated_at = datetime.now(UTC)

    def set_on_leave(self) -> None:
        """Mark technician as on leave."""
        self._availability = AvailabilityStatus.ON_LEAVE
        self.updated_at = datetime.now(UTC)

    # --- Skill Management (Composition & Aggregate Root - R2) ---

    @property
    def skills(self) -> list[TechnicianSkill]:
        """Return detached copies of skills to prevent external mutation of aggregate state."""
        return [s.clone() for s in self._skills]

    def add_skill(self, skill_name: str, proficiency_level: int = 3) -> TechnicianSkill:
        """Add a new skill. Raises ValueError if skill already exists."""
        if self.has_skill(skill_name):
            raise ValueError(f"Technician already has skill: {skill_name}")
        skill = TechnicianSkill(
            technician_id=self.id,
            skill_name=skill_name,
            _proficiency_level=proficiency_level,
        )
        self._skills.append(skill)
        self.updated_at = datetime.now(UTC)
        return skill.clone()

    def update_skill_proficiency(self, skill_name: str, proficiency_level: int) -> TechnicianSkill:
        """
        Update proficiency of an existing skill through the aggregate root.

        Validates proficiency bounds (1-5) and updates parent updated_at.
        Raises ValueError if skill is not possessed by technician.
        """
        for s in self._skills:
            if s.matches_skill(skill_name):
                s.update_proficiency(proficiency_level)
                self.updated_at = datetime.now(UTC)
                return s.clone()
        raise ValueError(f"Technician does not possess skill: {skill_name}")

    def remove_skill(self, skill_name: str) -> None:
        """Remove a skill by name."""
        initial_count = len(self._skills)
        self._skills = [s for s in self._skills if not s.matches_skill(skill_name)]
        if len(self._skills) < initial_count:
            self.updated_at = datetime.now(UTC)

    def has_skill(self, skill_name: str) -> bool:
        """Check if technician has a specific skill."""
        return any(s.matches_skill(skill_name) for s in self._skills)

    def get_skill(self, skill_name: str) -> TechnicianSkill | None:
        """Get a specific skill by name as a detached copy to prevent external mutation."""
        for s in self._skills:
            if s.matches_skill(skill_name):
                return s.clone()
        return None

    def get_skill_proficiency(self, skill_name: str) -> int:
        """Get proficiency level for a skill, 0 if not possessed."""
        for s in self._skills:
            if s.matches_skill(skill_name):
                return s.proficiency_level
        return 0

    # --- Workload Management (Encapsulation) ---

    @property
    def active_incident_count(self) -> int:
        """Current number of active incidents assigned to this technician."""
        return self._active_incident_count

    def update_active_incident_count(self, count: int) -> None:
        """Update active incident count derived from open incidents."""
        if count < 0:
            raise ValueError("Active incident count cannot be negative")
        self._active_incident_count = count

    @property
    def has_capacity(self) -> bool:
        """Check if technician can accept more incidents."""
        return self._active_incident_count < self.max_capacity

    @property
    def remaining_capacity(self) -> int:
        """Number of additional incidents this technician can handle."""
        return max(0, self.max_capacity - self._active_incident_count)

    # --- Eligibility Check (Domain Logic) ---

    def is_eligible_for(self, required_skill: str) -> bool:
        """
        Check if this technician is eligible for an incident requiring a specific skill.

        Eligibility requires:
        1. Technician is available
        2. Technician has the required skill
        3. Technician has capacity for more incidents
        """
        return self.is_available and self.has_skill(required_skill) and self.has_capacity

    def __repr__(self) -> str:
        return (
            f"Technician(id={self.id}, user_id={self.user_id}, "
            f"availability={self._availability.value}, "
            f"experience_years={self._experience_years}, "
            f"max_capacity={self._max_capacity})"
        )

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Technician):
            return self.id == other.id
        return False
