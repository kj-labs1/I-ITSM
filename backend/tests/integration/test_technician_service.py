"""
Integration tests for TechnicianProfileService — Task 1 & Task 2 corrections.

Verifies:
- Skill technician_id references the technician profile UUID (Technician.id),
  not the shared user UUID (Technician.user_id).
- Adding a skill via the service and retrieving it preserves correct IDs.
- update_technician service method correctly updates experience_years and max_capacity.
- Partial updates do not reset the untouched field.
- Invalid values are rejected with BusinessRuleError.
"""

from uuid import uuid4

import pytest

from app.application.technician.service import TechnicianProfileService
from app.core.exceptions import BusinessRuleError, TechnicianNotFoundError
from app.domain.technician.technician import Technician


class TestSkillTechnicianIdConsistency:
    """Task 1: Verify skill.technician_id equals the technician profile id."""

    @pytest.mark.asyncio
    async def test_add_skill_sets_profile_id_not_user_id(
        self,
        tech_service: TechnicianProfileService,
    ):
        """Skill.technician_id must equal Technician.id (profile UUID), not Technician.user_id."""
        user_id = uuid4()
        tech = await tech_service.create_technician(
            user_id=user_id,
            experience_years=3,
            max_capacity=5,
            initial_skills=[("NETWORK", 4)],
        )

        # Technician.id and Technician.user_id are distinct
        assert tech.id != tech.user_id

        # Every skill must reference the profile id
        for skill in tech.skills:
            assert skill.technician_id == tech.id
            assert skill.technician_id != tech.user_id

    @pytest.mark.asyncio
    async def test_skill_id_persists_through_save_and_reload(
        self,
        tech_service: TechnicianProfileService,
    ):
        """After save/reload, skill.technician_id still equals the technician profile id."""
        user_id = uuid4()
        created = await tech_service.create_technician(
            user_id=user_id,
            experience_years=2,
        )
        # Add skill via service (triggers save + reload)
        updated = await tech_service.add_or_update_skill(created.id, "DATABASE", 5)
        reloaded = await tech_service.get_technician(updated.id)

        assert len(reloaded.skills) == 1
        assert reloaded.skills[0].technician_id == reloaded.id
        assert reloaded.skills[0].technician_id != reloaded.user_id
        assert reloaded.skills[0].skill_name == "DATABASE"
        assert reloaded.skills[0].proficiency_level == 5

    @pytest.mark.asyncio
    async def test_domain_add_skill_uses_profile_id(self):
        """Pure domain: Technician.add_skill() sets technician_id to self.id."""
        tech = Technician(user_id=uuid4(), experience_years=1, max_capacity=5)
        skill = tech.add_skill("SECURITY", 3)
        assert skill.technician_id == tech.id
        assert skill.technician_id != tech.user_id

    @pytest.mark.asyncio
    async def test_multiple_skills_all_reference_profile_id(
        self,
        tech_service: TechnicianProfileService,
    ):
        """Multiple skills on one technician all carry the same profile UUID."""
        tech = await tech_service.create_technician(
            user_id=uuid4(),
            initial_skills=[("NETWORK", 4), ("CLOUD", 3), ("DATABASE", 5)],
        )
        assert len(tech.skills) == 3
        for skill in tech.skills:
            assert skill.technician_id == tech.id


