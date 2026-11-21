"""
API tests for Notifications, SLA Summary, and Audit Trail filters.
"""

from __future__ import annotations

from uuid import UUID

import pytest
from httpx import AsyncClient

from app.application.sla.notification_service import NotificationService
from app.application.sla.sla_service import SLAService
from app.domain.sla.enums import NotificationChannel, NotificationType


@pytest.mark.asyncio
async def test_notification_unread_and_count_endpoints(
    async_client: AsyncClient,
    notification_service: NotificationService,
) -> None:
    admin_id = UUID("00000000-0000-0000-0000-000000000001")

    # Send 2 notifications to admin
    await notification_service.send_notification(
        user_id=admin_id,
        title="Test Alert 1",
        message="Message 1",
        notification_type=NotificationType.GENERAL,
        channel=NotificationChannel.IN_APP,
    )
    notif2 = await notification_service.send_notification(
        user_id=admin_id,
        title="Test Alert 2",
        message="Message 2",
        notification_type=NotificationType.INCIDENT_ASSIGNED,
        channel=NotificationChannel.IN_APP,
    )

    # Check unread count
    res = await async_client.get("/api/v1/notifications/unread/count")
    assert res.status_code == 200
    data = res.json()
    assert data["unreadCount"] >= 2
    assert UUID(data["userId"]) == admin_id

    # Check unread list
    res = await async_client.get("/api/v1/notifications/unread")
    assert res.status_code == 200
    unread_items = res.json()
    assert len(unread_items) >= 2
    assert all(item["isRead"] is False for item in unread_items)

    # Mark one read
    await notification_service.mark_as_read(notif2.id)

    # Verify count decremented
    res = await async_client.get("/api/v1/notifications/unread/count")
    assert res.status_code == 200
    assert res.json()["unreadCount"] == data["unreadCount"] - 1


@pytest.mark.asyncio
async def test_sla_summary_endpoint(
    async_client: AsyncClient,
    sla_service: SLAService,
) -> None:
    # Ensure default policies exist
    await sla_service.ensure_default_policies()

    res = await async_client.get("/api/v1/sla/summary")
    assert res.status_code == 200
    data = res.json()
    assert "totalTracked" in data
    assert "metCount" in data
    assert "breachedCount" in data
    assert "warningCount" in data
    assert "activeCount" in data
    assert "complianceRate" in data
    assert "byPriority" in data
    assert len(data["byPriority"]) == 4
    priorities = {p["priority"] for p in data["byPriority"]}
    assert priorities == {"P1", "P2", "P3", "P4"}


@pytest.mark.asyncio
async def test_audit_logs_with_filtering(
    async_client: AsyncClient,
) -> None:
    res = await async_client.get("/api/v1/audit?eventType=IncidentCreatedEvent")
    assert res.status_code == 200
    assert isinstance(res.json(), list)
