import pytest


@pytest.mark.asyncio
async def test_api_rejects_invalid_date_range(async_client):
    response = await async_client.get(
        "/api/v1/incidents",
        params={
            "dateFrom": "2026-11-15T12:00:00Z",
            "dateTo": "2026-11-15T10:00:00Z",
        },
    )

    assert response.status_code == 400

    body = response.json()

    assert body["errorCode"] == "INVALID_DATE_RANGE"


@pytest.mark.asyncio
async def test_api_rejects_datetime_without_timezone(
    async_client,
):
    response = await async_client.get(
        "/api/v1/incidents",
        params={
            "dateFrom": "2026-11-15T10:00:00",
        },
    )

    assert response.status_code == 400

    body = response.json()

    assert body["errorCode"] == "TIMEZONE_REQUIRED"


@pytest.mark.asyncio
async def test_api_rejects_whitespace_incident_code(
    async_client,
):
    response = await async_client.get(
        "/api/v1/incidents",
        params={
            "incidentCode": "     ",
        },
    )

    assert response.status_code == 400

    body = response.json()

    assert body["errorCode"] == "INVALID_INCIDENT_CODE"


@pytest.mark.asyncio
async def test_api_rejects_limit_above_100(
    async_client,
):
    response = await async_client.get(
        "/api/v1/incidents",
        params={
            "limit": 101,
        },
    )

    # FastAPI's Query validation rejects this before the
    # application service is invoked.
    assert response.status_code == 422