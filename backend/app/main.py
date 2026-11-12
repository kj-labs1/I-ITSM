"""
FastAPI application factory and entrypoint.

Creates the ASGI application with middleware, exception handlers, and
routers wired up. The ``lifespan`` context manager handles startup/shutdown
lifecycle events (e.g. database pool initialisation).
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


# ── Lifespan ─────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup/shutdown events.

    Startup:
        - Configure structured logging.
        - Log application readiness.
        - Initialize local tables if running on SQLite.
        - Seed sample incidents in integration stub for interactive testing.

    Shutdown:
        - Log graceful shutdown.
    """
    settings = get_settings()
    setup_logging(level=settings.LOG_LEVEL)
    logger.info("I-ITSM v%s starting up (debug=%s)", settings.APP_VERSION, settings.DEBUG)

    # Auto-initialize local tables when using SQLite for seamless local demo
    if "sqlite" in settings.DATABASE_URL:
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

    yield
    logger.info("I-ITSM shutting down.")


# ── Application Factory ─────────────────────────────────────────────────────


def create_app() -> FastAPI:
    """Build and return the fully-configured FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        description=(
            "Intelligent IT Service Management — AI-powered incident classification "
            "and technician assignment."
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
