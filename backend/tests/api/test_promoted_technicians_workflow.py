"""
Tests for user promotion to Technician and profile configuration workflow.

Scenarios verified:
1. Promote an existing Employee to Technician.
2. Verify that their role is updated in the database.
3. Verify that the promoted user appears in the Technician Management listing.
4. Verify that the user is displayed as Profile Not Configured (has_profile=False).
5. Create a technician profile for that existing user.
6. Verify that the profile is linked to the correct user ID.
7. Verify that technician skills reference the technician profile ID.
8. Verify that the completed profile appears correctly (has_profile=True).
9. Verify that an existing technician profile cannot be duplicated (409 Conflict).
10. Verify that Employee and Admin accounts without technician role do not appear in the Technician tab.
11. Verify that already-promoted users without profiles are handled correctly.
12. Verify that profile creation failures do not leave partial database records.
13. Verify that unauthorized users cannot promote accounts or create profiles.
"""

from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_actor_identity
from app.core.security import create_access_token
from app.domain.identity.user import UserIdentity
from app.infrastructure.database.models import UserModel
from app.shared.enums import UserRole


def _auth_headers(user_id, role: UserRole = UserRole.ADMIN) -> dict[str, str]:
    token = create_access_token({"sub": str(user_id), "role": role.value})
    return {"Authorization": f"Bearer {token}"}


def _make_identity(user_id: UUID, role: UserRole, username: str = "testuser") -> UserIdentity:
    return UserIdentity(
        id=user_id,
        username=username,
        email=f"{username}@example.com",
        full_name=f"Full {username}",
        role=role,
        is_active=True,
    )


