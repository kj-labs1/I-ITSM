"""
TechnicianSkill domain entity.

OOP Design: Demonstrates Encapsulation — skill proficiency is validated
within the domain object, not by external code. The proficiency level
is constrained to 1-5 and can only be modified through controlled methods.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass
class TechnicianSkill:
    """Represents a technician's skill with a proficiency level.

    Encapsulation: Proficiency is validated on creation and update.
    The skill_name is immutable after creation.
    """

    technician_id: UUID
    skill_name: str
    _proficiency_level: int = field(default=3)
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        """Validate invariants on construction."""
        self._validate_proficiency(self._proficiency_level)

    @staticmethod
    def _validate_proficiency(level: int) -> None:
        """Enforce proficiency score bounds (1-5)."""
        if not isinstance(level, int) or not 1 <= level <= 5:
            raise ValueError(f"Proficiency level must be between 1 and 5, got {level}")

    @property
    def proficiency_level(self) -> int:
        """Return the current proficiency level."""
        return self._proficiency_level

    def update_proficiency(self, new_level: int) -> None:
        """Update proficiency through a controlled method with validation."""
        self._validate_proficiency(new_level)
        self._proficiency_level = new_level
        self.updated_at = datetime.now(UTC)

    def matches_skill(self, required_skill: str) -> bool:
        """Check if this skill matches the required skill (case-insensitive)."""
        return self.skill_name.upper() == required_skill.upper()
