from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Body

from app.api.dependencies import CurrentUser, DatabaseSession, Pagination
from app.schemas import (
    NotificationActionRequest,
    NotificationReadAllResponse,
    NotificationResponse,
    PaginatedResponse,
)
from app.services import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get(
    "",
    response_model=PaginatedResponse[NotificationResponse],
    summary="List global operational notifications",
)
def list_notifications(
    session: DatabaseSession,
    pagination: Pagination,
    _current_user: CurrentUser,
    unread_only: bool = False,
    include_resolved: bool = False,
) -> PaginatedResponse[NotificationResponse]:
    notifications, total = NotificationService(session).list_notifications(
        page=pagination.page,
        page_size=pagination.page_size,
        unread_only=unread_only,
        include_resolved=include_resolved,
    )
    return PaginatedResponse(
        items=[
            NotificationResponse.model_validate(notification)
            for notification in notifications
        ],
        page=pagination.page,
        page_size=pagination.page_size,
        total=total,
    )


@router.post(
    "/read-all",
    response_model=NotificationReadAllResponse,
    summary="Mark every active global notification as read",
)
def mark_all_notifications_as_read(
    session: DatabaseSession,
    _current_user: CurrentUser,
    _payload: Annotated[NotificationActionRequest | None, Body()] = None,
) -> NotificationReadAllResponse:
    updated_count = NotificationService(session).mark_all_active_as_read(
        now=datetime.now(UTC)
    )
    return NotificationReadAllResponse(updated_count=updated_count)


@router.post(
    "/{notification_id}/read",
    response_model=NotificationResponse,
    summary="Mark one global notification as read",
)
def mark_notification_as_read(
    notification_id: int,
    session: DatabaseSession,
    _current_user: CurrentUser,
    _payload: Annotated[NotificationActionRequest | None, Body()] = None,
) -> NotificationResponse:
    service = NotificationService(session)
    notification = service.mark_as_read(
        notification_id,
        now=datetime.now(UTC),
    )
    return NotificationResponse.model_validate(
        service.get_notification(notification.id)
    )
