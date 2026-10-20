"""Queue management for A3 (Module 3): patients join and leave, admins view and serve.

Ordering lives in queue_store: urgent before normal, then arrival order.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from .auth.dependencies import CurrentUser, require_admin
from .queue_store import (
    AlreadyQueuedError, EntryPriority, EntryStatus, NotQueuedError, QueueEntry, UpdateKind, queues,
)
from .services import services
from .wait_time import estimate_wait


class _CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, validate_by_name=True)


class QueueUpdateView(_CamelModel):
    id: int
    kind: UpdateKind
    message: str
    at: datetime


class QueueEntryView(_CamelModel):
    id: str
    ticket: str
    service_id: str
    service_name: str
    email: str
    priority: EntryPriority
    status: EntryStatus
    # 1 means next. None once the entry is no longer waiting.
    position: int | None
    people_ahead: int
    estimated_wait_minutes: int
    expected_duration_minutes: int
    joined_at: datetime
    # Newest first.
    updates: list[QueueUpdateView]


class ServeNextResult(_CamelModel):
    served: QueueEntryView | None
    queue: list[QueueEntryView]


class PriorityInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    priority: EntryPriority


router = APIRouter(prefix="/api/queues", tags=["queues"])


def _view(entry: QueueEntry) -> QueueEntryView:
    # Use the service's current name and duration; fall back to the join-time copy if it was deleted.
    service = services.get(entry.service_id)
    duration = service.expected_duration_minutes if service else entry.duration_minutes
    people_ahead = entry.position - 1 if entry.position else 0
    return QueueEntryView(
        id=entry.id, ticket=entry.ticket, service_id=entry.service_id,
        service_name=service.name if service else entry.service_name, email=entry.email,
        priority=entry.priority, status=entry.status, position=entry.position, people_ahead=people_ahead,
        estimated_wait_minutes=estimate_wait(people_ahead, duration), expected_duration_minutes=duration,
        joined_at=entry.joined_at,
        updates=[QueueUpdateView(id=u.id, kind=u.kind, message=u.message, at=u.at) for u in reversed(entry.updates)],
    )


def _line(service_id: str) -> list[QueueEntryView]:
    return [_view(entry) for entry in queues.waiting(service_id)]


def _require_service(service_id: str) -> None:
    if service_id not in services:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Service not found.")


@router.get("/me")
def my_queue(user: CurrentUser) -> QueueEntryView | None:
    """The signed-in user's current or just-served entry, or null."""
    entry = queues.current_for(user.id)
    return _view(entry) if entry else None


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def leave_queue(user: CurrentUser) -> Response:
    try:
        queues.leave(user.id)
    except NotQueuedError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "You're not waiting in a queue.") from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{service_id}/join", status_code=status.HTTP_201_CREATED)
def join_queue(service_id: str, user: CurrentUser) -> QueueEntryView:
    _require_service(service_id)
    service = services[service_id]
    if service.status != "open":
        raise HTTPException(status.HTTP_409_CONFLICT, "This clinic queue is closed.")
    try:
        entry = queues.join(service.id, service.name, service.expected_duration_minutes, user.id, user.email)
    except AlreadyQueuedError:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "You already have an active queue. Leave it before joining another service.",
        ) from None
    return _view(entry)


@router.get("/{service_id}", dependencies=[Depends(require_admin)])
def view_queue(service_id: str) -> list[QueueEntryView]:
    """Everyone waiting for this service, front of the line first."""
    _require_service(service_id)
    return _line(service_id)


@router.post("/{service_id}/serve-next", dependencies=[Depends(require_admin)])
def serve_next(service_id: str) -> ServeNextResult:
    _require_service(service_id)
    served = queues.serve_next(service_id)
    return ServeNextResult(served=_view(served) if served else None, queue=_line(service_id))


@router.patch("/{service_id}/entries/{entry_id}", dependencies=[Depends(require_admin)])
def set_entry_priority(service_id: str, entry_id: str, body: PriorityInput) -> list[QueueEntryView]:
    """Marks a waiting patient urgent (moves ahead of normal entries) or back to normal."""
    _require_service(service_id)
    try:
        queues.set_priority(service_id, entry_id, body.priority)
    except KeyError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "That patient isn't waiting in this queue.") from None
    return _line(service_id)
