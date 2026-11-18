from datetime import UTC, datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest

from app.application.incident.service import (
    IncidentApplicationService,
)
from app.core.exceptions import ValidationError


@pytest.fixture
def service_and_repository():
    repository = AsyncMock()
    repository.list_all.return_value = []

    publisher = AsyncMock()

    service = IncidentApplicationService(
        repository=repository,
        event_publisher=publisher,
    )

    return service, repository


@pytest.mark.asyncio
async def test_negative_skip_is_rejected(
    service_and_repository,
):
    service, repository = service_and_repository

    with pytest.raises(ValidationError) as exc:
        await service.list_incidents(skip=-1)

    assert exc.value.error_code == "INVALID_PAGINATION"
    repository.list_all.assert_not_awaited()


@pytest.mark.asyncio
async def test_limit_above_100_is_rejected(
    service_and_repository,
):
    service, repository = service_and_repository

    with pytest.raises(ValidationError) as exc:
        await service.list_incidents(limit=101)

    assert exc.value.error_code == "INVALID_PAGINATION"
    repository.list_all.assert_not_awaited()


@pytest.mark.asyncio
async def test_zero_limit_is_rejected(
    service_and_repository,
):
    service, repository = service_and_repository

    with pytest.raises(ValidationError):
        await service.list_incidents(limit=0)

    repository.list_all.assert_not_awaited()


@pytest.mark.asyncio
async def test_whitespace_incident_code_is_rejected(
    service_and_repository,
):
    service, repository = service_and_repository

    with pytest.raises(ValidationError) as exc:
        await service.list_incidents(
            incident_code="     ",
        )

    assert exc.value.error_code == "INVALID_INCIDENT_CODE"
    repository.list_all.assert_not_awaited()


@pytest.mark.asyncio
async def test_incident_code_is_trimmed(
    service_and_repository,
):
    service, repository = service_and_repository

    await service.list_incidents(
        incident_code=" INC-1001 ",
    )

    repository.list_all.assert_awaited_once()

    kwargs = repository.list_all.await_args.kwargs

    assert kwargs["incident_code"] == "INC-1001"


@pytest.mark.asyncio
async def test_naive_date_from_is_rejected(
    service_and_repository,
):
    service, repository = service_and_repository

    naive_date = datetime(2026, 11, 15, 10, 0, 0)

    with pytest.raises(ValidationError) as exc:
        await service.list_incidents(
            date_from=naive_date,
        )

    assert exc.value.error_code == "TIMEZONE_REQUIRED"
    repository.list_all.assert_not_awaited()


@pytest.mark.asyncio
async def test_naive_date_to_is_rejected(
    service_and_repository,
):
    service, repository = service_and_repository

    naive_date = datetime(2026, 11, 15, 10, 0, 0)

    with pytest.raises(ValidationError) as exc:
        await service.list_incidents(
            date_to=naive_date,
        )

    assert exc.value.error_code == "TIMEZONE_REQUIRED"
    repository.list_all.assert_not_awaited()


@pytest.mark.asyncio
async def test_invalid_date_range_is_rejected(
    service_and_repository,
):
    service, repository = service_and_repository

    date_from = datetime(
        2026, 11, 15, 12, 0,
        tzinfo=UTC,
    )

    date_to = datetime(
        2026, 11, 15, 10, 0,
        tzinfo=UTC,
    )

    with pytest.raises(ValidationError) as exc:
        await service.list_incidents(
            date_from=date_from,
            date_to=date_to,
        )

    assert exc.value.error_code == "INVALID_DATE_RANGE"
    repository.list_all.assert_not_awaited()


@pytest.mark.asyncio
async def test_search_dates_are_normalized_to_utc(
    service_and_repository,
):
    service, repository = service_and_repository

    india_timezone = timezone(
        timedelta(hours=5, minutes=30)
    )

    date_from = datetime(
        2026, 11, 14, 10, 0,
        tzinfo=india_timezone,
    )

    date_to = datetime(
        2026, 11, 15, 10, 0,
        tzinfo=india_timezone,
    )

    await service.list_incidents(
        date_from=date_from,
        date_to=date_to,
    )

    kwargs = repository.list_all.await_args.kwargs

    assert kwargs["date_from"].utcoffset() == timedelta(0)
    assert kwargs["date_to"].utcoffset() == timedelta(0)

    assert kwargs["date_from"] == date_from.astimezone(
        UTC
    )

    assert kwargs["date_to"] == date_to.astimezone(
        UTC
    )
