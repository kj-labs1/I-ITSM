"""
Shared enums for the I-ITSM domain model.

These enums are the single source of truth for categorical values used
across all modules. They match the team handbook definitions exactly.

OOP Design: Using ``str, Enum`` (StrEnum-compatible pattern) enables
JSON serialisation by default and allows direct comparison with string
literals while retaining type safety.
"""

from __future__ import annotations

from enum import Enum


class UserRole(str, Enum):
    """Roles that a user can hold within the system."""

    EMPLOYEE = "EMPLOYEE"
    TECHNICIAN = "TECHNICIAN"
    ADMIN = "ADMIN"


class Priority(str, Enum):
    """Incident priority levels (P1 = highest urgency)."""

    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"


class IncidentStatus(str, Enum):
    """Lifecycle states of an incident from creation to closure."""

    NEW = "NEW"
    CLASSIFIED = "CLASSIFIED"
    ASSIGNED = "ASSIGNED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    VERIFIED = "VERIFIED"
    CLOSED = "CLOSED"


class IncidentCategory(str, Enum):
    """Categories used for incident classification."""

    HARDWARE = "HARDWARE"
    SOFTWARE = "SOFTWARE"
    NETWORK = "NETWORK"
    DATABASE = "DATABASE"
    CLOUD = "CLOUD"
    SECURITY = "SECURITY"
    AUTHENTICATION = "AUTHENTICATION"
    APPLICATION = "APPLICATION"
    STORAGE = "STORAGE"


class AssignmentStrategyType(str, Enum):
    """Available strategies for the technician assignment engine."""

    SKILL_BASED = "SKILL_BASED"
    LEAST_LOADED = "LEAST_LOADED"


class AvailabilityStatus(str, Enum):
    """Current availability of a technician."""

    AVAILABLE = "AVAILABLE"
    BUSY = "BUSY"
    OFFLINE = "OFFLINE"
    ON_LEAVE = "ON_LEAVE"
