"""
Technician Management & Recommendation API Endpoints.

Ownership: Module M3 (Technician & Assignment Engine).
Agreed routes:
- GET   /api/v1/technicians
- POST  /api/v1/technicians
- GET   /api/v1/technicians/recommendations?incidentId={id}&strategy={strategy}&useLlm={bool}
- GET   /api/v1/technicians/{technician_id}
- PATCH /api/v1/technicians/{technician_id}
- PATCH /api/v1/technicians/{technician_id}/availability
- GET   /api/v1/technicians/{technician_id}/skills
- POST  /api/v1/technicians/{technician_id}/skills
- DELETE /api/v1/technicians/{technician_id}/skills/{skill_name}
"""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import (
    get_recommendation_service,
    get_technician_service,
)
from app.api.v1.schemas import (
    AvailabilityUpdateRequest,
    RecommendationItemResponse,
    RecommendationResponse,
    SkillCreateRequest,
    SkillResponse,
    TechnicianCreateRequest,
    TechnicianResponse,
    TechnicianUpdateRequest,
)
from app.application.assignment.service import (
    SmartTechnicianRecommendationService,
)
from app.application.technician.service import TechnicianProfileService
from app.domain.technician.technician import Technician
from app.shared.enums import AssignmentStrategyType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/technicians", tags=["Technicians"])


def _to_technician_response(tech: Technician) -> TechnicianResponse:
    """Helper converting domain Technician entity to Pydantic TechnicianResponse."""
    skills_response = [
        SkillResponse(
            id=s.id,
            technician_id=s.technician_id,
            skill_name=s.skill_name,
            proficiency_level=s.proficiency_level,
            created_at=s.created_at,
            updated_at=s.updated_at,
        )
        for s in tech.skills
    ]
    return TechnicianResponse(
        id=tech.id,
        user_id=tech.user_id,
        availability=tech.availability,
        experience_years=tech.experience_years,
        max_capacity=tech.max_capacity,
        active_incident_count=tech.active_incident_count,
        remaining_capacity=tech.remaining_capacity,
        skills=skills_response,
        created_at=tech.created_at,
        updated_at=tech.updated_at,
    )


# ── Recommendations Endpoint (Must be declared before {technician_id}) ───────


@router.get(
    "/recommendations",
    response_model=RecommendationResponse,
    summary="Get smart technician recommendations for an incident",
    description=(
        "Evaluates the technician pool using deterministic strategies "
        "(SKILL_BASED, LEAST_LOADED) optionally augmented by LLM reasoning."
    ),
)
async def get_recommendations(
    incident_id: UUID = Query(..., alias="incidentId", description="Incident UUID to evaluate"),
    strategy: AssignmentStrategyType = Query(
        default=AssignmentStrategyType.SKILL_BASED,
        description="Assignment strategy to use for ranking",
    ),
    use_llm: bool = Query(
        default=False,
        alias="useLlm",
        description="Whether to augment rankings with LLM reasoning",
    ),
    rec_service: SmartTechnicianRecommendationService = Depends(get_recommendation_service),
) -> RecommendationResponse:
    """Generate explainable, ranked technician recommendations."""
    result = await rec_service.get_recommendations(
        incident_id=incident_id,
        strategy_type=strategy,
        use_llm=use_llm,
    )

    recs_out = [
        RecommendationItemResponse(
            technician_id=r.technician_id,
            technician_user_id=r.technician_user_id,
            score=r.score,
            rank=r.rank,
            explanation=r.explanation,
            strategy_used=r.strategy_used,
            skill_match=r.skill_match,
            is_llm_enhanced=r.is_llm_enhanced,
        )
        for r in result.recommendations
    ]

    return RecommendationResponse(
        incident_id=incident_id,
        strategy_used=result.strategy_used,
        total_candidates=result.total_candidates,
        eligible_candidates=result.eligible_candidates,
        is_llm_enhanced=result.is_llm_enhanced,
        evaluation_time_ms=result.evaluation_time_ms,
        recommendations=recs_out,
    )


