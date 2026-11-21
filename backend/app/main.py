"""
FastAPI application factory and entrypoint.

Creates the ASGI application with middleware, exception handlers, and
routers wired up. The ``lifespan`` context manager handles startup/shutdown
lifecycle events (e.g. database pool initialisation, Member 4 event listener
registration, and scheduled SLA background monitoring).
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse

from app.api.v1.router import router as api_v1_router
from app.core.config import get_settings
from app.core.exceptions import IITSMException
from app.core.logging import setup_logging

logger = logging.getLogger("app.main")


# ── Member 4 Scoped Service Factories (for Event Listeners & Monitor) ────────


@asynccontextmanager
async def _scoped_sla_service() -> AsyncGenerator:
    from app.application.sla.sla_service import SLAService
    from app.infrastructure.database.session import get_session_factory
    from app.infrastructure.events.event_bus import get_event_bus
    from app.infrastructure.repositories.sla_repository import (
        SQLAlchemySLAPolicyRepository,
        SQLAlchemySLATrackingRepository,
    )

    factory = get_session_factory()
    async with factory() as session:
        try:
            service = SLAService(
                policy_repo=SQLAlchemySLAPolicyRepository(session),
                tracking_repo=SQLAlchemySLATrackingRepository(session),
                event_publisher=get_event_bus(),
            )
            yield service
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def _scoped_audit_service() -> AsyncGenerator:
    from app.application.sla.audit_service import AuditService
    from app.infrastructure.database.session import get_session_factory
    from app.infrastructure.repositories.sla_repository import SQLAlchemyAuditLogRepository

    factory = get_session_factory()
    async with factory() as session:
        try:
            yield AuditService(audit_repo=SQLAlchemyAuditLogRepository(session))
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def _scoped_notification_service() -> AsyncGenerator:
    from app.application.sla.notification_service import NotificationService
    from app.infrastructure.database.session import get_session_factory
    from app.infrastructure.repositories.sla_repository import SQLAlchemyNotificationRepository

    factory = get_session_factory()
    async with factory() as session:
        try:
            yield NotificationService(
                notification_repo=SQLAlchemyNotificationRepository(session)
            )
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def _scoped_incident_service() -> AsyncGenerator:
    from app.application.incident.service import IncidentApplicationService
    from app.infrastructure.database.session import get_session_factory
    from app.infrastructure.events.event_bus import get_event_bus
    from app.infrastructure.repositories.incident_repository import (
        SQLAlchemyIncidentRepository,
    )

    factory = get_session_factory()
    async with factory() as session:
        try:
            yield IncidentApplicationService(
                repository=SQLAlchemyIncidentRepository(session),
                event_publisher=get_event_bus(),
            )
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ── Lifespan ─────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup/shutdown events.

    Startup:
        - Configure structured logging.
        - Initialize local tables if running on SQLite.
        - Seed sample incidents in integration stub for interactive testing.
        - Seed default P1–P4 SLA policies (Member 4).
        - Register Member 4 Observer Pattern event listeners on InProcessEventBus.
        - Start 60-second background SLAMonitorTask.

    Shutdown:
        - Stop background SLAMonitorTask cleanly.
        - Log graceful shutdown.
    """
    settings = get_settings()
    setup_logging(level=settings.LOG_LEVEL)
    logger.info("I-ITSM v%s starting up (debug=%s)", settings.APP_VERSION, settings.DEBUG)

    # Auto-initialize local tables when using SQLite for seamless local demo
    if "sqlite" in settings.DATABASE_URL:
        import app.infrastructure.database.models  # noqa: F401
        import app.infrastructure.database.sla_models  # noqa: F401
        from app.infrastructure.database.base import Base
        from app.infrastructure.database.session import get_engine

        engine = get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("SQLite local database tables verified/created.")

    # Seed sample incidents in StubIncidentService for interactive Swagger/curl testing
    from uuid import UUID

    from app.integrations.incidents.stub_incident_service import get_stub_incident_service
    from app.shared.enums import IncidentCategory, Priority

    incident_stub = get_stub_incident_service()
    incident_stub.seed_incident(
        incident_id=UUID("11111111-2222-3333-4444-555555555555"),
        incident_code="INC-1001",
        category=IncidentCategory.NETWORK,
        required_skill="Network Diagnostics",
        priority=Priority.P1,
        description="Core network switch in Data Center B is dropping packets intermittently.",
    )
    incident_stub.seed_incident(
        incident_id=UUID("22222222-3333-4444-5555-666666666666"),
        incident_code="INC-1002",
        category=IncidentCategory.DATABASE,
        required_skill="Database Performance Tuning",
        priority=Priority.P2,
        description="High connection pool saturation and query timeouts on production Postgres.",
    )
    incident_stub.seed_incident(
        incident_id=UUID("33333333-4444-5555-6666-777777777777"),
        incident_code="INC-1003",
        category=IncidentCategory.SECURITY,
        required_skill="Security Auditing",
        priority=Priority.P3,
        description="Multiple failed SSH login attempts detected on internal Bastion host.",
    )

    # ── Member 4: Seed default SLA policies, subscribe listeners, start monitor
    from app.application.sla.listeners import (
        AuditEventListener,
        NotificationEventListener,
        SLALifecycleEventListener,
    )
    from app.application.sla.monitor import SLAMonitorTask
    from app.domain.assignment.events import DomainEvent
    from app.infrastructure.events.event_bus import get_event_bus

    try:
        async with _scoped_sla_service() as sla_service:
            await sla_service.ensure_default_policies()
    except Exception as exc:
        logger.warning("Skipping initial SLA policy seeding: %s", exc)

    event_bus = get_event_bus()
    audit_listener = AuditEventListener(_scoped_audit_service)
    notification_listener = NotificationEventListener(
        _scoped_notification_service,
        incident_service_factory=_scoped_incident_service,
    )
    sla_lifecycle_listener = SLALifecycleEventListener(_scoped_sla_service)

    event_bus.subscribe(DomainEvent, audit_listener)
    event_bus.subscribe(DomainEvent, notification_listener)
    event_bus.subscribe(DomainEvent, sla_lifecycle_listener)

    sla_monitor = SLAMonitorTask(_scoped_sla_service, interval_seconds=60.0)
    sla_monitor.start()

    yield

    await sla_monitor.stop()
    event_bus.unsubscribe(DomainEvent, audit_listener)
    event_bus.unsubscribe(DomainEvent, notification_listener)
    event_bus.unsubscribe(DomainEvent, sla_lifecycle_listener)
    logger.info("I-ITSM shutting down.")


