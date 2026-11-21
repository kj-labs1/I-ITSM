"""
Automated test suite for:
- Task 1: Incident ID Consistency (database UUID vs human-readable code).
- Task 2: Technician User ID Assignment (assigning via user_id).
- Task 3: Incident Archiving (soft-archive for closed incidents, admin-only).
- Task 4: Duplicate Incident Merging (merging duplicates into primary, admin-only).
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


def _make_incident_payload():
    return {
        "serviceId": str(uuid4()),
        "category": "NETWORK",
        "requiredSkill": "Network Routing",
        "description": "Core switch packet loss in data center rack 4",
        "impact": 4,
        "urgency": 4,
        "businessCriticality": 4,
    }


# ==============================================================================
# TASK 1: INCIDENT ID CONSISTENCY
# ==============================================================================


@pytest.mark.asyncio
async def test_incident_id_consistency_lifecycle(async_client: AsyncClient):
    """Verify backend generates canonical database UUID and keeps it consistent across operations."""
    # 1. Create incident
    create_resp = await async_client.post("/api/v1/incidents", json=_make_incident_payload())
    assert create_resp.status_code == 201
    created_data = create_resp.json()

    # Primary key UUID
    canonical_id = created_data["id"]
    incident_code = created_data["incidentCode"]

    # Canonical ID must be a valid UUID v4 string
    parsed_uuid = UUID(canonical_id)
    assert str(parsed_uuid) == canonical_id
    assert incident_code.startswith("INC-")
    assert canonical_id != incident_code

    # 2. Retrieve by canonical ID
    get_resp = await async_client.get(f"/api/v1/incidents/{canonical_id}")
    assert get_resp.status_code == 200
    get_data = get_resp.json()
    assert get_data["id"] == canonical_id
    assert get_data["incidentCode"] == incident_code

    # 3. Query list with incidentId filter
    list_resp = await async_client.get(f"/api/v1/incidents?incidentId={canonical_id}")
    assert list_resp.status_code == 200
    items = list_resp.json()
    assert len(items) == 1
    assert items[0]["id"] == canonical_id

    # 4. Update using canonical ID
    patch_resp = await async_client.patch(
        f"/api/v1/incidents/{canonical_id}",
        json={"impact": 5, "urgency": 5},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["id"] == canonical_id
    assert patch_resp.json()["impact"] == 5


# ==============================================================================
# TASK 2: TECHNICIAN USER ID ASSIGNMENT
# ==============================================================================


@pytest.mark.asyncio
async def test_assignment_uses_technician_user_id(async_client: AsyncClient):
    """Verify technician assignment accepts and records user_id, not profile_id."""
    # 1. Create a technician profile where user_id != profile_id
    tech_user_id = uuid4()
    tech_create_resp = await async_client.post(
        "/api/v1/technicians",
        json={
            "userId": str(tech_user_id),
            "maxCapacity": 5,
            "skills": [
                {"skillName": "Network Routing", "proficiencyLevel": 4},
            ],
        },
    )
    assert tech_create_resp.status_code == 201
    tech_profile = tech_create_resp.json()
    profile_id = tech_profile["id"]

    assert str(tech_user_id) == tech_profile["userId"]
    assert profile_id != str(tech_user_id)

    # 2. Create an incident
    inc_resp = await async_client.post("/api/v1/incidents", json=_make_incident_payload())
    assert inc_resp.status_code == 201
    incident_id = inc_resp.json()["id"]

    # 3. Request recommendations and verify user_id is returned
    rec_resp = await async_client.get(
        f"/api/v1/technicians/recommendations?incidentId={incident_id}&strategy=SKILL_BASED"
    )
    assert rec_resp.status_code == 200
    rec_data = rec_resp.json()
    assert len(rec_data["recommendations"]) > 0

    first_rec = rec_data["recommendations"][0]
    # Check that recommendation exposes user_id matching the technician's user_id
    assert first_rec["userId"] == str(tech_user_id)
    assert first_rec["technicianUserId"] == str(tech_user_id)
    assert first_rec["technicianId"] == profile_id

    # 4. Assign using technician_user_id
    assign_resp = await async_client.post(
        f"/api/v1/incidents/{incident_id}/assign",
        json={
            "technicianUserId": str(tech_user_id),
            "strategyUsed": "MANUAL",
            "reason": "Direct assignment with User ID",
        },
    )
    assert assign_resp.status_code == 200
    assign_data = assign_resp.json()
    assert assign_data["userId"] == str(tech_user_id)
    assert assign_data["technicianUserId"] == str(tech_user_id)

    # 5. Check incident details: assigned_technician_id must equal technician's user_id
    inc_check = await async_client.get(f"/api/v1/incidents/{incident_id}")
    assert inc_check.status_code == 200
    assert inc_check.json()["assignedTechnicianId"] == str(tech_user_id)


# ==============================================================================
# TASK 3: INCIDENT ARCHIVING
# ==============================================================================


@pytest.mark.asyncio
async def test_incident_archiving_workflow(async_client: AsyncClient):
    """Verify archive endpoint enforces permissions, closed-status check, and list filtering."""
    app = async_client._transport.app  # type: ignore
    admin_id = UUID("00000000-0000-0000-0000-000000000001")
    emp_id = uuid4()

    # 1. Create incident as admin
    inc_resp = await async_client.post("/api/v1/incidents", json=_make_incident_payload())
    assert inc_resp.status_code == 201
    incident_id = inc_resp.json()["id"]

    # 2. Try to archive non-closed incident -> fails with 400
    archive_attempt = await async_client.patch(f"/api/v1/incidents/{incident_id}/archive")
    assert archive_attempt.status_code == 400
    assert "CLOSED" in archive_attempt.json()["message"]

    # 3. Employee attempts archive -> 403 Forbidden
    app.dependency_overrides[get_actor_identity] = lambda: _make_identity(emp_id, UserRole.EMPLOYEE, "emp1")
    emp_attempt = await async_client.patch(f"/api/v1/incidents/{incident_id}/archive")
    assert emp_attempt.status_code == 403

    # Switch back to admin
    app.dependency_overrides[get_actor_identity] = lambda: _make_identity(admin_id, UserRole.ADMIN, "test_admin")

    # 4. Transition incident to CLOSED through valid state machine:
    # NEW -> ASSIGNED -> ACKNOWLEDGED -> IN_PROGRESS -> RESOLVED -> VERIFIED -> CLOSED
    s1 = await async_client.patch(
        f"/api/v1/incidents/{incident_id}/status",
        json={"status": "ASSIGNED"},
    )
    assert s1.status_code == 200

    s2 = await async_client.patch(
        f"/api/v1/incidents/{incident_id}/status",
        json={"status": "ACKNOWLEDGED"},
    )
    assert s2.status_code == 200

    s3 = await async_client.patch(
        f"/api/v1/incidents/{incident_id}/status",
        json={"status": "IN_PROGRESS"},
    )
    assert s3.status_code == 200

    s4 = await async_client.patch(
        f"/api/v1/incidents/{incident_id}/status",
        json={"status": "RESOLVED", "resolutionDetails": "Resolved by automated test"},
    )
    assert s4.status_code == 200

    s5 = await async_client.patch(
        f"/api/v1/incidents/{incident_id}/status",
        json={"status": "VERIFIED"},
    )
    assert s5.status_code == 200

    close_resp = await async_client.patch(
        f"/api/v1/incidents/{incident_id}/status",
        json={"status": "CLOSED"},
    )
    assert close_resp.status_code == 200
    assert close_resp.json()["status"] == "CLOSED"

    # 5. Archive the closed incident as Admin
    arch_resp = await async_client.patch(f"/api/v1/incidents/{incident_id}/archive")
    assert arch_resp.status_code == 200
    arch_data = arch_resp.json()
    assert arch_data["isArchived"] is True
    assert arch_data["archivedAt"] is not None
    assert arch_data["archivedBy"] == str(admin_id)

    # 6. Idempotency / re-archiving fails
    re_arch = await async_client.patch(f"/api/v1/incidents/{incident_id}/archive")
    assert re_arch.status_code == 400

    # 7. Default list excludes archived incident
    def_list = await async_client.get("/api/v1/incidents")
    assert def_list.status_code == 200
    incident_ids_in_list = [i["id"] for i in def_list.json()]
    assert incident_id not in incident_ids_in_list

    # 8. List with includeArchived=true includes it
    inc_list = await async_client.get("/api/v1/incidents?includeArchived=true")
    assert inc_list.status_code == 200
    incident_ids_in_inc = [i["id"] for i in inc_list.json()]
    assert incident_id in incident_ids_in_inc

    # 9. GET /incidents/archived returns it for Admin
    archived_list = await async_client.get("/api/v1/incidents/archived")
    assert archived_list.status_code == 200
    arch_ids = [i["id"] for i in archived_list.json()]
    assert incident_id in arch_ids

    # 10. Non-admin accessing /incidents/archived receives 403
    app.dependency_overrides[get_actor_identity] = lambda: _make_identity(emp_id, UserRole.EMPLOYEE, "emp1")
    emp_arch_list = await async_client.get("/api/v1/incidents/archived")
    assert emp_arch_list.status_code == 403


# ==============================================================================
# TASK 4: DUPLICATE INCIDENT MERGING
# ==============================================================================


@pytest.mark.asyncio
async def test_duplicate_incident_merging_workflow(async_client: AsyncClient):
    """Verify merge duplicates endpoint merges records, closes duplicates, preserves comments, and audits."""
    app = async_client._transport.app  # type: ignore
    admin_id = UUID("00000000-0000-0000-0000-000000000001")
    emp_id = uuid4()

    # 1. Create primary incident and duplicate incident
    payload1 = _make_incident_payload()
    payload2 = _make_incident_payload()

    res1 = await async_client.post("/api/v1/incidents", json=payload1)
    res2 = await async_client.post("/api/v1/incidents", json=payload2)
    assert res1.status_code == 201
    assert res2.status_code == 201

    primary_id = res1.json()["id"]
    duplicate_id = res2.json()["id"]

    # 2. Non-admin merge attempt -> 403 Forbidden
    app.dependency_overrides[get_actor_identity] = lambda: _make_identity(emp_id, UserRole.EMPLOYEE, "emp1")
    merge_attempt = await async_client.post(
        f"/api/v1/incidents/{primary_id}/merge",
        json={"duplicateIncidentIds": [duplicate_id]},
    )
    assert merge_attempt.status_code == 403

    # Switch back to admin
    app.dependency_overrides[get_actor_identity] = lambda: _make_identity(admin_id, UserRole.ADMIN, "test_admin")

    # 3. Self-merge attempt -> 400 Bad Request
    self_merge = await async_client.post(
        f"/api/v1/incidents/{primary_id}/merge",
        json={"duplicateIncidentIds": [primary_id]},
    )
    assert self_merge.status_code == 400
    assert "SELF_MERGE_DISALLOWED" in self_merge.json()["errorCode"]

    # 4. Valid merge
    merge_resp = await async_client.post(
        f"/api/v1/incidents/{primary_id}/merge",
        json={"duplicateIncidentIds": [duplicate_id]},
    )
    assert merge_resp.status_code == 200
    merge_data = merge_resp.json()
    assert merge_data["primaryIncidentId"] == primary_id
    assert merge_data["mergedCount"] == 1
    assert duplicate_id in merge_data["mergedIncidentIds"]

    # 5. Verify duplicate incident state
    dup_details = await async_client.get(f"/api/v1/incidents/{duplicate_id}")
    assert dup_details.status_code == 200
    dup_data = dup_details.json()
    assert dup_data["status"] == "CLOSED"
    assert dup_data["mergedIntoIncidentId"] == primary_id
    assert dup_data["mergedAt"] is not None
    assert dup_data["mergedBy"] == str(admin_id)
    assert "Merged into primary incident" in dup_data["resolutionDetails"]

    # 6. Verify primary incident received reference comment
    prim_details = await async_client.get(f"/api/v1/incidents/{primary_id}")
    assert prim_details.status_code == 200
    prim_data = prim_details.json()
    comments = prim_data["comments"]
    assert any("[Duplicate Merged]" in c["content"] and duplicate_id in c["content"] for c in comments)

    # 7. Cannot merge already merged incident
    re_merge = await async_client.post(
        f"/api/v1/incidents/{primary_id}/merge",
        json={"duplicateIncidentIds": [duplicate_id]},
    )
    assert re_merge.status_code == 400
    assert "ALREADY_MERGED" in re_merge.json()["errorCode"]
