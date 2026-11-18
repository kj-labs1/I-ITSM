
"""
Incident Management REST API — Member 2.

Endpoints:
- POST   /api/v1/incidents
- GET    /api/v1/incidents
- GET    /api/v1/incidents/{incident_id}
- PATCH  /api/v1/incidents/{incident_id}
- PATCH  /api/v1/incidents/{incident_id}/status
- POST   /api/v1/incidents/{incident_id}/comments

Member 2 owns these routes.
"""

from __future__ import annotations

import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import (
    get_actor_identity,
    get_incident_service,
)
from app.api.v1.schemas import (
    IncidentCommentCreateRequest,
    IncidentCommentResponse,
    IncidentCreateRequest,
    IncidentDetailsResponse,
    IncidentResponse,
    IncidentStatusUpdateRequest,
    IncidentUpdateRequest,
    PotentialDuplicateResponse,
)
from app.application.incident.service import IncidentApplicationService
from app.core.exceptions import (
    AuthorizationError,
)
from app.domain.identity.user import UserIdentity
from app.domain.incident.incident import Incident
from app.domain.incident.incident_comment import IncidentComment
from app.shared.enums import (
    IncidentCategory,
    IncidentStatus,
    Priority,
    UserRole,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/incidents",
    tags=["Incidents"],
)


# ============================================================
# RESPONSE CONVERSION HELPERS
# ============================================================


def _to_incident_response(
    incident: Incident,
) -> IncidentResponse:
    """Convert an Incident domain entity into an API response."""

    return IncidentResponse(
        id=incident.id,
        incident_code=incident.incident_code,
        reporter_id=incident.reporter_id,
        service_id=incident.service_id,
        category=incident.category,
        required_skill=incident.required_skill,
        description=incident.description,
        impact=incident.impact,
        urgency=incident.urgency,
        business_criticality=incident.business_criticality,
        priority=incident.priority,
        status=incident.status,
        assigned_technician_id=incident.assigned_technician_id,
        resolution_details=incident.resolution_details,
        created_at=incident.created_at,
        updated_at=incident.updated_at,
    )


def _to_comment_response(
    comment: IncidentComment,
) -> IncidentCommentResponse:
    """Convert an IncidentComment domain entity into an API response."""

    return IncidentCommentResponse(
        id=comment.id,
        incident_id=comment.incident_id,
        author_id=comment.author_id,
        content=comment.content,
        created_at=comment.created_at,
    )


def _check_incident_access(
    incident: Incident,
    actor: UserIdentity,
) -> None:
    """
    Ensure that the actor participates in the incident or has administrative privileges.
    """
    if actor.role == UserRole.ADMIN:
        return

    is_reporter = incident.reporter_id == actor.id
    is_assigned_technician = incident.assigned_technician_id == actor.id

    if not (is_reporter or is_assigned_technician):
        raise AuthorizationError(
            "You do not have permission to access this incident."
        )


# ============================================================
# 1. CREATE INCIDENT
# ============================================================


@router.post(
    "",
    response_model=IncidentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new incident",
)
async def create_incident(
    payload: IncidentCreateRequest,
    actor: UserIdentity = Depends(get_actor_identity),
    service: IncidentApplicationService = Depends(get_incident_service),
) -> IncidentResponse:
    """Create an incident reported by the authenticated user."""
    if actor.role == UserRole.TECHNICIAN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Technicians are not permitted to report incidents.",
        )

    incident = await service.create_incident(
        reporter_id=actor.id,
        service_id=payload.service_id,
        category=payload.category,
        required_skill=payload.required_skill,
        description=payload.description,
        impact=payload.impact,
        urgency=payload.urgency,
        business_criticality=payload.business_criticality,
    )

    return _to_incident_response(incident)


# ============================================================
# 2. LIST INCIDENTS
# ============================================================
@router.get(
    "/{incident_id}",
    response_model=IncidentDetailsResponse,
)
async def get_incident_details(
    incident_id: UUID,
    svc: IncidentApplicationService = Depends(get_incident_service),
    actor: UserIdentity = Depends(get_actor_identity),
):
    """Retrieve an incident along with its comments."""
    incident, comments = await svc.get_incident_details(incident_id)

    _check_incident_access(incident, actor)

    return IncidentDetailsResponse(
        **_to_incident_response(incident).model_dump(),
        comments=[
            _to_comment_response(comment)
            for comment in comments
        ],
    )

@router.get("", response_model=list[IncidentResponse])
async def list_incidents(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),

    incident_id: UUID | None = Query(
        default=None,
        alias="incidentId",
    ),
    incident_code: str | None = Query(
        default=None,
        alias="incidentCode",
        min_length=1,
        max_length=50,
    ),
    date_from: datetime | None = Query(
        default=None,
        alias="dateFrom",
    ),
    date_to: datetime | None = Query(
        default=None,
        alias="dateTo",
    ),
    status: IncidentStatus | None = Query(default=None),
    priority: Priority | None = Query(default=None),
    category: IncidentCategory | None = Query(default=None),
    service_id: UUID | None = Query(
        default=None,
        alias="serviceId",
    ),
    assigned_technician_id: UUID | None = Query(
        default=None,
        alias="assignedTechnicianId",
    ),

    svc: IncidentApplicationService = Depends(get_incident_service),
    actor: UserIdentity = Depends(get_actor_identity),
):
    """List incidents matching role-based visibility and optional search filters."""
    if actor.role == UserRole.TECHNICIAN:
        filter_reporter_id = None
        filter_assigned_tech_id = actor.id
    elif actor.role == UserRole.EMPLOYEE:
        filter_reporter_id = actor.id
        filter_assigned_tech_id = assigned_technician_id
    else:
        filter_reporter_id = None
        filter_assigned_tech_id = assigned_technician_id

    incidents = await svc.list_incidents(
        skip=skip,
        limit=limit,
        reporter_id=filter_reporter_id,
        incident_id=incident_id,
        incident_code=incident_code,
        date_from=date_from,
        date_to=date_to,
        status=status,
        priority=priority,
        category=category,
        service_id=service_id,
        assigned_technician_id=filter_assigned_tech_id,
    )

    return [
        IncidentResponse.model_validate(incident)
        for incident in incidents
    ]


