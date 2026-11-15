"""
Technician domain entity — the core domain model for Member 3.

OOP Design Decisions:
- Encapsulation: Availability, skills, and workload are managed through
  controlled methods. Direct state mutation is prevented.
- Composition: Technician HAS skills (list of TechnicianSkill).
- Domain Methods: Business logic lives in the entity, not in controllers.
- Integration: Uses the shared User UUID as identity (does not duplicate M1's User).

Proposed Fields (require team approval):
- experience_years: Used for ranking in strategies and tie-breaking
- max_capacity: Maximum concurrent incidents (default 10)
These are justified by the assignment algorithm requirements but are not
explicitly established in the handbook.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.domain.technician.skill import TechnicianSkill
from app.shared.enums import AvailabilityStatus


@dataclass
class Technician:
    """
    Technician domain entity.

    Uses the shared User UUID from M1's identity module as its primary identity.
    Technician-specific attributes are maintained separately from user account data.

    OOP: Demonstrates encapsulation through controlled state modification methods,
    composition through the skills collection, and domain-driven validation.
    """

    user_id: UUID
    _availability: AvailabilityStatus = field(default=AvailabilityStatus.AVAILABLE)
    _skills: list[TechnicianSkill] = field(default_factory=list)
    experience_years: int = 0  # PROPOSED — requires team approval
    max_capacity: int = 10  # PROPOSED — requires team approval
    _active_incident_count: int = 0
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        """Validate invariants on construction."""
        if self.experience_years < 0:
            raise ValueError("Experience years cannot be negative")
        if self.max_capacity < 1:
            raise ValueError("Max capacity must be at least 1")

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

    # --- Skill Management (Composition) ---

    @property
    def skills(self) -> list[TechnicianSkill]:
        """Return a copy of skills to prevent external mutation."""
        return list(self._skills)

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
        return skill

    def remove_skill(self, skill_name: str) -> None:
        """Remove a skill by name."""
        self._skills = [s for s in self._skills if not s.matches_skill(skill_name)]
        self.updated_at = datetime.now(UTC)

    def has_skill(self, skill_name: str) -> bool:
        """Check if technician has a specific skill."""
        return any(s.matches_skill(skill_name) for s in self._skills)

    def get_skill(self, skill_name: str) -> TechnicianSkill | None:
        """Get a specific skill by name."""
        for s in self._skills:
            if s.matches_skill(skill_name):
                return s
        return None

    def get_skill_proficiency(self, skill_name: str) -> int:
        """Get proficiency level for a skill, 0 if not possessed."""
        skill = self.get_skill(skill_name)
        return skill.proficiency_level if skill else 0

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
