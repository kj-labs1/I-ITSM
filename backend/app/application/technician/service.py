"""
Technician Profile Application Service.

OOP Design:
- Composition: Aggregates `TechnicianRepository`, `IncidentServiceBoundary`, and `EventPublisher`.
- Single Responsibility Principle: Coordinates technician profile lifecycles, skills,
  and availability transitions without holding persistence implementation details.
- Workload Derivation: Enforces that active incident count is always derived from the
  authoritative Incident service (Member 2), preventing competing state counters.
"""

from __future__ import annotations

import logging
from uuid import UUID

from app.application.interfaces.event_publisher import EventPublisher
from app.application.interfaces.incident_service import IncidentServiceBoundary
from app.application.interfaces.repositories import TechnicianRepository
from app.core.exceptions import (
    BusinessRuleError,
    TechnicianNotFoundError,
)
from app.domain.assignment.events import TechnicianAvailabilityChangedEvent
from app.domain.technician.skill import TechnicianSkill
from app.domain.technician.technician import Technician
from app.shared.enums import AvailabilityStatus

logger = logging.getLogger(__name__)


class TechnicianProfileService:
    """
    Application service managing technician profiles, skills, and availability.
    """

    def __init__(
        self,
        repository: TechnicianRepository,
        incident_service: IncidentServiceBoundary,
        event_publisher: EventPublisher,
    ) -> None:
        self.repository = repository
        self.incident_service = incident_service
        self.event_publisher = event_publisher

    async def _attach_workload(self, tech: Technician) -> None:
        """Derive and set the technician's active workload from the incident service."""
        count = await self.incident_service.get_active_incident_count(tech.user_id)
        tech.update_active_incident_count(count)

    async def create_technician(
        self,
        user_id: UUID,
        experience_years: int = 0,
        max_capacity: int = 10,
        initial_skills: list[tuple[str, int]] | None = None,
    ) -> Technician:
        """
        Register a new technician operational profile associated with an M1 User UUID.

        Validates:
        - A technician profile for this user_id does not already exist.
        - Experience years and max capacity meet domain constraints.
        """
        existing = await self.repository.get_by_user_id(user_id)
        if existing is not None:
            raise BusinessRuleError(
                f"A technician profile already exists for user_id {user_id}.",
                error_code="TECHNICIAN_ALREADY_EXISTS",
            )

        tech = Technician(
            user_id=user_id,
            experience_years=experience_years,
            max_capacity=max_capacity,
        )

        if initial_skills:
            for skill_name, prof in initial_skills:
                tech.add_skill(skill_name, prof)

        saved = await self.repository.save(tech)
        await self._attach_workload(saved)
        logger.info("Created technician profile %s for user %s", saved.id, user_id)
        return saved

    async def get_technician(self, technician_id: UUID) -> Technician:
        """Retrieve a technician profile by ID, with active workload attached."""
        tech = await self.repository.get_by_id(technician_id)
        if tech is None:
            raise TechnicianNotFoundError(resource_id=str(technician_id))
        await self._attach_workload(tech)
        return tech

    async def get_technician_by_user_id(self, user_id: UUID) -> Technician:
        """Retrieve a technician profile by user_id, with active workload attached."""
        tech = await self.repository.get_by_user_id(user_id)
        if tech is None:
            raise TechnicianNotFoundError(resource_id=str(user_id))
        await self._attach_workload(tech)
        return tech

    async def list_technicians(self, skip: int = 0, limit: int = 100) -> list[Technician]:
        """List all technicians with populated active incident counts."""
        techs = await self.repository.list_all(skip=skip, limit=limit)
        for t in techs:
            await self._attach_workload(t)
        return techs

    async def list_available_technicians(self) -> list[Technician]:
        """Retrieve all currently available technicians with workload attached."""
        techs = await self.repository.list_available()
        for t in techs:
            await self._attach_workload(t)
        return techs

    async def update_technician(
        self,
        technician_id: UUID,
        experience_years: int | None = None,
        max_capacity: int | None = None,
    ) -> Technician:
        """
        Update technician operational parameters.

        Validates:
        - experience_years is non-negative (if supplied).
        - max_capacity is at least 1 (if supplied).
        Updates only the fields that are supplied, leaving the other unchanged.
        """
        tech = await self.get_technician(technician_id)

        if experience_years is not None:
            if experience_years < 0:
                raise BusinessRuleError(
                    "Experience years cannot be negative.",
                    error_code="INVALID_EXPERIENCE_YEARS",
                )
            tech.experience_years = experience_years

        if max_capacity is not None:
            if max_capacity < 1:
                raise BusinessRuleError(
                    "Max capacity must be at least 1.",
                    error_code="INVALID_MAX_CAPACITY",
                )
            tech.max_capacity = max_capacity

        updated = await self.repository.update(tech)
        await self._attach_workload(updated)
        return updated

    async def update_availability(
        self,
        technician_id: UUID,
        new_status: AvailabilityStatus,
    ) -> Technician:
        """
        Update technician availability and publish availability change event.
        """
        tech = await self.get_technician(technician_id)
        old_status = tech.availability.value

        if new_status == AvailabilityStatus.AVAILABLE:
            tech.set_available()
        elif new_status == AvailabilityStatus.BUSY:
            tech.set_busy()
        elif new_status == AvailabilityStatus.OFFLINE:
            tech.set_offline()
        elif new_status == AvailabilityStatus.ON_LEAVE:
            tech.set_on_leave()

        updated = await self.repository.update(tech)
        await self._attach_workload(updated)

        await self.event_publisher.publish(
            TechnicianAvailabilityChangedEvent(
                technician_id=updated.id,
                previous_status=old_status,
                new_status=new_status.value,
            )
        )
        logger.info(
            "Updated technician %s availability: %s -> %s",
            technician_id,
            old_status,
            new_status.value,
        )
        return updated

    async def add_or_update_skill(
        self,
        technician_id: UUID,
        skill_name: str,
        proficiency_level: int,
    ) -> Technician:
        """Add a new skill or update proficiency of an existing skill."""
        tech = await self.get_technician(technician_id)

        existing_skill = tech.get_skill(skill_name)
        if existing_skill is not None:
            existing_skill.update_proficiency(proficiency_level)
        else:
            tech.add_skill(skill_name, proficiency_level)

        updated = await self.repository.update(tech)
        await self._attach_workload(updated)
        return updated

    async def remove_skill(
        self,
        technician_id: UUID,
        skill_name: str,
    ) -> Technician:
        """Remove a skill from the technician's profile."""
        tech = await self.get_technician(technician_id)
        tech.remove_skill(skill_name)
        updated = await self.repository.update(tech)
        await self._attach_workload(updated)
        return updated

    async def get_technician_skills(self, technician_id: UUID) -> list[TechnicianSkill]:
        """Retrieve skills for a specific technician."""
        tech = await self.get_technician(technician_id)
        return tech.skills
