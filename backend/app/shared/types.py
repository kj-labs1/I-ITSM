"""
Shared type aliases for domain identifiers.

Using ``TypeAlias`` makes function signatures self-documenting — a parameter
typed ``TechnicianId`` is immediately clear without inspecting the underlying
type, while remaining fully compatible with plain ``UUID`` at runtime.
"""

from __future__ import annotations

from typing import TypeAlias
from uuid import UUID

UserId: TypeAlias = UUID
IncidentId: TypeAlias = UUID
TechnicianId: TypeAlias = UUID
ServiceId: TypeAlias = UUID
