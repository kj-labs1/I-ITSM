"""
API endpoint tests for Member 4 (SLA, Audit Logs & Notifications).

Verifies camelCase JSON serialization, HTTP status codes, uniform error
envelopes, and all master routes defined in PROJECT_CONTRACT.md:
- GET   /api/v1/incidents/{id}/sla
- GET   /api/v1/sla/violations
- GET   /api/v1/sla/policies
- PATCH /api/v1/sla/policies/{priority}
- POST  /api/v1/sla/check
- GET   /api/v1/notifications
- PATCH /api/v1/notifications/{id}/read
- GET   /api/v1/incidents/{id}/audit
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.application.sla.audit_service import AuditService
from app.application.sla.notification_service import NotificationService
from app.domain.sla.enums import NotificationType


@pytest.mark.asyncio
async def test_sla_policies_and_incident_tracking_endpoints(async_client: AsyncClient) -> None:
    # 1. List default policies (auto-seeded P1–P4)
    resp = await async_client.get("/api/v1/sla/policies")
    assert resp.status_code == 200
    policies = resp.json()
    assert len(policies) == 4
    assert "responseTimeMinutes" in policies[0]
    assert "resolutionTimeMinutes" in policies[0]

    # 2. Update P1 policy
    patch_resp = await async_client.patch(
        "/api/v1/sla/policies/P1",
        json={"responseTimeMinutes": 10, "resolutionTimeMinutes": 180},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["responseTimeMinutes"] == 10

    # 3. Start SLA tracking for an overdue incident
    incident_id = str(uuid4())
    past = (datetime.now(UTC) - timedelta(minutes=25)).isoformat()
    start_resp = await async_client.post(
        f"/api/v1/incidents/{incident_id}/sla",
        json={"priority": "P1", "startedAt": past},
    )
    assert start_resp.status_code == 201
    assert start_resp.json()["incidentId"] == incident_id

    # 4. Trigger on-demand SLA check
    check_resp = await async_client.post("/api/v1/sla/check")
    assert check_resp.status_code == 200
    assert check_resp.json()["breachesTriggered"] == 1

    # 5. Get incident SLA status
    get_resp = await async_client.get(f"/api/v1/incidents/{incident_id}/sla")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["status"] == "BREACHED"
    assert data["isBreached"] is True

    # 6. List SLA violations
    viol_resp = await async_client.get("/api/v1/sla/violations")
    assert viol_resp.status_code == 200
    violations = viol_resp.json()
    assert len(violations) == 1
    assert violations[0]["incidentId"] == incident_id

    # 7. Non-existent incident returns 404 with uniform error envelope
    missing_resp = await async_client.get(f"/api/v1/incidents/{uuid4()}/sla")
    assert missing_resp.status_code == 404
    assert missing_resp.json()["errorCode"] == "SLA_TRACKING_NOT_FOUND"


@pytest.mark.asyncio
async def test_notifications_and_audit_endpoints(
    async_client: AsyncClient,
    audit_service: AuditService,
    notification_service: NotificationService,
) -> None:
    incident_id = uuid4()
    user_id = uuid4()

    # Seed audit entry and notification
    await audit_service.record(
        incident_id=incident_id,
        action="INCIDENT_ASSIGNED",
        event_type="IncidentAssignedEvent",
        actor_id=user_id,
        details="Assigned to technician",
    )
    notif = await notification_service.send_notification(
        user_id=user_id,
        incident_id=incident_id,
        title="New Assignment",
        message="Please investigate INC-1001",
        notification_type=NotificationType.INCIDENT_ASSIGNED,
    )

    # 1. GET /api/v1/incidents/{id}/audit
    audit_resp = await async_client.get(f"/api/v1/incidents/{incident_id}/audit")
    assert audit_resp.status_code == 200
    entries = audit_resp.json()
    assert len(entries) == 1
    assert entries[0]["action"] == "INCIDENT_ASSIGNED"
    assert entries[0]["incidentId"] == str(incident_id)

    # 2. GET /api/v1/notifications
    notif_list = await async_client.get(
        "/api/v1/notifications",
        params={"userId": str(user_id), "unreadOnly": "true"},
    )
    assert notif_list.status_code == 200
    items = notif_list.json()
    assert len(items) == 1
    assert items[0]["isRead"] is False

    # 3. PATCH /api/v1/notifications/{id}/read
    read_resp = await async_client.patch(f"/api/v1/notifications/{notif.id}/read")
    assert read_resp.status_code == 200
    assert read_resp.json()["isRead"] is True
    assert read_resp.json()["readAt"] is not None

    # 4. Unread filter should now return empty
    unread_after = await async_client.get(
        "/api/v1/notifications",
        params={"userId": str(user_id), "unreadOnly": "true"},
    )
    assert unread_after.status_code == 200
    assert unread_after.json() == []