# ── Technician Profile CRUD Endpoints ─────────────────────────────────────────


@router.get(
    "",
    response_model=list[TechnicianResponse],
    summary="List all technicians",
    description="Retrieve paginated list of technicians with active workloads.",
)
async def list_technicians(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    service: TechnicianProfileService = Depends(get_technician_service),
) -> list[TechnicianResponse]:
    techs = await service.list_technicians(skip=skip, limit=limit)
    return [_to_technician_response(t) for t in techs]


@router.post(
    "",
    response_model=TechnicianResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create technician profile",
    description="Initializes a technician operational profile linked to a shared User UUID.",
)
async def create_technician(
    payload: TechnicianCreateRequest,
    service: TechnicianProfileService = Depends(get_technician_service),
) -> TechnicianResponse:
    skills_tuples = [(s.skill_name, s.proficiency_level) for s in payload.skills]
    tech = await service.create_technician(
        user_id=payload.user_id,
        experience_years=payload.experience_years,
        max_capacity=payload.max_capacity,
        initial_skills=skills_tuples,
    )
    return _to_technician_response(tech)


@router.get(
    "/{technician_id}",
    response_model=TechnicianResponse,
    summary="Get technician profile by ID",
)
async def get_technician(
    technician_id: UUID,
    service: TechnicianProfileService = Depends(get_technician_service),
) -> TechnicianResponse:
    tech = await service.get_technician(technician_id)
    return _to_technician_response(tech)


@router.patch(
    "/{technician_id}",
    response_model=TechnicianResponse,
    summary="Update technician operational parameters",
)
async def update_technician(
    technician_id: UUID,
    payload: TechnicianUpdateRequest,
    service: TechnicianProfileService = Depends(get_technician_service),
) -> TechnicianResponse:
    tech = await service.get_technician(technician_id)
    if payload.experience_years is not None:
        tech.experience_years = payload.experience_years
    if payload.max_capacity is not None:
        tech.max_capacity = payload.max_capacity

    updated = await service.repository.update(tech)
    await service._attach_workload(updated)
    return _to_technician_response(updated)


@router.patch(
    "/{technician_id}/availability",
    response_model=TechnicianResponse,
    summary="Update technician availability",
)
async def update_availability(
    technician_id: UUID,
    payload: AvailabilityUpdateRequest,
    service: TechnicianProfileService = Depends(get_technician_service),
) -> TechnicianResponse:
    updated = await service.update_availability(technician_id, payload.availability)
    return _to_technician_response(updated)


# ── Skills Management Endpoints ──────────────────────────────────────────────


@router.get(
    "/{technician_id}/skills",
    response_model=list[SkillResponse],
    summary="List technician skills",
)
async def list_technician_skills(
    technician_id: UUID,
    service: TechnicianProfileService = Depends(get_technician_service),
) -> list[SkillResponse]:
    skills = await service.get_technician_skills(technician_id)
    return [
        SkillResponse(
            id=s.id,
            technician_id=s.technician_id,
            skill_name=s.skill_name,
            proficiency_level=s.proficiency_level,
            created_at=s.created_at,
            updated_at=s.updated_at,
        )
        for s in skills
    ]


@router.post(
    "/{technician_id}/skills",
    response_model=TechnicianResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add or update technician skill",
)
async def add_or_update_skill(
    technician_id: UUID,
    payload: SkillCreateRequest,
    service: TechnicianProfileService = Depends(get_technician_service),
) -> TechnicianResponse:
    updated = await service.add_or_update_skill(
        technician_id=technician_id,
        skill_name=payload.skill_name,
        proficiency_level=payload.proficiency_level,
    )
    return _to_technician_response(updated)


@router.delete(
    "/{technician_id}/skills/{skill_name}",
    response_model=TechnicianResponse,
    summary="Remove a skill from technician",
)
async def remove_skill(
    technician_id: UUID,
    skill_name: str,
    service: TechnicianProfileService = Depends(get_technician_service),
) -> TechnicianResponse:
    updated = await service.remove_skill(technician_id, skill_name)
    return _to_technician_response(updated)