# ── Application Factory ─────────────────────────────────────────────────────


def create_app() -> FastAPI:
    """Build and return the fully-configured FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        description=(
            "Intelligent IT Service Management — AI-powered incident classification, "
            "technician assignment, SLA tracking, audit logging, and notifications."
        ),
        version=settings.APP_VERSION,
        lifespan=lifespan,
    )

    # ── Middleware ────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Exception Handlers ───────────────────────────────────────────────

    @app.exception_handler(IITSMException)
    async def iitsm_exception_handler(request: Request, exc: IITSMException) -> JSONResponse:
        """Catch all domain/business exceptions and return a uniform error envelope."""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "timestamp": datetime.now(UTC).isoformat(),
                "status": exc.status_code,
                "errorCode": exc.error_code,
                "message": exc.message,
                "detail": exc.message,
                "path": request.url.path,
            },
        )

    # ── Routers ──────────────────────────────────────────────────────────
    app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)

    # ── Health & Root ────────────────────────────────────────────────────

    @app.get("/health", tags=["Health"], summary="Health check")
    async def health_check():
        """Return basic application health status."""
        return {
            "status": "healthy",
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
        }

    @app.get("/", include_in_schema=False)
    async def root_redirect():
        """Redirect the root URL to the interactive API docs."""
        return RedirectResponse(url="/docs")

    return app


# Module-level app instance used by ``uvicorn app.main:app``
app = create_app()
