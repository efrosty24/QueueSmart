"""Authenticated notifications and read-state endpoints. No email/SMS delivery."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, StrictBool
from pydantic.alias_generators import to_camel

from .auth.dependencies import CurrentUser
from .notification_store import NotificationKind
from .queue_store import queues


class NotificationView(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, validate_by_name=True, from_attributes=True)

    id: str
    entry_id: str
    ticket: str
    service_id: str
    service_name: str
    kind: NotificationKind
    category: Literal["queue", "status"]
    title: str
    message: str
    at: datetime
    read: bool


class ReadInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    read: StrictBool


router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("")
def list_notifications(user: CurrentUser) -> list[NotificationView]:
    return [NotificationView.model_validate(item) for item in queues.notifications.for_user(user.id)]


@router.patch("/{notification_id}/read")
def mark_read(notification_id: UUID, body: ReadInput, user: CurrentUser) -> NotificationView:
    try:
        item = queues.notifications.mark_read(user.id, str(notification_id), body.read)
    except KeyError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Notification not found.") from None
    return NotificationView.model_validate(item)


@router.post("/read-all", status_code=status.HTTP_204_NO_CONTENT)
def mark_all_read(user: CurrentUser) -> Response:
    queues.notifications.mark_all_read(user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
