"""Service management for A3. Records live in memory and reset on restart."""

from typing import Annotated, Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr, StringConstraints, computed_field

from .auth.dependencies import get_current_user, require_admin
from .queue_store import queues
from .wait_time import estimate_wait

Priority = Literal["low", "medium", "high"]
QueueStatus = Literal["open", "closed"]


class ServiceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Annotated[StrictStr, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    description: Annotated[StrictStr, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]
    expected_duration_minutes: Annotated[StrictInt, Field(alias="expectedDurationMinutes", ge=1, le=480)]
    priority: Priority


class Service(ServiceInput):
    id: str
    status: QueueStatus = "closed"

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


services: dict[str, Service] = {}


def reset_services() -> None:
    seeds = [
        Service(id="sick-visit", name="Sick Visit", description="Meet with clinic staff about a new health concern.",
                expectedDurationMinutes=12, priority="high", status="open"),
        Service(id="flu-shot", name="Flu Shot", description="Visit the campus clinic for your seasonal flu vaccination.",
                expectedDurationMinutes=5, priority="low", status="open"),
        Service(id="prescription-refill", name="Prescription Refill", description="Talk with clinic staff about an existing prescription.",
                expectedDurationMinutes=6, priority="medium", status="open"),
        Service(id="lab-work", name="Lab Work", description="Sample collection and testing requested by your clinic provider.",
                expectedDurationMinutes=10, priority="medium"),
    ]
    services.clear()
    services.update({service.id: service for service in seeds})


reset_services()
router = APIRouter(prefix="/api/services", tags=["services"], dependencies=[Depends(get_current_user)])


def _get_service(service_id: str) -> Service:
    service = services.get(service_id)
    if service is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Service not found.")
    return service


@router.get("")
def list_services() -> list[Service]:
    return list(services.values())


@router.post("", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
def create_service(body: ServiceInput) -> Service:
    service = Service(id=str(uuid4()), **body.model_dump(by_alias=True))
    services[service.id] = service
    return service


@router.put("/{service_id}", dependencies=[Depends(require_admin)])
def update_service(service_id: str, body: ServiceInput) -> Service:
    current = _get_service(service_id)
    updated = current.model_copy(update=body.model_dump())
    services[service_id] = updated
    return updated


@router.patch("/{service_id}/status", dependencies=[Depends(require_admin)])
def set_service_status(service_id: str, body: StatusInput) -> Service:
    updated = _get_service(service_id).model_copy(update={"status": body.status})
    services[service_id] = updated
    return updated


@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_admin)])
def delete_service(service_id: str) -> Response:
    _get_service(service_id)
    del services[service_id]
    queues.remove_service(service_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
