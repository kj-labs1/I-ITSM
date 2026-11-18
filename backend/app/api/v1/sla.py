"""
SLA REST API endpoints — Member 4.

Routes owned (per PROJECT_CONTRACT.md):
- GET   /api/v1/incidents/{incident_id}/sla
- POST  /api/v1/incidents/{incident_id}/sla
- GET   /api/v1/sla/violations
- GET   /api/v1/sla/policies
- POST  /api/v1/sla/policies
- PATCH /api/v1/sla/policies/{priority}
- POST  /api/v1/sla/check
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import (
    get_actor_identity,
    get_incident_service,
    get_sla_service,
)
from app.api.v1.sla_schemas import (
    IncidentSLAResponse,
    SLACheckSummaryResponse,
    SLAPolicyCreateRequest,
    SLAPolicyResponse,
    SLAPolicyUpdateRequest,
    SLATrackingStartRequest,
)
from app.application.incident.service import IncidentApplicationService
from app.application.sla.sla_service import SLAService
from app.domain.identity.user import UserIdentity
from app.domain.sla.policy import SLAPolicy
from app.domain.sla.tracking import IncidentSLATracking
from app.shared.enums import Priority, UserRole

router = APIRouter(tags=["SLA"])


def _policy_to_response(policy: SLAPolicy) -> SLAPolicyResponse:
    return SLAPolicyResponse(
        id=policy.id,
        priority=policy.priority,
        name=policy.name,
        response_time_minutes=policy.response_time_minutes,
        resolution_time_minutes=policy.resolution_time_minutes,
        warning_threshold_percent=policy.warning_threshold_percent,
        escalation_enabled=policy.escalation_enabled,
        created_at=policy.created_at,
        updated_at=policy.updated_at,
    )


def _tracking_to_response(tracking: IncidentSLATracking) -> IncidentSLAResponse:
    now = datetime.now(UTC)
    return IncidentSLAResponse(
        id=tracking.id,
        incident_id=tracking.incident_id,
        policy_id=tracking.policy_id,
        priority=tracking.priority,
        status=tracking.status,
        started_at=tracking.started_at,
        response_due_at=tracking.response_due_at,
        resolution_due_at=tracking.resolution_due_at,
        first_responded_at=tracking.first_responded_at,
        resolved_at=tracking.resolved_at,
        response_breached=tracking.response_breached,
        resolution_breached=tracking.resolution_breached,
        is_breached=tracking.is_breached,
        warning_sent=tracking.warning_sent,
        remaining_response_seconds=tracking.remaining_response_seconds(now),
        remaining_resolution_seconds=tracking.remaining_resolution_seconds(now),
        created_at=tracking.created_at,
        updated_at=tracking.updated_at,
    )


@router.get(
    "/incidents/{incident_id}/sla",
    response_model=IncidentSLAResponse,
    summary="Get SLA status for an incident",
)
async def get_incident_sla(
    incident_id: UUID,
    actor: UserIdentity = Depends(get_actor_identity),
    sla_service: SLAService = Depends(get_sla_service),
    incident_service: IncidentApplicationService = Depends(get_incident_service),
) -> IncidentSLAResponse:
    """Retrieve SLA deadlines, remaining time, and breach status for an incident."""
    if actor.role != UserRole.ADMIN:
        incident = await incident_service.get_incident_entity(incident_id)
        if incident.reporter_id != actor.id and incident.assigned_technician_id != actor.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: You cannot view SLA tracking for this incident.",
            )
    tracking = await sla_service.get_incident_sla(incident_id)
    return _tracking_to_response(tracking)


@router.post(
    "/incidents/{incident_id}/sla",
    response_model=IncidentSLAResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start SLA tracking for an incident",
)
async def start_incident_sla(
    incident_id: UUID,
    payload: SLATrackingStartRequest,
    actor: UserIdentity = Depends(get_actor_identity),
    sla_service: SLAService = Depends(get_sla_service),
) -> IncidentSLAResponse:
    """Initialize SLA tracking for an incident using its priority's SLA policy."""
    if actor.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can initialize SLA tracking manually.",
        )
    tracking = await sla_service.start_tracking(
        incident_id=incident_id,
        priority=payload.priority,
        started_at=payload.started_at,
    )
    return _tracking_to_response(tracking)


