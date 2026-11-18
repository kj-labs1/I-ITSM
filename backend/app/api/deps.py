"""
FastAPI dependency injection providers.

OOP Design:
- Dependency Inversion Principle: Provides concrete instances of repositories,
  services, and event publishers to API endpoints using FastAPI's `Depends()`.
- Facilitates painless test substitution via `app.dependency_overrides`.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.assignment.service import (
    SmartTechnicianRecommendationService,
    TechnicianAssignmentService,
)
from app.application.interfaces.event_publisher import EventPublisher
from app.application.interfaces.incident_service import IncidentServiceBoundary
from app.application.interfaces.repositories import TechnicianRepository
from app.application.interfaces.sla_repositories import (
    AuditLogRepository,
    NotificationRepository,
    SLAPolicyRepository,
    SLATrackingRepository,
)
from app.application.sla.audit_service import AuditService
from app.application.sla.notification_service import NotificationService
from app.application.sla.sla_service import SLAService
from app.application.technician.service import TechnicianProfileService
from app.infrastructure.database.session import get_db_session
from app.infrastructure.events.event_bus import get_event_bus
from app.infrastructure.repositories.sla_repository import (
    SQLAlchemyAuditLogRepository,
    SQLAlchemyNotificationRepository,
    SQLAlchemySLAPolicyRepository,
    SQLAlchemySLATrackingRepository,
)
from app.infrastructure.repositories.technician_repository import (
    SQLAlchemyTechnicianRepository,
)
from app.integrations.incidents.stub_incident_service import (
    get_stub_incident_service,
)
from app.integrations.llm.factory import LLMProviderFactory
from app.integrations.llm.provider import LLMProvider


def get_technician_repository(
    session: AsyncSession = Depends(get_db_session),
) -> TechnicianRepository:
    """Provide a scoped SQLAlchemyTechnicianRepository."""
    return SQLAlchemyTechnicianRepository(session)


def get_incident_service_boundary() -> IncidentServiceBoundary:
    """
    Provide the IncidentServiceBoundary implementation.

    In development, returns the StubIncidentService.
    When Member 2 integrates their persistent service, swap it here.
    """
    return get_stub_incident_service()


def get_event_publisher() -> EventPublisher:
    """Provide the global domain EventPublisher."""
    return get_event_bus()


def get_llm_provider() -> LLMProvider:
    """Provide the configured LLMProvider instance via LLMProviderFactory."""
    return LLMProviderFactory.create()


def get_technician_service(
    repo: TechnicianRepository = Depends(get_technician_repository),
    incident_service: IncidentServiceBoundary = Depends(get_incident_service_boundary),
    event_bus: EventPublisher = Depends(get_event_publisher),
) -> TechnicianProfileService:
    """Provide the TechnicianProfileService."""
    return TechnicianProfileService(
        repository=repo,
        incident_service=incident_service,
        event_publisher=event_bus,
    )


def get_recommendation_service(
    repo: TechnicianRepository = Depends(get_technician_repository),
    incident_service: IncidentServiceBoundary = Depends(get_incident_service_boundary),
    llm_provider: LLMProvider = Depends(get_llm_provider),
) -> SmartTechnicianRecommendationService:
    """Provide the SmartTechnicianRecommendationService."""
    return SmartTechnicianRecommendationService(
        technician_repo=repo,
        incident_service=incident_service,
        llm_provider=llm_provider,
    )


def get_assignment_service(
    repo: TechnicianRepository = Depends(get_technician_repository),
    incident_service: IncidentServiceBoundary = Depends(get_incident_service_boundary),
    event_bus: EventPublisher = Depends(get_event_publisher),
) -> TechnicianAssignmentService:
    """Provide the TechnicianAssignmentService."""
    return TechnicianAssignmentService(
        technician_repo=repo,
        incident_service=incident_service,
        event_publisher=event_bus,
    )


# ── Module 4: SLA, Audit & Notifications Dependencies ─────────────────────────


def get_sla_policy_repository(
    session: AsyncSession = Depends(get_db_session),
) -> SLAPolicyRepository:
    """Provide a scoped SQLAlchemySLAPolicyRepository."""
    return SQLAlchemySLAPolicyRepository(session)


def get_sla_tracking_repository(
    session: AsyncSession = Depends(get_db_session),
) -> SLATrackingRepository:
    """Provide a scoped SQLAlchemySLATrackingRepository."""
    return SQLAlchemySLATrackingRepository(session)


def get_audit_log_repository(
    session: AsyncSession = Depends(get_db_session),
) -> AuditLogRepository:
    """Provide a scoped SQLAlchemyAuditLogRepository."""
    return SQLAlchemyAuditLogRepository(session)


def get_notification_repository(
    session: AsyncSession = Depends(get_db_session),
) -> NotificationRepository:
    """Provide a scoped SQLAlchemyNotificationRepository."""
    return SQLAlchemyNotificationRepository(session)


def get_sla_service(
    policy_repo: SLAPolicyRepository = Depends(get_sla_policy_repository),
    tracking_repo: SLATrackingRepository = Depends(get_sla_tracking_repository),
    event_bus: EventPublisher = Depends(get_event_publisher),
) -> SLAService:
    """Provide the SLAService."""
    return SLAService(
        policy_repo=policy_repo,
        tracking_repo=tracking_repo,
        event_publisher=event_bus,
    )


def get_audit_service(
    audit_repo: AuditLogRepository = Depends(get_audit_log_repository),
) -> AuditService:
    """Provide the AuditService."""
    return AuditService(audit_repo=audit_repo)


def get_notification_service(
    notification_repo: NotificationRepository = Depends(get_notification_repository),
) -> NotificationService:
    """Provide the NotificationService."""
    return NotificationService(notification_repo=notification_repo)


async def get_actor_user_id() -> UUID:
    """
    Return the authenticated user ID executing the request.
    In this foundation phase before M1's JWT middleware is live, returns
    a deterministic fallback actor UUID if no token is provided.
    """
    return UUID("00000000-0000-0000-0000-000000000001")
