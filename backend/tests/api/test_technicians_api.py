"""
API integration tests for Technician endpoints.

Verifies:
- HTTP status codes (200, 201, 400, 404, 409).
- JSON formatting (camelCase fields).
- Endpoints:
  - GET /api/v1/technicians
  - POST /api/v1/technicians
  - GET /api/v1/technicians/{id}
  - PATCH /api/v1/technicians/{id}
  - PATCH /api/v1/technicians/{id}/availability
  - GET/POST/DELETE /api/v1/technicians/{id}/skills
- TC17: Invalid API request payloads return uniform 400/404/409 error envelope.
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient


class TestTechniciansAPI:
    """Test suite for /api/v1/technicians REST endpoints."""

    @pytest.mark.asyncio
    async def test_create_and_get_technician(self, async_client: AsyncClient):
        """TC1, TC2: Create a technician profile and retrieve it."""
        user_id = str(uuid4())
        payload = {
            "userId": user_id,
            "experienceYears": 4,
            "maxCapacity": 8,
            "skills": [
                {"skillName": "NETWORK", "proficiencyLevel": 4},
                {"skillName": "CLOUD", "proficiencyLevel": 3},
            ],
        }

        # 1. Create technician
        create_resp = await async_client.post("/api/v1/technicians", json=payload)
        assert create_resp.status_code == 201
        data = create_resp.json()

        assert data["userId"] == user_id
        assert data["availability"] == "AVAILABLE"
        assert data["experienceYears"] == 4
        assert data["maxCapacity"] == 8
        assert data["activeIncidentCount"] == 0
        assert data["remainingCapacity"] == 8
        assert len(data["skills"]) == 2
        tech_id = data["id"]

        # 2. Get technician by ID
        get_resp = await async_client.get(f"/api/v1/technicians/{tech_id}")
        assert get_resp.status_code == 200
        get_data = get_resp.json()
        assert get_data["id"] == tech_id
        assert get_data["userId"] == user_id

    @pytest.mark.asyncio
    async def test_list_technicians(self, async_client: AsyncClient):
        """List all technicians with pagination."""
        # Create two technicians
        for i in range(2):
            await async_client.post(
                "/api/v1/technicians",
                json={
                    "userId": str(uuid4()),
                    "experienceYears": i + 2,
                    "maxCapacity": 10,
                },
            )

        resp = await async_client.get("/api/v1/technicians?skip=0&limit=10")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 2

    @pytest.mark.asyncio
    async def test_update_availability(self, async_client: AsyncClient):
        """TC4: Update technician availability status via API."""
        user_id = str(uuid4())
        create_resp = await async_client.post(
            "/api/v1/technicians",
            json={"userId": user_id, "experienceYears": 3},
        )
        tech_id = create_resp.json()["id"]

        patch_resp = await async_client.patch(
            f"/api/v1/technicians/{tech_id}/availability",
            json={"availability": "BUSY"},
        )
        assert patch_resp.status_code == 200
        assert patch_resp.json()["availability"] == "BUSY"

    @pytest.mark.asyncio
    async def test_manage_technician_skills(self, async_client: AsyncClient):
        """TC3: Add, list, and delete technician skills."""
        user_id = str(uuid4())
        create_resp = await async_client.post(
            "/api/v1/technicians",
            json={"userId": user_id, "experienceYears": 3},
        )
        tech_id = create_resp.json()["id"]

        # Add skill
        add_skill_resp = await async_client.post(
            f"/api/v1/technicians/{tech_id}/skills",
            json={"skillName": "DATABASE", "proficiencyLevel": 5},
        )
        assert add_skill_resp.status_code == 201
        assert any(s["skillName"] == "DATABASE" for s in add_skill_resp.json()["skills"])

        # List skills
        list_skills_resp = await async_client.get(f"/api/v1/technicians/{tech_id}/skills")
        assert list_skills_resp.status_code == 200
        assert len(list_skills_resp.json()) == 1

        # Delete skill
        del_skill_resp = await async_client.delete(f"/api/v1/technicians/{tech_id}/skills/DATABASE")
        assert del_skill_resp.status_code == 200
        assert not any(s["skillName"] == "DATABASE" for s in del_skill_resp.json()["skills"])

    @pytest.mark.asyncio
    async def test_invalid_api_requests(self, async_client: AsyncClient):
        """TC17: Validation errors (400), not found (404), and conflict (409)."""
        # 1. Missing required field -> 422 Unprocessable Entity (FastAPI standard)
        bad_resp = await async_client.post("/api/v1/technicians", json={})
        assert bad_resp.status_code in (400, 422)

        # 2. Invalid proficiency level outside 1-5 -> 422
        user_id = str(uuid4())
        bad_skill_resp = await async_client.post(
            "/api/v1/technicians",
            json={
                "userId": user_id,
                "skills": [{"skillName": "NETWORK", "proficiencyLevel": 99}],
            },
        )
        assert bad_skill_resp.status_code in (400, 422)

        # 3. Not found -> 404
        missing_id = str(uuid4())
        nf_resp = await async_client.get(f"/api/v1/technicians/{missing_id}")
        assert nf_resp.status_code == 404
        error_body = nf_resp.json()
        assert error_body["errorCode"] in ("TECHNICIAN_NOT_FOUND", "RESOURCE_NOT_FOUND")

        # 4. Duplicate technician creation for same user_id -> 409
        uid = str(uuid4())
        await async_client.post("/api/v1/technicians", json={"userId": uid})
        dup_resp = await async_client.post("/api/v1/technicians", json={"userId": uid})
        assert dup_resp.status_code == 409
        assert dup_resp.json()["errorCode"] == "TECHNICIAN_ALREADY_EXISTS"

    @pytest.mark.asyncio
    async def test_skill_response_contains_profile_id(self, async_client: AsyncClient):
        """Skill technician_id in API response equals the technician profile id, not user_id."""
        user_id = str(uuid4())
        create_resp = await async_client.post(
            "/api/v1/technicians",
            json={
                "userId": user_id,
                "skills": [{"skillName": "NETWORK", "proficiencyLevel": 4}],
            },
        )
        assert create_resp.status_code == 201
        data = create_resp.json()
        tech_id = data["id"]

        # tech_id != user_id
        assert tech_id != user_id

        # Every skill's technicianId must equal the profile id
        for skill in data["skills"]:
            assert skill["technicianId"] == tech_id
            assert skill["technicianId"] != user_id

        # Also verify via GET /{id}/skills
        skills_resp = await async_client.get(f"/api/v1/technicians/{tech_id}/skills")
        assert skills_resp.status_code == 200
        for skill in skills_resp.json():
            assert skill["technicianId"] == tech_id

    @pytest.mark.asyncio
    async def test_patch_update_technician_via_service(self, async_client: AsyncClient):
        """PATCH /technicians/{id} updates fields through the service layer."""
        user_id = str(uuid4())
        create_resp = await async_client.post(
            "/api/v1/technicians",
            json={"userId": user_id, "experienceYears": 2, "maxCapacity": 5},
        )
        tech_id = create_resp.json()["id"]

        # Update only experience_years
        patch_resp = await async_client.patch(
            f"/api/v1/technicians/{tech_id}",
            json={"experienceYears": 10},
        )
        assert patch_resp.status_code == 200
        data = patch_resp.json()
        assert data["experienceYears"] == 10
        assert data["maxCapacity"] == 5  # Unchanged

        # Update only max_capacity
        patch_resp2 = await async_client.patch(
            f"/api/v1/technicians/{tech_id}",
            json={"maxCapacity": 20},
        )
        assert patch_resp2.status_code == 200
        data2 = patch_resp2.json()
        assert data2["maxCapacity"] == 20
        assert data2["experienceYears"] == 10  # Preserved

    @pytest.mark.asyncio
    async def test_patch_update_rejects_invalid_values(self, async_client: AsyncClient):
        """PATCH /technicians/{id} rejects negative experience or zero capacity."""
        user_id = str(uuid4())
        create_resp = await async_client.post(
            "/api/v1/technicians",
            json={"userId": user_id, "experienceYears": 3, "maxCapacity": 5},
        )
        tech_id = create_resp.json()["id"]

        # Negative experience_years — rejected by Pydantic schema (ge=0) as 422
        neg_exp = await async_client.patch(
            f"/api/v1/technicians/{tech_id}",
            json={"experienceYears": -1},
        )
        assert neg_exp.status_code in (409, 422)

        # Zero max_capacity — rejected by Pydantic schema (ge=1) as 422
        zero_cap = await async_client.patch(
            f"/api/v1/technicians/{tech_id}",
            json={"maxCapacity": 0},
        )
        assert zero_cap.status_code in (409, 422)