@router.get(
    "/sla/violations",
    response_model=list[IncidentSLAResponse],
    summary="List SLA violations and optional warnings",
)
async def list_sla_violations(
    include_warnings: bool = Query(
        default=False,
        alias="includeWarnings",
        description="When true, include WARNING incidents alongside BREACHED incidents.",
    ),
    priority: Priority | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    actor: UserIdentity = Depends(get_actor_identity),
    sla_service: SLAService = Depends(get_sla_service),
) -> list[IncidentSLAResponse]:
    """Return incidents that have breached (or are approaching) their SLA deadlines."""
    if actor.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can list SLA violations.",
        )
    records = await sla_service.list_violations(
        include_warnings=include_warnings,
        priority=priority,
        skip=skip,
        limit=limit,
    )
    return [_tracking_to_response(r) for r in records]


@router.get(
    "/sla/policies",
    response_model=list[SLAPolicyResponse],
    summary="List SLA policies (P1–P4)",
)
async def list_sla_policies(
    sla_service: SLAService = Depends(get_sla_service),
) -> list[SLAPolicyResponse]:
    """List all configured SLA policies."""
    policies = await sla_service.list_policies()
    return [_policy_to_response(p) for p in policies]


@router.post(
    "/sla/policies",
    response_model=SLAPolicyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an SLA policy",
)
async def create_sla_policy(
    payload: SLAPolicyCreateRequest,
    actor: UserIdentity = Depends(get_actor_identity),
    sla_service: SLAService = Depends(get_sla_service),
) -> SLAPolicyResponse:
    """Create a new SLA policy for a priority level."""
    if actor.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can create SLA policies.",
        )
    policy = await sla_service.create_policy(
        priority=payload.priority,
        name=payload.name,
        response_time_minutes=payload.response_time_minutes,
        resolution_time_minutes=payload.resolution_time_minutes,
        warning_threshold_percent=payload.warning_threshold_percent,
        escalation_enabled=payload.escalation_enabled,
    )
    return _policy_to_response(policy)


@router.patch(
    "/sla/policies/{priority}",
    response_model=SLAPolicyResponse,
    summary="Update an SLA policy by priority",
)
async def update_sla_policy(
    priority: Priority,
    payload: SLAPolicyUpdateRequest,
    actor: UserIdentity = Depends(get_actor_identity),
    sla_service: SLAService = Depends(get_sla_service),
) -> SLAPolicyResponse:
    """Update response/resolution target durations or warning threshold for a priority."""
    if actor.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can update SLA policies.",
        )
    policy = await sla_service.update_policy(
        priority=priority,
        name=payload.name,
        response_time_minutes=payload.response_time_minutes,
        resolution_time_minutes=payload.resolution_time_minutes,
        warning_threshold_percent=payload.warning_threshold_percent,
        escalation_enabled=payload.escalation_enabled,
    )
    return _policy_to_response(policy)


@router.post(
    "/sla/check",
    response_model=SLACheckSummaryResponse,
    summary="Run an on-demand SLA breach/warning evaluation sweep",
)
async def trigger_sla_check(
    actor: UserIdentity = Depends(get_actor_identity),
    sla_service: SLAService = Depends(get_sla_service),
) -> SLACheckSummaryResponse:
    """Evaluate all active incident SLAs immediately and trigger alerts if needed."""
    if actor.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can trigger SLA checks.",
        )
    results = await sla_service.evaluate_active_slas()
    return SLACheckSummaryResponse(
        evaluated_count=len(results),
        warnings_triggered=sum(1 for r in results if r.newly_warned),
        breaches_triggered=sum(1 for r in results if r.newly_breached),
    )
