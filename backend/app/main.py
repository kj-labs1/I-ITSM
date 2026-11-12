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

    Shutdown:
        - Log graceful shutdown.
    """
    settings = get_settings()
    setup_logging(level=settings.LOG_LEVEL)
    logger.info("I-ITSM v%s starting up (debug=%s)", settings.APP_VERSION, settings.DEBUG)
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
