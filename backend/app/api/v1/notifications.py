"""
Notification REST API endpoints — Member 4.

Routes owned (per PROJECT_CONTRACT.md):
- GET   /api/v1/notifications
- GET   /api/v1/notifications/{notification_id}
- PATCH /api/v1/notifications/{notification_id}/read
- PATCH /api/v1/notifications/read-all
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_actor_identity, get_notification_service
from app.api.v1.sla_schemas import NotificationResponse, NotificationsReadAllResponse
from app.application.sla.notification_service import NotificationService
from app.domain.identity.user import UserIdentity
from app.domain.sla.notification import Notification
from app.shared.enums import UserRole

router = APIRouter(prefix="/notifications", tags=["Notifications"])


def _to_response(notification: Notification) -> NotificationResponse:
    return NotificationResponse(
        id=notification.id,
        user_id=notification.user_id,
        incident_id=notification.incident_id,
        channel=notification.channel,
        notification_type=notification.notification_type,
        title=notification.title,
        message=notification.message,
        is_read=notification.is_read,
        read_at=notification.read_at,
        delivery_status=notification.delivery_status,
        created_at=notification.created_at,
        updated_at=notification.updated_at,
    )


@router.get(
    "",
    response_model=list[NotificationResponse],
    summary="List notifications",
)
async def list_notifications(
    user_id: UUID | None = Query(
        default=None,
        alias="userId",
        description="Filter by recipient user UUID. Omit to list all visible notifications.",
    ),
    incident_id: UUID | None = Query(default=None, alias="incidentId"),
    unread_only: bool = Query(default=False, alias="unreadOnly"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    actor: UserIdentity = Depends(get_actor_identity),
    notification_service: NotificationService = Depends(get_notification_service),
) -> list[NotificationResponse]:
    """List notifications ordered newest-first."""
    target_user_id = user_id
    if actor.role != UserRole.ADMIN:
        target_user_id = actor.id
    items = await notification_service.list_notifications(
        user_id=target_user_id,
        incident_id=incident_id,
        unread_only=unread_only,
        skip=skip,
        limit=limit,
    )
    return [_to_response(item) for item in items]


@router.patch(
    "/read-all",
    response_model=NotificationsReadAllResponse,
    summary="Mark all notifications as read for a user",
)
async def mark_all_notifications_read(
    user_id: UUID | None = Query(default=None, alias="userId"),
    actor: UserIdentity = Depends(get_actor_identity),
    notification_service: NotificationService = Depends(get_notification_service),
) -> NotificationsReadAllResponse:
    """Mark all unread notifications for the target (or current) user as read."""
    target_user = actor.id if actor.role != UserRole.ADMIN else (user_id or actor.id)
    count = await notification_service.mark_all_read(target_user)
    return NotificationsReadAllResponse(user_id=target_user, marked_count=count)


@router.get(
    "/{notification_id}",
    response_model=NotificationResponse,
    summary="Get notification details",
)
async def get_notification(
    notification_id: UUID,
    actor: UserIdentity = Depends(get_actor_identity),
    notification_service: NotificationService = Depends(get_notification_service),
) -> NotificationResponse:
    """Retrieve a single notification by its UUID."""
    item = await notification_service.get_notification(notification_id)
    if actor.role != UserRole.ADMIN and item.user_id != actor.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Cannot view notifications belonging to other users.",
        )
    return _to_response(item)


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationResponse,
    summary="Mark a notification as read",
)
async def mark_notification_read(
    notification_id: UUID,
    actor: UserIdentity = Depends(get_actor_identity),
    notification_service: NotificationService = Depends(get_notification_service),
) -> NotificationResponse:
    """Mark a specific notification as read and record its ``readAt`` timestamp."""
    item = await notification_service.get_notification(notification_id)
    if actor.role != UserRole.ADMIN and item.user_id != actor.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Cannot modify notifications belonging to other users.",
        )
    updated = await notification_service.mark_as_read(notification_id)
    return _to_response(updated)
