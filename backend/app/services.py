"""Service management (Module 2). Services are stored in the SQLite Service table
(service_store); each service's open/closed status is its Queue row's status."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr, StringConstraints, computed_field

from .auth.dependencies import get_current_user, require_admin
from .queue_store import QueueStatus, queues
from .service_store import DuplicateServiceNameError, Priority, ServiceRecord
from .wait_time import estimate_wait

# The same store the queues use, so services and queues share one database.
service_store = queues.services


class ServiceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Annotated[StrictStr, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    description: Annotated[StrictStr, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]
    expected_duration_minutes: Annotated[StrictInt, Field(alias="expectedDurationMinutes", ge=1, le=480)]
    priority: Priority


class Service(ServiceInput):
    id: str

    @computed_field
    @property
    def status(self) -> QueueStatus:
        return queues.status(self.id)

    @computed_field(alias="queueLength")
    @property
    def queue_length(self) -> int:
        return queues.waiting_count(self.id)

    @computed_field(alias="estimatedWaitMinutes")
    @property
    def estimated_wait_minutes(self) -> int:
        return estimate_wait(self.queue_length, self.expected_duration_minutes)


class StatusInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: QueueStatus


def _to_service(record: ServiceRecord) -> Service:
    return Service(
        id=record.id, name=record.name, description=record.description,
        expectedDurationMinutes=record.expected_duration_minutes, priority=record.priority,
    )


def reset_services() -> None:
    """Test helper: back to just the seeded services (clears queues, which reference services)."""
    service_store.reset()


router = APIRouter(prefix="/api/services", tags=["services"], dependencies=[Depends(get_current_user)])


def _get_service(service_id: str) -> ServiceRecord:
    service = service_store.get(service_id)
    if service is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Service not found.")
    return service


def _duplicate_name() -> HTTPException:
    return HTTPException(status.HTTP_409_CONFLICT, "A service with this name already exists.")


@router.get("")
def list_services() -> list[Service]:
    return [_to_service(record) for record in service_store.list()]


@router.post("", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
def create_service(body: ServiceInput) -> Service:
    try:
        record = service_store.create(body.name, body.description, body.expected_duration_minutes, body.priority)
    except DuplicateServiceNameError:
        raise _duplicate_name() from None
    # New services start closed until an admin opens their queue.
    queues.set_status(record.id, "closed")
    return _to_service(record)


@router.put("/{service_id}", dependencies=[Depends(require_admin)])
def update_service(service_id: str, body: ServiceInput) -> Service:
    _get_service(service_id)
    try:
        record = service_store.update(
            service_id, body.name, body.description, body.expected_duration_minutes, body.priority,
        )
    except DuplicateServiceNameError:
        raise _duplicate_name() from None
    if record is None:  # archived by someone else in the meantime
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Service not found.")
    return _to_service(record)


@router.patch("/{service_id}/status", dependencies=[Depends(require_admin)])
def set_service_status(service_id: str, body: StatusInput) -> Service:
    record = _get_service(service_id)
    queues.set_status(service_id, body.status)
    return _to_service(record)


@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_admin)])
def delete_service(service_id: str) -> Response:
    """Archives the service: it disappears from listings, its queue closes, and anyone
    waiting leaves. The row stays so past queue entries and history keep their service."""
    _get_service(service_id)
    service_store.archive(service_id)
    queues.remove_service(service_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
