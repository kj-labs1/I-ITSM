"""
Pytest configuration and shared test fixtures.

Provides:
- In-memory async SQLite engine & session for isolated repository and API tests.
- FastAPI test client (`httpx.AsyncClient` with `ASGITransport`).
- Pre-configured test doubles: `MockLLMProvider`, `StubIncidentService`, `InProcessEventBus`.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from app.application.incident.service import IncidentApplicationService

from app.infrastructure.repositories.incident_repository import (
    SQLAlchemyIncidentRepository,
)

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.api.deps import (
    get_assignment_service,
    get_db_session,
    get_event_publisher,
    get_incident_service_boundary,
    get_llm_provider,
    get_recommendation_service,
    get_technician_repository,
    get_technician_service,
    get_incident_service
)
from app.application.assignment.service import (
    SmartTechnicianRecommendationService,
    TechnicianAssignmentService,
)
from app.application.technician.service import TechnicianProfileService
import app.infrastructure.database.incident_models
from app.infrastructure.database.base import Base
from app.infrastructure.events.event_bus import InProcessEventBus
from app.infrastructure.repositories.technician_repository import (
    SQLAlchemyTechnicianRepository,
)
from app.integrations.incidents.stub_incident_service import StubIncidentService
from app.integrations.llm.mock_provider import MockLLMProvider
from app.main import create_app


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

    # Create scoped test services
    repo = SQLAlchemyTechnicianRepository(db_session)

    incident_repo = SQLAlchemyIncidentRepository(db_session)

    incident_service = IncidentApplicationService(
        repository=incident_repo,
        event_publisher=event_bus,
    )

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

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
