"""
Pytest configuration and shared test fixtures.

Provides:
- In-memory async SQLite engine & session for isolated repository and API tests.
- FastAPI test client (`httpx.AsyncClient` with `ASGITransport`).
- Pre-configured test doubles: `MockLLMProvider`, `StubIncidentService`, `InProcessEventBus`.
- Member 4 repositories and services (`sla_service`, `audit_service`, `notification_service`).
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from uuid import UUID

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

import app.infrastructure.database.incident_models

# Register all ORM models with SQLAlchemy metadata before create_all
import app.infrastructure.database.models  # noqa: F401
import app.infrastructure.database.sla_models  # noqa: F401
from app.api.deps import (
    get_actor_identity,
    get_actor_user_id,
    get_assignment_service,
    get_audit_log_repository,
    get_audit_service,
    get_db_session,
    get_event_publisher,
    get_incident_service,
    get_incident_service_boundary,
    get_llm_provider,
    get_notification_repository,
    get_notification_service,
    get_recommendation_service,
    get_sla_policy_repository,
    get_sla_service,
    get_sla_tracking_repository,
    get_technician_repository,
    get_technician_service,
)
from app.application.assignment.service import (
    SmartTechnicianRecommendationService,
    TechnicianAssignmentService,
)
from app.application.incident.service import IncidentApplicationService
from app.application.sla.audit_service import AuditService
from app.application.sla.notification_service import NotificationService
from app.application.sla.sla_service import SLAService
from app.application.technician.service import TechnicianProfileService
from app.domain.identity.user import UserIdentity
from app.infrastructure.database.base import Base
from app.infrastructure.events.event_bus import InProcessEventBus
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
from app.integrations.incidents.stub_incident_service import StubIncidentService
from app.integrations.llm.mock_provider import MockLLMProvider
from app.main import create_app
from app.shared.enums import UserRole


@pytest.fixture(scope="session")
def event_loop():
    """Create a session-scoped event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def test_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Create an isolated in-memory SQLite database for testing."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional database session rolled back after each test."""
    session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest.fixture
def mock_llm() -> MockLLMProvider:
    """Return a clean MockLLMProvider."""
    return MockLLMProvider()


@pytest.fixture
def stub_incidents() -> StubIncidentService:
    """Return a fresh in-memory stub incident service."""
    return StubIncidentService()


@pytest.fixture
def event_bus() -> InProcessEventBus:
    """Return a fresh in-process event bus."""
    return InProcessEventBus()


@pytest.fixture
def tech_repo(db_session: AsyncSession) -> SQLAlchemyTechnicianRepository:
    """Return an SQLAlchemy repository connected to the test session."""
    return SQLAlchemyTechnicianRepository(db_session)


@pytest.fixture
def tech_service(
    tech_repo: SQLAlchemyTechnicianRepository,
    stub_incidents: StubIncidentService,
    event_bus: InProcessEventBus,
) -> TechnicianProfileService:
    """Return a TechnicianProfileService wired with test doubles."""
    return TechnicianProfileService(
        repository=tech_repo,
        incident_service=stub_incidents,
        event_publisher=event_bus,
    )


@pytest.fixture
def rec_service(
    tech_repo: SQLAlchemyTechnicianRepository,
    stub_incidents: StubIncidentService,
    mock_llm: MockLLMProvider,
) -> SmartTechnicianRecommendationService:
    """Return a SmartTechnicianRecommendationService wired with test doubles."""
    return SmartTechnicianRecommendationService(
        technician_repo=tech_repo,
        incident_service=stub_incidents,
        llm_provider=mock_llm,
    )


@pytest.fixture
def assign_service(
    tech_repo: SQLAlchemyTechnicianRepository,
    stub_incidents: StubIncidentService,
    event_bus: InProcessEventBus,
) -> TechnicianAssignmentService:
    """Return a TechnicianAssignmentService wired with test doubles."""
    return TechnicianAssignmentService(
        technician_repo=tech_repo,
        incident_service=stub_incidents,
        event_publisher=event_bus,
    )