# ============================================================
# 3. GET INCIDENT DETAILS
# ============================================================


@router.get(
    "/{incident_id}/duplicates",
    response_model=list[PotentialDuplicateResponse],
)
async def get_potential_duplicates(
    incident_id: UUID,
    svc: IncidentApplicationService = Depends(get_incident_service),
    actor: UserIdentity = Depends(get_actor_identity),
):
    """
    Retrieve possible duplicates of an incident.
    """

    incident = await svc.get_incident_entity(incident_id)

    _check_incident_access(incident, actor)

    matches = await svc.find_potential_duplicates(incident_id)

    return [
        PotentialDuplicateResponse(
            incident_id=match.incident.id,
            incident_code=match.incident.incident_code,
            category=match.incident.category,
            priority=match.incident.priority,
            status=match.incident.status,
            created_at=match.incident.created_at,
            similarity_score=round(match.similarity_score, 3),
            explanation=match.explanation,
        )
        for match in matches
    ]


# ============================================================
# 4. UPDATE INCIDENT
# ============================================================


@router.patch(
    "/{incident_id}",
    response_model=IncidentResponse,
    summary="Update incident information",
)
async def update_incident(
    incident_id: UUID,
    payload: IncidentUpdateRequest,
    actor: UserIdentity = Depends(get_actor_identity),
    service: IncidentApplicationService = Depends(get_incident_service),
) -> IncidentResponse:
    """Update permitted incident fields."""

    existing = await service.get_incident_entity(incident_id)

    if actor.role != UserRole.ADMIN and existing.reporter_id != actor.id:
        raise AuthorizationError(
            "Only the incident reporter or an administrator can update its information."
        )

    changes = payload.model_dump(exclude_unset=True)

    updated = await service.update_incident(
        incident_id=incident_id,
        changes=changes,
    )

    return _to_incident_response(updated)


# ============================================================
# 5. UPDATE INCIDENT STATUS
# ============================================================


@router.patch(
    "/{incident_id}/status",
    response_model=IncidentResponse,
    summary="Change incident lifecycle status",
)
async def update_incident_status(
    incident_id: UUID,
    payload: IncidentStatusUpdateRequest,
    actor: UserIdentity = Depends(get_actor_identity),
    service: IncidentApplicationService = Depends(get_incident_service),
) -> IncidentResponse:
    """
    Change status using the IncidentLifecycle state machine with role enforcement.
    """

    existing = await service.get_incident_entity(incident_id)

    if actor.role == UserRole.ADMIN:
        pass
    elif actor.role == UserRole.TECHNICIAN:
        if existing.assigned_technician_id != actor.id:
            raise AuthorizationError("Technicians can only update status for incidents assigned to them.")
        allowed_tech_statuses = {
            IncidentStatus.ACKNOWLEDGED,
            IncidentStatus.IN_PROGRESS,
            IncidentStatus.RESOLVED,
        }
        if payload.status not in allowed_tech_statuses:
            raise AuthorizationError(f"Technicians cannot transition incident to '{payload.status.value}'.")
    elif actor.role == UserRole.EMPLOYEE:
        if existing.reporter_id != actor.id:
            raise AuthorizationError("Employees can only verify or close their own reported incidents.")
        allowed_emp_statuses = {
            IncidentStatus.VERIFIED,
            IncidentStatus.CLOSED,
        }
        if payload.status not in allowed_emp_statuses:
            raise AuthorizationError(f"Employees cannot transition incident to '{payload.status.value}'.")
    else:
        raise AuthorizationError("Unauthorized to update incident status.")

    updated = await service.update_incident_status(
        incident_id=incident_id,
        new_status=payload.status,
        actor_id=actor.id,
        resolution_details=payload.resolution_details,
    )

    return _to_incident_response(updated)


# ============================================================
# 6. ADD INCIDENT COMMENT
# ============================================================


@router.post(
    "/{incident_id}/comments",
    response_model=IncidentCommentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a comment to an incident",
)
async def add_incident_comment(
    incident_id: UUID,
    payload: IncidentCommentCreateRequest,
    actor: UserIdentity = Depends(get_actor_identity),
    service: IncidentApplicationService = Depends(get_incident_service),
) -> IncidentCommentResponse:
    """Add a comment to an incident."""

    existing = await service.get_incident_entity(incident_id)

    _check_incident_access(existing, actor)

    comment = await service.add_comment(
        incident_id=incident_id,
        author_id=actor.id,
        content=payload.content,
    )

    return _to_comment_response(comment)
