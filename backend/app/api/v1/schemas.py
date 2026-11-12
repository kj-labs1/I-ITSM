"""
Pydantic v2 DTO schemas for API request and response serialization.

Conventions enforced:
- JSON naming: camelCase field names (via Pydantic alias_generator).
- Identifiers: UUID v4.
- Timestamps: ISO-8601 in UTC.
- Enums: Exact shared string representations matching the team handbook.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from app.shared.enums import AvailabilityStatus


class BaseDTO(BaseModel):
    """Base class for all API DTOs configuring camelCase serialization."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


# ── Technician Skill Schemas ──────────────────────────────────────────────────


class SkillCreateRequest(BaseDTO):
    """Payload to create or add a skill to a technician profile."""

    skill_name: str = Field(min_length=1, max_length=100, examples=["NETWORK"])
    proficiency_level: int = Field(default=3, ge=1, le=5, examples=[4])


class SkillResponse(BaseDTO):
    """Read representation of an acquired technician skill."""

    id: UUID
    technician_id: UUID
    skill_name: str
    proficiency_level: int
    created_at: datetime
    updated_at: datetime


# ── Technician Profile Schemas ────────────────────────────────────────────────


class TechnicianCreateRequest(BaseDTO):
    """Payload to create an operational technician profile."""

    user_id: UUID = Field(
        description="Shared User UUID from M1 Identity table",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    experience_years: int = Field(default=0, ge=0, description="Proposed field")
    max_capacity: int = Field(default=10, ge=1, description="Proposed field")
    skills: list[SkillCreateRequest] = Field(default_factory=list)


class TechnicianUpdateRequest(BaseDTO):
    """Payload to update technician operational parameters."""

    experience_years: int | None = Field(default=None, ge=0)
    max_capacity: int | None = Field(default=None, ge=1)


class AvailabilityUpdateRequest(BaseDTO):
    """Payload to update a technician's availability status."""

    availability: AvailabilityStatus = Field(examples=[AvailabilityStatus.AVAILABLE])


class TechnicianResponse(BaseDTO):
    """Read representation of a technician profile with computed workload."""

    id: UUID
    user_id: UUID
    availability: AvailabilityStatus
    experience_years: int
    max_capacity: int
    active_incident_count: int
    remaining_capacity: int
    skills: list[SkillResponse]
    created_at: datetime
    updated_at: datetime


# ── Recommendation Schemas ───────────────────────────────────────────────────


class RecommendationItemResponse(BaseDTO):
    """Ranked technician candidate with scoring rationale."""

    technician_id: UUID
    technician_user_id: UUID
    score: float
    rank: int
    explanation: str
    strategy_used: str
    skill_match: bool = True
    is_llm_enhanced: bool = False


class RecommendationResponse(BaseDTO):
    """Full recommendation query result."""

    incident_id: UUID
    strategy_used: str
    total_candidates: int
    eligible_candidates: int
    is_llm_enhanced: bool
    evaluation_time_ms: float
    recommendations: list[RecommendationItemResponse]


# ── Assignment Schemas ────────────────────────────────────────────────────────


class AssignTechnicianRequest(BaseDTO):
    """Payload to request incident assignment."""

    technician_id: UUID = Field(
        description="ID of the selected technician profile or user_id",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    strategy_used: str = Field(
        default="MANUAL",
        examples=["SKILL_BASED", "LEAST_LOADED", "MANUAL"],
    )
    reason: str = Field(
        default="",
        description="Optional administrator reason or AI justification string",
    )


class AssignTechnicianResponse(BaseDTO):
    """Response confirming incident assignment execution."""

    incident_id: UUID
    incident_code: str
    technician_id: UUID
    technician_user_id: UUID
    status: str
    strategy_used: str
    assigned_by: UUID
