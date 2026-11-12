"""
Unit tests for Technician and TechnicianSkill domain entities.

OOP Verification:
- Encapsulation: Validates that state modifications occur via controlled domain methods.
- Invariants: Verifies bounds checking (proficiency 1-5, non-negative experience, capacity >= 1).
- Composition: Verifies that skills are managed as child domain objects.
"""

from uuid import uuid4

import pytest

from app.domain.technician.skill import TechnicianSkill
from app.domain.technician.technician import Technician
from app.shared.enums import AvailabilityStatus


class TestTechnicianSkillDomain:
    """Tests for TechnicianSkill domain entity."""

    def test_skill_creation_and_validation(self):
        """TC3: Skill proficiency must be between 1 and 5."""
        tech_id = uuid4()
        skill = TechnicianSkill(
            technician_id=tech_id,
            skill_name="NETWORK",
            _proficiency_level=4,
        )
        assert skill.technician_id == tech_id
        assert skill.skill_name == "NETWORK"
        assert skill.proficiency_level == 4

        # Invalid bounds
        with pytest.raises(ValueError, match="Proficiency level must be between 1 and 5"):
            TechnicianSkill(technician_id=tech_id, skill_name="DATABASE", _proficiency_level=0)

        with pytest.raises(ValueError, match="Proficiency level must be between 1 and 5"):
            TechnicianSkill(technician_id=tech_id, skill_name="DATABASE", _proficiency_level=6)

    def test_skill_proficiency_update(self):
        """Encapsulation: Proficiency update enforced via controlled method."""
        skill = TechnicianSkill(technician_id=uuid4(), skill_name="CLOUD", _proficiency_level=2)
        skill.update_proficiency(5)
        assert skill.proficiency_level == 5

        with pytest.raises(ValueError):
            skill.update_proficiency(10)

    def test_skill_matching(self):
        """Case-insensitive skill matching."""
        skill = TechnicianSkill(technician_id=uuid4(), skill_name="Python", _proficiency_level=3)
        assert skill.matches_skill("PYTHON")
        assert skill.matches_skill("python")
        assert not skill.matches_skill("JAVA")


class TestTechnicianDomain:
    """Tests for Technician domain entity."""

    def test_technician_creation_and_defaults(self):
        """TC1 & TC2: Technician creation and default attributes."""
        user_id = uuid4()
        tech = Technician(
            user_id=user_id,
            experience_years=5,
            max_capacity=8,
        )
        assert tech.user_id == user_id
        assert tech.is_available is True
        assert tech.availability == AvailabilityStatus.AVAILABLE
        assert tech.experience_years == 5
        assert tech.max_capacity == 8
        assert tech.active_incident_count == 0
        assert tech.remaining_capacity == 8
        assert tech.skills == []

    def test_technician_invalid_invariants(self):
        """Domain validation on constructor arguments."""
        with pytest.raises(ValueError, match="Experience years cannot be negative"):
            Technician(user_id=uuid4(), experience_years=-1)

        with pytest.raises(ValueError, match="Max capacity must be at least 1"):
            Technician(user_id=uuid4(), max_capacity=0)

    def test_availability_state_transitions(self):
        """TC4: Availability validation and controlled state transitions."""
        tech = Technician(user_id=uuid4())
        assert tech.is_available is True

        tech.set_busy()
        assert tech.availability == AvailabilityStatus.BUSY
        assert tech.is_available is False

        tech.set_offline()
        assert tech.availability == AvailabilityStatus.OFFLINE
        assert tech.is_available is False

        tech.set_on_leave()
        assert tech.availability == AvailabilityStatus.ON_LEAVE
        assert tech.is_available is False

        tech.set_available()
        assert tech.availability == AvailabilityStatus.AVAILABLE
        assert tech.is_available is True

    def test_skill_management_composition(self):
        """TC3: Adding, querying, and removing skills via domain methods."""
        tech = Technician(user_id=uuid4())
        tech.add_skill("NETWORK", 4)
        tech.add_skill("SECURITY", 5)

        assert tech.has_skill("NETWORK")
        assert tech.has_skill("network")
        assert tech.has_skill("SECURITY")
        assert not tech.has_skill("DATABASE")

        assert tech.get_skill_proficiency("NETWORK") == 4
        assert tech.get_skill_proficiency("SECURITY") == 5
        assert tech.get_skill_proficiency("DATABASE") == 0

        # Cannot add duplicate skill
        with pytest.raises(ValueError, match="already has skill"):
            tech.add_skill("NETWORK", 3)

        # Removing a skill
        tech.remove_skill("NETWORK")
        assert not tech.has_skill("NETWORK")

    def test_capacity_and_workload_encapsulation(self):
        """TC10: Workload and capacity boundary checking."""
        tech = Technician(user_id=uuid4(), max_capacity=3)
        assert tech.has_capacity is True
        assert tech.remaining_capacity == 3

        tech.update_active_incident_count(2)
        assert tech.active_incident_count == 2
        assert tech.has_capacity is True
        assert tech.remaining_capacity == 1

        tech.update_active_incident_count(3)
        assert tech.active_incident_count == 3
        assert tech.has_capacity is False
        assert tech.remaining_capacity == 0

        with pytest.raises(ValueError, match="Active incident count cannot be negative"):
            tech.update_active_incident_count(-1)

    def test_eligibility_compound_check(self):
        """Eligibility requires availability, skill match, and remaining capacity."""
        tech = Technician(user_id=uuid4(), max_capacity=2)
        tech.add_skill("NETWORK", 4)

        # Eligible
        assert tech.is_eligible_for("NETWORK") is True

        # Ineligible due to wrong skill
        assert tech.is_eligible_for("DATABASE") is False

        # Ineligible due to status
        tech.set_busy()
        assert tech.is_eligible_for("NETWORK") is False
        tech.set_available()

        # Ineligible due to capacity reached
        tech.update_active_incident_count(2)
        assert tech.is_eligible_for("NETWORK") is False
