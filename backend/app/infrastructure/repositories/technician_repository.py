"""
SQLAlchemy implementation of TechnicianRepository.

OOP Design:
- Repository Pattern: Translates between SQLAlchemy ORM models and pure Python domain
  entities (`Technician`, `TechnicianSkill`).
- Encapsulates database query building and session handling behind the domain interface.
- Composition: Aggregates skills as child records within the technician aggregate root.
"""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.application.interfaces.repositories import TechnicianRepository
from app.domain.technician.skill import TechnicianSkill
from app.domain.technician.technician import Technician
from app.infrastructure.database.models import TechnicianModel, TechnicianSkillModel
from app.shared.enums import AvailabilityStatus

logger = logging.getLogger(__name__)


class SQLAlchemyTechnicianRepository(TechnicianRepository):
    """
    SQLAlchemy-backed repository managing persistence for Technician entities.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_domain(self, model: TechnicianModel) -> Technician:
        """Map a TechnicianModel ORM instance to a pure domain Technician entity."""
        skills = [
            TechnicianSkill(
                technician_id=model.id,
                skill_name=sm.skill_name,
                _proficiency_level=sm.proficiency_level,
                id=sm.id,
                created_at=sm.created_at,
                updated_at=sm.updated_at,
            )
            for sm in (model.skills or [])
        ]

        avail = model.availability
        if isinstance(avail, str):
            avail = AvailabilityStatus(avail)

        tech = Technician(
            user_id=model.user_id,
            _availability=avail,
            _skills=skills,
            experience_years=model.experience_years,
            max_capacity=model.max_capacity,
            _active_incident_count=0,
            id=model.id,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
        return tech

    async def get_by_id(self, technician_id: UUID) -> Technician | None:
        stmt = (
            select(TechnicianModel)
            .options(selectinload(TechnicianModel.skills))
            .where(TechnicianModel.id == technician_id)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def get_by_user_id(self, user_id: UUID) -> Technician | None:
        stmt = (
            select(TechnicianModel)
            .options(selectinload(TechnicianModel.skills))
            .where(TechnicianModel.user_id == user_id)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def list_all(self, skip: int = 0, limit: int = 100) -> list[Technician]:
        stmt = (
            select(TechnicianModel)
            .options(selectinload(TechnicianModel.skills))
            .order_by(TechnicianModel.created_at.asc())
            .offset(skip)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        models = result.scalars().unique().all()
        return [self._to_domain(m) for m in models]

    async def list_available(self) -> list[Technician]:
        stmt = (
            select(TechnicianModel)
            .options(selectinload(TechnicianModel.skills))
            .where(TechnicianModel.availability == AvailabilityStatus.AVAILABLE)
            .order_by(TechnicianModel.experience_years.desc())
        )
        result = await self._session.execute(stmt)
        models = result.scalars().unique().all()
        return [self._to_domain(m) for m in models]

    async def save(self, technician: Technician) -> Technician:
        model = TechnicianModel(
            id=technician.id,
            user_id=technician.user_id,
            availability=technician.availability,
            experience_years=technician.experience_years,
            max_capacity=technician.max_capacity,
            created_at=technician.created_at,
            updated_at=technician.updated_at,
        )
        for skill in technician.skills:
            model.skills.append(
                TechnicianSkillModel(
                    id=skill.id,
                    technician_id=model.id,
                    skill_name=skill.skill_name,
                    proficiency_level=skill.proficiency_level,
                    created_at=skill.created_at,
                    updated_at=skill.updated_at,
                )
            )

        self._session.add(model)
        await self._session.flush()
        # Reload with eager skills
        loaded = await self.get_by_id(model.id)
        return loaded if loaded is not None else self._to_domain(model)

    async def update(self, technician: Technician) -> Technician:
        stmt = (
            select(TechnicianModel)
            .options(selectinload(TechnicianModel.skills))
            .where(TechnicianModel.id == technician.id)
        )
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()
        if not existing:
            raise ValueError(f"Technician with id {technician.id} not found in database.")

        existing.availability = technician.availability
        existing.experience_years = technician.experience_years
        existing.max_capacity = technician.max_capacity
        existing.updated_at = technician.updated_at

        # Synchronize child skill collection
        existing_skills_by_name = {s.skill_name.upper(): s for s in existing.skills}
        domain_skills_by_name = {s.skill_name.upper(): s for s in technician.skills}

        # Remove skills not in domain entity
        for name, sm in list(existing_skills_by_name.items()):
            if name not in domain_skills_by_name:
                existing.skills.remove(sm)

        # Add or update skills from domain entity
        for name, ds in domain_skills_by_name.items():
            if name in existing_skills_by_name:
                existing_skills_by_name[name].proficiency_level = ds.proficiency_level
                existing_skills_by_name[name].updated_at = ds.updated_at
            else:
                existing.skills.append(
                    TechnicianSkillModel(
                        id=ds.id,
                        technician_id=existing.id,
                        skill_name=ds.skill_name,
                        proficiency_level=ds.proficiency_level,
                        created_at=ds.created_at,
                        updated_at=ds.updated_at,
                    )
                )

        await self._session.flush()
        loaded = await self.get_by_id(existing.id)
        return loaded if loaded is not None else self._to_domain(existing)

    async def delete(self, technician_id: UUID) -> bool:
        stmt = select(TechnicianModel).where(TechnicianModel.id == technician_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is not None:
            await self._session.delete(model)
            await self._session.flush()
            return True
        return False

    async def count(self) -> int:
        stmt = select(func.count()).select_from(TechnicianModel)
        result = await self._session.execute(stmt)
        return int(result.scalar_one() or 0)
