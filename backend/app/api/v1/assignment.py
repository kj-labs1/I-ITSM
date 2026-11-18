"""
Incident Assignment API Endpoints.

Ownership Boundary:
- Endpoint owned by: Member 3 (Technician & Assignment Engine)
- Operation: POST /api/v1/incidents/{incident_id}/assign
- Delegates incident status change & persistence to Member 2 boundary (`assign_technician`).
- Publishes IncidentAssignedEvent to notify Member 4 (SLA & Audit).
"""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import (
    get_actor_identity,
    get_assignment_service,
)
from app.api.v1.schemas import (
    AssignTechnicianRequest,
    AssignTechnicianResponse,
)
from app.application.assignment.service import (
    TechnicianAssignmentService,
)
from app.domain.identity.user import UserIdentity
from app.shared.enums import UserRole

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Assignment"])


@router.post(
    "/incidents/{incident_id}/assign",
    response_model=AssignTechnicianResponse,
    status_code=status.HTTP_200_OK,
    summary="Assign a technician to an incident",
    description=(
        "Validates eligibility, capacity, and skill requirements, "
        "delegates persistence to Member 2, and publishes assignment event for Member 4."
    ),
)
async def assign_technician_to_incident(
    incident_id: UUID,
    payload: AssignTechnicianRequest,
    actor: UserIdentity = Depends(get_actor_identity),
    assignment_service: TechnicianAssignmentService = Depends(get_assignment_service),
) -> AssignTechnicianResponse:
    """Execute validated incident assignment."""
    if actor.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can assign technicians to incidents.",
        )

    res = await assignment_service.assign_technician(
        incident_id=incident_id,
        technician_id=payload.technician_id,
        actor_id=actor.id,
        strategy_used=payload.strategy_used,
        reason=payload.reason,
    )

    return AssignTechnicianResponse(
        incident_id=res["incidentId"],
        incident_code=res["incidentCode"],
        technician_id=res["technicianId"],
        technician_user_id=res["technicianUserId"],
        status=res["status"],
        strategy_used=res["strategyUsed"],
        assigned_by=res["assignedBy"],
    )
