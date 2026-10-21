"""Completed queue participation, independent of the current queue (A3 Module 6)."""

import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Literal


@dataclass(frozen=True)
class HistoryVisit:
    id: str
    user_id: str
    ticket: str
    service_id: str
    service_name: str
    joined_at: datetime
    finished_at: datetime
    outcome: Literal["served", "left"]
    waited_minutes: int


class HistoryStore:
    def __init__(self) -> None:
        self._visits: dict[str, HistoryVisit] = {}
        self._lock = threading.Lock()

    def record(self, *, entry_id: str, user_id: str, ticket: str, service_id: str,
               service_name: str, joined_at: datetime, finished_at: datetime,
               outcome: Literal["served", "left"]) -> HistoryVisit:
        visit = HistoryVisit(
            id=entry_id, user_id=user_id, ticket=ticket, service_id=service_id,
            service_name=service_name, joined_at=joined_at, finished_at=finished_at, outcome=outcome,
            waited_minutes=max(0, int((finished_at - joined_at).total_seconds() // 60)),
        )
        with self._lock:
            # Repeated completion reports must never add another row or change the outcome.
            return self._visits.setdefault(entry_id, visit)

    def for_user(self, user_id: str) -> list[HistoryVisit]:
        with self._lock:
            visits = [visit for visit in reversed(list(self._visits.values())) if visit.user_id == user_id]
        return sorted(visits, key=lambda visit: visit.finished_at, reverse=True)

    def reset(self) -> None:
        with self._lock:
            self._visits.clear()
