"""Completed queue participation stored in SQLite (Assignment 4, Part 6)."""

import sqlite3
from contextlib import nullcontext
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

from .database import Database, database_path


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


def _visit(row: sqlite3.Row) -> HistoryVisit:
    return HistoryVisit(
        id=row["entry_id"], user_id=row["user_id"], ticket=row["ticket"],
        service_id=row["service_id"], service_name=row["service_name"],
        joined_at=datetime.fromisoformat(row["joined_at"]), finished_at=datetime.fromisoformat(row["finished_at"]),
        outcome=row["outcome"], waited_minutes=row["waited_minutes"],
    )


class HistoryStore:
    def __init__(self, path: str | Path | None = None) -> None:
        self.database = Database(path if path is not None else database_path())

    def record(self, *, entry_id: str, user_id: str, ticket: str, service_id: str,
               service_name: str, joined_at: datetime, finished_at: datetime,
               outcome: Literal["served", "left"], connection: sqlite3.Connection | None = None) -> HistoryVisit:
        with (nullcontext(connection) if connection is not None else self.database.connect()) as conn:
            # One row per entry. Repeated completion reports preserve the original outcome.
            conn.execute(
                "INSERT INTO History (entry_id, user_id, ticket, service_id, service_name, joined_at, "
                "finished_at, outcome, waited_minutes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT (entry_id) DO NOTHING",
                (entry_id, user_id, ticket, service_id, service_name, joined_at.isoformat(), finished_at.isoformat(),
                 outcome, max(0, int((finished_at - joined_at).total_seconds() // 60))),
            )
            row = conn.execute("SELECT * FROM History WHERE entry_id = ? AND user_id = ?", (entry_id, user_id)).fetchone()
            if row is None:
                raise sqlite3.IntegrityError("History entry belongs to another account.")
            return _visit(row)

    def for_user(self, user_id: str) -> list[HistoryVisit]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM History WHERE user_id = ? ORDER BY julianday(finished_at) DESC, rowid DESC",
                (user_id,),
            ).fetchall()
            return [_visit(row) for row in rows]

    def reset(self) -> None:
        """Test helper; normal startup preserves all saved history."""
        with self.database.connect() as connection:
            connection.execute("DELETE FROM History")
