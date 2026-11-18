
"""
API integration tests for Member 2 Incident Management endpoints.
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient


def create_payload():

    return {
        "serviceId": str(uuid4()),
        "category": "NETWORK",
        "requiredSkill": "NETWORK",
        "description": "Campus Wi-Fi is unavailable",
        "impact": 4,
        "urgency": 5,
        "businessCriticality": 5,
    }


@pytest.mark.asyncio
async def test_create_incident(async_client: AsyncClient):

    response = await async_client.post(
        "/api/v1/incidents",
        json=create_payload(),
    )

    assert response.status_code == 201

    data = response.json()

    assert data["incidentCode"].startswith("INC-")
    assert data["priority"] == "P1"
    assert data["status"] == "NEW"

    assert data["reporterId"] is not None
    assert data["id"] is not None


@pytest.mark.asyncio
async def test_list_incidents(async_client: AsyncClient):

    await async_client.post(
        "/api/v1/incidents",
        json=create_payload(),
    )

    response = await async_client.get(
        "/api/v1/incidents"
    )

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_get_incident_details(async_client: AsyncClient):

    create_response = await async_client.post(
        "/api/v1/incidents",
        json=create_payload(),
    )

    incident_id = create_response.json()["id"]

    response = await async_client.get(
        f"/api/v1/incidents/{incident_id}"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == incident_id
    assert data["incidentCode"].startswith("INC-")
    assert isinstance(data["comments"], list)


@pytest.mark.asyncio
async def test_update_incident(async_client: AsyncClient):

    create_response = await async_client.post(
        "/api/v1/incidents",
        json={
            **create_payload(),
            "impact": 2,
            "urgency": 2,
            "businessCriticality": 2,
        },
    )

    incident_id = create_response.json()["id"]

    assert create_response.json()["priority"] == "P4"

    update_response = await async_client.patch(
        f"/api/v1/incidents/{incident_id}",
        json={
            "description": "Complete network failure",
            "impact": 5,
            "urgency": 5,
        },
    )

    assert update_response.status_code == 200

    data = update_response.json()

    assert data["description"] == "Complete network failure"
    assert data["priority"] == "P2"


@pytest.mark.asyncio
async def test_invalid_status_transition(
    async_client: AsyncClient,
):

    create_response = await async_client.post(
        "/api/v1/incidents",
        json=create_payload(),
    )

    incident_id = create_response.json()["id"]

    response = await async_client.patch(
        f"/api/v1/incidents/{incident_id}/status",
        json={
            "status": "CLOSED",
        },
    )

    assert response.status_code == 409

    data = response.json()

    assert data["errorCode"] == "INVALID_STATUS_TRANSITION"
    assert data["status"] == 409


@pytest.mark.asyncio
async def test_valid_status_transition(
    async_client: AsyncClient,
):

    create_response = await async_client.post(
        "/api/v1/incidents",
        json=create_payload(),
    )

    incident_id = create_response.json()["id"]

    response = await async_client.patch(
        f"/api/v1/incidents/{incident_id}/status",
        json={
            "status": "CLASSIFIED",
        },
    )

    assert response.status_code == 200

    assert response.json()["status"] == "CLASSIFIED"


@pytest.mark.asyncio
async def test_add_incident_comment(
    async_client: AsyncClient,
):

    create_response = await async_client.post(
        "/api/v1/incidents",
        json=create_payload(),
    )

    incident_id = create_response.json()["id"]

    response = await async_client.post(
        f"/api/v1/incidents/{incident_id}/comments",
        json={
            "content": "Please investigate the Wi-Fi issue."
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["incidentId"] == incident_id

    assert (
        data["content"]
        == "Please investigate the Wi-Fi issue."
    )


@pytest.mark.asyncio
async def test_incident_comments_appear_in_details(
    async_client: AsyncClient,
):

    create_response = await async_client.post(
        "/api/v1/incidents",
        json=create_payload(),
    )

    incident_id = create_response.json()["id"]

    await async_client.post(
        f"/api/v1/incidents/{incident_id}/comments",
        json={
            "content": "Initial investigation started."
        },
    )

    details_response = await async_client.get(
        f"/api/v1/incidents/{incident_id}"
    )

    assert details_response.status_code == 200

    comments = details_response.json()["comments"]

    assert len(comments) == 1

    assert (
        comments[0]["content"]
        == "Initial investigation started."
    )


@pytest.mark.asyncio
async def test_incident_list_can_filter_by_category(async_client):
    """Verify category filtering on the incident list."""

    network_payload = create_payload()
    network_payload["category"] = "NETWORK"

    software_payload = create_payload()
    software_payload["category"] = "SOFTWARE"
    software_payload["requiredSkill"] = "SOFTWARE"

    network_response = await async_client.post(
        "/api/v1/incidents",
        json=network_payload,
    )

    software_response = await async_client.post(
        "/api/v1/incidents",
        json=software_payload,
    )

    assert network_response.status_code == 201
    assert software_response.status_code == 201

    response = await async_client.get(
        "/api/v1/incidents",
        params={"category": "NETWORK"},
    )

    assert response.status_code == 200

    incidents = response.json()

    assert len(incidents) >= 1

    assert all(
        item["category"] == "NETWORK"
        for item in incidents
    )


@pytest.mark.asyncio
async def test_incident_list_can_filter_by_incident_code(async_client):
    """Verify partial incident-code search."""

    payload = create_payload()

    create_response = await async_client.post(
        "/api/v1/incidents",
        json=payload,
    )

    assert create_response.status_code == 201

    incident_code = create_response.json()["incidentCode"]

    response = await async_client.get(
        "/api/v1/incidents",
        params={"incidentCode": incident_code},
    )

    assert response.status_code == 200

    results = response.json()

    assert any(
        incident["incidentCode"] == incident_code
        for incident in results
    )


@pytest.mark.asyncio
async def test_duplicate_endpoint_finds_similar_incident(async_client):
    """Verify the API flags a similar incident."""

    service_id = str(uuid4())

    first_payload = create_payload()
    first_payload["serviceId"] = service_id
    first_payload["category"] = "NETWORK"
    first_payload["requiredSkill"] = "NETWORK"
    first_payload["description"] = (
        "Network router connection failure after restart"
    )

    first_response = await async_client.post(
        "/api/v1/incidents",
        json=first_payload,
    )

    assert first_response.status_code == 201

    first_id = first_response.json()["id"]

    second_payload = create_payload()
    second_payload["serviceId"] = service_id
    second_payload["category"] = "NETWORK"
    second_payload["requiredSkill"] = "NETWORK"
    second_payload["description"] = (
        "Network router connection failure after server restart"
    )

    second_response = await async_client.post(
        "/api/v1/incidents",
        json=second_payload,
    )

    assert second_response.status_code == 201

    second_id = second_response.json()["id"]

    duplicate_response = await async_client.get(
        f"/api/v1/incidents/{second_id}/duplicates"
    )

    assert duplicate_response.status_code == 200

    duplicates = duplicate_response.json()

    assert any(
        item["incidentId"] == first_id
        for item in duplicates
    )

    matching_duplicate = next(
        item
        for item in duplicates
        if item["incidentId"] == first_id
    )

    assert matching_duplicate["similarityScore"] >= 0.50
    assert matching_duplicate["explanation"]


@pytest.mark.asyncio
async def test_duplicate_endpoint_returns_empty_list_without_matches(
    async_client,
):
    """Verify an unrelated incident has no duplicate matches."""

    payload = create_payload()
    payload["description"] = (
        "The printer has a paper jam in tray number three"
    )

    create_response = await async_client.post(
        "/api/v1/incidents",
        json=payload,
    )

    assert create_response.status_code == 201

    incident_id = create_response.json()["id"]

    response = await async_client.get(
        f"/api/v1/incidents/{incident_id}/duplicates"
    )

    assert response.status_code == 200
    assert response.json() == []
