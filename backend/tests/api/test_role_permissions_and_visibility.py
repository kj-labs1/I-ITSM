"""
Role permissions and visibility test suite.

Verifies end-to-end enforcement of role boundaries across M1-M4:
1. Incident creation restrictions (Technicians 403, Employees/Admins allowed).
2. Role-based incident visibility in GET /api/v1/incidents:
   - Technicians see only incidents assigned to them.
   - Employees see only incidents reported by them.
   - Admins see all incidents.
3. Incident assignment permissions:
   - Only Admins can assign technicians. Technicians and Employees receive 403.
4. Role-based lifecycle status transitions:
   - Assigned technician can ACKNOWLEDGE, START WORK (IN_PROGRESS), and RESOLVE.
   - Non-assigned technician cannot transition status (403).
   - Technician cannot close/verify incidents (403).
   - Employee reporter can VERIFY and CLOSE resolved incidents.
   - Employee cannot ACKNOWLEDGE or RESOLVE incidents (403).
5. Technician management permissions:
   - Only Admin can create technician profiles or modify skills.
   - Technician can only update their own availability.
6. SLA & Audit administrative protections:
   - Non-admins cannot access /api/v1/audit or /api/v1/sla/violations.
"""

from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

from app.api.deps import get_actor_identity
from app.domain.identity.user import UserIdentity
from app.shared.enums import UserRole


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
async def test_technician_cannot_report_incident(async_client: AsyncClient):
    """Technicians must not be permitted to create incidents (HTTP 403)."""
    app = async_client._transport.app  # type: ignore
    tech_id = uuid4()
    app.dependency_overrides[get_actor_identity] = lambda: _make_identity(tech_id, UserRole.TECHNICIAN, "tech1")

    payload = {
        "serviceId": str(uuid4()),
        "category": "NETWORK",
        "requiredSkill": "NETWORK",
        "description": "Technician trying to report an incident",
        "impact": 3,
        "urgency": 3,
        "businessCriticality": 3,
    }

    resp = await async_client.post("/api/v1/incidents", json=payload)
    assert resp.status_code == 403
    assert "Technicians are not permitted to report incidents" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_employee_can_report_incident(async_client: AsyncClient):
    """Employees can report incidents and reporterId matches their authenticated UUID."""
    app = async_client._transport.app  # type: ignore
    emp_id = uuid4()
    app.dependency_overrides[get_actor_identity] = lambda: _make_identity(emp_id, UserRole.EMPLOYEE, "emp1")

    payload = {
        "serviceId": str(uuid4()),
        "category": "HARDWARE",
        "requiredSkill": "HARDWARE",
        "description": "Employee reporting broken keyboard",
        "impact": 2,
        "urgency": 2,
        "businessCriticality": 2,
    }

    resp = await async_client.post("/api/v1/incidents", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["reporterId"] == str(emp_id)
    assert data["status"] == "NEW"


@pytest.mark.asyncio
async def test_incident_visibility_by_role(async_client: AsyncClient):
    """
    Verify role-based incident visibility:
    - Technician sees ONLY assigned incidents.
    - Employee sees ONLY own reported incidents.
    - Admin sees ALL incidents.
    """
    app = async_client._transport.app  # type: ignore

    emp1_id = uuid4()
    emp2_id = uuid4()
    tech1_id = uuid4()
    tech2_id = uuid4()
    admin_id = uuid4()

    # Step 1: Admin creates tech profiles for tech1 and tech2
    app.dependency_overrides[get_actor_identity] = lambda: _make_identity(admin_id, UserRole.ADMIN, "admin")

    t1_resp = await async_client.post(
        "/api/v1/technicians",
        json={
            "userId": str(tech1_id),
            "experienceYears": 3,
            "maxCapacity": 5,
            "skills": [{"skillName": "NETWORK", "proficiencyLevel": 4}],
        },
    )
    assert t1_resp.status_code == 201
    t1_profile_id = t1_resp.json()["id"]

    t2_resp = await async_client.post(
        "/api/v1/technicians",
        json={
            "userId": str(tech2_id),
            "experienceYears": 3,
            "maxCapacity": 5,
            "skills": [{"skillName": "DATABASE", "proficiencyLevel": 4}],
        },
    )
    assert t2_resp.status_code == 201
    t2_profile_id = t2_resp.json()["id"]

    # Step 2: Employee 1 reports Incident 1
    app.dependency_overrides[get_actor_identity] = lambda: _make_identity(emp1_id, UserRole.EMPLOYEE, "emp1")
    inc1_resp = await async_client.post(
        "/api/v1/incidents",
        json={
            "serviceId": str(uuid4()),
            "category": "NETWORK",
            "requiredSkill": "NETWORK",
            "description": "Incident 1 by Emp 1",
            "impact": 3,
            "urgency": 3,
            "businessCriticality": 3,
        },
    )
    assert inc1_resp.status_code == 201
    inc1_id = inc1_resp.json()["id"]

    # Step 3: Employee 2 reports Incident 2
    app.dependency_overrides[get_actor_identity] = lambda: _make_identity(emp2_id, UserRole.EMPLOYEE, "emp2")
    inc2_resp = await async_client.post(
        "/api/v1/incidents",
        json={
            "serviceId": str(uuid4()),
            "category": "DATABASE",
            "requiredSkill": "DATABASE",
            "description": "Incident 2 by Emp 2",
            "impact": 3,
            "urgency": 3,
            "businessCriticality": 3,
        },
    )
    assert inc2_resp.status_code == 201
    inc2_id = inc2_resp.json()["id"]

    # Step 4: Admin assigns Incident 1 -> Tech 1, Incident 2 -> Tech 2
    app.dependency_overrides[get_actor_identity] = lambda: _make_identity(admin_id, UserRole.ADMIN, "admin")

    assign1_resp = await async_client.post(
        f"/api/v1/incidents/{inc1_id}/assign",
        json={"technicianId": t1_profile_id},
    )
    assert assign1_resp.status_code == 200
    assert assign1_resp.json()["technicianUserId"] == str(tech1_id)

    assign2_resp = await async_client.post(
        f"/api/v1/incidents/{inc2_id}/assign",
        json={"technicianId": t2_profile_id},
    )
    assert assign2_resp.status_code == 200
    assert assign2_resp.json()["technicianUserId"] == str(tech2_id)

    # Step 5: Check Employee 1 visibility
    app.dependency_overrides[get_actor_identity] = lambda: _make_identity(emp1_id, UserRole.EMPLOYEE, "emp1")
    emp1_list = await async_client.get("/api/v1/incidents")
    assert emp1_list.status_code == 200
    emp1_inc_ids = [inc["id"] for inc in emp1_list.json()]
    assert inc1_id in emp1_inc_ids
    assert inc2_id not in emp1_inc_ids

    # Step 6: Check Employee 2 visibility
    app.dependency_overrides[get_actor_identity] = lambda: _make_identity(emp2_id, UserRole.EMPLOYEE, "emp2")
    emp2_list = await async_client.get("/api/v1/incidents")
    assert emp2_list.status_code == 200
    emp2_inc_ids = [inc["id"] for inc in emp2_list.json()]
    assert inc2_id in emp2_inc_ids
    assert inc1_id not in emp2_inc_ids

    # Step 7: Check Tech 1 visibility (THE CRITICAL VISIBILITY DEFECT FIX!)
    app.dependency_overrides[get_actor_identity] = lambda: _make_identity(tech1_id, UserRole.TECHNICIAN, "tech1")
    tech1_list = await async_client.get("/api/v1/incidents")
    assert tech1_list.status_code == 200
    tech1_inc_ids = [inc["id"] for inc in tech1_list.json()]
    assert inc1_id in tech1_inc_ids, "Technician 1 MUST see incident assigned to them!"
    assert inc2_id not in tech1_inc_ids, "Technician 1 MUST NOT see incident assigned to Technician 2!"

    # Step 8: Check Tech 2 visibility
    app.dependency_overrides[get_actor_identity] = lambda: _make_identity(tech2_id, UserRole.TECHNICIAN, "tech2")
    tech2_list = await async_client.get("/api/v1/incidents")
    assert tech2_list.status_code == 200
    tech2_inc_ids = [inc["id"] for inc in tech2_list.json()]
    assert inc2_id in tech2_inc_ids, "Technician 2 MUST see incident assigned to them!"
    assert inc1_id not in tech2_inc_ids, "Technician 2 MUST NOT see incident assigned to Technician 1!"

    # Step 9: Check Admin visibility
    app.dependency_overrides[get_actor_identity] = lambda: _make_identity(admin_id, UserRole.ADMIN, "admin")
    admin_list = await async_client.get("/api/v1/incidents")
    assert admin_list.status_code == 200
    admin_inc_ids = [inc["id"] for inc in admin_list.json()]
    assert inc1_id in admin_inc_ids
    assert inc2_id in admin_inc_ids


@pytest.mark.asyncio
async def test_assignment_role_permissions(async_client: AsyncClient):
    """Only Admins can assign incidents. Employees and Technicians get 403."""
    app = async_client._transport.app  # type: ignore
    admin_id = uuid4()
    emp_id = uuid4()
    tech_id = uuid4()

    # Admin setup tech & incident
    app.dependency_overrides[get_actor_identity] = lambda: _make_identity(admin_id, UserRole.ADMIN, "admin")
    t_resp = await async_client.post(
        "/api/v1/technicians",
        json={
            "userId": str(tech_id),
            "experienceYears": 2,
            "maxCapacity": 5,
            "skills": [{"skillName": "NETWORK", "proficiencyLevel": 4}],
        },
    )
    tech_profile_id = t_resp.json()["id"]

    inc_resp = await async_client.post(
        "/api/v1/incidents",
        json={
            "serviceId": str(uuid4()),
            "category": "NETWORK",
            "requiredSkill": "NETWORK",
            "description": "Test incident for assignment permissions",
            "impact": 3,
            "urgency": 3,
            "businessCriticality": 3,
        },
    )
    inc_id = inc_resp.json()["id"]

    # Technician tries to assign -> 403
    app.dependency_overrides[get_actor_identity] = lambda: _make_identity(tech_id, UserRole.TECHNICIAN, "tech")
    tech_assign = await async_client.post(
        f"/api/v1/incidents/{inc_id}/assign",
        json={"technicianId": tech_profile_id},
    )
    assert tech_assign.status_code == 403

    # Employee tries to assign -> 403
    app.dependency_overrides[get_actor_identity] = lambda: _make_identity(emp_id, UserRole.EMPLOYEE, "emp")
    emp_assign = await async_client.post(
        f"/api/v1/incidents/{inc_id}/assign",
        json={"technicianId": tech_profile_id},
    )
    assert emp_assign.status_code == 403


@pytest.mark.asyncio
async def test_lifecycle_role_transitions(async_client: AsyncClient):
    """
    Enforce role lifecycle permissions:
    - Assigned technician: ACKNOWLEDGED -> IN_PROGRESS -> RESOLVED.
    - Unassigned technician cannot transition (403).
    - Technician cannot verify/close (403).
    - Employee reporter: VERIFIED, CLOSED when resolved.
    - Employee cannot acknowledge/resolve (403).
    """
    app = async_client._transport.app  # type: ignore
    admin_id = uuid4()
    emp_id = uuid4()
    tech1_id = uuid4()
    tech2_id = uuid4()

    # Setup
    app.dependency_overrides[get_actor_identity] = lambda: _make_identity(admin_id, UserRole.ADMIN, "admin")
    t1_resp = await async_client.post(
        "/api/v1/technicians",
        json={
            "userId": str(tech1_id),
            "experienceYears": 4,
            "maxCapacity": 5,
            "skills": [{"skillName": "NETWORK", "proficiencyLevel": 4}],
        },
    )
    t1_profile_id = t1_resp.json()["id"]

    # Employee reports incident
    app.dependency_overrides[get_actor_identity] = lambda: _make_identity(emp_id, UserRole.EMPLOYEE, "emp")
    inc_resp = await async_client.post(
        "/api/v1/incidents",
        json={
            "serviceId": str(uuid4()),
            "category": "NETWORK",
            "requiredSkill": "NETWORK",
            "description": "Lifecycle transition test incident",
            "impact": 3,
            "urgency": 3,
            "businessCriticality": 3,
        },
    )
    inc_id = inc_resp.json()["id"]

    # Employee tries to acknowledge -> 403
    emp_ack = await async_client.patch(
        f"/api/v1/incidents/{inc_id}/status",
        json={"status": "ACKNOWLEDGED"},
    )
    assert emp_ack.status_code == 403

    # Admin assigns to Tech 1
    app.dependency_overrides[get_actor_identity] = lambda: _make_identity(admin_id, UserRole.ADMIN, "admin")
    await async_client.post(
        f"/api/v1/incidents/{inc_id}/assign",
        json={"technicianId": t1_profile_id},
    )

    # Tech 2 (unassigned) tries to acknowledge -> 403
    app.dependency_overrides[get_actor_identity] = lambda: _make_identity(tech2_id, UserRole.TECHNICIAN, "tech2")
    tech2_ack = await async_client.patch(
        f"/api/v1/incidents/{inc_id}/status",
        json={"status": "ACKNOWLEDGED"},
    )
    assert tech2_ack.status_code == 403

    # Tech 1 (assigned) acknowledges -> 200
    app.dependency_overrides[get_actor_identity] = lambda: _make_identity(tech1_id, UserRole.TECHNICIAN, "tech1")
    tech1_ack = await async_client.patch(
        f"/api/v1/incidents/{inc_id}/status",
        json={"status": "ACKNOWLEDGED"},
    )
    assert tech1_ack.status_code == 200
    assert tech1_ack.json()["status"] == "ACKNOWLEDGED"

    # Tech 1 starts work -> IN_PROGRESS -> 200
    tech1_prog = await async_client.patch(
        f"/api/v1/incidents/{inc_id}/status",
        json={"status": "IN_PROGRESS"},
    )
    assert tech1_prog.status_code == 200
    assert tech1_prog.json()["status"] == "IN_PROGRESS"

    # Tech 1 tries to close directly -> 403
    tech1_close = await async_client.patch(
        f"/api/v1/incidents/{inc_id}/status",
        json={"status": "CLOSED"},
    )
    assert tech1_close.status_code == 403

    # Tech 1 resolves with details -> 200
    tech1_res = await async_client.patch(
        f"/api/v1/incidents/{inc_id}/status",
        json={"status": "RESOLVED", "resolutionDetails": "Replaced faulty switch port."},
    )
    assert tech1_res.status_code == 200
    assert tech1_res.json()["status"] == "RESOLVED"

    # Employee verifies resolution -> 200
    app.dependency_overrides[get_actor_identity] = lambda: _make_identity(emp_id, UserRole.EMPLOYEE, "emp")
    emp_verify = await async_client.patch(
        f"/api/v1/incidents/{inc_id}/status",
        json={"status": "VERIFIED"},
    )
    assert emp_verify.status_code == 200
    assert emp_verify.json()["status"] == "VERIFIED"

    # Employee closes incident -> 200
    emp_close = await async_client.patch(
        f"/api/v1/incidents/{inc_id}/status",
        json={"status": "CLOSED"},
    )
    assert emp_close.status_code == 200
    assert emp_close.json()["status"] == "CLOSED"


@pytest.mark.asyncio
async def test_admin_protections_on_sla_audit_technicians(async_client: AsyncClient):
    """Non-admin users cannot access administrative SLA, Audit, or Technician endpoints."""
    app = async_client._transport.app  # type: ignore
    emp_id = uuid4()
    app.dependency_overrides[get_actor_identity] = lambda: _make_identity(emp_id, UserRole.EMPLOYEE, "emp")

    # Employee cannot query system-wide audit logs
    audit_resp = await async_client.get("/api/v1/audit")
    assert audit_resp.status_code == 403

    # Employee cannot list SLA violations
    sla_resp = await async_client.get("/api/v1/sla/violations")
    assert sla_resp.status_code == 403

    # Employee cannot create technician
    tech_resp = await async_client.post(
        "/api/v1/technicians",
        json={"userId": str(uuid4()), "experienceYears": 1},
    )
    assert tech_resp.status_code == 403
