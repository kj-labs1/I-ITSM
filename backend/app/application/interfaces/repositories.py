"""
Repository interfaces — Repository Pattern.

OOP Design:
- Repository Pattern decouples business and application logic from specific persistence
  mechanisms (SQLAlchemy, mock, in-memory).
- Interface Segregation & Dependency Inversion: High-level application services
  depend strictly on this abstract contract.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.technician.technician import Technician


class TechnicianRepository(ABC):
    """
    Abstract repository interface for Technician domain entities.

    Provides domain-level persistence methods without exposing ORM models
    or query execution details to application services.
    """

    @abstractmethod
    async def get_by_id(
        self,
        technician_id: UUID,
        for_update: bool = False,
    ) -> Technician | None:
        """Retrieve a technician domain entity by its profile ID."""
        ...

    @abstractmethod
    async def get_by_user_id(
        self,
        user_id: UUID,
        for_update: bool = False,
    ) -> Technician | None:
        """Retrieve a technician domain entity by its shared User UUID."""
        ...

    @abstractmethod
    async def list_all(self, skip: int = 0, limit: int = 100) -> list[Technician]:
        """List all technician profiles with pagination."""
        ...

    @abstractmethod
    async def list_available(self) -> list[Technician]:
        """Retrieve all technicians whose current status is AVAILABLE."""
        ...

    @abstractmethod
    async def save(self, technician: Technician) -> Technician:
        """Persist a new technician domain entity along with its skills."""
        ...

    @abstractmethod
    async def update(self, technician: Technician) -> Technician:
        """Update an existing technician domain entity and synchronise skills."""
        ...

    @abstractmethod
    async def delete(self, technician_id: UUID) -> bool:
        """Delete a technician profile and cascade associated skills."""
        ...

    @abstractmethod
    async def count(self) -> int:
        """Return the total number of registered technicians."""
        ...
