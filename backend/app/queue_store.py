"""In-memory queues for Module 3. Entries reset on restart, like accounts and services.

Each service has one line. Urgent entries go ahead of normal ones; within the same
priority, whoever arrived first is served first.
"""

import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import uuid4

EntryPriority = Literal["normal", "urgent"]
EntryStatus = Literal["waiting", "served", "left"]
UpdateKind = Literal["joined", "moved", "delayed", "almost-ready", "served"]

# Positions at or below this count as "almost ready" (matches the frontend).
ALMOST_READY_POSITION = 2
_PRIORITY_RANK: dict[EntryPriority, int] = {"urgent": 0, "normal": 1}


class AlreadyQueuedError(Exception):
    pass


class NotQueuedError(Exception):
    pass


@dataclass(frozen=True)
class QueueUpdate:
    id: int
    kind: UpdateKind
    message: str
    at: datetime


@dataclass
class QueueEntry:
    id: str
    service_id: str
    # Kept so an entry still has a name and duration if its service is deleted.
    service_name: str
    duration_minutes: int
    user_id: str
    email: str
    ticket: str
    # Increasing join counter: the arrival order, even when two clocks read the same.
    arrival: int
    joined_at: datetime
    priority: EntryPriority = "normal"
    status: EntryStatus = "waiting"
    # The last position announced to this entry; None once it stops waiting.
    position: int | None = None
    finished_at: datetime | None = None
    updates: list[QueueUpdate] = field(default_factory=list)

    def add_update(self, kind: UpdateKind, message: str, at: datetime) -> None:
        self.updates.append(QueueUpdate(len(self.updates) + 1, kind, message, at))


# Demo patients waiting on every start, so the seeded wait estimates stay 48 and 10 minutes.
_SEED_QUEUES = {
    "sick-visit": ("Sick Visit", 12, ["jordan.lee", "casey.kim", "morgan.diaz", "riley.chen"]),
    "flu-shot": ("Flu Shot", 5, ["avery.patel", "taylor.brooks"]),
}


class QueueStore:
    def __init__(self) -> None:
        self._entries: dict[str, QueueEntry] = {}
        self._arrivals = 0
        # FastAPI runs sync endpoints in a thread pool, so guard changes.
        self._lock = threading.Lock()

    def waiting(self, service_id: str) -> list[QueueEntry]:
        """The service's line, front first: urgent before normal, then arrival order."""
        entries = [e for e in self._entries.values() if e.service_id == service_id and e.status == "waiting"]
        return sorted(entries, key=lambda e: (_PRIORITY_RANK[e.priority], e.arrival))

    def waiting_count(self, service_id: str) -> int:
        return sum(1 for e in self._entries.values() if e.service_id == service_id and e.status == "waiting")

    def current_for(self, user_id: str) -> QueueEntry | None:
        """The user's latest entry. A served one stays visible until they join again."""
        latest = max((e for e in self._entries.values() if e.user_id == user_id), key=lambda e: e.arrival, default=None)
        return None if latest is None or latest.status == "left" else latest

    def join(self, service_id: str, service_name: str, duration_minutes: int, user_id: str, email: str,
             now: datetime | None = None) -> QueueEntry:
        now = now or datetime.now(UTC)
        with self._lock:
            current = self.current_for(user_id)
            if current and current.status == "waiting":
                raise AlreadyQueuedError(current.id)
            self._arrivals += 1
            entry = QueueEntry(
                id=str(uuid4()), service_id=service_id, service_name=service_name,
                duration_minutes=duration_minutes, user_id=user_id, email=email,
                ticket=f"{service_name[:1].upper()}-{self._arrivals:03d}", arrival=self._arrivals, joined_at=now,
            )
            self._entries[entry.id] = entry
            self._reposition(service_id, now)
            entry.add_update("joined", f"You joined the {service_name} queue at position {entry.position}.", now)
            return entry

    def leave(self, user_id: str, now: datetime | None = None) -> QueueEntry:
        now = now or datetime.now(UTC)
        with self._lock:
            entry = self.current_for(user_id)
            if entry is None or entry.status != "waiting":
                raise NotQueuedError(user_id)
            self._finish(entry, "left", now)
            self._reposition(entry.service_id, now)
            return entry

    def serve_next(self, service_id: str, now: datetime | None = None) -> QueueEntry | None:
        """Calls in the person at the front of the line. None if nobody is waiting."""
        now = now or datetime.now(UTC)
        with self._lock:
            line = self.waiting(service_id)
            if not line:
                return None
            entry = line[0]
            self._finish(entry, "served", now)
            entry.add_update("served", "You have been served. Thanks for visiting!", now)
            self._reposition(service_id, now)
            return entry

    def set_priority(self, service_id: str, entry_id: str, priority: EntryPriority,
                     now: datetime | None = None) -> QueueEntry:
        """Raises KeyError unless the entry is waiting in this service's line."""
        now = now or datetime.now(UTC)
        with self._lock:
            entry = self._entries.get(entry_id)
            if entry is None or entry.service_id != service_id or entry.status != "waiting":
                raise KeyError(entry_id)
            entry.priority = priority
            self._reposition(service_id, now)
            return entry

    def remove_service(self, service_id: str, now: datetime | None = None) -> None:
        """A deleted service can't serve anyone, so everyone still waiting leaves its line."""
        now = now or datetime.now(UTC)
        with self._lock:
            for entry in self.waiting(service_id):
                self._finish(entry, "left", now)

    def reset(self) -> None:
        """Clears every entry and re-adds the demo patients."""
        with self._lock:
            self._entries.clear()
            self._arrivals = 0
        now = datetime.now(UTC)
        for service_id, (name, duration, people) in _SEED_QUEUES.items():
            for index, person in enumerate(people):
                self.join(service_id, name, duration, f"demo-{person}", f"{person}@university.edu",
                          now - timedelta(minutes=(len(people) - index) * 6))

    @staticmethod
    def _finish(entry: QueueEntry, status: EntryStatus, now: datetime) -> None:
        entry.status = status
        entry.position = None
        entry.finished_at = now

    def _reposition(self, service_id: str, now: datetime) -> None:
        """Renumbers the line and tells everyone whose place changed."""
        for position, entry in enumerate(self.waiting(service_id), start=1):
            previous, entry.position = entry.position, position
            if previous is None or position == previous:
                continue
            if position > previous:
                entry.add_update("delayed", f"The queue order changed, so you moved back to position {position}.", now)
            elif position == 1:
                entry.add_update("moved", "You're next in line.", now)
            elif position <= ALMOST_READY_POSITION:
                entry.add_update("almost-ready", "You're almost up. Head to the clinic now.", now)
            else:
                entry.add_update("moved", f"You moved up to position {position}.", now)


queues = QueueStore()
queues.reset()
