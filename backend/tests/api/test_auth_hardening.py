"""
Tests for Authentication Hardening:
- Rejection of missing, malformed, expired, and invalid JWT tokens with 401.
- Verification that actor_id and reporter_id are strictly derived from JWT claims in production.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_db_session,
    get_incident_repository,
    get_incident_service,
)
from app.application.incident.service import IncidentApplicationService
from app.core.config import get_settings
from app.core.security import create_access_token
from app.infrastructure.database.models import ServiceModel, UserModel
from app.infrastructure.events.event_bus import InProcessEventBus
from app.infrastructure.repositories.incident_repository import (
    SQLAlchemyIncidentRepository,
)
from app.main import create_app
from app.shared.enums import UserRole


@pytest.mark.asyncio
async def test_unauthenticated_request_rejected_with_401():
    """Verify that calling production protected endpoints without headers returns 401."""
    app = create_app()

    async with (
        ASGITransport(app=app) as transport,
        AsyncClient(transport=transport, base_url="http://test") as client,
    ):
            resp = await client.get("/api/v1/auth/me")
            assert resp.status_code == 401
            assert "Not authenticated" in resp.text or "headers" in resp.headers.get("www-authenticate", "")

            resp = await client.post("/api/v1/incidents", json={})
            assert resp.status_code == 401


@pytest.mark.asyncio
async def test_invalid_and_expired_tokens_return_401():
    """Verify malformed, expired, and invalid-signature JWT tokens are rejected with 401."""
    app = create_app()
    settings = get_settings()

    async with (
        ASGITransport(app=app) as transport,
        AsyncClient(transport=transport, base_url="http://test") as client,
    ):
            # 1. Malformed token
            resp = await client.get(
                "/api/v1/auth/me",
                headers={"Authorization": "Bearer not-a-valid-token-at-all"},
            )
            assert resp.status_code == 401

            # 2. Expired token
            expired_claims = {
                "sub": str(uuid4()),
                "role": UserRole.EMPLOYEE.value,
                "exp": datetime.now(UTC) - timedelta(hours=2),
            }
            expired_token = jwt.encode(
                expired_claims,
                settings.JWT_SECRET_KEY,
                algorithm=settings.JWT_ALGORITHM,
            )
            resp = await client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {expired_token}"},
            )
            assert resp.status_code == 401

            # 3. Invalid signature (signed with wrong secret)
            bad_signature_token = jwt.encode(
                {"sub": str(uuid4()), "role": "EMPLOYEE"},
                "completely-wrong-secret-key",
                algorithm="HS256",
            )
            resp = await client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {bad_signature_token}"},
            )
            assert resp.status_code == 401


@pytest.mark.asyncio
async def test_production_reporter_id_derived_from_jwt(db_session: AsyncSession):
    """Verify that reporterId in production is authoritatively derived from the JWT."""
    app = create_app()
    event_bus = InProcessEventBus()

    # Pre-seed user and service
    user = UserModel(
        username="jwt_reporter",
        email="reporter@iitsm.local",
        full_name="JWT Reporter",
        password_hash="fakehash",
        role=UserRole.EMPLOYEE,
        is_active=True,
    )
    svc = ServiceModel(name="JWT Test Service", business_criticality=4, is_active=True)
    db_session.add_all([user, svc])
    await db_session.flush()

    # Create real JWT token for this user
    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    headers = {"Authorization": f"Bearer {token}"}

    # Wire database session without mocking get_actor_user_id
    incident_repo = SQLAlchemyIncidentRepository(db_session)
    incident_svc = IncidentApplicationService(incident_repo, event_bus)

    app.dependency_overrides[get_db_session] = lambda: db_session
    app.dependency_overrides[get_incident_repository] = lambda: incident_repo
    app.dependency_overrides[get_incident_service] = lambda: incident_svc

    async with (
        ASGITransport(app=app) as transport,
        AsyncClient(transport=transport, base_url="http://test") as client,
    ):
            resp = await client.post(
                "/api/v1/incidents",
                headers=headers,
                json={
                    "title": "Incident with authentic reporter",
                    "description": "Ensuring reporter is derived from token sub",
                    "category": "SOFTWARE",
                    "impact": 3,
                    "urgency": 3,
                    "businessCriticality": 4,
                    "requiredSkill": "Python",
                    "serviceId": str(svc.id),
                    "reporterId": str(uuid4()),  # Attempt to spoof reporterId in payload
                },
            )
            assert resp.status_code == 201, resp.text
            created_incident = resp.json()

            # The system must use user.id from the JWT sub claim, NOT the spoofed reporterId from body!
            assert created_incident["reporterId"] == str(user.id)
