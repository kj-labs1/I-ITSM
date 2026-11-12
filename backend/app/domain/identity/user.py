"""
User identity integration boundary.

OOP Design: This module defines the contract that Member 3 (Technician)
depends on from Member 1 (Identity). The UserIdentity class is a
value object representing the minimal user information needed by the
technician domain. It does NOT replicate M1's User entity — it is
a read-only projection consumed across module boundaries.

Design Pattern: Interface Segregation Principle — M3 depends only on
the subset of user data it needs, not the full User entity.
"""

from dataclasses import dataclass
from uuid import UUID

from app.shared.enums import UserRole


@dataclass(frozen=True)
class UserIdentity:
    """Read-only projection of a user from M1's identity module."""

    id: UUID
    username: str
    email: str
    full_name: str
    role: UserRole
    is_active: bool = True
