"""
Audit Trail REST API endpoints — Member 4.

Routes owned (per PROJECT_CONTRACT.md):
- GET /api/v1/incidents/{incident_id}/audit
- GET /api/v1/audit
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import (
    get_actor_identity,
    get_audit_service,
    get_incident_service,
)
from app.api.v1.sla_schemas import AuditLogResponse
from app.application.incident.service import IncidentApplicationService
from app.application.sla.audit_service import AuditService
from app.domain.identity.user import UserIdentity
from app.domain.sla.audit import AuditLogEntry
from app.shared.enums import UserRole

router = APIRouter(tags=["Audit"])


def _to_response(entry: AuditLogEntry) -> AuditLogResponse:
    return AuditLogResponse(
        id=entry.id,
        incident_id=entry.incident_id,
        actor_id=entry.actor_id,
        action=entry.action,
        event_type=entry.event_type,
        previous_value=entry.previous_value,
        new_value=entry.new_value,
        details=entry.details,
        occurred_at=entry.occurred_at,
        created_at=entry.created_at,
    )


@router.get(
    "/incidents/{incident_id}/audit",
    response_model=list[AuditLogResponse],
    summary="Get audit trail timeline for an incident",
)
async def get_incident_audit_trail(
    incident_id: UUID,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    actor: UserIdentity = Depends(get_actor_identity),
    audit_service: AuditService = Depends(get_audit_service),
    incident_service: IncidentApplicationService = Depends(get_incident_service),
) -> list[AuditLogResponse]:
    """Return the chronological audit event timeline for a specific incident."""
    if actor.role != UserRole.ADMIN:
        incident = await incident_service.get_incident_entity(incident_id)
        if incident.reporter_id != actor.id and incident.assigned_technician_id != actor.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: You cannot view audit trails for this incident.",
            )
    entries = await audit_service.get_incident_audit_trail(
        incident_id=incident_id,
        skip=skip,
        limit=limit,
    )
    return [_to_response(e) for e in entries]


@router.get(
    "/audit",
    response_model=list[AuditLogResponse],
    summary="Query audit logs",
)
async def list_audit_logs(
    incident_id: UUID | None = Query(default=None, alias="incidentId"),
    actor_id: UUID | None = Query(default=None, alias="actorId"),
    action: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    actor: UserIdentity = Depends(get_actor_identity),
    audit_service: AuditService = Depends(get_audit_service),
) -> list[AuditLogResponse]:
    """Query system-wide audit logs with optional filtering."""
    if actor.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can query system-wide audit logs.",
        )
    entries = await audit_service.query_audit_logs(
        incident_id=incident_id,
        actor_id=actor_id,
        action=action,
        skip=skip,
        limit=limit,
    )
    return [_to_response(e) for e in entries]
