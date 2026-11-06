"""Persistent queues and queue entries in SQLite (Assignment 4).

Each service has one queue. Urgent entries go ahead of normal ones; within the same
priority, whoever arrived first is served first. Notifications and history are still
in memory; they are recorded only after the database change commits.
"""

import sqlite3
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from functools import partial
from pathlib import Path
from typing import Literal
from uuid import uuid4

from .auth.store import SEED_PASSWORD, EmailTakenError, UserStore
from .database import Database, database_path
from .history_store import HistoryStore
from .notification_store import NotificationKind, NotificationStore

EntryPriority = Literal["normal", "urgent"]
EntryStatus = Literal["waiting", "served", "left"]
QueueStatus = Literal["open", "closed"]
UpdateKind = Literal["joined", "moved", "delayed", "almost-ready", "served"]

# Positions at or below this count as "almost ready" (matches the frontend).
ALMOST_READY_POSITION = 2


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


@dataclass(frozen=True)
class QueueEntry:
    """A snapshot of one QueueEntry row. Fetch it again to see later changes."""

    id: str
    queue_id: str
    service_id: str
    # Kept so an entry still has a name and duration if its service is deleted.
    service_name: str
    duration_minutes: int
    user_id: str
    email: str
    ticket: str
    arrival: int
    joined_at: datetime
    priority: EntryPriority = "normal"
    status: EntryStatus = "waiting"
    # 1 is next in line. None once the entry stops waiting.
    position: int | None = None
    finished_at: datetime | None = None
    # Oldest first.
    updates: list[QueueUpdate] = field(default_factory=list)


# Queue availability for the seeded services (see services.reset_services).
_SEED_STATUSES: dict[str, QueueStatus] = {
    "sick-visit": "open", "flu-shot": "open", "prescription-refill": "open", "lab-work": "closed",
}
# Demo patients waiting on a new database, so the seeded wait estimates are 48 and 10 minutes.
_SEED_PATIENTS = {
    "sick-visit": ("Sick Visit", 12, ["jordan.lee", "casey.kim", "morgan.diaz", "riley.chen"]),
    "flu-shot": ("Flu Shot", 5, ["avery.patel", "taylor.brooks"]),
}

_ENTRY_QUERY = """
    SELECT e.*, q.service_id, c.email
    FROM QueueEntry AS e
    JOIN Queue AS q ON q.queue_id = e.queue_id
    JOIN UserCredentials AS c ON c.user_id = e.user_id
"""
# Urgent before normal, then arrival order.
_LINE_ORDER = "ORDER BY e.priority = 'normal', e.arrival"

Effects = list[Callable[[], object]]