# ── Member 4 Fixtures ────────────────────────────────────────────────────────


@pytest.fixture
def sla_service(
    db_session: AsyncSession,
    event_bus: InProcessEventBus,
) -> SLAService:
    """Return an SLAService connected to the isolated test session."""
    return SLAService(
        policy_repo=SQLAlchemySLAPolicyRepository(db_session),
        tracking_repo=SQLAlchemySLATrackingRepository(db_session),
        event_publisher=event_bus,
    )


@pytest.fixture
def audit_service(db_session: AsyncSession) -> AuditService:
    """Return an AuditService connected to the isolated test session."""
    return AuditService(audit_repo=SQLAlchemyAuditLogRepository(db_session))


@pytest.fixture
def notification_service(db_session: AsyncSession) -> NotificationService:
    """Return a NotificationService connected to the isolated test session."""
    return NotificationService(notification_repo=SQLAlchemyNotificationRepository(db_session))


@pytest_asyncio.fixture
async def async_client(
    db_session: AsyncSession,
    stub_incidents: StubIncidentService,
    mock_llm: MockLLMProvider,
    event_bus: InProcessEventBus,
) -> AsyncGenerator[AsyncClient, None]:
    """
    Provide an HTTPX AsyncClient with all dependencies wired to test doubles.
    """
    app = create_app()

    # Create scoped test services (M3 + M4)
    repo = SQLAlchemyTechnicianRepository(db_session)

    incident_repo = SQLAlchemyIncidentRepository(db_session)

    incident_service = IncidentApplicationService(
        repository=incident_repo,
        event_publisher=event_bus,
    )
    stub_incidents._fallback = incident_service

    t_svc = TechnicianProfileService(repo, stub_incidents, event_bus)

    r_svc = SmartTechnicianRecommendationService(
        repo,
        stub_incidents,
        mock_llm,
    )

    a_svc = TechnicianAssignmentService(
        repo,
        stub_incidents,
        event_bus,
    )

    policy_repo = SQLAlchemySLAPolicyRepository(db_session)
    tracking_repo = SQLAlchemySLATrackingRepository(db_session)
    audit_repo = SQLAlchemyAuditLogRepository(db_session)
    notif_repo = SQLAlchemyNotificationRepository(db_session)

    s_svc = SLAService(policy_repo, tracking_repo, event_bus)
    aud_svc = AuditService(audit_repo)
    n_svc = NotificationService(notif_repo)

    # Override dependencies
    app.dependency_overrides[get_db_session] = lambda: db_session
    app.dependency_overrides[get_technician_repository] = lambda: repo
    app.dependency_overrides[get_incident_service_boundary] = lambda: stub_incidents
    app.dependency_overrides[get_incident_service] = lambda: incident_service
    app.dependency_overrides[get_event_publisher] = lambda: event_bus
    app.dependency_overrides[get_llm_provider] = lambda: mock_llm
    app.dependency_overrides[get_technician_service] = lambda: t_svc
    app.dependency_overrides[get_recommendation_service] = lambda: r_svc
    app.dependency_overrides[get_assignment_service] = lambda: a_svc

    app.dependency_overrides[get_sla_policy_repository] = lambda: policy_repo
    app.dependency_overrides[get_sla_tracking_repository] = lambda: tracking_repo
    app.dependency_overrides[get_audit_log_repository] = lambda: audit_repo
    app.dependency_overrides[get_notification_repository] = lambda: notif_repo
    app.dependency_overrides[get_sla_service] = lambda: s_svc
    app.dependency_overrides[get_audit_service] = lambda: aud_svc
    app.dependency_overrides[get_notification_service] = lambda: n_svc

    default_actor_id = UUID("00000000-0000-0000-0000-000000000001")
    default_identity = UserIdentity(
        id=default_actor_id,
        username="test_admin",
        email="test_admin@example.com",
        full_name="Test Administrator",
        role=UserRole.ADMIN,
        is_active=True,
    )
    app.dependency_overrides[get_actor_identity] = lambda: default_identity
    app.dependency_overrides[get_actor_user_id] = lambda: default_actor_id

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
