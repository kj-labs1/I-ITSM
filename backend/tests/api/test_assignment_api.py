"""
API integration tests for Technician Recommendations and Incident Assignment endpoints.

Verifies:
- GET  /api/v1/technicians/recommendations?incidentId={id}&strategy={strategy}&useLlm={bool}
- POST /api/v1/incidents/{incident_id}/assign
- Error responses: 404 for missing incident/technician, 409 for duplicate or invalid assignment.
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.integrations.incidents.stub_incident_service import StubIncidentService
from app.shared.enums import IncidentCategory, IncidentStatus, Priority


class TestAssignmentAPI:
    """Test suite for recommendations and assignment endpoints."""

    @pytest.mark.asyncio
    async def test_recommendations_endpoint_skill_based(
        self,
        async_client: AsyncClient,
        stub_incidents: StubIncidentService,
    ):
        """TC5: Query recommendations using SKILL_BASED strategy."""
        # 1. Create two technicians
        await async_client.post(
            "/api/v1/technicians",
            json={
                "userId": str(uuid4()),
                "experienceYears": 2,
                "skills": [{"skillName": "NETWORK", "proficiencyLevel": 3}],
            },
        )
        tech2_resp = await async_client.post(
            "/api/v1/technicians",
            json={
                "userId": str(uuid4()),
                "experienceYears": 8,
                "skills": [{"skillName": "NETWORK", "proficiencyLevel": 5}],
            },
        )

        # 2. Seed an incident requiring NETWORK
        inc = stub_incidents.seed_incident(
            category=IncidentCategory.NETWORK,
            required_skill="NETWORK",
            priority=Priority.P1,
        )

        # 3. Query recommendations
        rec_url = f"/api/v1/technicians/recommendations?incidentId={inc.id}&strategy=SKILL_BASED"
        resp = await async_client.get(rec_url)
        assert resp.status_code == 200
        data = resp.json()

        assert data["incidentId"] == str(inc.id)
        assert data["strategyUsed"] == "SKILL_BASED"
        assert len(data["recommendations"]) == 2
        # Tech 2 should be ranked 1st
        assert data["recommendations"][0]["technicianId"] == tech2_resp.json()["id"]
        assert data["recommendations"][0]["rank"] == 1

    @pytest.mark.asyncio
    async def test_recommendations_endpoint_least_loaded(
        self,
        async_client: AsyncClient,
        stub_incidents: StubIncidentService,
    ):
        """TC7: Query recommendations using LEAST_LOADED strategy."""
        await async_client.post(
            "/api/v1/technicians",
            json={
                "userId": str(uuid4()),
                "experienceYears": 5,
                "skills": [{"skillName": "DATABASE", "proficiencyLevel": 4}],
            },
        )

        inc = stub_incidents.seed_incident(
            category=IncidentCategory.DATABASE,
            required_skill="DATABASE",
        )

        rec_url = f"/api/v1/technicians/recommendations?incidentId={inc.id}&strategy=LEAST_LOADED"
        resp = await async_client.get(rec_url)
        assert resp.status_code == 200
        data = resp.json()
        assert data["strategyUsed"] == "LEAST_LOADED"
        assert len(data["recommendations"]) == 1

    @pytest.mark.asyncio
    async def test_recommendations_endpoint_llm_enhanced(
        self,
        async_client: AsyncClient,
        stub_incidents: StubIncidentService,
    ):
        """TC18: Query recommendations with useLlm=true flag."""
        await async_client.post(
            "/api/v1/technicians",
            json={
                "userId": str(uuid4()),
                "experienceYears": 4,
                "skills": [{"skillName": "CLOUD", "proficiencyLevel": 4}],
            },
        )

        inc = stub_incidents.seed_incident(
            category=IncidentCategory.CLOUD,
            required_skill="CLOUD",
        )

        rec_url = f"/api/v1/technicians/recommendations?incidentId={inc.id}&useLlm=true"
        resp = await async_client.get(rec_url)
        assert resp.status_code == 200
        data = resp.json()
        assert data["isLlmEnhanced"] is True
        assert len(data["recommendations"]) == 1
        assert data["recommendations"][0]["isLlmEnhanced"] is True

    @pytest.mark.asyncio
    async def test_assign_technician_endpoint(
        self,
        async_client: AsyncClient,
        stub_incidents: StubIncidentService,
    ):
        """TC12: Assign technician via POST /api/v1/incidents/{id}/assign."""
        tech_resp = await async_client.post(
            "/api/v1/technicians",
            json={
                "userId": str(uuid4()),
                "experienceYears": 4,
                "skills": [{"skillName": "SECURITY", "proficiencyLevel": 5}],
            },
        )
        tech_id = tech_resp.json()["id"]

        inc = stub_incidents.seed_incident(
            category=IncidentCategory.SECURITY,
            required_skill="SECURITY",
        )

        assign_payload = {
            "technicianId": tech_id,
            "strategyUsed": "SKILL_BASED",
            "reason": "Top scoring security engineer",
        }

        resp = await async_client.post(
            f"/api/v1/incidents/{inc.id}/assign",
            json=assign_payload,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["incidentId"] == str(inc.id)
        assert data["technicianId"] == tech_id
        assert data["status"] == "ASSIGNED"

        # Verify M2 stub reflects ASSIGNED status
        updated_inc = await stub_incidents.get_incident(inc.id)
        assert updated_inc.status == IncidentStatus.ASSIGNED

    @pytest.mark.asyncio
    async def test_assign_conflict_handling(
        self,
        async_client: AsyncClient,
        stub_incidents: StubIncidentService,
    ):
        """TC13: Re-assigning an already assigned incident returns 409 Conflict."""
        tech_resp = await async_client.post(
            "/api/v1/technicians",
            json={
                "userId": str(uuid4()),
                "skills": [{"skillName": "STORAGE", "proficiencyLevel": 4}],
            },
        )
        tech_id = tech_resp.json()["id"]

        inc = stub_incidents.seed_incident(
            category=IncidentCategory.STORAGE,
            required_skill="STORAGE",
        )

        payload = {"technicianId": tech_id, "strategyUsed": "MANUAL"}

        # First assignment succeeds
        first_resp = await async_client.post(f"/api/v1/incidents/{inc.id}/assign", json=payload)
        assert first_resp.status_code == 200

        # Duplicate attempt fails with 409
        dup_resp = await async_client.post(f"/api/v1/incidents/{inc.id}/assign", json=payload)
        assert dup_resp.status_code == 409
        body = dup_resp.json()
        assert body["errorCode"] == "DUPLICATE_ASSIGNMENT"
        assert body["status"] == 409
