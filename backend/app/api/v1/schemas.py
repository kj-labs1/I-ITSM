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

from app.shared.enums import (
    AvailabilityStatus,
    IncidentCategory,
    IncidentStatus,
    Priority,
)


class BaseDTO(BaseModel):
    """Base class for all API DTOs configuring camelCase serialization."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )

# ============================================================
# MEMBER 2 — INCIDENT MANAGEMENT SCHEMAS
# ============================================================


class IncidentCreateRequest(BaseDTO):
    """Request DTO for creating a new incident."""

    service_id: UUID

    category: IncidentCategory

    required_skill: str = Field(
        min_length=1,
        max_length=100,
    )

    description: str = Field(
        min_length=1,
        max_length=5000,
    )

    impact: int = Field(
        ge=1,
        le=5,
    )

    urgency: int = Field(
        ge=1,
        le=5,
    )

    # Temporary integration inputs until M1's service catalogue
    # provides business criticality and required skill server-side.
    business_criticality: int = Field(
        ge=1,
        le=5,
    )


class IncidentUpdateRequest(BaseDTO):
    """Request DTO for updating permitted incident fields."""

    description: str | None = Field(
        default=None,
        min_length=1,
        max_length=5000,
    )

    impact: int | None = Field(
        default=None,
        ge=1,
        le=5,
    )

    urgency: int | None = Field(
        default=None,
        ge=1,
        le=5,
    )


class IncidentStatusUpdateRequest(BaseDTO):
    """Request DTO for changing incident lifecycle status."""

    status: IncidentStatus

    resolution_details: str | None = Field(
        default=None,
        max_length=5000,
    )


class IncidentCommentCreateRequest(BaseDTO):
    """Request DTO for adding an incident comment."""

    content: str = Field(
        min_length=1,
        max_length=5000,
    )


class IncidentCommentResponse(BaseDTO):
    """Response DTO for an incident comment."""

    id: UUID
    incident_id: UUID
    author_id: UUID
    content: str
    created_at: datetime


class IncidentResponse(BaseDTO):
    """Standard incident response DTO."""

    id: UUID
    incident_code: str

    reporter_id: UUID
    service_id: UUID

    category: IncidentCategory
    required_skill: str
    description: str

    impact: int
    urgency: int
    business_criticality: int

    priority: Priority
    status: IncidentStatus

    assigned_technician_id: UUID | None
    resolution_details: str | None

    created_at: datetime
    updated_at: datetime


class IncidentDetailsResponse(IncidentResponse):
    """Detailed incident response including comments."""

    comments: list[IncidentCommentResponse] = Field(
        default_factory=list
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

class PotentialDuplicateResponse(BaseDTO):
    """Read representation of a potential duplicate incident."""

    incident_id: UUID
    incident_code: str
    category: IncidentCategory
    priority: Priority
    status: IncidentStatus
    created_at: datetime
    similarity_score: float = Field(ge=0.0, le=1.0)
    explanation: str
