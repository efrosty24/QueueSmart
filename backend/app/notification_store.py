"""SQLite notifications and sent/viewed state (Assignment 4, Part 6)."""

import sqlite3
from contextlib import nullcontext
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal
from uuid import uuid4

from .database import Database, database_path

NotificationKind = Literal["joined", "moved", "delayed", "almost-ready", "served", "left"]
_TITLES: dict[NotificationKind, str] = {
    "joined": "Queue joined", "moved": "Position updated", "delayed": "Queue delayed",
    "almost-ready": "Almost ready", "served": "Visit completed", "left": "Left queue",
}


@dataclass(frozen=True)
class Notification:
    id: str
    user_id: str
    entry_id: str
    ticket: str
    service_id: str
    service_name: str
    kind: NotificationKind
    category: Literal["queue", "status"]
    title: str
    message: str
    at: datetime
    read: bool = False


def _notification(row: sqlite3.Row) -> Notification:
    return Notification(
        id=row["notification_id"], user_id=row["user_id"], entry_id=row["entry_id"],
        ticket=row["ticket"], service_id=row["service_id"], service_name=row["service_name"],
        kind=row["kind"], category=row["category"], title=row["title"], message=row["message"],
        at=datetime.fromisoformat(row["at"]), read=row["status"] == "viewed",
    )


class NotificationStore:
    def __init__(self, path: str | Path | None = None) -> None:
        self.database = Database(path if path is not None else database_path())

    def add(self, *, user_id: str, entry_id: str, ticket: str, service_id: str,
            service_name: str, kind: NotificationKind, message: str, at: datetime,
            event_key: str | None = None, connection: sqlite3.Connection | None = None) -> Notification:
        event_key = event_key or str(uuid4())
        # Queue mutations supply their transaction. Standalone calls own a connection.
        with (nullcontext(connection) if connection is not None else self.database.connect()) as conn:
            conn.execute(
                "INSERT INTO Notification (notification_id, user_id, entry_id, event_key, ticket, service_id, "
                "service_name, kind, category, title, message, at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT (entry_id, event_key) DO NOTHING",
                (str(uuid4()), user_id, entry_id, event_key, ticket, service_id, service_name, kind,
                 "queue" if kind in ("moved", "delayed") else "status", _TITLES[kind],
                 f"{service_name}: {message}", at.isoformat()),
            )
            row = conn.execute(
                "SELECT * FROM Notification WHERE entry_id = ? AND event_key = ? AND user_id = ?",
                (entry_id, event_key, user_id),
            ).fetchone()
            if row is None:
                raise sqlite3.IntegrityError("Notification entry belongs to another account.")
            return _notification(row)

    def for_user(self, user_id: str) -> list[Notification]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM Notification WHERE user_id = ? ORDER BY julianday(at) DESC, rowid DESC",
                (user_id,),
            ).fetchall()
            return [_notification(row) for row in rows]

    def mark_read(self, user_id: str, notification_id: str, read: bool) -> Notification:
        with self.database.connect() as connection:
            row = connection.execute(
                "UPDATE Notification SET status = ? WHERE notification_id = ? AND user_id = ? RETURNING *",
                ("viewed" if read else "sent", notification_id, user_id),
            ).fetchone()
            if row is None:
                raise KeyError(notification_id)
            return _notification(row)

    def mark_all_read(self, user_id: str) -> None:
        with self.database.connect() as connection:
            connection.execute("UPDATE Notification SET status = 'viewed' WHERE user_id = ? AND status = 'sent'", (user_id,))

    def reset(self) -> None:
        """Test helper; normal startup preserves all saved notifications."""
        with self.database.connect() as connection:
            connection.execute("DELETE FROM Notification")
