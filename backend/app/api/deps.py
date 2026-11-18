
"""
FastAPI dependency injection providers.

Provides concrete implementations of the application's
repository and service abstractions.

Production incident operations use Member 2's persistent service.
Tests may override the service boundary with StubIncidentService.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.assignment.service import (
    SmartTechnicianRecommendationService,
    TechnicianAssignmentService,
)
from app.application.incident.service import IncidentApplicationService
from app.application.interfaces.event_publisher import EventPublisher
from app.application.interfaces.incident_repository import IncidentRepository
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
from app.core.security import decode_access_token
from app.infrastructure.database.session import get_db_session
from app.infrastructure.events.event_bus import get_event_bus
from app.infrastructure.repositories.incident_repository import (
    SQLAlchemyIncidentRepository,
)
from app.infrastructure.repositories.sla_repository import (
    SQLAlchemyAuditLogRepository,
    SQLAlchemyNotificationRepository,
    SQLAlchemySLAPolicyRepository,
    SQLAlchemySLATrackingRepository,
)
from app.infrastructure.repositories.technician_repository import (
    SQLAlchemyTechnicianRepository,
)
from app.integrations.llm.factory import LLMProviderFactory
from app.integrations.llm.provider import LLMProvider

# ============================================================
# REPOSITORY DEPENDENCIES
# ============================================================


def get_technician_repository(
    session: AsyncSession = Depends(get_db_session),
) -> TechnicianRepository:
    """Provide a scoped SQLAlchemyTechnicianRepository."""

    return SQLAlchemyTechnicianRepository(session)


def get_incident_repository(
    session: AsyncSession = Depends(get_db_session),
) -> IncidentRepository:
    """Provide a scoped SQLAlchemyIncidentRepository."""

    return SQLAlchemyIncidentRepository(session)


# ============================================================
# SHARED INFRASTRUCTURE DEPENDENCIES
# ============================================================


def get_event_publisher() -> EventPublisher:
    """Provide the global event publisher."""

    return get_event_bus()


def get_llm_provider() -> LLMProvider:
    """Provide the configured LLM provider."""

    return LLMProviderFactory.create()


# ============================================================
# MEMBER 2 — INCIDENT APPLICATION SERVICE
# ============================================================


def get_incident_service(
    repository: IncidentRepository = Depends(get_incident_repository),
    event_publisher: EventPublisher = Depends(get_event_publisher),
) -> IncidentApplicationService:
    """Provide Member 2's persistent incident application service."""

    return IncidentApplicationService(
        repository=repository,
        event_publisher=event_publisher,
    )


def get_incident_service_boundary(
    service: IncidentApplicationService = Depends(get_incident_service),
) -> IncidentServiceBoundary:
    """
    Provide the persistent incident service through Member 3's interface.

    This replaces the in-memory stub in production.
    Tests can override this dependency with StubIncidentService.
    """

    return service


# ============================================================
# MEMBER 3 — TECHNICIAN APPLICATION SERVICES
# ============================================================


def get_technician_service(
    repo: TechnicianRepository = Depends(get_technician_repository),
    incident_service: IncidentServiceBoundary = Depends(
        get_incident_service_boundary
    ),
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
    incident_service: IncidentServiceBoundary = Depends(
        get_incident_service_boundary
    ),
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
    incident_service: IncidentServiceBoundary = Depends(
        get_incident_service_boundary
    ),
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


# ============================================================
# ACTOR IDENTITY
# ============================================================


_optional_oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="api/v1/auth/login",
    auto_error=False,
)


async def get_actor_user_id(
    token: str | None = Depends(_optional_oauth2_scheme),
) -> UUID:
    """
    Return the authenticated actor's UUID from JWT token when present,
    falling back to test placeholder when unauthenticated.
    """
    if token:
        try:
            payload = decode_access_token(token)
            return UUID(payload["sub"])
        except Exception:
            pass

    return UUID("00000000-0000-0000-0000-000000000001")
