"""
API tests for Member 1: Authentication, User Management, Service Catalog, and Incident Categories.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.infrastructure.database.models import (
    IncidentCategoryModel,
    ServiceModel,
    UserModel,
)
from app.shared.enums import IncidentCategory, UserRole


@pytest.fixture
def auth_headers_factory():
    """Helper to generate Authorization headers for any user and role."""
    def _create_headers(user_id, role: UserRole = UserRole.EMPLOYEE):
        token = create_access_token({"sub": str(user_id), "role": role.value})
        return {"Authorization": f"Bearer {token}"}
    return _create_headers


@pytest.mark.asyncio
async def test_user_registration_and_login(async_client: AsyncClient):
    # 1. Register a new user
    reg_resp = await async_client.post(
        "/api/v1/auth/register",
        json={
            "username": "johndoe",
            "email": "johndoe@example.com",
            "fullName": "John Doe",
            "password": "StrongPassword123!",
        },
    )
    assert reg_resp.status_code == 201, reg_resp.text
    user_data = reg_resp.json()
    assert user_data["username"] == "johndoe"
    assert user_data["email"] == "johndoe@example.com"
    assert user_data["role"] == "EMPLOYEE"
    assert user_data["isActive"] is True

    # 2. Duplicate registration fails
    dup_resp = await async_client.post(
        "/api/v1/auth/register",
        json={
            "username": "johndoe",
            "email": "another@example.com",
            "fullName": "John Duplicate",
            "password": "StrongPassword123!",
        },
    )
    assert dup_resp.status_code == 409

    # 3. Login with correct credentials
    login_resp = await async_client.post(
        "/api/v1/auth/login",
        data={"username": "johndoe", "password": "StrongPassword123!"},
    )
    assert login_resp.status_code == 200, login_resp.text
    tokens = login_resp.json()
    assert "accessToken" in tokens
    token = tokens["accessToken"]

    # 4. Access /me endpoint
    me_resp = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["username"] == "johndoe"
    assert me_data["fullName"] == "John Doe"

    # 5. Login with invalid password fails
    bad_login = await async_client.post(
        "/api/v1/auth/login",
        data={"username": "johndoe", "password": "WrongPassword!"},
    )
    assert bad_login.status_code == 401


@pytest.mark.asyncio
async def test_admin_user_management(
    db_session: AsyncSession,
    async_client: AsyncClient,
    auth_headers_factory,
):
    # Pre-seed an admin and an employee in database
    admin = UserModel(
        username="admin_user",
        email="admin@iitsm.local",
        full_name="Admin Boss",
        password_hash="fakehash",
        role=UserRole.ADMIN,
        is_active=True,
    )
    employee = UserModel(
        username="worker_bee",
        email="worker@iitsm.local",
        full_name="Worker Bee",
        password_hash="fakehash",
        role=UserRole.EMPLOYEE,
        is_active=True,
    )
    db_session.add_all([admin, employee])
    await db_session.flush()

    admin_headers = auth_headers_factory(admin.id, UserRole.ADMIN)
    employee_headers = auth_headers_factory(employee.id, UserRole.EMPLOYEE)

    # Employee cannot access admin user list
    resp = await async_client.get("/api/v1/users", headers=employee_headers)
    assert resp.status_code == 403

    # Admin can list users
    resp = await async_client.get("/api/v1/users", headers=admin_headers)
    assert resp.status_code == 200
    users = resp.json()
    assert len(users) >= 2

    # Admin summary
    resp = await async_client.get("/api/v1/users/summary", headers=admin_headers)
    assert resp.status_code == 200
    summary = resp.json()
    assert summary["totalUsers"] >= 2
    assert summary["usersByRole"]["ADMIN"] >= 1

    # Update employee role to TECHNICIAN
    resp = await async_client.patch(
        f"/api/v1/users/{employee.id}",
        headers=admin_headers,
        json={"role": "TECHNICIAN"},
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "TECHNICIAN"

    # Admin cannot deactivate own account
    resp = await async_client.delete(
        f"/api/v1/users/{admin.id}",
        headers=admin_headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_service_catalog_management(
    db_session: AsyncSession,
    async_client: AsyncClient,
    auth_headers_factory,
):
    admin = UserModel(
        username="admin_svc",
        email="adminsvc@iitsm.local",
        full_name="Admin Svc",
        password_hash="fakehash",
        role=UserRole.ADMIN,
        is_active=True,
    )
    employee = UserModel(
        username="emp_svc",
        email="empsvc@iitsm.local",
        full_name="Emp Svc",
        password_hash="fakehash",
        role=UserRole.EMPLOYEE,
        is_active=True,
    )
    db_session.add_all([admin, employee])
    await db_session.flush()

    admin_headers = auth_headers_factory(admin.id, UserRole.ADMIN)
    employee_headers = auth_headers_factory(employee.id, UserRole.EMPLOYEE)

    # 1. Create service as admin
    resp = await async_client.post(
        "/api/v1/services",
        headers=admin_headers,
        json={
            "name": "Corporate Email",
            "description": "Hosted email exchange",
            "businessCriticality": 4,
        },
    )
    assert resp.status_code == 201
    service_id = resp.json()["id"]

    # 2. List services as employee
    resp = await async_client.get("/api/v1/services", headers=employee_headers)
    assert resp.status_code == 200
    svcs = resp.json()
    assert any(s["name"] == "Corporate Email" for s in svcs)

    # 3. Update service
    resp = await async_client.patch(
        f"/api/v1/services/{service_id}",
        headers=admin_headers,
        json={"businessCriticality": 5},
    )
    assert resp.status_code == 200
    assert resp.json()["businessCriticality"] == 5

    # 4. Deactivate service
    resp = await async_client.delete(
        f"/api/v1/services/{service_id}",
        headers=admin_headers,
    )
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_incident_category_configuration(
    db_session: AsyncSession,
    async_client: AsyncClient,
    auth_headers_factory,
):
    admin = UserModel(
        username="admin_cat",
        email="admincat@iitsm.local",
        full_name="Admin Cat",
        password_hash="fakehash",
        role=UserRole.ADMIN,
        is_active=True,
    )
    employee = UserModel(
        username="emp_cat",
        email="empcat@iitsm.local",
        full_name="Emp Cat",
        password_hash="fakehash",
        role=UserRole.EMPLOYEE,
        is_active=True,
    )
    db_session.add_all([admin, employee])
    await db_session.flush()

    admin_headers = auth_headers_factory(admin.id, UserRole.ADMIN)
    employee_headers = auth_headers_factory(employee.id, UserRole.EMPLOYEE)

    # 1. Create category mapping
    resp = await async_client.post(
        "/api/v1/categories",
        headers=admin_headers,
        json={
            "category": "NETWORK",
            "description": "Network connectivity issues",
            "requiredSkill": "Network Routing",
        },
    )
    assert resp.status_code == 201
    cat_id = resp.json()["id"]
    assert resp.json()["requiredSkill"] == "Network Routing"

    # 2. Duplicate category rejected
    resp = await async_client.post(
        "/api/v1/categories",
        headers=admin_headers,
        json={
            "category": "NETWORK",
            "requiredSkill": "Cisco",
        },
    )
    assert resp.status_code == 409

    # 3. List categories
    resp = await async_client.get("/api/v1/categories", headers=employee_headers)
    assert resp.status_code == 200
    cats = resp.json()
    assert any(c["category"] == "NETWORK" for c in cats)

    # 4. Update category required skill
    resp = await async_client.patch(
        f"/api/v1/categories/{cat_id}",
        headers=admin_headers,
        json={"requiredSkill": "Advanced Routing"},
    )
    assert resp.status_code == 200
    assert resp.json()["requiredSkill"] == "Advanced Routing"


@pytest.mark.asyncio
async def test_reports_summary(
    db_session: AsyncSession,
    async_client: AsyncClient,
    auth_headers_factory,
):
    admin = UserModel(
        username="admin_rep",
        email="adminrep@iitsm.local",
        full_name="Admin Rep",
        password_hash="fakehash",
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add(admin)
    svc = ServiceModel(name="Core VPN", business_criticality=3, is_active=True)
    cat = IncidentCategoryModel(
        category=IncidentCategory.SECURITY,
        required_skill="Firewall",
        is_active=True,
    )
    db_session.add_all([svc, cat])
    await db_session.flush()

    admin_headers = auth_headers_factory(admin.id, UserRole.ADMIN)

    resp = await async_client.get("/api/v1/reports/summary", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["users"]["total"] >= 1
    assert data["services"]["total"] >= 1
    assert data["categories"]["total"] >= 1