def _time(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value is not None else None


def _load(connection: sqlite3.Connection, rows: list[sqlite3.Row]) -> list[QueueEntry]:
    """Builds entries from rows, fetching every entry's updates in one query."""
    updates: dict[str, list[QueueUpdate]] = {row["entry_id"]: [] for row in rows}
    if updates:
        placeholders = ", ".join("?" * len(updates))
        for row in connection.execute(
            f"SELECT * FROM QueueEntryUpdate WHERE entry_id IN ({placeholders}) ORDER BY update_id",
            tuple(updates),
        ):
            updates[row["entry_id"]].append(QueueUpdate(row["update_id"], row["kind"], row["message"], _time(row["at"])))
    return [
        QueueEntry(
            id=row["entry_id"], queue_id=row["queue_id"], service_id=row["service_id"],
            service_name=row["service_name"], duration_minutes=row["duration_minutes"],
            user_id=row["user_id"], email=row["email"], ticket=row["ticket"], arrival=row["arrival"],
            joined_at=_time(row["joined_at"]), priority=row["priority"], status=row["status"],
            position=row["position"], finished_at=_time(row["finished_at"]), updates=updates[row["entry_id"]],
        )
        for row in rows
    ]


class QueueStore:
    def __init__(self, path: str | Path | None = None) -> None:
        self.database = Database(path if path is not None else database_path())
        # FastAPI runs sync endpoints in a thread pool; BEGIN IMMEDIATE also guards other processes.
        self._lock = threading.Lock()
        self.notifications = NotificationStore()
        self.history = HistoryStore()

    # --- Reads ---------------------------------------------------------------

    def status(self, service_id: str) -> QueueStatus:
        """The service's queue availability. A service without a queue is closed."""
        with self.database.connect() as connection:
            row = connection.execute("SELECT status FROM Queue WHERE service_id = ?", (service_id,)).fetchone()
        return row["status"] if row else "closed"

    def get(self, entry_id: str) -> QueueEntry | None:
        with self.database.connect() as connection:
            return self._get(connection, entry_id)

    def waiting(self, service_id: str) -> list[QueueEntry]:
        """The service's line, front first."""
        with self.database.connect() as connection:
            return self._line(connection, "q.service_id = ?", service_id)

    def waiting_count(self, service_id: str) -> int:
        with self.database.connect() as connection:
            return connection.execute(
                "SELECT count(*) FROM QueueEntry AS e JOIN Queue AS q ON q.queue_id = e.queue_id "
                "WHERE q.service_id = ? AND e.status = 'waiting'",
                (service_id,),
            ).fetchone()[0]

    def current_for(self, user_id: str) -> QueueEntry | None:
        """The user's latest entry. A served one stays visible until they join again."""
        with self.database.connect() as connection:
            return self._current(connection, user_id)

    # --- Changes -------------------------------------------------------------

    def set_status(self, service_id: str, status: QueueStatus, now: datetime | None = None) -> None:
        """Opens or closes the service's queue, creating the queue if it has none yet."""
        with self._write() as (connection, _):
            self._save_queue(connection, service_id, status, now or datetime.now(UTC), replace=True)

    def join(self, service_id: str, service_name: str, duration_minutes: int, user_id: str,
             now: datetime | None = None) -> QueueEntry:
        now = now or datetime.now(UTC)
        entry_id = str(uuid4())
        with self._write() as (connection, effects):
            current = self._current(connection, user_id)
            if current and current.status == "waiting":
                raise AlreadyQueuedError(current.id)
            # Joining a service that has no queue row yet opens one for it.
            queue_id = self._save_queue(connection, service_id, "open", now, replace=False)
            arrival = connection.execute("SELECT coalesce(max(arrival), 0) + 1 FROM QueueEntry").fetchone()[0]
            # New entries are normal priority with the latest arrival, so they always join at the back.
            position = connection.execute(
                "SELECT count(*) + 1 FROM QueueEntry WHERE queue_id = ? AND status = 'waiting'", (queue_id,),
            ).fetchone()[0]
            connection.execute(
                "INSERT INTO QueueEntry (entry_id, queue_id, user_id, arrival, ticket, position, joined_at, "
                "service_name, duration_minutes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (entry_id, queue_id, user_id, arrival, f"{service_name[:1].upper()}-{arrival:03d}", position,
                 now.isoformat(), service_name, duration_minutes),
            )
            entry = self._get(connection, entry_id)
            self._add_update(connection, effects, entry, "joined",
                             f"You joined the {service_name} queue at position {position}.", now)
            if position <= ALMOST_READY_POSITION:
                self._notify(effects, entry, "almost-ready", "You're almost up. Head to the clinic now.", now)
            return self._get(connection, entry_id)

    def leave(self, user_id: str, now: datetime | None = None) -> QueueEntry:
        now = now or datetime.now(UTC)
        with self._write() as (connection, effects):
            entry = self._current(connection, user_id)
            if entry is None or entry.status != "waiting":
                raise NotQueuedError(user_id)
            self._finish(connection, effects, entry, "left", now)
            self._reposition(connection, effects, entry.queue_id, now)
            return self._get(connection, entry.id)

    def serve_next(self, service_id: str, now: datetime | None = None) -> QueueEntry | None:
        """Calls in the person at the front of the line. None if nobody is waiting."""
        now = now or datetime.now(UTC)
        with self._write() as (connection, effects):
            line = self._line(connection, "q.service_id = ?", service_id)
            if not line:
                return None
            entry = line[0]
            self._finish(connection, effects, entry, "served", now)
            self._add_update(connection, effects, entry, "served", "You have been served. Thanks for visiting!", now)
            self._reposition(connection, effects, entry.queue_id, now)
            return self._get(connection, entry.id)

    def set_priority(self, service_id: str, entry_id: str, priority: EntryPriority,
                     now: datetime | None = None) -> QueueEntry:
        """Raises KeyError unless the entry is waiting in this service's line."""
        now = now or datetime.now(UTC)
        with self._write() as (connection, effects):
            entry = self._get(connection, entry_id)
            if entry is None or entry.service_id != service_id or entry.status != "waiting":
                raise KeyError(entry_id)
            connection.execute("UPDATE QueueEntry SET priority = ? WHERE entry_id = ?", (priority, entry_id))
            self._reposition(connection, effects, entry.queue_id, now)
            return self._get(connection, entry_id)

    def remove_service(self, service_id: str, now: datetime | None = None) -> None:
        """A deleted service can't serve anyone: everyone waiting leaves and its queue closes.
        The queue row stays so past entries keep their service."""
        now = now or datetime.now(UTC)
        with self._write() as (connection, effects):
            for entry in self._line(connection, "q.service_id = ?", service_id):
                self._finish(connection, effects, entry, "left", now)
            connection.execute("UPDATE Queue SET status = 'closed' WHERE service_id = ?", (service_id,))

    def seed(self, now: datetime | None = None) -> None:
        """Adds missing seeded queues, plus demo patients on a database with no entries yet.
        Saved queues and entries are never overwritten."""
        now = now or datetime.now(UTC)
        with self._write() as (connection, _):
            for service_id, status in _SEED_STATUSES.items():
                self._save_queue(connection, service_id, status, now, replace=False)
            if connection.execute("SELECT 1 FROM QueueEntry LIMIT 1").fetchone():
                return
        accounts = UserStore(self.database.path)
        for service_id, (name, duration, people) in _SEED_PATIENTS.items():
            for index, person in enumerate(people):
                email = f"{person}@university.edu"
                try:
                    user = accounts.create(email, SEED_PASSWORD, person.replace(".", " ").title())
                except EmailTakenError:
                    user = accounts.get_by_email(email)
                self.join(service_id, name, duration, user.id, now - timedelta(minutes=(len(people) - index) * 6))

    def reset(self) -> None:
        """Test helper: deletes every queue (cascading to entries), then seeds again."""
        with self._write() as (connection, _):
            connection.execute("DELETE FROM Queue")
        self.notifications.reset()
        self.history.reset()
        self.seed()

    # --- Helpers -------------------------------------------------------------

    @contextmanager
    def _write(self) -> Iterator[tuple[sqlite3.Connection, Effects]]:
        """One write transaction. Notifications and history are recorded once it commits."""
        effects: Effects = []
        with self._lock, self.database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            yield connection, effects
        for effect in effects:
            effect()

    def _get(self, connection: sqlite3.Connection, entry_id: str) -> QueueEntry | None:
        rows = connection.execute(f"{_ENTRY_QUERY} WHERE e.entry_id = ?", (entry_id,)).fetchall()
        return _load(connection, rows)[0] if rows else None

    def _line(self, connection: sqlite3.Connection, condition: str, value: str) -> list[QueueEntry]:
        rows = connection.execute(
            f"{_ENTRY_QUERY} WHERE {condition} AND e.status = 'waiting' {_LINE_ORDER}", (value,),
        ).fetchall()
        return _load(connection, rows)

    def _current(self, connection: sqlite3.Connection, user_id: str) -> QueueEntry | None:
        rows = connection.execute(
            f"{_ENTRY_QUERY} WHERE e.user_id = ? ORDER BY e.arrival DESC LIMIT 1", (user_id,),
        ).fetchall()
        latest = _load(connection, rows)[0] if rows else None
        return None if latest is None or latest.status == "left" else latest

    def _save_queue(self, connection: sqlite3.Connection, service_id: str, status: QueueStatus,
                    now: datetime, *, replace: bool) -> str:
        """Creates the service's queue if missing (or updates its status when replace=True); returns its ID."""
        connection.execute(
            "INSERT INTO Queue (queue_id, service_id, status, created_at) VALUES (?, ?, ?, ?) "
            "ON CONFLICT (service_id) DO " + ("UPDATE SET status = excluded.status" if replace else "NOTHING"),
            (str(uuid4()), service_id, status, now.isoformat()),
        )
        return connection.execute("SELECT queue_id FROM Queue WHERE service_id = ?", (service_id,)).fetchone()[0]

    def _finish(self, connection: sqlite3.Connection, effects: Effects, entry: QueueEntry,
                status: Literal["served", "left"], now: datetime) -> None:
        connection.execute(
            "UPDATE QueueEntry SET status = ?, position = NULL, finished_at = ? WHERE entry_id = ?",
            (status, now.isoformat(), entry.id),
        )
        effects.append(partial(
            self.history.record, entry_id=entry.id, user_id=entry.user_id, ticket=entry.ticket,
            service_id=entry.service_id, service_name=entry.service_name,
            joined_at=entry.joined_at, finished_at=now, outcome=status,
        ))
        if status == "left":
            self._notify(effects, entry, "left", "You left the queue. Your visit is saved to History.", now)

    def _notify(self, effects: Effects, entry: QueueEntry, kind: NotificationKind, message: str,
                at: datetime) -> None:
        effects.append(partial(
            self.notifications.add, user_id=entry.user_id, entry_id=entry.id, ticket=entry.ticket,
            service_id=entry.service_id, service_name=entry.service_name, kind=kind, message=message, at=at,
        ))

    def _add_update(self, connection: sqlite3.Connection, effects: Effects, entry: QueueEntry,
                    kind: UpdateKind, message: str, at: datetime) -> None:
        connection.execute(
            "INSERT INTO QueueEntryUpdate (entry_id, update_id, kind, message, at) "
            "SELECT ?, coalesce(max(update_id), 0) + 1, ?, ?, ? FROM QueueEntryUpdate WHERE entry_id = ?",
            (entry.id, kind, message, at.isoformat(), entry.id),
        )
        self._notify(effects, entry, kind, message, at)

    def _reposition(self, connection: sqlite3.Connection, effects: Effects, queue_id: str, now: datetime) -> None:
        """Renumbers the line and tells everyone whose place changed."""
        for position, entry in enumerate(self._line(connection, "e.queue_id = ?", queue_id), start=1):
            previous = entry.position
            if position == previous:
                continue
            connection.execute("UPDATE QueueEntry SET position = ? WHERE entry_id = ?", (position, entry.id))
            if position > previous:
                self._add_update(connection, effects, entry, "delayed",
                                 f"The queue order changed, so you moved back to position {position}.", now)
            elif position == 1:
                self._add_update(connection, effects, entry, "moved", "You're next in line.", now)
                if previous > ALMOST_READY_POSITION:
                    self._notify(effects, entry, "almost-ready", "You're almost up. Head to the clinic now.", now)
            elif position <= ALMOST_READY_POSITION:
                self._add_update(connection, effects, entry, "almost-ready",
                                 "You're almost up. Head to the clinic now.", now)
            else:
                self._add_update(connection, effects, entry, "moved", f"You moved up to position {position}.", now)


queues = QueueStore()
queues.seed()
