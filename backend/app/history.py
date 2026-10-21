"""History comes from queue completion on the server, never from client claims."""

from datetime import datetime
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from .auth.dependencies import CurrentUser
from .queue_store import queues


class HistoryView(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, validate_by_name=True, from_attributes=True)

    id: str
    ticket: str
    service_id: str
    service_name: str
    joined_at: datetime
    finished_at: datetime
    outcome: Literal["served", "left"]
    waited_minutes: int


router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("")
def list_history(user: CurrentUser) -> list[HistoryView]:
    return [HistoryView.model_validate(visit) for visit in queues.history.for_user(user.id)]