class TestUpdateTechnicianService:
    """Task 2: Verify the public update_technician service method."""

    @pytest.mark.asyncio
    async def test_update_experience_years(
        self,
        tech_service: TechnicianProfileService,
    ):
        """Updating experience_years succeeds and persists correctly."""
        tech = await tech_service.create_technician(
            user_id=uuid4(), experience_years=2, max_capacity=8,
        )
        updated = await tech_service.update_technician(
            tech.id, experience_years=7,
        )
        assert updated.experience_years == 7
        assert updated.max_capacity == 8  # Unchanged

    @pytest.mark.asyncio
    async def test_update_max_capacity(
        self,
        tech_service: TechnicianProfileService,
    ):
        """Updating max_capacity succeeds and persists correctly."""
        tech = await tech_service.create_technician(
            user_id=uuid4(), experience_years=3, max_capacity=5,
        )
        updated = await tech_service.update_technician(
            tech.id, max_capacity=12,
        )
        assert updated.max_capacity == 12
        assert updated.experience_years == 3  # Unchanged

    @pytest.mark.asyncio
    async def test_update_both_fields(
        self,
        tech_service: TechnicianProfileService,
    ):
        """Updating both experience_years and max_capacity in one call."""
        tech = await tech_service.create_technician(
            user_id=uuid4(), experience_years=1, max_capacity=4,
        )
        updated = await tech_service.update_technician(
            tech.id, experience_years=10, max_capacity=20,
        )
        assert updated.experience_years == 10
        assert updated.max_capacity == 20

    @pytest.mark.asyncio
    async def test_update_no_fields_is_noop(
        self,
        tech_service: TechnicianProfileService,
    ):
        """Supplying neither field leaves the technician unchanged."""
        tech = await tech_service.create_technician(
            user_id=uuid4(), experience_years=5, max_capacity=10,
        )
        updated = await tech_service.update_technician(tech.id)
        assert updated.experience_years == 5
        assert updated.max_capacity == 10

    @pytest.mark.asyncio
    async def test_partial_update_does_not_reset_other_field(
        self,
        tech_service: TechnicianProfileService,
    ):
        """Updating only experience_years must NOT reset max_capacity, and vice versa."""
        tech = await tech_service.create_technician(
            user_id=uuid4(), experience_years=4, max_capacity=6,
        )
        # Update only experience_years
        after_exp = await tech_service.update_technician(
            tech.id, experience_years=9,
        )
        assert after_exp.experience_years == 9
        assert after_exp.max_capacity == 6

        # Update only max_capacity
        after_cap = await tech_service.update_technician(
            tech.id, max_capacity=15,
        )
        assert after_cap.max_capacity == 15
        assert after_cap.experience_years == 9  # Preserved from previous update

    @pytest.mark.asyncio
    async def test_reject_negative_experience_years(
        self,
        tech_service: TechnicianProfileService,
    ):
        """Negative experience_years is rejected with BusinessRuleError."""
        tech = await tech_service.create_technician(
            user_id=uuid4(), experience_years=3,
        )
        with pytest.raises(BusinessRuleError, match="Experience years cannot be negative"):
            await tech_service.update_technician(tech.id, experience_years=-1)

    @pytest.mark.asyncio
    async def test_reject_zero_max_capacity(
        self,
        tech_service: TechnicianProfileService,
    ):
        """max_capacity of 0 is rejected with BusinessRuleError."""
        tech = await tech_service.create_technician(
            user_id=uuid4(), max_capacity=5,
        )
        with pytest.raises(BusinessRuleError, match="Max capacity must be at least 1"):
            await tech_service.update_technician(tech.id, max_capacity=0)

    @pytest.mark.asyncio
    async def test_reject_negative_max_capacity(
        self,
        tech_service: TechnicianProfileService,
    ):
        """Negative max_capacity is rejected with BusinessRuleError."""
        tech = await tech_service.create_technician(
            user_id=uuid4(), max_capacity=5,
        )
        with pytest.raises(BusinessRuleError, match="Max capacity must be at least 1"):
            await tech_service.update_technician(tech.id, max_capacity=-3)

    @pytest.mark.asyncio
    async def test_update_nonexistent_technician_raises(
        self,
        tech_service: TechnicianProfileService,
    ):
        """Updating a non-existent technician raises TechnicianNotFoundError."""
        with pytest.raises(TechnicianNotFoundError):
            await tech_service.update_technician(uuid4(), experience_years=5)

    @pytest.mark.asyncio
    async def test_update_preserves_skills(
        self,
        tech_service: TechnicianProfileService,
    ):
        """Updating operational parameters does not affect existing skills."""
        tech = await tech_service.create_technician(
            user_id=uuid4(),
            experience_years=2,
            max_capacity=5,
            initial_skills=[("NETWORK", 4), ("DATABASE", 3)],
        )
        updated = await tech_service.update_technician(
            tech.id, experience_years=8,
        )
        assert len(updated.skills) == 2
        skill_names = {s.skill_name for s in updated.skills}
        assert skill_names == {"NETWORK", "DATABASE"}

    @pytest.mark.asyncio
    async def test_add_or_update_skill_proficiency_persistence(
        self,
        tech_service: TechnicianProfileService,
    ):
        """Updating existing skill proficiency via service persists through database reload."""
        tech = await tech_service.create_technician(
            user_id=uuid4(),
            initial_skills=[("NETWORK", 2)],
        )
        assert tech.skills[0].proficiency_level == 2

        # Update proficiency to 5
        updated = await tech_service.add_or_update_skill(tech.id, "NETWORK", 5)
        assert updated.get_skill_proficiency("NETWORK") == 5

        # Reload from database to verify persistence
        reloaded = await tech_service.get_technician(tech.id)
        assert reloaded.get_skill_proficiency("NETWORK") == 5
        assert len(reloaded.skills) == 1

    @pytest.mark.asyncio
    async def test_add_or_update_skill_rejects_invalid_proficiency(
        self,
        tech_service: TechnicianProfileService,
    ):
        """Invalid proficiency levels are rejected with BusinessRuleError."""
        tech = await tech_service.create_technician(user_id=uuid4())

        with pytest.raises(BusinessRuleError, match="Proficiency level must be between 1 and 5"):
            await tech_service.add_or_update_skill(tech.id, "NETWORK", 0)

        with pytest.raises(BusinessRuleError, match="Proficiency level must be between 1 and 5"):
            await tech_service.add_or_update_skill(tech.id, "NETWORK", 6)