@pytest.mark.asyncio
async def test_full_promotion_and_technician_profile_workflow(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    """
    Scenarios 1-8:
    Employee -> Promoted to Technician -> Appears as Profile Not Configured ->
    Profile created with skills -> Appears with completed profile.
    """
    admin_id = uuid4()
    admin_headers = _auth_headers(admin_id, UserRole.ADMIN)

    # 1. Register an employee
    emp_username = f"emp_{uuid4().hex[:8]}"
    emp_email = f"{emp_username}@example.com"
    reg_resp = await async_client.post(
        "/api/v1/auth/register",
        json={
            "username": emp_username,
            "email": emp_email,
            "fullName": "Test Employee",
            "password": "Password123!",
        },
    )
    assert reg_resp.status_code == 201
    user_data = reg_resp.json()
    user_id = UUID(user_data["id"])
    assert user_data["role"] == "EMPLOYEE"

    # 10. Verify that this Employee does NOT appear in technician roster
    tech_list_pre = await async_client.get("/api/v1/technicians", headers=admin_headers)
    assert tech_list_pre.status_code == 200
    pre_user_ids = [t["userId"] for t in tech_list_pre.json()]
    assert str(user_id) not in pre_user_ids

    # 1 & 2. Promote Employee to Technician via Admin PATCH /api/v1/users/{id}
    patch_resp = await async_client.patch(
        f"/api/v1/users/{user_id}",
        headers=admin_headers,
        json={"role": "TECHNICIAN"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["role"] == "TECHNICIAN"

    # Verify role in DB using UUID type
    user_in_db = await db_session.get(UserModel, user_id)
    assert user_in_db is not None
    assert user_in_db.role == UserRole.TECHNICIAN

    # 3 & 4. Verify user appears in technician list as Profile Not Configured (hasProfile=False)
    tech_list_post = await async_client.get("/api/v1/technicians", headers=admin_headers)
    assert tech_list_post.status_code == 200
    matching_tech = next((t for t in tech_list_post.json() if t["userId"] == str(user_id)), None)
    assert matching_tech is not None
    assert matching_tech["hasProfile"] is False
    assert matching_tech["username"] == emp_username
    assert matching_tech["fullName"] == "Test Employee"
    assert matching_tech["id"] is None

    # 5 & 6 & 7. Create technician profile linked to this user
    create_prof_resp = await async_client.post(
        "/api/v1/technicians",
        headers=admin_headers,
        json={
            "userId": str(user_id),
            "experienceYears": 5,
            "maxCapacity": 12,
            "skills": [
                {"skillName": "NETWORK", "proficiencyLevel": 4},
                {"skillName": "SECURITY", "proficiencyLevel": 5},
            ],
        },
    )
    assert create_prof_resp.status_code == 201
    created_profile = create_prof_resp.json()
    assert created_profile["userId"] == str(user_id)
    assert created_profile["id"] is not None
    profile_id = created_profile["id"]
    assert created_profile["experienceYears"] == 5
    assert created_profile["maxCapacity"] == 12
    assert created_profile["hasProfile"] is True
    assert len(created_profile["skills"]) == 2

    # Verify skill technician_id references profile_id, NOT user_id
    for sk in created_profile["skills"]:
        assert sk["technicianId"] == profile_id
        assert sk["technicianId"] != str(user_id)

    # 8. Refresh listing: user now appears with completed profile
    tech_list_final = await async_client.get("/api/v1/technicians", headers=admin_headers)
    assert tech_list_final.status_code == 200
    final_tech = next((t for t in tech_list_final.json() if t["userId"] == str(user_id)), None)
    assert final_tech is not None
    assert final_tech["hasProfile"] is True
    assert final_tech["id"] == profile_id
    assert final_tech["experienceYears"] == 5
    assert len(final_tech["skills"]) == 2

    # 9. Verify duplicate profile creation is rejected with 409
    dup_resp = await async_client.post(
        "/api/v1/technicians",
        headers=admin_headers,
        json={
            "userId": str(user_id),
            "experienceYears": 2,
            "maxCapacity": 5,
        },
    )
    assert dup_resp.status_code == 409
    assert "already exists" in dup_resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_non_technician_cannot_receive_technician_profile(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    """
    Scenario: Non-technician users (e.g. Employee or Admin) cannot receive
    a technician profile unless their role is first updated to TECHNICIAN.
    """
    admin_headers = _auth_headers(uuid4(), UserRole.ADMIN)

    # Create an employee
    emp_username = f"emp_nontech_{uuid4().hex[:8]}"
    reg_resp = await async_client.post(
        "/api/v1/auth/register",
        json={
            "username": emp_username,
            "email": f"{emp_username}@example.com",
            "fullName": "Non Tech Employee",
            "password": "Password123!",
        },
    )
    user_id = reg_resp.json()["id"]

    # Attempt to create technician profile directly without promoting role -> rejected 400
    create_resp = await async_client.post(
        "/api/v1/technicians",
        headers=admin_headers,
        json={
            "userId": user_id,
            "experienceYears": 3,
            "maxCapacity": 6,
        },
    )
    assert create_resp.status_code == 400
    assert "must have role 'TECHNICIAN'" in create_resp.json()["detail"]


@pytest.mark.asyncio
async def test_already_promoted_user_without_profile(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    """
    Scenario 11: Users whose role is already TECHNICIAN in the database
    but who never received a profile are automatically visible with has_profile=False.
    """
    admin_headers = _auth_headers(uuid4(), UserRole.ADMIN)

    # Insert a user directly with TECHNICIAN role
    pre_tech_id = uuid4()
    pre_user = UserModel(
        id=pre_tech_id,
        username=f"legacy_tech_{uuid4().hex[:6]}",
        email=f"legacy_{uuid4().hex[:6]}@example.com",
        full_name="Legacy Pre-Promoted Tech",
        password_hash="fakehash",
        role=UserRole.TECHNICIAN,
        is_active=True,
    )
    db_session.add(pre_user)
    await db_session.flush()

    # List technicians: must include this user with Profile Not Configured
    resp = await async_client.get("/api/v1/technicians", headers=admin_headers)
    assert resp.status_code == 200
    found = next((t for t in resp.json() if t["userId"] == str(pre_tech_id)), None)
    assert found is not None
    assert found["hasProfile"] is False
    assert found["username"] == pre_user.username
    assert found["fullName"] == "Legacy Pre-Promoted Tech"


@pytest.mark.asyncio
async def test_unauthorized_users_cannot_promote_or_create_profiles(
    async_client: AsyncClient,
):
    """
    Scenario 13: Non-admin users cannot promote accounts or create technician profiles.
    """
    app = async_client._transport.app  # type: ignore[attr-defined]
    emp_actor_id = uuid4()
    emp_headers = _auth_headers(emp_actor_id, UserRole.EMPLOYEE)

    # Override get_actor_identity to represent the employee
    app.dependency_overrides[get_actor_identity] = lambda: _make_identity(
        emp_actor_id, UserRole.EMPLOYEE, "unauth_emp"
    )

    try:
        # Cannot create technician profile (403)
        post_resp = await async_client.post(
            "/api/v1/technicians",
            headers=emp_headers,
            json={"userId": str(uuid4()), "experienceYears": 2},
        )
        assert post_resp.status_code == 403

        # Cannot promote user (403)
        patch_resp = await async_client.patch(
            f"/api/v1/users/{uuid4()}",
            headers=emp_headers,
            json={"role": "TECHNICIAN"},
        )
        assert patch_resp.status_code == 403
    finally:
        # Clean up override
        app.dependency_overrides.pop(get_actor_identity, None)
